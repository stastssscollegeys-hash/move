"""状態判定エンジン

馬体重増減・休養日数・年齢・性別・斤量差から
馬の出走時コンディションを 0-100 でスコアリングする。
"""

from typing import Any, Optional
import math

from .base import BaseEngine

# 性別コード → 数値（モデル用）
_SEX_CODE: dict[str, int] = {
    "牡": 1,
    "牝": 2,
    "セ": 3,   # セン馬
    "騸": 3,   # 同上（別表記）
}

# 休養日数の評価区間
# (下限日数, 上限日数, スコア補正)
_REST_SCORE_TABLE: list[tuple[int, int, float]] = [
    (0,   13,   -10.0),  # 中2週以内（短期間隔、疲労懸念）
    (14,  27,     5.0),  # 中2〜3週（標準間隔）
    (28,  55,    10.0),  # 中4〜7週（理想的）
    (56,  111,   0.0),   # 2〜3ヶ月（やや間隔あき）
    (112, 223,  -5.0),   # 4〜7ヶ月（長期休養明け）
    (224, 9999, -15.0),  # 8ヶ月以上（超長期休養）
]


def _rest_score(days: Optional[int]) -> float:
    """休養日数から補正スコアを返す。データなしは 0.0。"""
    if days is None:
        return 0.0
    for lo, hi, score in _REST_SCORE_TABLE:
        if lo <= days <= hi:
            return score
    return 0.0


def _age_peak_score(age: Optional[int], sex: Optional[str]) -> float:
    """年齢・性別ピーク補正スコア（0-100 の加算補正ではなく基準値）を返す。

    牡・セン馬: 4〜5歳がピーク
    牝馬:       3〜4歳がピーク
    """
    if age is None:
        return 50.0

    is_female = sex in ("牝",)
    if is_female:
        # 牝馬ピーク曲線
        peak = 3.5
    else:
        peak = 4.5

    # ガウス型ピーク関数（σ=1.5 — 感度を上げて年齢差を反映）
    score = 100.0 * math.exp(-0.5 * ((age - peak) / 1.5) ** 2)
    return max(15.0, score)  # 最低15点


class ConditionEngine(BaseEngine):
    """出走時コンディションを評価するエンジン。"""

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用のコンディション系特徴量を返す。

        Returns
        -------
        dict
            - ``weight_change``: 馬体重増減（kg、増加=正）
            - ``weight_change_abs``: 馬体重増減の絶対値
            - ``rest_days``: 前走からの休養日数
            - ``rest_score``: 休養日数評価スコア補正値
            - ``age``: 馬齢
            - ``sex_code``: 性別コード（牡=1, 牝=2, セ=3）
            - ``age_peak_score``: 年齢ピーク評価スコア（0-100）
            - ``weight_carried``: 斤量（kg）
            - ``weight_carried_diff``: 前走との斤量差（増加=正）
        """
        weight_diff: Optional[int] = horse_data.get("weight_diff")
        age: Optional[int] = horse_data.get("age")
        sex: Optional[str] = horse_data.get("sex")
        weight_carried: Optional[float] = horse_data.get("weight_carried")

        # 休養日数: 過去走の日付から計算
        rest_days: Optional[int] = horse_data.get("rest_days")
        if rest_days is None:
            past = horse_data.get("past_results") or []
            if past:
                last_date_str = past[0].get("date")
                race_date_str = race_data.get("date") or (horse_data.get("race_id") or "")[:8]
                if last_date_str and race_date_str and len(last_date_str) == 8 and len(race_date_str) == 8:
                    try:
                        from datetime import date as _date
                        ld = _date(int(last_date_str[:4]), int(last_date_str[4:6]), int(last_date_str[6:8]))
                        rd = _date(int(race_date_str[:4]), int(race_date_str[4:6]), int(race_date_str[6:8]))
                        rest_days = (rd - ld).days
                    except (ValueError, TypeError):
                        rest_days = None

        # 前走との斤量差
        weight_carried_diff: Optional[float] = None
        past = horse_data.get("past_results") or []
        if past and weight_carried is not None:
            prev_wc = past[0].get("weight_carried")
            if prev_wc is not None:
                try:
                    weight_carried_diff = float(weight_carried) - float(prev_wc)
                except (TypeError, ValueError):
                    weight_carried_diff = None

        return {
            "weight_change": weight_diff,
            "weight_change_abs": abs(weight_diff) if weight_diff is not None else None,
            "rest_days": rest_days,
            "rest_score": _rest_score(rest_days),
            "age": age,
            "sex_code": _SEX_CODE.get(sex or "", 0),
            "age_peak_score": _age_peak_score(age, sex),
            "weight_carried": weight_carried,
            "weight_carried_diff": weight_carried_diff,
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """コンディションスコアを返す（0-100）。

        年齢ピーク（40%）、休養日数評価（35%）、馬体重増減（25%）の加重平均。
        """
        feats = self.get_features(horse_data, race_data)

        # 年齢ピークスコア（0-100）
        age_score = self._clamp(self._safe(feats["age_peak_score"], 50.0))

        # 休養日数スコア（基準50点 + 補正値）
        rest_score = self._clamp(50.0 + self._safe(feats["rest_score"]))

        # 馬体重増減スコア
        # ±6kg 以内を理想（100点）、それ以上は減点
        wc = feats.get("weight_change_abs")
        if wc is None:
            weight_score = 50.0
        else:
            weight_score = self._clamp(100.0 - max(0.0, float(wc) - 6.0) * 5.0)

        score = age_score * 0.40 + rest_score * 0.35 + weight_score * 0.25
        return self._clamp(score)
