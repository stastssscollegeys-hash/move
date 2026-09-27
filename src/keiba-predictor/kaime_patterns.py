# -*- coding: utf-8 -*-
"""
kaime_patterns.py — レースの「型」を判定する（2026-09-26新規）
================================================================
ユーザー指示（2026-09-26）:
  「パターンを詳細にして、この型にはまった場合はこれ、という買い目の出し方の構造にする。
    パターンは過去のレース結果を研究してどんどん増やしていく」

型の判定はすべて **レース前に分かる情報だけ** で行う（結果リーク禁止）:
  ・確定単勝オッズ（当日朝の実オッズ。前日版なら前日オッズ）
  ・指数の順位
  ・頭数
型ごとの最良の買い方は pattern_mine.py が過去レースの確定払戻から実測して決める。
実測結果は daily_pdca/db/pattern_roi.json に入り、kaime_select が参照する。
"""
from __future__ import annotations

# ── 型の定義 ────────────────────────────────────────────────────
# match(ctx) -> bool。ctx は build_ctx() が作る。
# 複数の型に当てはまる場合は priority の小さい方を優先する。
PATTERNS = [
    dict(id="P1", name="1番人気が抜けている", priority=1,
         desc="単勝1番人気が2.5倍以下で、2番人気との差が2.0倍以上",
         match=lambda c: c["o1"] <= 2.5 and (c["o2"] - c["o1"]) >= 2.0),
    dict(id="P2", name="上位が拮抗して人気が割れている", priority=2,
         desc="1番人気が4.0倍以上で、上位4頭が6.0倍以内に収まる",
         match=lambda c: c["o1"] >= 4.0 and c["o4"] <= 6.0),
    dict(id="P3", name="少頭数", priority=3,
         desc="10頭以下",
         match=lambda c: c["n"] <= 10),
    dict(id="P4", name="指数1位が人気薄（市場とズレが大きい）", priority=4,
         desc="指数1位の単勝人気が6番人気以下",
         match=lambda c: c["idx1_pop"] >= 6),
    dict(id="P5", name="指数1位と市場1番人気が一致", priority=5,
         desc="指数1位がそのまま単勝1番人気",
         match=lambda c: c["idx1_pop"] == 1),
    dict(id="P6", name="混戦・人気薄まで手が広い", priority=6,
         desc="1番人気が5.0倍以上、かつ10番人気が30倍以内",
         match=lambda c: c["o1"] >= 5.0 and c["o10"] <= 30.0),
    dict(id="P7", name="指数上位に中穴がいる", priority=7,
         desc="指数3位以内に8〜14番人気の馬がいる",
         match=lambda c: c["has_mid_ana"]),
    dict(id="P0", name="その他（標準）", priority=99,
         desc="どの型にも当てはまらない",
         match=lambda c: True),
]

# ── 型ごとの既定の買い方（pattern_mine.py の実測で上書きされる）────
DEFAULT_STRUCTURE = {
    "P1": "馬単◎1着流し",
    "P2": "馬連BOX3",
    "P3": "馬連BOX3",
    "P4": "馬連穴軸流し",
    "P5": "馬連◎流し",
    "P6": "馬連◎流し",
    "P7": "3連複2列目",
    "P0": "馬連◎流し",
}


def build_ctx(score: dict, odds: dict) -> dict:
    """型判定に使う特徴量をレース前情報だけで作る"""
    pop = sorted(odds, key=lambda u: odds[u])
    o = [odds[u] for u in pop]
    rank = sorted(odds, key=lambda u: -score[u])
    idx1 = rank[0]
    pop_of = {u: i + 1 for i, u in enumerate(pop)}
    mid = [u for u in rank[:3] if 8 <= pop_of[u] <= 14]
    return dict(
        n=len(odds),
        o1=o[0], o2=o[1] if len(o) > 1 else o[0],
        o4=o[3] if len(o) > 3 else o[-1],
        o10=o[9] if len(o) > 9 else o[-1],
        idx1=idx1, idx1_pop=pop_of[idx1],
        has_mid_ana=bool(mid), mid_ana=mid[0] if mid else None,
        pop_of=pop_of, pop=pop, rank=rank,
    )


def classify(score: dict, odds: dict):
    """当てはまる型を priority 順に返す。先頭が採用する型。"""
    c = build_ctx(score, odds)
    hit = [p for p in sorted(PATTERNS, key=lambda p: p["priority"]) if p["match"](c)]
    return hit, c
