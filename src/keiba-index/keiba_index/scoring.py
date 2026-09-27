# -*- coding: utf-8 -*-
"""採点エンジン: 騎手/調教師ティア・スコア計算・シルシ判定"""
from .factors import FACTORS, PENDING_FACTORS

# ────── 騎手ティア ──────
JOCKEY_TIER = {
    "C.ルメール": ("S", 9), "川田将雅": ("S", 9), "D.レーン": ("S", 9),
    "坂井瑠星": ("A", 7), "戸崎圭太": ("A", 7), "松山弘平": ("A", 7),
    "岩田望来": ("B+", 6), "横山武史": ("B+", 6), "浜中俊": ("B+", 6),
    "北村友一": ("B+", 6), "鮫島克駿": ("B+", 6), "藤岡佑介": ("B+", 6),
    "M.デムーロ": ("A", 7), "福永祐一": ("A", 7),
    "岩田康誠": ("B+", 6), "武豊": ("B", 5), "田辺裕信": ("B", 5),
    "津村明秀": ("B", 5), "西村淳也": ("B", 5), "横山和生": ("B", 5),
    "横山典弘": ("B", 5), "団野大成": ("B", 5), "荻野極": ("B", 4),
    "佐々木大輔": ("B", 4), "高杉朗輝": ("C", 3), "永野猛蔵": ("B", 4),
    "菅原明良": ("B", 5), "吉田隼人": ("B", 5), "三浦皇成": ("B", 5),
    "藤岡康太": ("B", 5), "石川裕紀人": ("B", 5), "木幡巧也": ("B", 4),
    "亀田温心": ("B", 4), "松岡正海": ("B", 5), "北村宏司": ("B", 5),
    "中山雄太": ("B", 4), "大野拓弥": ("B", 4), "角田大和": ("B", 4),
    "丹内祐次": ("B", 5),
}

# ────── 調教師ティア ──────
TRAINER_TIER = {
    "友道康夫": ("S", 10), "藤原英昭": ("S", 10), "堀宣行": ("S", 10),
    "矢作芳人": ("S", 10), "国枝栄": ("A", 8), "木村哲也": ("A", 8),
    "中内田充正": ("A", 8), "斉藤崇史": ("A", 8), "手塚貴久": ("A", 8),
    "池江泰寿": ("A", 8), "杉山晴紀": ("A", 8), "須貝尚介": ("A", 8),
    "上原佑紀": ("B+", 7), "宮田敬介": ("A", 8), "斉藤誠": ("B+", 7),
    "吉岡辰弥": ("B+", 7), "尾形和幸": ("B", 5), "野中賢二": ("B", 5),
    "奥村豊": ("B", 5), "梅田智之": ("B", 5), "武井亮": ("B", 4),
    "福永祐一": ("A", 8),
}


def get_jockey_score(name: str) -> int:
    return JOCKEY_TIER.get(name, ("B", 5))[1]


def get_trainer_score(name: str) -> int:
    return TRAINER_TIER.get(name, ("B", 5))[1]


def get_shirushi(estimated_score: float) -> str:
    """推定スコアからシルシ（◎○▲△—）を返す"""
    if estimated_score >= 115: return "◎"
    if estimated_score >= 100: return "○"
    if estimated_score >= 88:  return "▲"
    if estimated_score >= 75:  return "△"
    return "—"


def score_horse(horse: dict) -> dict:
    """
    1頭分のスコアを計算する。

    Parameters
    ----------
    horse : dict
        キー: sc (list[int|None]), flags (list[(str, int)])

    Returns
    -------
    dict
        sub: 確定ファクター合計
        flg: フラグ補正合計
        conf: 確定計 (sub + flg)
        pend: 保留最大値
        est: 推定計 (確定 + 保留×0.65)
    """
    sc = horse.get("sc", [])
    flags = horse.get("flags", [])

    sub  = sum(x for x in sc if x is not None)
    # flags は tuple (desc, val) または dict {description, adjustment} の両形式に対応
    def _flag_val(f):
        return f["adjustment"] if isinstance(f, dict) else f[1]
    flg  = sum(_flag_val(f) for f in flags)
    conf = sub + flg
    pend_max = sum(FACTORS[i][1] for i, x in enumerate(sc) if x is None)
    estimated = conf + pend_max * 0.65

    return {
        "sub": sub,
        "flg": flg,
        "conf": conf,
        "pend": pend_max,
        "est": int(estimated),
    }


# シルシ → 背景色マッピング (Hex, COL参照は excel_builder.py で定義)
SHIRUSHI_COLOR_KEY = {
    "◎": "HONMEI",
    "○": "TAIKOU",
    "▲": "ANA",
    "△": "CHUUI",
    "—": "KESHI",
}
