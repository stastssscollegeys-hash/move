# -*- coding: utf-8 -*-
"""
oikiri_calibrate.py — 点数をレース内の順位で評価に直す（2026-09-25）
=====================================================================
素のラベル出力はSを一度も付けなかった（正解S6頭を全てAと判定）。
Kaggle検証（@xjuntaro）でも「確率出力を実データで閾値調整したものが最良」と報告されている。
ここでは同じ考えで、レース内で点数の順位を取り、実際の評価の出現比率に合わせて割り当て直す。
比率は手作業で貯めた60頭の実測（S10% / A20% / B48% / C22%）を使う。
"""
from __future__ import annotations
import json, sys, io
from collections import Counter, defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ORDER = {g: i for i, g in enumerate("SABCDE")}
SHARE = [("S", 0.10), ("A", 0.20), ("B", 0.48), ("C", 0.22)]

src = Path(sys.argv[1])
rows = [r for r in json.loads(src.read_text(encoding="utf-8")) if r.get("score") is not None]
by_race = defaultdict(list)
for r in rows:
    by_race[r["race"]].append(r)

for race, rs in by_race.items():
    rs.sort(key=lambda r: -r["score"])
    n = len(rs)
    cuts, acc = [], 0.0
    for g, share in SHARE:
        acc += share * n
        cuts.append((g, round(acc)))
    i = 0
    for g, upto in cuts:
        while i < min(upto, n):
            rs[i]["pred_cal"] = g
            i += 1
    for r in rs[i:]:
        r["pred_cal"] = "C"

n = len(rows)
raw = sum(r["pred"] == r["grade_true"] for r in rows)
cal = sum(r["pred_cal"] == r["grade_true"] for r in rows)
near = sum(abs(ORDER[r["pred_cal"]] - ORDER[r["grade_true"]]) <= 1 for r in rows)
print(f"■ レース内順位で割り当て直した結果（{n}頭）")
print(f"  素のラベル 完全一致: {raw/n*100:.1f}%")
print(f"  順位調整後 完全一致: {cal/n*100:.1f}%   隣接1段階以内 {near/n*100:.1f}%")
s_true = [r for r in rows if r["grade_true"] == "S"]
print(f"  S評価の再現: 素={sum(r['pred'] == 'S' for r in s_true)}/{len(s_true)}  順位調整後={sum(r['pred_cal'] == 'S' for r in s_true)}/{len(s_true)}")
print("\n■ 正解 × 順位調整後（行＝正解）")
gs = [g for g in "SABC"]
print("      " + "".join(f"{g:>5}" for g in gs))
for t in gs:
    c = Counter(r["pred_cal"] for r in rows if r["grade_true"] == t)
    print(f"  {t:<4}" + "".join(f"{c.get(g, 0):>5}" for g in gs))
out = src.with_name(src.stem + "_cal.json")
out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n保存:", out)
