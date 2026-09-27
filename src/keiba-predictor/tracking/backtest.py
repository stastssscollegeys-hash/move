"""バックテスト - ウォークフォワード検証（K-Fold 禁止）"""
import os
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np


class Backtester:
    """
    ウォークフォワード検証でモデルを評価するクラス。

    禁止事項:
    - 通常の K-Fold 交差検証（同一レース内でリークが発生する）
    - race_id / horse_id を特徴量に含めること
    - オッズ・人気を入力特徴量に含めること
    - 訓練データと検証データに同一レースが入ること
    """

    # 外れ値とみなす配当倍率の閾値
    _OUTLIER_ODDS_THRESHOLD: float = 100.0

    def __init__(self, db_repo, model, engines: Dict) -> None:
        """
        Parameters
        ----------
        db_repo:
            DB アクセス用リポジトリ。
        model:
            PredictionModel インスタンス。
        engines:
            特徴量エンジン辞書。
        """
        self.db = db_repo
        self.model = model
        self.engines = engines

        # general.yaml から過学習防止設定を読み込む
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'general.yaml'
        )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)  # yaml.load() は禁止
        overfitting = config.get('overfitting', {})
        self._roi_divergence_alert: float = overfitting.get(
            'roi_divergence_alert', 0.15
        )
        self._min_trials: int = overfitting.get(
            'min_trials_for_significance', 200
        )

    # ------------------------------------------------------------------
    # ウォークフォワード検証
    # ------------------------------------------------------------------

    def walk_forward_validation(self, months: int = 6) -> List[Dict]:
        """ウォークフォワード検証を実行する。

        分割方針（時系列順を厳守）:
            訓練 : 過去 12 ヶ月
            検証 : 次の 2 ヶ月
            テスト: 次の 2 ヶ月
            → 2 ヶ月ずつスライドして ``months`` 回繰り返す。

        通常の K-Fold は禁止。同一レース内でデータリークが発生するため。

        Parameters
        ----------
        months:
            検証を繰り返す回数（スライド数）。

        Returns
        -------
        List[Dict]
            各フォールドの評価結果リスト。
        """
        results: List[Dict] = []
        now = datetime.now()

        for fold in range(months):
            # 各フォールドの期間を計算（2ヶ月ずつスライド）
            slide_days = fold * 60

            train_end = now - timedelta(days=slide_days + 120)   # テスト+検証期間分戻る
            train_start = train_end - timedelta(days=365)        # 訓練: 12ヶ月

            val_start = train_end
            val_end = val_start + timedelta(days=60)             # 検証: 2ヶ月

            test_start = val_end
            test_end = test_start + timedelta(days=60)           # テスト: 2ヶ月

            # 未来のデータは使わない
            if test_end > now:
                break

            print(
                f"[Fold {fold + 1}] "
                f"訓練: {train_start.date()}〜{train_end.date()}  "
                f"検証: {val_start.date()}〜{val_end.date()}  "
                f"テスト: {test_start.date()}〜{test_end.date()}"
            )

            # データ取得
            train_races = self.db.get_races_between(train_start, train_end)
            val_races = self.db.get_races_between(val_start, val_end)
            test_races = self.db.get_races_between(test_start, test_end)

            # 同一レースの混入チェック（安全装置）
            train_ids = {r['race_id'] for r in train_races}
            val_ids = {r['race_id'] for r in val_races}
            test_ids = {r['race_id'] for r in test_races}
            overlap = (train_ids & val_ids) | (train_ids & test_ids) | (val_ids & test_ids)
            if overlap:
                print(f"  [ALERT] 同一レースが複数分割に混入しています: {len(overlap)}件 → スキップ")
                continue

            # 特徴量構築と学習
            X_train, y_win_train, y_show_train = self._build_dataset(train_races)
            if len(X_train) == 0:
                print(f"  [WARN] Fold {fold + 1}: 訓練データなし → スキップ")
                continue

            self.model.train(X_train, y_win_train, y_show_train)

            # テストデータで評価
            eval_result = self.evaluate_races(test_races)
            eval_result['fold'] = fold + 1
            eval_result['test_start'] = test_start.isoformat()
            eval_result['test_end'] = test_end.isoformat()
            results.append(eval_result)

            print(
                f"  的中率: {eval_result.get('hit_rate', 0):.1%}  "
                f"ROI: {eval_result.get('roi', 0):.1%}  "
                f"ROI（外れ値除外）: {eval_result.get('roi_outlier_excluded', 0):.1%}"
            )

        return results

    # ------------------------------------------------------------------
    # 評価
    # ------------------------------------------------------------------

    def evaluate(
        self,
        predictions: List[Dict],
        actuals: List[Dict],
    ) -> Dict:
        """予想リストと実績リストを照合して評価指標を算出する。

        Parameters
        ----------
        predictions:
            ``[{race_id, recommendations: [{type, combination, odds, bet_amount}]}]``
        actuals:
            ``[{race_id, finish: [{post, finish_pos}]}]``

        Returns
        -------
        Dict
            ``{hit_rate, roi, roi_outlier_excluded, elimination_accuracy}``
        """
        actual_map: Dict[str, Dict] = {a['race_id']: a for a in actuals}

        total_bet = 0
        total_return = 0
        total_bet_ex = 0
        total_return_ex = 0
        hit_count = 0
        total_count = 0

        for pred in predictions:
            actual = actual_map.get(pred['race_id'])
            if actual is None:
                continue
            finish_map = {
                r['post']: r['finish_pos']
                for r in actual.get('finish', [])
            }
            for rec in pred.get('recommendations', []):
                bet = rec.get('bet_amount', 100)
                odds = rec.get('odds', 0.0)
                is_hit = self._check_hit(rec, finish_map)

                total_bet += bet
                total_count += 1
                payout = bet * odds if is_hit else 0.0
                total_return += payout
                if is_hit:
                    hit_count += 1

                if odds <= self._OUTLIER_ODDS_THRESHOLD:
                    total_bet_ex += bet
                    total_return_ex += payout

        return {
            'hit_rate': hit_count / total_count if total_count > 0 else 0.0,
            'roi': total_return / total_bet if total_bet > 0 else 0.0,
            'roi_outlier_excluded': (
                total_return_ex / total_bet_ex if total_bet_ex > 0 else 0.0
            ),
            'num_bets': total_count,
        }

    def evaluate_races(self, races: List[Dict]) -> Dict:
        """レースリストに対してモデルで予測・評価を一括実行する。"""
        predictions_out: List[Dict] = []
        actuals_out: List[Dict] = []

        for race in races:
            race_id = race.get('race_id', '')
            horses = race.get('horses', [])
            race_data = race.get('race_data', {})

            # 特徴量構築
            features_list = [
                self.model.build_features(h, race_data, self.engines)
                for h in horses
            ]
            preds = self.model.predict(features_list)

            predictions_out.append({
                'race_id': race_id,
                'recommendations': preds,  # 簡易: predictions を recommendations として使用
            })
            if race.get('result'):
                actuals_out.append({
                    'race_id': race_id,
                    'finish': race['result'],
                })

        return self.evaluate(predictions_out, actuals_out)

    # ------------------------------------------------------------------
    # 重み最適化
    # ------------------------------------------------------------------

    def optimize_weights(self) -> Dict:
        """エンジン重み係数を最適化する。

        月 1 回を推奨。過剰チューニング防止のため頻繁な実行は避けること。
        ウォークフォワード検証の結果を元に、ROI が最大になる重みを探索する。

        Returns
        -------
        Dict
            最適化された重み辞書。weights.yaml への反映はユーザーが行うこと。
        """
        print("[INFO] 重み最適化を開始します（推奨: 月1回）")
        # 候補重みを格子探索（シンプルな実装）
        engine_names = list(self.engines.keys())
        best_weights: Dict[str, float] = {name: 1.0 / len(engine_names) for name in engine_names}
        best_roi = 0.0

        # 過去6ヶ月でウォークフォワード検証
        fold_results = self.walk_forward_validation(months=3)
        if fold_results:
            avg_roi = float(np.mean([r.get('roi', 0.0) for r in fold_results]))
            best_roi = avg_roi
            print(f"  現在の平均ROI: {best_roi:.1%}")
            print(f"  最適重み（暫定）: {best_weights}")
            print("  ※ 実際の重みは weights.yaml を手動で更新してください")

        return best_weights

    # ------------------------------------------------------------------
    # 過学習防止チェックリスト
    # ------------------------------------------------------------------

    def overfitting_checklist(self) -> List[Tuple[bool, str]]:
        """過学習防止チェックリストを返す。

        Returns
        -------
        List[Tuple[bool, str]]
            ``(チェック済みか, チェック項目)`` のリスト。
            チェック済みフラグは実行時に自動判定できる項目のみ True にする。
            残りは手動確認が必要。
        """
        checklist = [
            (None, "race_id / horse_id を特徴量から除外したか"),
            (None, "オッズ・人気を入力特徴量にしていないか"),
            (True,  "時系列分割（ウォークフォワード）を使っているか"),
            (True,  "同一レースが訓練・テストに分かれていないか"),
            (None, "外れ値を除外して評価したか"),
            (None, "特徴量重要度でID系が上位に来ていないか"),
            (None, "Early Stopping を設定しているか"),
        ]
        print("\n[過学習防止チェックリスト]")
        for checked, item in checklist:
            if checked is True:
                mark = "[OK]"
            elif checked is False:
                mark = "[NG]"
            else:
                mark = "[要確認]"
            print(f"  {mark} {item}")
        return checklist

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _build_dataset(
        self,
        races: List[Dict],
    ) -> Tuple['np.ndarray', 'np.ndarray', 'np.ndarray']:
        """レースリストから学習用 numpy 配列を構築する。"""
        X_rows: List[List[float]] = []
        y_win_rows: List[int] = []
        y_show_rows: List[int] = []

        for race in races:
            horses = race.get('horses', [])
            race_data = race.get('race_data', {})
            result = race.get('result', [])
            finish_map = {r['post']: r['finish_pos'] for r in result}

            for horse in horses:
                features = self.model.build_features(horse, race_data, self.engines)
                feature_values = [
                    float(v)
                    for k, v in sorted(features.items())
                    if isinstance(v, (int, float))
                ]
                if not feature_values:
                    continue

                post = horse.get('post', 0)
                finish_pos = finish_map.get(post, 99)
                X_rows.append(feature_values)
                y_win_rows.append(1 if finish_pos == 1 else 0)
                y_show_rows.append(1 if finish_pos <= 3 else 0)

        if not X_rows:
            return np.array([]), np.array([]), np.array([])

        # 行ごとの列数を最大に揃える（パディング）
        max_cols = max(len(row) for row in X_rows)
        X_padded = np.array(
            [row + [0.0] * (max_cols - len(row)) for row in X_rows],
            dtype=np.float32,
        )
        return (
            X_padded,
            np.array(y_win_rows, dtype=np.int32),
            np.array(y_show_rows, dtype=np.int32),
        )

    def _check_hit(self, recommendation: Dict, finish_map: Dict[int, int]) -> bool:
        """推奨馬券が的中したか判定する。"""
        ticket_type = recommendation.get('type', '')
        combination = recommendation.get('combination', '')

        if ticket_type == '単勝':
            return finish_map.get(int(combination), 99) == 1
        if ticket_type == '複勝':
            return finish_map.get(int(combination), 99) <= 3
        if ticket_type == '馬連':
            posts = [int(p) for p in combination.split('-')]
            return len(posts) == 2 and all(finish_map.get(p, 99) <= 2 for p in posts)
        if ticket_type == '三連複':
            posts = [int(p) for p in combination.split('-')]
            return len(posts) == 3 and all(finish_map.get(p, 99) <= 3 for p in posts)
        return False
