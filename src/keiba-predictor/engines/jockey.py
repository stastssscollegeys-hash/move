"""騎手分析エンジン

騎手の勝率・連対率・コース別成績・乗り替わり効果を評価する。
寄与度2位のエンジン。
"""

from typing import Any, Optional

from .base import BaseEngine


class JockeyEngine(BaseEngine):
    """騎手の成績・適性を評価するエンジン。"""

    # 乗り替わり効果の補正値
    # 名手への乗り替わりはプラス、乗り替わりなし=0
    _JOCKEY_CHANGE_BONUS: float = 5.0
    _JOCKEY_CHANGE_PENALTY: float = -3.0  # 格下騎手への交代

    def _get_jockey_stats(self, horse_data: dict[str, Any]) -> dict[str, Any]:
        """馬データから騎手統計を取得する。

        smartrc.jp のデータから間接的に騎手力を推定する:
        - 推定人気が高い → 騎手評価が高い馬に騎乗している可能性
        - 過去走の着順と人気の差 → 騎手の腕前を反映
        """
        jockey_win_rate: Optional[float] = horse_data.get("jockey_win_rate")
        jockey_show_rate: Optional[float] = horse_data.get("jockey_show_rate")
        jockey_course_rate: Optional[float] = horse_data.get("jockey_course_rate")

        # smartrc データがない場合: 過去走の「人気より好走した率」で騎手力を推定
        if jockey_win_rate is None:
            past = horse_data.get("past_results") or []
            if past:
                outperform = 0
                total = 0
                for p in past[:5]:
                    finish = p.get("finish")
                    pop = p.get("popularity")
                    if finish is not None and pop is not None:
                        total += 1
                        if finish <= pop:
                            outperform += 1
                if total > 0:
                    jockey_win_rate = outperform / total
                    wins = sum(1 for p in past[:5] if p.get("finish") == 1)
                    shows = sum(1 for p in past[:5] if (p.get("finish") or 99) <= 3)
                    jockey_show_rate = shows / len(past[:5])
                else:
                    # 過去走はあるが人気データがない → 中立値
                    jockey_win_rate = 0.15
                    jockey_show_rate = 0.35
            else:
                # 新馬・初出走 → 中立値
                jockey_win_rate = 0.12
                jockey_show_rate = 0.30

        return {
            "jockey_win_rate": jockey_win_rate,
            "jockey_show_rate": jockey_show_rate,
            "jockey_course_rate": jockey_course_rate,
        }

    def _detect_jockey_change(self, horse_data: dict[str, Any]) -> Optional[float]:
        """乗り替わりの有無と効果を推定する。

        前走と今走の騎手名を比較。
        Returns: 補正値（乗り替わりなし=0.0、判断不能=None）
        """
        current_jockey = horse_data.get("jockey")
        past = horse_data.get("past_results") or []
        if not past or not current_jockey:
            return None

        prev_jockey = past[0].get("jockey")
        if prev_jockey is None:
            return None

        if current_jockey == prev_jockey:
            return 0.0  # 継続騎乗

        # 乗り替わりあり → 簡易評価（詳細なデータがある場合は騎手ランクで判定）
        # ここでは中立（情報不足）として小さなプラスを与える
        return self._JOCKEY_CHANGE_BONUS * 0.3

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用の騎手系特徴量を返す。

        Returns
        -------
        dict
            - ``jockey_win_rate``: 騎手通算勝率（0-1）
            - ``jockey_show_rate``: 騎手通算複勝率（0-1）
            - ``jockey_course_rate``: 騎手の当コース勝率（0-1）
            - ``jockey_change_effect``: 乗り替わり効果補正値
        """
        stats = self._get_jockey_stats(horse_data)
        change_effect = self._detect_jockey_change(horse_data)

        return {
            "jockey_win_rate": stats["jockey_win_rate"],
            "jockey_show_rate": stats["jockey_show_rate"],
            "jockey_course_rate": stats["jockey_course_rate"],
            "jockey_change_effect": change_effect,
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """騎手スコアを返す（0-100）。

        勝率（50%）、複勝率（30%）、コース勝率（20%）の加重平均を
        100点満点に換算する。
        """
        feats = self.get_features(horse_data, race_data)

        # 各指標を 0-100 スケールに変換
        # 勝率: 0.25（25%）→ 100点（トップジョッキー基準）
        win_score = self._clamp(self._safe(feats["jockey_win_rate"]) / 0.25 * 100)
        # 複勝率: 0.60（60%）→ 100点
        show_score = self._clamp(self._safe(feats["jockey_show_rate"]) / 0.60 * 100)
        # コース勝率: 0.30（30%）→ 100点
        course_score = self._clamp(self._safe(feats["jockey_course_rate"]) / 0.30 * 100)

        base_score = win_score * 0.50 + show_score * 0.30 + course_score * 0.20
        change_bonus = self._safe(feats["jockey_change_effect"])

        return self._clamp(base_score + change_bonus)
