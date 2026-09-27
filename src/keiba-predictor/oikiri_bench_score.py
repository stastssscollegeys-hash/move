# -*- coding: utf-8 -*-
"""
oikiri_bench_score.py — 追い切り自動採点の一致率を測る（2026-09-25）
====================================================================
判定基準（事前に決めておく）:
  ・完全一致が「いつもBと答える」ベースライン（最頻値）を明確に上回ること
  ・隣接1段階以内（S⇔A、A⇔B…）が9割以上 → 大外しをしないなら因子としては使える
  ・確信度が高い層ほど当たる（確信度に意味がある）こと
"""
from __future__ import annotations
import json, sys, io
from collections import Counter
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ORDER = {g: i for i, g in enumerate("SABCDE")}
p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Desktop" / "競馬予想レポート" / "20260920" / "research" / "oikiri_pred.json"
rows = [r for r in json.loads(p.read_text(encoding="utf-8")) if r.get("pred")]
n = len(rows)
exact = sum(r["pred"] == r["grade_true"] for r in rows)
near = sum(abs(ORDER[r["pred"]] - ORDER[r["grade_true"]]) <= 1 for r in rows)
base = Counter(r["grade_true"] for r in rows).most_common(1)[0]

print(f"■ 追い切りコメントの自動採点（{n}頭）")
print(f"  完全一致       : {exact}/{n} = {exact/n*100:.1f}%")
print(f"  隣接1段階以内  : {near}/{n} = {near/n*100:.1f}%")
print(f"  ベースライン   : 全部「{base[0]}」と答える = {base[1]/n*100:.1f}%")
print(f"  平均応答       : {sum(r['ms'] for r in rows)//n:,}ms")

print("\n■ 正解 × 予測（行＝正解）")
gs = [g for g in "SABCDE" if any(r["grade_true"] == g or r["pred"] == g for r in rows)]
print("      " + "".join(f"{g:>5}" for g in gs))
for t in gs:
    c = Counter(r["pred"] for r in rows if r["grade_true"] == t)
    print(f"  {t:<4}" + "".join(f"{c.get(g, 0):>5}" for g in gs))

print("\n■ 確信度別")
for lo, hi in ((0.9, 1.01), (0.8, 0.9), (0.0, 0.8)):
    sub = [r for r in rows if lo <= (r.get("confidence") or 0) < hi]
    if sub:
        e = sum(r["pred"] == r["grade_true"] for r in sub)
        print(f"  {lo:.1f}以上{hi if hi <= 1 else 1.0:.1f}未満: {len(sub):>3}頭  完全一致{e/len(sub)*100:5.1f}%")

print("\n■ 外した馬")
for r in rows:
    if r["pred"] != r["grade_true"]:
        print(f"  {r['race']:<10} {r['馬名']:<12} 正解{r['grade_true']} → 予測{r['pred']}（確信{r.get('confidence', 0):.2f}）")
