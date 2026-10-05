# -*- coding: utf-8 -*-
"""combo_detail.py — 割安な組み合わせ（モデル確率／市場確率の比が大きい組）の回収率を、年ごと・しきい値ごとに見る（2026-10-02）"""
import collections, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C

preds, pay = C.predictions(), C.load_pay()
MINQ = {"馬連": 0.03, "ワイド": 0.08, "馬単": 0.02, "3連複": 0.01}
THR = (1.2, 1.3, 1.4, 1.5, 1.7, 2.0)
rec = collections.defaultdict(list)          # (券種, thr, 年) → [(賭け, 払戻, 開催日)]
for i, pr in enumerate(preds):
    pk = f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}"
    pp = pay.get(pk)
    if not pp:
        continue
    cm, cq = C.combos(pr["p"], pr["uma"]), C.combos(pr["q"], pr["uma"])
    for t in MINQ:
        tab = pp.get(t, {})
        for thr in THR:
            sel = [c for c in cm[t] if cq[t][c] >= MINQ[t] and cm[t][c] / cq[t][c] >= thr]
            rec[(t, thr, pr["key"][0][:4])].append((100.0 * len(sel), sum(tab.get("-".join(map(str, c)), 0) for c in sel)))
    if (i + 1) % 8000 == 0:
        print(f"  {i+1:,}/{len(preds):,}", flush=True)
years = sorted({k[2] for k in rec})
for t in MINQ:
    print(f"\n■ {t}（比のしきい値ごと・年ごとの回収率）")
    print(f"{'比≧':>5}{'点数':>8}{'全体':>8}{'95%区間':>16}" + "".join(f"{y:>7}" for y in years))
    for thr in THR:
        allv = [x for y in years for x in rec[(t, thr, y)]]
        st, rt = [x[0] for x in allv], [x[1] for x in allv]
        if sum(st) == 0:
            continue
        lo, hi = C.ci(st, rt)
        per = []
        for y in years:
            v = rec[(t, thr, y)]
            s = sum(x[0] for x in v)
            per.append(f"{sum(x[1] for x in v)/s*100:>6.0f}%" if s >= 3000 else "     - ")
        print(f"{thr:>5.1f}{int(sum(st)/100):>8,}{sum(rt)/sum(st)*100:>7.1f}% ［{lo*100:>5.1f}〜{hi*100:>5.1f}%］" + "".join(f"{x:>7}" for x in per))
