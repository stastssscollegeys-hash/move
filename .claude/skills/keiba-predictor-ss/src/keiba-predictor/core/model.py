"""LightGBM予測モデル - オッズを入力に使わない設計"""
import os
import pickle
import yaml
import numpy as np
from typing import Dict, List, Optional

try:
    import lightgbm as lgb
    _LGB_AVAILABLE = True
except ImportError:
    _LGB_AVAILABLE = False
    print("[WARN] lightgbm がインストールされていません。ルールベース推定で動作します。")


# 絶対に特徴量に含めてはいけない列
_FORBIDDEN_FEATURES = frozenset([
    'win_odds', 'popularity', 'est_popularity', 'race_id', 'horse_id'
])


class PredictionModel:
    """
    LightGBM ベースの競馬予測モデル。
    オッズ・人気・ID 系を特徴量から完全に排除し、過学習を防ぐ設計。
    """

    MODEL_PATH: str = os.path.expanduser('~/.keiba/model.pkl')

    def __init__(self, config_path: Optional[str] = None) -> None:
        """LightGBM パラメータを YAML から読み込む。"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'weights.yaml'
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)  # yaml.load() は禁止
        self.lgb_params: Dict = config['lightgbm']
        self.model_win: Optional[object] = None   # 1着予測モデル
        self.model_show: Optional[object] = None  # 3着以内予測モデル

    # ------------------------------------------------------------------
    # 特徴量構築
    # ------------------------------------------------------------------

    def build_features(
        self,
        horse_data: Dict,
        race_data: Dict,
        engines: Dict,
    ) -> Dict:
        """全エンジンから特徴量を統合し、禁止特徴量を除外する。

        Parameters
        ----------
        horse_data:
            馬個別データ。
        race_data:
            レースデータ（距離・コース種別・馬場状態等）。
        engines:
            ``engine.get_features(horse_data, race_data)`` を実装したエンジン辞書。

        Returns
        -------
        features:
            禁止特徴量が除去されたフラットな特徴量辞書。
        """
        features: Dict = {}

        for engine_name, engine in engines.items():
            try:
                engine_features = engine.get_features(horse_data, race_data)
                features.update(engine_features)
            except Exception as exc:
                print(f"[WARN] エンジン '{engine_name}' の特徴量取得に失敗: {exc}")

        # 禁止特徴量の除去
        removed = []
        for key in list(features.keys()):
            if key in _FORBIDDEN_FEATURES:
                del features[key]
                removed.append(key)
        if removed:
            print(f"[WARN] 禁止特徴量を除外しました: {removed}")

        return features

    # ------------------------------------------------------------------
    # 推定
    # ------------------------------------------------------------------

    def predict(self, features_list: List[Dict]) -> List[Dict]:
        """推定勝率・複勝率を算出する。

        Parameters
        ----------
        features_list:
            馬ごとの特徴量辞書リスト。各辞書に ``post``（枠番/馬番）と
            ``name``（馬名）が含まれていることを推奨。

        Returns
        -------
        List[Dict]
            ``[{post, name, win_prob, show_prob}, ...]``
            勝率の合計が 100% になるよう正規化済み。
        """
        if not _LGB_AVAILABLE or self.model_win is None:
            return self._rule_based_predict(features_list)

        # --- LightGBM 推定 ---
        feature_keys = sorted(
            k for k in features_list[0].keys()
            if k not in ('post', 'name') and k not in _FORBIDDEN_FEATURES
        )
        X = np.array(
            [[row.get(k, 0.0) for k in feature_keys] for row in features_list],
            dtype=np.float32,
        )

        win_probs_raw: np.ndarray = self.model_win.predict(X)
        show_probs_raw: np.ndarray = self.model_show.predict(X)

        # 勝率を正規化（合計 100%）
        win_total = win_probs_raw.sum()
        win_probs = (win_probs_raw / win_total) if win_total > 0 else win_probs_raw

        # 複勝率は 0〜1 にクリップ
        show_probs = np.clip(show_probs_raw, 0.0, 1.0)

        results = []
        for i, row in enumerate(features_list):
            results.append({
                'post': row.get('post', i + 1),
                'name': row.get('name', f'馬{i + 1}'),
                'win_prob': float(win_probs[i]),
                'show_prob': float(show_probs[i]),
            })

        return sorted(results, key=lambda x: x['win_prob'], reverse=True)

    def _rule_based_predict(self, features_list: List[Dict]) -> List[Dict]:
        """モデル学習前のルールベース推定。

        重みYAML の feature_weights に基づいてスコアを算出し、
        ソフトマックスで勝率に変換する。
        """
        # スコア構成: 過去実績重視 + 確定要素
        # 分析結果: エンジンスコアは的中/外れを区別できない
        # → 過去走の安定性（確定事実）と市場評価（人気）を重視
        SCORE_KEYS = [
            ('past_performance_score', 0.35),   # 能力指数（最重要）
            ('course_fitness_score', 0.20),     # コース適性（CR値+実績）
            ('jockey_score', 0.10),
            ('bloodline_course_score_norm', 0.10),
            ('condition_score', 0.10),
            ('track_bias_score', 0.08),
            ('trainer_score', 0.07),
        ]

        raw_scores = []
        for row in features_list:
            score = sum(
                row.get(key, 0.0) * weight for key, weight in SCORE_KEYS
            )
            # 確定要素ボーナス
            score += row.get('cr_tb_bonus', 0.0) * 0.03     # CR乖離（効果小さいため縮小）
            score += row.get('close_finish_bonus', 0.0) * 0.08
            score += row.get('career_win_rate', 0.0) * 10.0
            score += row.get('interval_bonus', 0.0) * 0.06
            # PDCA20: 基本情報は消去法で反映。スコアには最小限のみ
            basic = row.get('basic_info_bonus', 0.0)
            if basic < -5:  # 大きなペナルティのみ反映
                score += basic * 0.05

            # PDCA21+24: 荒れ度を先に取得（以降の全ブロックで使用）
            upset = row.get('upset_score', 0)

            # PDCA22+24: smartrc直接活用（上がり3F+距離適性+馬体重安定）
            # PDCA24: 荒れるレースでは距離適性・CR値の重みを上げる
            agari_score = row.get('agari_rank_score', 0)
            ds_bonus = row.get('distance_fit_bonus', 0)
            ws_bonus = row.get('weight_stability_bonus', 0)

            if upset >= 3:
                # 荒れるレース: 距離適性と馬体重安定をより重視
                score += agari_score * 0.6  # 上がりは控えめに
                score += ds_bonus * 1.0     # 距離適性を2倍に強化
                score += ws_bonus * 0.6     # 馬体重安定も強化
            else:
                score += agari_score * 0.8
                score += ds_bonus * 0.5
                score += ws_bonus * 0.4

            # PDCA24+25: 荒れるレースでCR値ボーナス強化（上限抑制済み）
            # PDCA24: 胎内川で効果あり。PDCA25: エプソムCで過大評価→上限3に抑制
            cr_raw = row.get('cr_raw', 0)
            if upset >= 3 and cr_raw >= 5:
                score += min(cr_raw * 0.3, 3)  # CR5以上で最大+3点（5→3に抑制）

            # PDCA26: 昇降級ボーナス（リサーチ: 昇級初戦は回収率67%、降級は11%勝率）
            # old_pr: A=大幅昇級, B=昇級, C=同クラス, D=降級
            old_pr = row.get('old_pr', 'C')
            if old_pr == 'A':
                score -= 5  # 大幅昇級: 複勝率最低、特にダート短距離で危険
            elif old_pr == 'B':
                score -= 2  # 昇級: 過剰人気になりやすい、割引
            elif old_pr == 'D':
                score += 4  # 降級: 格上からの参戦、能力上位

            # PDCA26: テンの相対スコア（先行力の指標）
            # リサーチ: 逃げ馬回収率171%、先行馬が最も安定
            ten_rank = row.get('ten_has_rank_score', 0)
            score += ten_rank * 0.5  # テンが速い馬にボーナス

            # PDCA26: テン+上がり二刀流ボーナス
            # リサーチ: 先行+上がり速い = 最も儲けやすい馬
            if ten_rank >= 6 and agari_score >= 6:
                score += 4  # 二刀流ボーナス（前半も後半も速い）

            # PDCA29: ローテーション実績ボーナス
            # 同種ローテ（短縮/同距離/延長）での過去好走実績
            rota_record = row.get('rota_track_record', 0)
            score += rota_record  # 最大+5点

            # PDCA30: コース別枠順スコア
            # リサーチ: 中山1600m内枠+5, 外枠-4 など競馬場×距離で大きな差
            gate_sc = row.get('gate_score', 0)
            score += gate_sc

            # PDCA31: 短距離専用ロジック
            # リサーチ: 短距離は逃げ有利(回収率210%), 上がりより前半スピードが重要
            race_dist = row.get('race_distance', 0)
            try:
                race_dist_v = int(race_dist)
            except (ValueError, TypeError):
                race_dist_v = 0

            # PDCA23: 上がり3F+先行脚質の組み合わせボーナス
            # リサーチ: 上がり最速+逃げ先行→単勝回収率95%（上がりだけなら78%）
            running_style = row.get('running_style', '')

            # PDCA32: ローカル場（小回り）での先行有利ボーナス
            # リサーチ: 福島60.3%, 新潟61.9%, 小倉55% — 小回りは先行有利が顕著
            is_local = row.get('is_local_venue', 0)
            if is_local and race_dist_v > 1400:
                # ローカル場の中長距離: 先行有利が強い
                if running_style in ('逃げ', '先行'):
                    score += 3  # 小回りは先行有利
                elif running_style == '追い込み':
                    score -= 2  # 小回りで追い込みは届きにくい

            # PDCA34: 中京の直線長さ+急坂を考慮
            # リサーチ: 中京は直線410.7m（JRA2位）+高低差3.4m
            # 先行馬が急坂で止まりやすく、差し追込が他場より有力
            # 3月データ: 中京62.5%（阪神72.0%, 中山72.5%比で-10pt）
            race_venue = row.get('race_venue', '')
            if race_venue == '中京' and race_dist_v > 1400:
                if running_style == '逃げ':
                    score -= 2  # 中京では逃げの優位性が低い（急坂で止まる）
                elif running_style in ('差し', '追い込み'):
                    score += 2  # 中京では差しが届く（直線長い）

            if race_dist_v <= 1400:
                # ── 短距離専用ロジック ──
                # 逃げ・先行に大幅ボーナス（短距離は前残り圧倒的）
                if running_style == '逃げ':
                    score += 6  # 逃げ: 単勝回収率210%
                elif running_style == '先行':
                    score += 3  # 先行: 回収率113%
                elif running_style == '追い込み':
                    score -= 3  # 追い込み: 短距離では届かない

                # 短距離では上がり3Fの重みを下げる（前半スピードが重要）
                # agari_scoreは既に加算済みなので、短距離では差分で減らす
                if agari_score >= 7:
                    score -= 2  # 上がり上位の重みを下げる（短距離では過大評価）

                # テン3Fの重みを上げる（短距離では前半スピードが重要）
                ten_rank = row.get('ten_has_rank_score', 0)
                score += ten_rank * 0.8  # 短距離ではテンの重みを倍増

            else:
                # ── 中長距離のロジック（従来通り）──
                # PDCA28: 展開予測 — 先行争い激化フラグ
                pace_pressure = row.get('pace_pressure', 0)
                if pace_pressure >= 2:
                    if running_style == '逃げ':
                        score -= 4
                    elif running_style == '先行':
                        score -= 1
                    elif running_style in ('差し', '追い込み'):
                        score += 2

            if agari_score >= 7 and running_style in ('逃げ', '先行'):
                score += 5  # 上がり上位+先行 = 強い組み合わせ

            # PDCA23: 5-7番人気の穴馬検出強化
            # リサーチ: 5番26.9%, 6番21.1%, 7番16.3%で3着内に来る
            # 特に多頭数(13頭以上)で6番人気の回収率が最高(81.8%)
            # PDCA27: 穴馬押し上げ強化は逆効果（58.3%に悪化）。PDCA23の値が最適
            num_horses = len(features_list)
            _est_pop_23 = row.get('est_popularity')
            if _est_pop_23 is not None:
                try:
                    pop_v = int(_est_pop_23)
                    # 上がり上位+距離適性ありの中穴馬にボーナス
                    if 5 <= pop_v <= 7:
                        ds_bonus = row.get('distance_fit_bonus', 0)
                        if agari_score >= 5 and ds_bonus >= 3:
                            score += 4  # 上がり+距離適性の中穴
                        elif agari_score >= 5 or ds_bonus >= 3:
                            score += 2  # どちらか一方
                        # 多頭数での中穴ボーナス
                        if num_horses >= 13:
                            score += 1
                except (ValueError, TypeError):
                    pass

            # PDCA17: 前走好走は逆指標（50850頭統計: 好走50% < 凡走54%）
            # 前走で人気以上に好走した馬は「出し切った」可能性がある
            # → 微ペナルティを与える（人気馬には適用しない）
            past_perf_raw = row.get('past_performance_score', 50)
            est_pop_raw = row.get('est_popularity')
            if est_pop_raw is not None and past_perf_raw > 70:
                try:
                    pop_v = int(est_pop_raw)
                    if pop_v >= 4:  # 4番人気以下で前走好走 → 反動リスク
                        score -= 2
                except (ValueError, TypeError):
                    pass

            # === PDCA14: 5085頭統計 + 巻き返しパターン ===
            # 発見: 1番人気+前走凡走(人気以下) = 複勝率85%
            # 発見: 人気馬+前走凡走 = 巻き返す確率が非常に高い
            est_pop = row.get('est_popularity')
            past_perf = row.get('past_performance_score', 50)

            # PDCA21: 荒れ度に応じて人気ボーナスを動的調整
            # （upsetは176行目で取得済み）

            if est_pop is not None:
                try:
                    pop_val = int(est_pop)

                    # 荒れ度による人気ボーナス倍率
                    # 0-2: 堅い→通常, 3-5: やや荒れ→減額, 6+: 大荒れ→大幅減額
                    # PDCA27: 0.4→0.2/0.3は悪化。0.4が最適バランス
                    if upset >= 6:
                        pop_mult = 0.4   # 大荒れ: 人気ボーナス60%カット
                    elif upset >= 3:
                        pop_mult = 0.7   # やや荒れ: 30%カット
                    else:
                        pop_mult = 1.0   # 堅い: 通常

                    # PDCA33: 馬場悪化時は人気馬の信頼度をさらに下げる
                    # リサーチ: 荒れ+馬場悪化(稍重以上)+1-2人気→大敗76件の共通パターン
                    track_cond = row.get('track_condition', '')
                    if track_cond in ('稍重', '重', '不良'):
                        pop_mult *= 0.8  # 馬場悪化で人気ボーナスさらに20%減

                    # PDCA34: ダート×荒れ度の追加割引
                    # リサーチ: ダートはクラスが上がるほど荒れやすい
                    # + 砂被り/揉まれリスクで1-2人気が大敗するパターン多発
                    # 3月データ: 芝74.2% vs ダート65.3%（-8.9pt）
                    race_surface = row.get('race_surface', '')
                    if 'ダート' in race_surface and upset >= 3:
                        pop_mult *= 0.85  # ダート荒れで追加15%減

                    # 人気ボーナス（PDCA13最適値 × 荒れ度調整）
                    if pop_val == 1:
                        score += 12 * pop_mult
                    elif pop_val == 2:
                        score += 8 * pop_mult
                    elif pop_val == 3:
                        score += 5 * pop_mult
                    elif pop_val <= 5:
                        score += 2 * pop_mult
                    # PDCA30: 6番人気以下の割引を統計データに合わせて強化
                    # リサーチ: 6番人気複勝率22%, 7番18%, 8番14%, 10番以下9%
                    # 以前のPDCA21ボーナス(+3)は穴馬過大評価の原因→削除
                    elif pop_val in (6, 7):
                        score *= 0.80   # 複勝率18-22%帯: 20%割引
                    elif pop_val in (8, 9, 10):
                        score *= 0.65   # 複勝率9-14%帯: 35%割引
                    elif pop_val >= 11:
                        score *= 0.50   # 複勝率9%以下: 50%割引

                    # PDCA34: ダート1800m多頭数の揉まれリスク補正
                    # リサーチ: ダート1800mは1コーナーまで距離が短く、
                    # 多頭数(14頭+)で外枠の人気馬が揉まれて大敗するパターン多発
                    # 3月外れ: リザードアイランド1人気→12着, ルミテュット1人気→6着 等
                    race_surface = row.get('race_surface', '')
                    if 'ダート' in race_surface and race_dist_v >= 1700 and race_dist_v <= 1900:
                        if num_horses >= 14 and pop_val <= 3:
                            score -= 2  # 多頭数ダート中距離は揉まれリスク大
                except (ValueError, TypeError):
                    pass

            raw_scores.append(score)

        # ソフトマックスで確率に変換（温度パラメータで分散を調整）
        # 温度が高い → 確率が均等に近づく（穴馬の勝率が上がる）
        # 温度が低い → 本命に集中する
        # 適度な分散: 本命30-40%、対抗15-25%、穴5-10%を目標
        temperature = 8.0
        arr = np.array(raw_scores, dtype=np.float64)
        arr = arr / temperature
        arr -= arr.max()  # オーバーフロー防止
        exp_arr = np.exp(arr)
        win_probs = exp_arr / exp_arr.sum()

        # PDCA30: 複勝率を人気帯別の統計的上限でキャリブレーション
        # リサーチ: win_probの単純スケールでは不人気馬のshow_probが過大評価される
        # 人気帯別の実績複勝率を上限として適用
        _POP_SHOW_CAP = {
            1: 0.64, 2: 0.53, 3: 0.43, 4: 0.35, 5: 0.29,
            6: 0.22, 7: 0.18, 8: 0.14, 9: 0.11, 10: 0.09,
        }
        num_horses = len(features_list)
        base_show_rate = 3.0 / max(num_horses, 3)
        show_probs = np.clip(win_probs * (1.0 / base_show_rate), 0.0, 0.99)

        # 人気帯別上限を適用（過大評価を防止）
        for i, row in enumerate(features_list):
            est_pop = row.get('est_popularity')
            if est_pop is not None:
                try:
                    pop_v = int(est_pop)
                    cap = _POP_SHOW_CAP.get(pop_v, 0.08 if pop_v > 10 else 0.64)
                    show_probs[i] = min(show_probs[i], cap)
                except (ValueError, TypeError):
                    pass

        results = []
        for i, row in enumerate(features_list):
            results.append({
                'post': row.get('post', i + 1),
                'name': row.get('name', f'馬{i + 1}'),
                'win_prob': float(win_probs[i]),
                'show_prob': float(show_probs[i]),
            })

        return sorted(results, key=lambda x: x['win_prob'], reverse=True)

    # ------------------------------------------------------------------
    # 学習
    # ------------------------------------------------------------------

    def train(
        self,
        X: 'np.ndarray',
        y_win: 'np.ndarray',
        y_show: 'np.ndarray',
    ) -> None:
        """LightGBM モデルを学習する。

        Parameters
        ----------
        X:
            特徴量行列（禁止特徴量を事前に除去しておくこと）。
        y_win:
            1着ラベル（0/1）。
        y_show:
            3着以内ラベル（0/1）。
        """
        if not _LGB_AVAILABLE:
            raise RuntimeError("lightgbm がインストールされていません。")

        # ID系特徴量が上位に来ていないか確認するためのコールバック
        def _feature_importance_check(env: 'lgb.callback.CallbackEnv') -> None:
            if env.iteration % 100 == 0:
                imp = env.model.feature_importance(importance_type='gain')
                feat_names = env.model.feature_name()
                top_feats = sorted(
                    zip(feat_names, imp), key=lambda x: x[1], reverse=True
                )[:5]
                for name, gain in top_feats:
                    if any(bad in name for bad in ('id', 'popularity', 'odds')):
                        print(
                            f"[ALERT] 禁止特徴量候補 '{name}' が重要度上位に出現 "
                            f"(iteration={env.iteration})"
                        )

        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_win_train, y_win_val = y_win[:split], y_win[split:]
        y_show_train, y_show_val = y_show[:split], y_show[split:]

        # 1着モデル
        print("[INFO] 1着モデルを学習中...")
        ds_train_win = lgb.Dataset(X_train, label=y_win_train)
        ds_val_win = lgb.Dataset(X_val, label=y_win_val, reference=ds_train_win)
        self.model_win = lgb.train(
            params={**self.lgb_params, 'objective': 'binary', 'metric': 'auc'},
            train_set=ds_train_win,
            valid_sets=[ds_val_win],
            callbacks=[
                lgb.early_stopping(self.lgb_params.get('early_stopping_rounds', 50)),
                lgb.log_evaluation(100),
                _feature_importance_check,
            ],
        )

        # 複勝モデル（3着以内）
        print("[INFO] 複勝モデルを学習中...")
        ds_train_show = lgb.Dataset(X_train, label=y_show_train)
        ds_val_show = lgb.Dataset(X_val, label=y_show_val, reference=ds_train_show)
        self.model_show = lgb.train(
            params={**self.lgb_params, 'objective': 'binary', 'metric': 'auc'},
            train_set=ds_train_show,
            valid_sets=[ds_val_show],
            callbacks=[
                lgb.early_stopping(self.lgb_params.get('early_stopping_rounds', 50)),
                lgb.log_evaluation(100),
            ],
        )

        # 特徴量重要度を出力
        self._log_feature_importance()

    def _log_feature_importance(self, top_n: int = 20) -> None:
        """特徴量重要度を降順で表示し、ID系が上位にいれば警告する。"""
        if self.model_win is None:
            return
        imp = self.model_win.feature_importance(importance_type='gain')
        feat_names = self.model_win.feature_name()
        ranked = sorted(zip(feat_names, imp), key=lambda x: x[1], reverse=True)
        print(f"\n[INFO] 特徴量重要度 TOP{top_n}（1着モデル）")
        for name, gain in ranked[:top_n]:
            flag = " ← [ALERT] ID系/禁止特徴量の疑い" if any(
                bad in name for bad in ('id', 'popularity', 'odds')
            ) else ''
            print(f"  {name:<35s}: {gain:.1f}{flag}")

    # ------------------------------------------------------------------
    # 保存・読み込み
    # ------------------------------------------------------------------

    def save(self) -> None:
        """モデルを ``~/.keiba/model.pkl`` に保存する。"""
        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
        with open(self.MODEL_PATH, 'wb') as f:
            pickle.dump({'model_win': self.model_win, 'model_show': self.model_show}, f)
        print(f"[INFO] モデルを保存しました: {self.MODEL_PATH}")

    def load(self) -> bool:
        """保存済みモデルを読み込む。

        Returns
        -------
        bool
            読み込みに成功した場合 True。
        """
        if not os.path.exists(self.MODEL_PATH):
            print(f"[INFO] 保存済みモデルが見つかりません: {self.MODEL_PATH}")
            return False
        try:
            with open(self.MODEL_PATH, 'rb') as f:
                data = pickle.load(f)
            self.model_win = data.get('model_win')
            self.model_show = data.get('model_show')
            print(f"[INFO] モデルを読み込みました: {self.MODEL_PATH}")
            return True
        except Exception as exc:
            print(f"[WARN] モデルの読み込みに失敗しました: {exc}")
            return False
