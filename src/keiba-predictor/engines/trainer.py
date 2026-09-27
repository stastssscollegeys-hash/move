"""調教師分析エンジン

調教師の開催場別勝率・東西所属・遠征有無を評価する。
"""

from typing import Any, Optional

from .base import BaseEngine

# 東日本開催場
_EAST_VENUES: frozenset[str] = frozenset([
    "tokyo", "nakayama", "niigata", "fukushima", "kokura",
    "東京", "中山", "新潟", "福島", "小倉",
])

# 西日本開催場
_WEST_VENUES: frozenset[str] = frozenset([
    "hanshin", "kyoto", "chukyo", "hakodate", "sapporo",
    "阪神", "京都", "中京", "函館", "札幌",
])

# 東西所属コード
_AFFILIATION_CODE: dict[str, int] = {
    "east": 1,   # 美浦（東）
    "west": 2,   # 栗東（西）
    "unknown": 0,
}


def _venue_affiliation(venue: Optional[str]) -> str:
    """開催場から東西を判定する。"""
    if not venue:
        return "unknown"
    v = venue.lower()
    if v in _EAST_VENUES:
        return "east"
    if v in _WEST_VENUES:
        return "west"
    return "unknown"


class TrainerEngine(BaseEngine):
    """調教師の実績・遠征適性を評価するエンジン。"""

    def _trainer_venue_rate(
        self, horse_data: dict[str, Any], venue: Optional[str]
    ) -> Optional[float]:
        """過去走から調教師の当開催場における勝率を算出する。

        直接スクレイプされたデータがあればそれを使用し、
        なければ過去走の同開催場レースから集計する。
        """
        # スクレイパーが直接提供する場合
        rate = horse_data.get("trainer_venue_rate")
        if rate is not None:
            return float(rate)

        if not venue:
            return None

        past = horse_data.get("past_results") or []
        same_venue = [p for p in past if p.get("venue") == venue]
        if not same_venue:
            return None

        wins = sum(1 for p in same_venue if p.get("finish") == 1)
        return wins / len(same_venue)

    def _is_away(self, horse_data: dict[str, Any], venue: Optional[str]) -> Optional[bool]:
        """遠征かどうかを判定する。

        調教師の所属（東西）と開催場の東西が異なれば遠征とみなす。
        smartrc の tozai フィールド: "1"=東(美浦), "2"=西(栗東)
        """
        # smartrc の tozai フィールドを優先
        tozai = horse_data.get("tozai")
        trainer_affiliation: Optional[str] = horse_data.get("trainer_affiliation")

        if tozai == "1":
            trainer_affiliation = "east"
        elif tozai == "2":
            trainer_affiliation = "west"

        if not trainer_affiliation or not venue:
            return None

        venue_affil = _venue_affiliation(venue)
        if venue_affil == "unknown":
            return None

        return trainer_affiliation.lower() != venue_affil

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用の調教師系特徴量を返す。

        Returns
        -------
        dict
            - ``trainer_venue_rate``: 調教師の当開催場勝率（0-1）
            - ``trainer_east_west``: 東西所属コード（東=1, 西=2, 不明=0）
            - ``is_away``: 遠征フラグ（True/False/None）
            - ``away_penalty``: 遠征ペナルティスコア補正値
        """
        venue: Optional[str] = race_data.get("venue")

        trainer_venue_rate = self._trainer_venue_rate(horse_data, venue)

        # 東西所属
        trainer_affiliation: Optional[str] = horse_data.get("trainer_affiliation")
        if trainer_affiliation:
            affil_code = _AFFILIATION_CODE.get(trainer_affiliation.lower(), 0)
        else:
            affil_code = 0

        is_away = self._is_away(horse_data, venue)

        # 遠征ペナルティ: 遠征の場合はスコアを下げる
        if is_away is True:
            away_penalty = -8.0
        elif is_away is False:
            away_penalty = 3.0   # ホーム開催はわずかにプラス
        else:
            away_penalty = 0.0   # 不明はニュートラル

        return {
            "trainer_venue_rate": trainer_venue_rate,
            "trainer_east_west": affil_code,
            "is_away": is_away,
            "away_penalty": away_penalty,
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """調教師スコアを返す（0-100）。

        開催場勝率（70%）＋遠征補正（30%）の加重スコア。
        勝率データなしは中立値（50.0）を使用。
        """
        feats = self.get_features(horse_data, race_data)

        # 開催場勝率: 0.20（20%）→ 100点（トップトレーナー基準）
        venue_rate = feats.get("trainer_venue_rate")
        if venue_rate is not None:
            venue_score = self._clamp(float(venue_rate) / 0.20 * 100.0)
        else:
            venue_score = 50.0  # データなし → 中立

        # 遠征補正をスコアに加算
        away_penalty = self._safe(feats.get("away_penalty"), 0.0)
        base = venue_score * 0.70 + 50.0 * 0.30  # 遠征補正なし部分
        score = base + away_penalty

        return self._clamp(score)
