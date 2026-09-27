"""消去法フィルタリング - 統計的根拠に基づく「来ない馬」の除外"""
import os
import yaml
from typing import List, Dict, Tuple, Optional


class EliminationFilter:
    """
    YAMLで定義した8ルールに基づいて「来ない馬」を除外するフィルター。
    min_remaining 未満まで消去しないよう安全装置を持つ。
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """消去ルールを YAML から読み込む。"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'elimination.yaml'
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)  # yaml.load() は禁止
        self.rules: Dict = self.config['rules']
        self.min_remaining: int = self.config.get('min_remaining', 3)

    # ------------------------------------------------------------------
    # 公開 API
    # ------------------------------------------------------------------

    def apply(
        self,
        horses: List[Dict],
        race_data: Dict,
    ) -> Tuple[List[Dict], List[Dict]]:
        """消去法を全ルール順に適用する。

        Parameters
        ----------
        horses:
            出走馬リスト。各辞書には馬情報が格納されている。
        race_data:
            レース情報（grade, num_runners 等）。

        Returns
        -------
        (残存馬リスト, 消去馬リスト)
            消去馬には ``elimination_rule`` / ``elimination_reason`` キーが付与される。
        """
        eliminated: List[Dict] = []
        remaining: List[Dict] = list(horses)

        # 人気上位保護: 推定人気3番以内の馬は消去しない
        # （市場が高く評価している馬を消去すると的中率が大幅に下がるため）
        protected_pop_threshold = 3

        for rule_id, rule in self.rules.items():
            if not rule.get('enabled', True):
                continue

            for horse in list(remaining):
                # 残存馬が最小数を割り込む場合はそのルールを打ち切る
                if len(remaining) - 1 < self.min_remaining:
                    break

                # 人気上位保護: 推定人気3番以内は消去しない
                pop = horse.get('popularity') or horse.get('est_popularity')
                if pop is not None:
                    try:
                        if int(pop) <= protected_pop_threshold:
                            continue
                    except (ValueError, TypeError):
                        pass

                should_eliminate, reason = self._check_rule(
                    rule_id, rule, horse, race_data
                )
                if should_eliminate:
                    horse['elimination_rule'] = rule_id
                    horse['elimination_reason'] = reason
                    eliminated.append(horse)
                    remaining.remove(horse)

        return remaining, eliminated

    # ------------------------------------------------------------------
    # ルール判定（内部）
    # ------------------------------------------------------------------

    def _check_rule(
        self,
        rule_id: str,
        rule: Dict,
        horse: Dict,
        race_data: Dict,
    ) -> Tuple[bool, str]:
        """個別ルールを評価し (消去すべきか, 理由文) を返す。

        ルール一覧
        ----------
        ELIM-001 : 13番人気以下
        ELIM-002 : リーディング30位以下の騎手（重賞時のみ）
        ELIM-003 : 7歳以上
        ELIM-004 : 前走10着以下
        ELIM-005 : 前走10番人気以下
        ELIM-006 : 血統×コーススコア < 20
        ELIM-007 : 体重変動 +20kg 以上 or -10kg 以下
        ELIM-008 : 休養365日以上 かつ 過去勝利なし
        """
        dispatch = {
            'ELIM-001': self._rule_elim001,
            'ELIM-002': self._rule_elim002,
            'ELIM-003': self._rule_elim003,
            'ELIM-004': self._rule_elim004,
            'ELIM-005': self._rule_elim005,
            'ELIM-006': self._rule_elim006,
            'ELIM-007': self._rule_elim007,
            'ELIM-008': self._rule_elim008,
        }
        handler = dispatch.get(rule_id)
        if handler is None:
            # 未定義ルールは汎用比較で処理
            return self._generic_compare(rule, horse, race_data)
        return handler(rule, horse, race_data)

    # --- 各ルール ---

    def _rule_elim001(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-001: 13番人気以下を消去。"""
        popularity = horse.get('popularity')
        if popularity is None:
            return False, ''
        threshold: int = rule.get('threshold', 13)
        if popularity >= threshold:
            return True, f"人気{popularity}番（{threshold}番人気以上は消去）"
        return False, ''

    def _rule_elim002(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-002: リーディング30位以下の騎手（重賞時のみ）を消去。"""
        # 重賞フラグが立っていない場合はスキップ
        is_graded = race_data.get('is_graded', False)
        if not is_graded:
            return False, ''
        jockey_ranking = horse.get('jockey_ranking')
        if jockey_ranking is None:
            return False, ''
        threshold: int = rule.get('threshold', 30)
        if jockey_ranking > threshold:
            return True, (
                f"騎手リーディング{jockey_ranking}位（重賞/{threshold}位超は消去）"
            )
        return False, ''

    def _rule_elim003(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-003: 7歳以上を消去。"""
        age = horse.get('age')
        if age is None:
            return False, ''
        threshold: int = rule.get('threshold', 7)
        if age >= threshold:
            return True, f"{age}歳（{threshold}歳以上は消去）"
        return False, ''

    def _rule_elim004(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-004: 前走10着以下を消去。"""
        last_finish = horse.get('last_finish')
        if last_finish is None:
            return False, ''
        threshold: int = rule.get('threshold', 10)
        if last_finish >= threshold:
            return True, f"前走{last_finish}着（{threshold}着以下は消去）"
        return False, ''

    def _rule_elim005(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-005: 前走10番人気以下を消去。"""
        last_popularity = horse.get('last_popularity')
        if last_popularity is None:
            return False, ''
        threshold: int = rule.get('threshold', 10)
        if last_popularity >= threshold:
            return True, (
                f"前走{last_popularity}番人気（{threshold}番人気以下は消去）"
            )
        return False, ''

    def _rule_elim006(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-006: 血統×コーススコア < 20 を消去。"""
        score = horse.get('bloodline_course_score')
        if score is None:
            return False, ''
        threshold: int = rule.get('threshold', 20)
        if score < threshold:
            return True, f"血統×コーススコア{score}（{threshold}未満は消去）"
        return False, ''

    def _rule_elim007(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-007: 体重変動 +20kg 以上 or -10kg 以下を消去。"""
        weight_change = horse.get('weight_change')
        if weight_change is None:
            return False, ''
        upper: int = rule.get('threshold_upper', 20)
        lower: int = rule.get('threshold_lower', -10)
        if weight_change >= upper:
            return True, f"体重増{weight_change:+d}kg（+{upper}kg以上は消去）"
        if weight_change <= lower:
            return True, f"体重減{weight_change:+d}kg（{lower}kg以下は消去）"
        return False, ''

    def _rule_elim008(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """ELIM-008: 休養365日以上 かつ 過去勝利なし を消去。"""
        rest_days = horse.get('rest_days', 0)
        threshold: int = rule.get('threshold', 365)
        if rest_days < threshold:
            return False, ''
        # 過去勝利があれば消去しない
        past_results: List[Dict] = horse.get('past_results', [])
        has_win = any(r.get('finish') == 1 for r in past_results)
        if not has_win:
            return True, (
                f"休養{rest_days}日＋過去勝利なし（{threshold}日超/無勝利は消去）"
            )
        return False, ''

    # --- 汎用比較（未定義ルール用） ---

    def _generic_compare(
        self, rule: Dict, horse: Dict, race_data: Dict
    ) -> Tuple[bool, str]:
        """field / operator / threshold の汎用比較。"""
        field: str = rule.get('field', '')
        operator: str = rule.get('operator', '>=')
        threshold = rule.get('threshold')
        value = horse.get(field)
        if value is None or threshold is None:
            return False, ''
        op_map = {
            '>=': value >= threshold,
            '>': value > threshold,
            '<=': value <= threshold,
            '<': value < threshold,
            '==': value == threshold,
        }
        if op_map.get(operator, False):
            return True, f"{field}={value}（閾値{operator}{threshold}で消去）"
        return False, ''
