"""馬場バイアスエンジン

クッション値・含水率・開催週・枠番・脚質を組み合わせて
馬場バイアスによる有利不利を 0-100 でスコアリングする。

芝とダートで高含水率時の有利・不利が逆転する点に注意:
  芝:   高含水率 → 時計がかかる → 外差し有利
  ダート: 高含水率 → 砂が締まり高速 → 内先行有利（逆転現象）
"""

from typing import Any, Optional

from .base import BaseEngine

# 脚質コード → 先行指数（1.0=完全先行、0.0=追い込み）
_RUNNING_STYLE_INDEX: dict[str, float] = {
    "逃げ":    1.0,
    "先行":    0.75,
    "差し":    0.35,
    "追い込み": 0.0,
    "自在":    0.5,
}

# 馬場状態 → 数値スコア（重いほど 1.0 に近い）
_CONDITION_SCORE: dict[str, float] = {
    "良":   0.0,
    "稍重": 0.33,
    "重":   0.67,
    "不良": 1.0,
}


class BiasEngine(BaseEngine):
    """馬場バイアスを評価するエンジン。"""

    def calculate_bias(self, race_data: dict[str, Any]) -> dict[str, float]:
        """馬場バイアス強度を算出する。

        Parameters
        ----------
        race_data:
            ``race_info`` 辞書。``cushion_value``・``moisture``・
            ``track_condition``・``surface``・``week_of_meeting`` を参照。

        Returns
        -------
        dict
            - ``inner_advantage``: 内枠有利度（0.0 不利 〜 1.0 有利）
            - ``front_advantage``: 先行有利度（0.0 不利 〜 1.0 有利）
        """
        surface = (race_data.get("surface") or "turf").lower()
        is_turf = surface not in ("ダート", "dirt", "d")

        cushion_raw = race_data.get("cushion_value")
        moisture_raw = race_data.get("moisture")
        try:
            cushion: Optional[float] = float(cushion_raw) if cushion_raw is not None and str(cushion_raw).strip() not in ('', 'N/A', 'None') else None
        except (ValueError, TypeError):
            cushion = None
        try:
            moisture: Optional[float] = float(moisture_raw) if moisture_raw is not None and str(moisture_raw).strip() not in ('', 'N/A', 'None') else None
        except (ValueError, TypeError):
            moisture = None
        condition_raw: str = race_data.get("track_condition") or race_data.get("condition") or "良"
        week_raw = race_data.get("week_of_meeting")
        try:
            week = int(week_raw) if week_raw is not None else 1
        except (ValueError, TypeError):
            week = 1

        condition_score = _CONDITION_SCORE.get(condition_raw, 0.0)

        if is_turf:
            # ---- 芝バイアス ----
            # 含水率が高い / クッション値が低い / 馬場が渋い → 外差し有利
            moisture_val = moisture if moisture is not None else 8.0
            cushion_val = cushion if cushion is not None else 9.0
            # 開催後半（週が進む）ほど内が荒れる → 外有利
            week_factor = min((week - 1) / 4.0, 1.0)  # 4週で最大

            outside_pressure = (
                min(moisture_val / 15.0, 1.0) * 0.35
                + max(0.0, 1.0 - cushion_val / 12.0) * 0.35
                + condition_score * 0.15
                + week_factor * 0.15
            )
            inner_advantage = max(0.0, 1.0 - outside_pressure)
            front_advantage = max(0.0, 0.65 - condition_score * 0.35)

        else:
            # ---- ダートバイアス（逆転現象）----
            # 含水率が高い / 馬場が良い（砂が締まる）→ 高速 → 内先行有利
            moisture_val = moisture if moisture is not None else 5.0
            moisture_factor = min(moisture_val / 12.0, 1.0)

            # ダートは乾燥（低含水率）すると砂が深くなり差しが届く
            inner_advantage = 0.5 + moisture_factor * 0.3 - condition_score * 0.1
            inner_advantage = max(0.0, min(1.0, inner_advantage))
            front_advantage = 0.5 + moisture_factor * 0.25 + (1.0 - condition_score) * 0.15
            front_advantage = max(0.0, min(1.0, front_advantage))

        return {
            "inner_advantage": round(inner_advantage, 3),
            "front_advantage": round(front_advantage, 3),
        }

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用の馬場バイアス系特徴量を返す。

        Returns
        -------
        dict
            - ``cushion_value``: クッション値（芝のみ有意）
            - ``moisture``: 含水率（%）
            - ``week_of_meeting``: 開催週（1〜）
            - ``inner_advantage``: 内枠有利度（0-1）
            - ``front_advantage``: 先行有利度（0-1）
            - ``gate_bias_score``: 枠番×内有利度のスコア（0-100）
            - ``pace_bias_score``: 脚質×先行有利度のスコア（0-100）
        """
        bias = self.calculate_bias(race_data)
        inner_adv = bias["inner_advantage"]
        front_adv = bias["front_advantage"]

        # 枠番バイアス: 内枠（1-4）ほど内有利恩恵を受ける
        gate_num: Optional[int] = horse_data.get("gate_num")
        if gate_num is not None:
            # 枠番を 0-1 に正規化（1枠=1.0, 8枠=0.0）
            gate_norm = max(0.0, (8 - gate_num) / 7.0)
            gate_bias_score = gate_norm * inner_adv * 100.0
        else:
            gate_bias_score = None

        # 脚質バイアス: 先行脚質ほど先行有利恩恵を受ける
        running_style: Optional[str] = horse_data.get("running_style")
        style_index = _RUNNING_STYLE_INDEX.get(running_style or "", 0.5)
        pace_bias_score = style_index * front_adv * 100.0

        return {
            "cushion_value": race_data.get("cushion_value"),
            "moisture": race_data.get("moisture"),
            "week_of_meeting": race_data.get("week_of_meeting"),
            "inner_advantage": inner_adv,
            "front_advantage": front_adv,
            "gate_bias_score": gate_bias_score,
            "pace_bias_score": round(pace_bias_score, 2),
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """馬場バイアスによる有利不利スコアを返す（0-100）。

        枠番バイアス（50%）＋脚質バイアス（50%）の加重平均。
        データ欠損時はニュートラル（50.0）を返す。
        """
        feats = self.get_features(horse_data, race_data)

        gate_score = feats.get("gate_bias_score")
        pace_score = feats.get("pace_bias_score")

        if gate_score is None and pace_score is None:
            return 50.0

        g = self._safe(gate_score, 50.0)
        p = self._safe(pace_score, 50.0)

        score = g * 0.50 + p * 0.50
        return self._clamp(score)
