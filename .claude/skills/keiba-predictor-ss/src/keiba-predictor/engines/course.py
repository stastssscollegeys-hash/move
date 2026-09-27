"""コース適性エンジン

CR値・距離シェア・ダート適性シェア・会場別勝率・芝ダート適性を評価する。
"""

from typing import Any, Optional

from .base import BaseEngine

# 距離カテゴリ区分（メートル）
_DISTANCE_CATEGORIES: list[tuple[str, int, int]] = [
    ("sprint",   0,    1400),   # スプリント
    ("mile",     1401, 1800),   # マイル
    ("middle",   1801, 2200),   # 中距離
    ("classic",  2201, 2600),   # クラシック
    ("long",     2601, 9999),   # 長距離
]


def _distance_category(distance: Optional[int]) -> Optional[str]:
    """距離をカテゴリ文字列に変換する。"""
    if distance is None:
        return None
    for name, lo, hi in _DISTANCE_CATEGORIES:
        if lo <= distance <= hi:
            return name
    return None


class CourseEngine(BaseEngine):
    """コース・距離・芝ダート適性を評価するエンジン。"""

    def _venue_win_rate(self, horse_data: dict[str, Any], venue: Optional[str]) -> Optional[float]:
        """過去走から当開催場の勝率を算出する。"""
        if not venue:
            return None
        past = horse_data.get("past_results") or []
        same_venue = [p for p in past if p.get("venue") == venue]
        if not same_venue:
            return None
        wins = sum(1 for p in same_venue if p.get("finish") == 1)
        return wins / len(same_venue)

    def _surface_fitness(
        self, horse_data: dict[str, Any], surface: Optional[str]
    ) -> Optional[float]:
        """芝・ダートの適性スコアを過去走から算出する（0-1）。"""
        if not surface:
            return None
        # smartrc から取得した適性シェアを優先
        if surface.lower() in ("dirt", "ダート", "d"):
            share = horse_data.get("dirt_share")
        else:
            # 芝適性シェアは distance_share で代替（サイト仕様による）
            share = horse_data.get("distance_share")

        if share is not None:
            return self._clamp(float(share) / 100.0, 0.0, 1.0)

        # データなし → 過去走の芝ダート一致率で推計
        past = horse_data.get("past_results") or []
        if not past:
            return None
        same_surface = [
            p for p in past
            if (p.get("surface") or "").lower() == (surface or "").lower()
        ]
        if not same_surface:
            return 0.3  # 実績なし → 低適性
        wins = sum(1 for p in same_surface if p.get("finish") == 1)
        top3 = sum(1 for p in same_surface if (p.get("finish") or 99) <= 3)
        return top3 / len(same_surface)

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用のコース適性系特徴量を返す。

        Returns
        -------
        dict
            - ``cr_value``: CR値（smartrc 指標）
            - ``distance_share``: 距離別シェア（%、0-100）
            - ``dirt_share``: ダート適性シェア（%、0-100）
            - ``venue_win_rate``: 当開催場の勝率（0-1）
            - ``surface_fitness``: 芝ダート適性スコア（0-1）
            - ``distance_category``: 距離カテゴリ文字列
            - ``distance_match``: 今走距離と過去最多出走距離の一致度（0-1）
        """
        venue = race_data.get("venue")
        surface = race_data.get("surface")
        distance: Optional[int] = race_data.get("distance")

        cr_value = horse_data.get("cr_value")
        distance_share = horse_data.get("distance_share")
        dirt_share = horse_data.get("dirt_share")
        venue_win_rate = self._venue_win_rate(horse_data, venue)
        surface_fitness = self._surface_fitness(horse_data, surface)
        dist_category = _distance_category(distance)

        # 今走距離と過去走距離の一致度
        past = horse_data.get("past_results") or []
        past_distances = [p.get("distance") for p in past if p.get("distance") is not None]
        if past_distances and distance is not None:
            same_dist = sum(
                1 for d in past_distances
                if abs(int(d) - distance) <= 200  # ±200m を同距離とみなす
            )
            distance_match: Optional[float] = same_dist / len(past_distances)
        else:
            distance_match = None

        return {
            "cr_value": cr_value,
            "distance_share": distance_share,
            "dirt_share": dirt_share,
            "venue_win_rate": venue_win_rate,
            "surface_fitness": surface_fitness,
            "distance_category": dist_category,
            "distance_match": distance_match,
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """コース適性スコアを返す（0-100）。

        50850頭統計: CR値の差はたった0.7（予測力低い）
        → CR値15%に削減、距離一致度とコース実績を重視
        """
        feats = self.get_features(horse_data, race_data)

        # CR値: smartrcの値は1-100程度のスケール
        # データ実態: 4,9,14,26,31,39,43,49,82 など幅広い
        cr_raw = self._safe(feats.get("cr_value"))
        if cr_raw > 0:
            # 対数スケールで差を出す（低い値でも差が出るように）
            import math
            cr_score = self._clamp(math.log1p(cr_raw) / math.log1p(100) * 100)
        else:
            cr_score = 30.0  # CR値なし → 低め

        # 芝ダート適性（0-1 → 0-100）
        sf_score = self._clamp(self._safe(feats.get("surface_fitness"), 0.5) * 100.0)

        # 距離一致度（0-1 → 0-100）
        dm_score = self._clamp(self._safe(feats.get("distance_match"), 0.5) * 100.0)

        # 当コース実績（smartrc exp_cur_course_cnt/wi3）
        # ベイズ平滑化: スムーズ勝率 = (wi3 + α*全体平均) / (cnt + α)
        course_cnt = self._safe(horse_data.get("exp_cur_course_cnt"))
        course_wi3 = self._safe(horse_data.get("exp_cur_course_wi3"))
        alpha = 5.0  # スムージングパラメータ
        base_rate = 0.2  # 全体平均の複勝率（約20%）
        if course_cnt > 0:
            smoothed = (course_wi3 + alpha * base_rate) / (course_cnt + alpha)
            course_exp_score = self._clamp(smoothed * 100.0)
        elif course_cnt == 0:
            course_exp_score = self._clamp(base_rate * 100.0)  # 経験なし→全体平均
        else:
            course_exp_score = 50.0

        # ローテーション適性（距離延長/短縮/同距離）
        rota = horse_data.get("rota_type")
        rota_eval = (horse_data.get("rota_eval") or "").strip()
        if rota == "2":  # 同距離
            rota_score = 60.0
        elif rota == "1":  # 短縮
            rota_score = 55.0
        elif rota == "3":  # 延長
            rota_score = 50.0
        else:
            rota_score = 50.0

        # 50850頭統計: CR値差0.7→ウェイト削減、距離一致+コース実績を重視
        score = (
            cr_score * 0.15
            + sf_score * 0.20
            + dm_score * 0.25
            + course_exp_score * 0.25
            + rota_score * 0.15
        )
        return self._clamp(score)
