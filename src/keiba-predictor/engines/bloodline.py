"""血統適性エンジン

コース×血統の交互作用特徴量を生成する。
サンデー系5小系統分類と大系統10分類を実装。
"""

from typing import Any, Optional

from .base import BaseEngine

# サンデー系5小系統分類
# キー: 小系統コード、値: 代表種牡馬リスト
SUNDAY_SUBTYPES: dict[str, list[str]] = {
    "P": ["アドマイヤムーン", "ダイワメジャー", "クロフネ", "スクリーンヒーロー"],   # スプリント・マイル
    "T": ["ステイゴールド", "ハーツクライ", "オルフェーヴル", "ゴールドシップ"],      # スタミナ・長距離
    "D": ["ゴールドアリュール", "クロフネ", "アグネスデジタル"],                      # ダート
    "L": ["フジキセキ", "マーベラスサンデー", "サクラバクシンオー"],                  # ローカル・軽い芝
    "Deep": ["ディープインパクト", "キズナ", "リアルスティール", "サトノダイヤモンド",
             "エピファネイア", "ジェンティルドンナ"],                                 # ディープ系
}

# 大系統10分類
# キー: 系統コード、値: キーワードリスト（種牡馬名に含まれる文字列で判定）
MAJOR_LINES: dict[str, list[str]] = {
    "SS":  ["サンデーサイレンス", "ディープインパクト", "ハーツクライ", "ステイゴールド",
            "ダイワメジャー", "ゴールドアリュール", "アドマイヤムーン", "フジキセキ",
            "オルフェーヴル", "キズナ", "エピファネイア"],
    "MP":  ["ミスタープロスペクター", "キングカメハメハ", "ロードカナロア", "ヘニーヒューズ",
            "クロフネ", "アグネスデジタル"],
    "ND":  ["ノーザンダンサー", "サドラーズウェルズ", "ガリレオ", "フランケル",
            "モンジュー", "デインヒル"],
    "NR":  ["ナスルーラ", "グレイソヴリン", "プリンスリーギフト"],
    "RB":  ["ロベルト", "ブライアンズタイム", "シンボリクリスエス", "エピファネイア"],
    "HR":  ["ヘイルトゥリーズン", "レインボウクエスト"],   # SS以外のHR系
    "TB":  ["トニービン", "ジャングルポケット", "アドマイヤジャパン"],
    "LF":  ["リファール", "デインヒル"],
    "NJ":  ["ニジンスキー", "カーリアン"],
    "OT":  [],   # その他
}

# 距離カテゴリ
_DIST_CAT: list[tuple[str, int, int]] = [
    ("short",  0,    1400),
    ("mile",   1401, 1800),
    ("mid",    1801, 2200),
    ("long",   2201, 9999),
]


def _dist_category(distance: Optional[int]) -> str:
    if distance is None:
        return "unknown"
    for name, lo, hi in _DIST_CAT:
        if lo <= distance <= hi:
            return name
    return "unknown"


class BloodlineEngine(BaseEngine):
    """血統×コース適性の交互作用特徴量を生成するエンジン。"""

    def classify_line(self, sire_name: Optional[str]) -> str:
        """種牡馬名を大系統コード（SS/MP/ND/...）に分類する。

        Parameters
        ----------
        sire_name:
            種牡馬名（日本語）。None の場合は ``'OT'``。

        Returns
        -------
        str
            大系統コード（2文字）。
        """
        if not sire_name:
            return "OT"
        for code, keywords in MAJOR_LINES.items():
            if code == "OT":
                continue
            for kw in keywords:
                if kw in sire_name:
                    return code
        return "OT"

    def classify_sunday_subtype(self, sire_name: Optional[str]) -> Optional[str]:
        """サンデー系種牡馬を5小系統（P/T/D/L/Deep）に分類する。

        サンデー系でない場合は None を返す。

        Parameters
        ----------
        sire_name:
            種牡馬名（日本語）。

        Returns
        -------
        str or None
            小系統コード、またはサンデー系でない場合 None。
        """
        if not sire_name:
            return None
        # まずサンデー系か確認
        if self.classify_line(sire_name) != "SS":
            return None
        for subtype, names in SUNDAY_SUBTYPES.items():
            for name in names:
                if name in sire_name:
                    return subtype
        # サンデー系だが小系統未分類 → Deep 扱い
        return "Deep"

    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用の血統交互作用特徴量を返す。

        Returns
        -------
        dict
            - ``sire_line``: 父の大系統コード（例: ``'SS'``）
            - ``bms_line``: 母父の大系統コード
            - ``sunday_subtype``: サンデー系小系統（非SSなら None）
            - ``sire_line_x_surface``: 父系統×芝ダート（例: ``'SS_turf'``）
            - ``sire_line_x_distance``: 父系統×距離カテゴリ（例: ``'SS_mile'``）
            - ``bms_line_x_condition``: 母父系統×馬場状態（例: ``'ND_heavy'``）
            - ``ss_subtype_x_surface``: SS小系統×芝ダート（SS以外は None）
        """
        sire: Optional[str] = horse_data.get("sire")
        bms: Optional[str] = horse_data.get("bms")
        surface: str = (race_data.get("surface") or "turf").lower()
        distance: Optional[int] = race_data.get("distance")
        condition: str = (race_data.get("track_condition") or "良")

        # 馬場状態を英語キーへ変換
        _cond_map = {"良": "good", "稍重": "yielding", "重": "heavy", "不良": "soft"}
        condition_en = _cond_map.get(condition, "good")

        # 芝ダートを統一表記へ
        surface_en = "dirt" if surface in ("ダート", "dirt", "d") else "turf"

        sire_line = self.classify_line(sire)
        bms_line = self.classify_line(bms)
        sunday_subtype = self.classify_sunday_subtype(sire)
        dist_cat = _dist_category(distance)

        return {
            "sire_line": sire_line,
            "bms_line": bms_line,
            "sunday_subtype": sunday_subtype,
            "sire_line_x_surface": f"{sire_line}_{surface_en}",
            "sire_line_x_distance": f"{sire_line}_{dist_cat}",
            "bms_line_x_condition": f"{bms_line}_{condition_en}",
            "ss_subtype_x_surface": (
                f"{sunday_subtype}_{surface_en}" if sunday_subtype else None
            ),
        }

    def calculate_score(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> float:
        """血統適性スコアを返す（0-100）。

        smartrc の系統コード（f_llcode 等）が利用可能ならそれを活用。
        なければ種牡馬名マッチング + 大系統×コース適性テーブルで算出。
        """
        feats = self.get_features(horse_data, race_data)
        surface_en: str = feats["sire_line_x_surface"].split("_", 1)[-1]
        sire_line: str = feats["sire_line"]
        sunday_subtype: Optional[str] = feats["sunday_subtype"]

        # ── smartrc の dirt_share を最優先で活用 ──
        # ダートレースなら dirt_share が高い＝血統的にダート向き
        dirt_share = horse_data.get("dirt_share")
        if dirt_share is not None:
            share = self._safe(dirt_share)
            if surface_en == "dirt":
                # ダートレース: share 高い = 有利 (0→30, 5→65, 10→100)
                smartrc_score = self._clamp(30 + share * 7)
            else:
                # 芝レース: share 低い = 有利 (0→90, 5→55, 10→20)
                smartrc_score = self._clamp(90 - share * 7)
        else:
            smartrc_score = None

        # ── 大系統×芝ダート 基本スコアテーブル ──
        _line_surface_score: dict[tuple[str, str], float] = {
            ("SS",  "turf"):  75.0, ("SS",  "dirt"):  50.0,
            ("MP",  "turf"):  55.0, ("MP",  "dirt"):  70.0,
            ("ND",  "turf"):  65.0, ("ND",  "dirt"):  50.0,
            ("NR",  "turf"):  55.0, ("NR",  "dirt"):  55.0,
            ("RB",  "turf"):  60.0, ("RB",  "dirt"):  65.0,
            ("HR",  "turf"):  55.0, ("HR",  "dirt"):  55.0,
            ("TB",  "turf"):  70.0, ("TB",  "dirt"):  45.0,
            ("LF",  "turf"):  65.0, ("LF",  "dirt"):  50.0,
            ("NJ",  "turf"):  65.0, ("NJ",  "dirt"):  50.0,
            ("OT",  "turf"):  50.0, ("OT",  "dirt"):  50.0,
        }
        name_score = _line_surface_score.get((sire_line, surface_en), 50.0)

        # SS小系統ボーナス
        subtype_bonus = 0.0
        if sunday_subtype == "D" and surface_en == "dirt":
            subtype_bonus = 10.0
        elif sunday_subtype == "T" and surface_en == "turf":
            subtype_bonus = 5.0
        elif sunday_subtype == "Deep" and surface_en == "turf":
            subtype_bonus = 8.0

        name_score = self._clamp(name_score + subtype_bonus)

        # ── 統合: smartrc データがあればそちらを重視 ──
        if smartrc_score is not None:
            # smartrc 70% + 名前マッチ 30%
            final = smartrc_score * 0.7 + name_score * 0.3
        else:
            final = name_score

        return self._clamp(final)
