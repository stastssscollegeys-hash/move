"""レース難易度判定 - 買わないことが最大のエッジ"""
import os
import yaml
from typing import Dict, List, Optional


class DifficultyJudge:
    """
    レース難易度を 1〜5 の5段階で判定するクラス。
    難易度4以上は原則として見送り推奨とする。
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """general.yaml から見送り閾値を読み込む。"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'general.yaml'
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)  # yaml.load() は禁止
        self.max_difficulty: int = (
            config.get('race_selection', {}).get('max_difficulty', 3)
        )

    def judge(self, race_data: Dict, horses: List[Dict]) -> Dict:
        """レース難易度を5段階で判定する。

        Parameters
        ----------
        race_data:
            レース情報。``num_runners`` / ``grade`` 等を含む辞書。
        horses:
            出走馬リスト。各馬に ``popularity_rank`` / ``past_results`` 等を含む。

        Returns
        -------
        Dict
            ``{score: int, reasons: List[str], should_skip: bool}``
        """
        score = 1
        reasons: List[str] = []

        # --- 出走頭数 ---
        num = race_data.get('num_runners', 0)
        if num >= 16:
            score += 2
            reasons.append(f"多頭数（{num}頭）")
        elif num >= 12:
            score += 1
            reasons.append(f"やや多頭数（{num}頭）")

        # --- 人気ランクA馬の有無 ---
        # ランクA = 圧倒的1番人気など、軸にできる強い馬の目安
        has_rank_a = any(h.get('popularity_rank') == 'A' for h in horses)
        if not has_rank_a:
            score += 1
            reasons.append("人気ランクA馬なし（明確な軸不在）")

        # --- 初出走馬（過去走データなし）が3頭以上 ---
        newcomers = sum(1 for h in horses if not h.get('past_results'))
        if newcomers >= 3:
            score += 1
            reasons.append(f"初出走馬{newcomers}頭（データ不足）")

        # --- 過去走データが3戦未満の馬が過半数 ---
        data_poor = sum(
            1 for h in horses if len(h.get('past_results', [])) < 3
        )
        if data_poor > len(horses) // 2:
            score += 1
            reasons.append(
                f"データ3戦未満の馬が過半数（{data_poor}/{len(horses)}頭）"
            )

        # --- 悪天候・不良馬場 ---
        condition = race_data.get('condition', '')
        if condition in ('不良', '重'):
            score += 1
            reasons.append(f"馬場状態：{condition}（荒れやすい）")

        # PDCA35: ハンデ戦
        race_name = race_data.get('race_name', '')
        grade = race_data.get('grade', '')
        if 'ハンデ' in race_name or 'ハンデ' in grade:
            score += 1
            reasons.append("ハンデ戦（荒れやすい）")

        # --- スコアを 1〜5 に丸める ---
        score = max(1, min(score, 5))

        should_skip = score > self.max_difficulty

        # --- PDCA21: 荒れ度スコア（人気信頼度調整に使用）---
        upset_score = self._calc_upset_score(race_data, horses)

        return {
            'score': score,
            'reasons': reasons,
            'should_skip': should_skip,
            'upset_score': upset_score,
        }

    def _calc_upset_score(self, race_data: Dict, horses: List[Dict]) -> int:
        """レースの荒れ度スコアを算出する（0-15）。

        リサーチ根拠:
        - 15頭以上: 1番人気勝率29.9%（10頭以下の50%から大幅低下）
        - 不良馬場: 平均配当1,410円（良の1,010円の+40%）
        - ハンデ戦: 平均配当1,180円
        - 新馬戦: 平均配当1,220円（全クラス最高）
        - 牝馬限定ハンデ重賞: 三連単平均が極めて高い
        - 1番人気オッズ3.0倍以上: 荒れやすい
        - 福島/小倉/新潟: 平均配当が高い

        Returns
        -------
        int
            0-2: 堅い（人気信頼）
            3-5: やや荒れ（穴馬注意）
            6+:  大荒れ警戒（人気馬の信頼度を下げる）
        """
        upset = 0

        # 頭数
        num = race_data.get('num_runners', 0)
        if num >= 16:
            upset += 3
        elif num >= 14:
            upset += 2
        elif num >= 12:
            upset += 1

        # 馬場状態
        condition = race_data.get('condition', '')
        if condition == '不良':
            upset += 3
        elif condition == '重':
            upset += 2
        elif condition == '稍重':
            upset += 1

        # ハンデ戦（レース名 or 斤量バラつきから推定）
        # PDCA36: ハンデ重賞はさらに+1（ダービー卿CT: 1番人気過去10年1勝）
        race_name = race_data.get('race_name', '')
        grade = race_data.get('grade', '')
        is_handicap = 'ハンデ' in race_name or 'ハンデ' in grade
        is_graded = any(g in grade for g in ('G', 'Ｇ', 'J', 'C', 'E'))
        if is_handicap:
            upset += 3 if is_graded else 2
        elif horses:
            # 斤量が4種類以上ならハンデ戦と推定
            weights = set()
            for h in horses:
                w = h.get('weight_carried')
                if w is not None:
                    try:
                        weights.add(float(w))
                    except (ValueError, TypeError):
                        pass
            if len(weights) >= 4:
                upset += 2  # ハンデ戦相当

        # 新馬戦・未勝利
        if '新馬' in race_name:
            upset += 2
        elif '未勝利' in race_name:
            upset += 1

        # 牝馬限定（レース名 or 全頭牝馬で検出）
        all_female = False
        if horses:
            sexes = [h.get('sex', '') for h in horses if h.get('sex')]
            if sexes and all(s in ('牝', '牝馬') for s in sexes):
                all_female = True
        if '牝' in race_name or all_female:
            upset += 1

        # 1番人気のオッズ（3.0倍以上で荒れやすい）
        top_pop_odds = None
        for h in horses:
            pop = h.get('est_popularity') or h.get('popularity')
            if pop is not None:
                try:
                    if int(pop) == 1:
                        top_pop_odds = h.get('win_odds')
                        break
                except (ValueError, TypeError):
                    pass
        if top_pop_odds is not None:
            try:
                odds_val = float(top_pop_odds)
                if odds_val >= 5.0:
                    upset += 3
                elif odds_val >= 3.0:
                    upset += 2
            except (ValueError, TypeError):
                pass

        # PDCA35: 荒れやすい競馬場（福島/小倉/新潟/函館）
        venue = race_data.get('venue', '')
        if any(v in venue for v in ('福島', '小倉', '新潟', '函館')):
            upset += 1

        # PDCA35: 夏開催（6-8月に拡大。統計: 4月万馬券率1.28%最高、6月も高い）
        date_str = str(race_data.get('date', ''))
        if len(date_str) >= 6:
            try:
                month = int(date_str[4:6])
                if 6 <= month <= 8:
                    upset += 1
            except (ValueError, TypeError):
                pass

        # PDCA35: 古馬OPクラス（三連単平均246,870円、全クラス中最荒れ）
        if any(k in race_name for k in ('オープン', 'OP', 'リステッド')):
            upset += 1

        # PDCA35: 3勝クラス（到達率9.5%→実力拮抗で荒れやすい）
        if '3勝' in race_name:
            upset += 1

        # PDCA35: 降級制度廃止(2019〜)で条件戦が難化(+32%)
        if len(date_str) >= 4:
            try:
                year = int(date_str[:4])
                if year >= 2019:
                    is_jouken = any(k in race_name for k in ('1勝', '2勝', '3勝', '未勝利'))
                    if is_jouken:
                        upset += 1
            except (ValueError, TypeError):
                pass

        return upset
