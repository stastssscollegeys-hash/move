"""能力指数エンジン

過去成績ベースのスピード指数・上がり3F・テン1F を算出し、
馬の総合能力を 0-100 でスコアリングする。
寄与度1位の最重要エンジン。
"""

from typing import Any, Optional

from .base import BaseEngine

# 直近5走の重み（最新走ほど高ウェイト）
_SPEED_WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]

# クラス補正値（上位クラスほど高く評価）
_CLASS_BONUS: dict[str, float] = {
    "G1": 15.0,
    "G2": 10.0,
    "G3": 7.0,
    "OP": 5.0,    # オープン
    "L":  4.0,    # リステッド
    "3勝": 3.0,
    "2勝": 2.0,
    "1勝": 1.0,
    "未勝利": 0.0,
    "新馬": 0.0,
}


class AbilityEngine(BaseEngine):
    """過去成績ベースの能力指数エンジン。"""

    def calculate_speed_index(self, past_results: list[dict[str, Any]]) -> float:
        """スピード指数を算出する。

        直近5走の CR 値（または仮想スコア）に重み付き移動平均を適用し、
        クラス補正を加算して返す。

        Parameters
        ----------
        past_results:
            スクレイパーが返す過去走リスト（新しい順）。

        Returns
        -------
        float
            スピード指数（基準50、理論上限100）。
        """
        if not past_results:
            return 50.0  # データなし → 平均値を返す

        scores: list[float] = []
        weights: list[float] = []

        for i, pr in enumerate(past_results[:5]):
            # CR 値があればそれを使用、なければ着順から仮算出
            cr = pr.get("cr_value")
            if cr is not None:
                raw_score = float(cr)
            else:
                finish = pr.get("finish")
                horse_count = pr.get("horse_count") or 16
                if finish is not None:
                    # 着順を0-100スケールに変換（1着=100、最下位=0）
                    raw_score = max(0.0, 100.0 * (1.0 - (finish - 1) / max(horse_count - 1, 1)))
                else:
                    continue  # データ欠損はスキップ

            # クラス補正
            grade = pr.get("grade") or pr.get("class") or ""
            bonus = 0.0
            for key, val in _CLASS_BONUS.items():
                if key in grade:
                    bonus = val
                    break

            scores.append(raw_score + bonus)
            weights.append(_SPEED_WEIGHTS[i])

        if not scores:
            return 50.0

        total_weight = sum(weights)
        if total_weight == 0:
            return 50.0

        index = sum(s * w for s, w in zip(scores, weights)) / total_weight
        return self._clamp(index)

    def calculate_last_3f_rating(self, past_results: list[dict[str, Any]]) -> float:
        """上がり3F の相対評価スコアを算出する（0-100）。

        直近5走の上がり3F 平均を基準値（35.5秒）と比較し、
        速いほど高スコアを返す。
        """
        values: list[float] = []
        for pr in past_results[:5]:
            v = pr.get("last_3f")
            if v is not None:
                values.append(float(v))

        if not values:
            return 50.0

        avg = sum(values) / len(values)
        # 33.0秒 → 100点、38.0秒 → 0点 の線形変換
        score = (38.0 - avg) / (38.0 - 33.0) * 100.0
        return self._clamp(score)

    def calculate_ten_1f_rating(self, past_results: list[dict[str, Any]]) -> float:
        """テン1F のペース適性スコアを算出する（0-100）。

        速いテン1F は先行・逃げ馬の指標。
        ペース適性として中立評価（高いほど先行力あり）。
        """
        values: list[float] = []
        for pr in past_results[:5]:
            v = pr.get("ten_1f")
            if v is not None:
                values.append(float(v))

        if not values:
            return 50.0

        avg = sum(values) / len(values)
        # 11.0秒 → 100点、13.5秒 → 0点 の線形変換
        score = (13.5 - avg) / (13.5 - 11.0) * 100.0
        return self._clamp(score)

    def _recent_form(self, past_results: list[dict[str, Any]]) -> float:
        """直近3走の平均着順を返す（データなしは None）。

        着順が小さいほど良い（1着=最高）。
        """
        finishes: list[float] = []
        for pr in past_results[:3]:
            f = pr.get("finish")
            if f is not None:
                finishes.append(float(f))
        if not finishes:
            return 8.0  # データなし → 中間値
        return sum(finishes) / len(finishes)

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用の能力系特徴量を返す。

        Returns
        -------
        dict
            - ``speed_index``: スピード指数（0-100）
            - ``last_3f_avg``: 上がり3F 平均（秒）
            - ``last_3f_rating``: 上がり3F 相対評価（0-100）
            - ``ten_1f_avg``: テン1F 平均（秒）
            - ``ten_1f_rating``: テン1F 評価（0-100）
            - ``best_finish_rate``: 最高着順 / 頭数（小さいほど良い、0-1）
            - ``recent_form``: 直近3走平均着順
            - ``class_adjustment``: 今走クラス × 前走クラス の補正差分
        """
        past = horse_data.get("past_results") or []

        speed_index = self.calculate_speed_index(past)
        last_3f_rating = self.calculate_last_3f_rating(past)
        ten_1f_rating = self.calculate_ten_1f_rating(past)

        # 上がり3F 平均（生値）
        last_3f_vals = [float(p["last_3f"]) for p in past[:5] if p.get("last_3f") is not None]
        last_3f_avg = sum(last_3f_vals) / len(last_3f_vals) if last_3f_vals else None

        # テン1F 平均（生値）
        ten_1f_vals = [float(p["ten_1f"]) for p in past[:5] if p.get("ten_1f") is not None]
        ten_1f_avg = sum(ten_1f_vals) / len(ten_1f_vals) if ten_1f_vals else None

        # 最高着順の割合（1着ならほぼ0に近い）
        finishes = [int(p["finish"]) for p in past[:5] if p.get("finish") is not None]
        horse_counts = [int(p["horse_count"]) for p in past[:5] if p.get("horse_count") is not None]
        if finishes and horse_counts:
            best_finish_rate = min(
                f / max(hc, 1) for f, hc in zip(finishes, horse_counts)
            )
        else:
            best_finish_rate = None

        recent_form = self._recent_form(past)

        # クラス補正差分（今走 vs 前走）
        current_grade = race_data.get("grade") or ""
        prev_grade = (past[0].get("grade") or past[0].get("class") or "") if past else ""
        current_bonus = next((v for k, v in _CLASS_BONUS.items() if k in current_grade), 0.0)
        prev_bonus = next((v for k, v in _CLASS_BONUS.items() if k in prev_grade), 0.0)
        class_adjustment = current_bonus - prev_bonus  # 昇級なら負、降級なら正

        return {
            "speed_index": speed_index,
            "last_3f_avg": last_3f_avg,
            "last_3f_rating": last_3f_rating,
            "ten_1f_avg": ten_1f_avg,
            "ten_1f_rating": ten_1f_rating,
            "best_finish_rate": best_finish_rate,
            "recent_form": recent_form,
            "class_adjustment": class_adjustment,
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """能力指数エンジンの総合スコアを返す（0-100）。

        スピード指数（40%）、上がり3F評価（25%）、テン1F評価（15%）、
        smartrc独自指標（20%）の加重平均。
        """
        past = horse_data.get("past_results") or []
        speed = self.calculate_speed_index(past)
        last_3f = self.calculate_last_3f_rating(past)
        ten_1f = self.calculate_ten_1f_rating(past)

        # smartrc の ten_has（テンハロン）/ agari_has（上がりハロン）を活用
        smartrc_score = 50.0
        ten_has = horse_data.get("ten_has")  # 既にfloat変換済み
        agari_has = horse_data.get("agari_has")
        if ten_has is not None and agari_has is not None:
            # テンハロン: 低いほど先行力あり（36.0基準）
            ten_score = self._clamp((38.0 - ten_has) / (38.0 - 33.0) * 100.0)
            # 上がりハロン: 低いほど末脚あり（35.0基準）
            agari_score = self._clamp((37.0 - agari_has) / (37.0 - 33.0) * 100.0)
            smartrc_score = ten_score * 0.4 + agari_score * 0.6
        elif agari_has is not None:
            smartrc_score = self._clamp((37.0 - agari_has) / (37.0 - 33.0) * 100.0)
        elif ten_has is not None:
            smartrc_score = self._clamp((38.0 - ten_has) / (38.0 - 33.0) * 100.0)

        # 着順安定性ボーナス（直近3走の着順のバラつきが少ない＝信頼性が高い）
        stability_score = 50.0
        finishes = [p.get("finish") for p in past[:3] if p.get("finish") is not None]
        if len(finishes) >= 2:
            import statistics
            avg_finish = statistics.mean(finishes)
            std_finish = statistics.stdev(finishes) if len(finishes) >= 2 else 0
            # 平均着順が低く、バラつきが少ないほど高スコア
            # avg_finish=1→100, avg_finish=8→20
            avg_score = self._clamp(100 - (avg_finish - 1) * 12)
            # std=0→bonus20, std=5→bonus0
            stability_bonus = max(0, 20 - std_finish * 4)
            stability_score = self._clamp(avg_score + stability_bonus)
        elif len(finishes) == 1:
            stability_score = self._clamp(100 - (finishes[0] - 1) * 12)

        # 前走着順スコア（50850頭統計: 差2.5で2番目に重要）
        last_finish_score = 50.0
        if finishes:
            lf = finishes[0]
            # 1着=100, 3着=70, 5着=50, 10着=10
            last_finish_score = self._clamp(100 - (lf - 1) * 10)

        score = (speed * 0.20 + last_3f * 0.15 + ten_1f * 0.10
                + smartrc_score * 0.10 + stability_score * 0.20
                + last_finish_score * 0.25)
        return self._clamp(score)
