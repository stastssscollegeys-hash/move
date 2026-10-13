# -*- coding: utf-8 -*-
"""
walk_bands_test.py — 年ごとの前向き検証の「EV≧しきい値」単勝買いを、オッズ帯別・年別に分解する（2026-10-14）
=====================================================================================================
run_walk の「10倍以下・EV≧1.0 が109.1%［99.1〜119.5%］」が、10倍という切り方の産物でないかを見る。
  ・年ごとに その年より前で学習 → その年の単勝（EV≧thr）を オッズ帯 別に 回収率
  ・帯ごとに全年まとめの回収率と95%区間（レース単位ブートストラップ）、プラスの年数
使い方: python walk_bands_test.py [--thr 1.0] [--l2 0.01]      # 約3〜5分・メモリ3GB前後
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import predict_day as P

E.SOURCE = P.HIST
BANDS = [(1.0, 3.0), (3.0, 6.0), (6.0, 10.0), (10.0, 20.0), (20.0, 1e9)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thr", type=float, default=1.0)
    ap.add_argument("--l2", type=float, default=0.01)
    a = ap.parse_args()
    races, _ = E.build()
    years = sorted({r["key"][0][:4] for r in races})
    # 帯ごと・年ごとに レースごとの (賭け金, 戻り) を溜める
    acc = {b: {} for b in BANDS}
    for y in years:
        if int(y) < 2019:
            continue
        tr = [r for r in races if r["key"][0][:4] < y]
        te = [r for r in races if r["key"][0][:4] == y]
        if len(tr) < 5000 or not te:
            continue
        beta, w = E.fit(E.pack(tr), a.l2)
        for b in BANDS:
            st, rt = [], []
            for r in te:
                p = E.probs(r, beta, w)
                ev = p * r["odds"]
                sel = np.where((ev >= a.thr) & (r["odds"] >= b[0]) & (r["odds"] < b[1]))[0]
                st.append(100.0 * len(sel))
                rt.append(100.0 * r["odds"][r["win"]] if r["win"] in sel else 0.0)
            acc[b][y] = (np.array(st), np.array(rt))
    print(f"■ EV≧{a.thr} の単勝をオッズ帯別に（年ごとの前向き・正則化{a.l2}）")
    print(f"{'オッズ帯':>10}{'点数':>8}{'回収率':>9}{'95%区間':>17}{'プラスの年':>11}   年別")
    for b in BANDS:
        ys = sorted(acc[b])
        st = np.concatenate([acc[b][y][0] for y in ys]); rt = np.concatenate([acc[b][y][1] for y in ys])
        roi, lo, hi = E.roi_ci(st, rt)
        per = []
        for y in ys:
            s, r = acc[b][y]
            per.append(r.sum() / s.sum() if s.sum() else float("nan"))
        pos = sum(1 for v in per if v == v and v > 1.0)
        lab = f"{b[0]:g}〜{b[1]:g}倍" if b[1] < 1e8 else f"{b[0]:g}倍〜"
        print(f"{lab:>10}{int(st.sum() / 100):>8,}{(roi or 0) * 100:>8.1f}%  ［{(lo or 0) * 100:>5.1f}〜{(hi or 0) * 100:>5.1f}%］{pos:>6}/{len(ys)}   "
              + " ".join(f"{v * 100:>4.0f}" if v == v else "  - " for v in per))


if __name__ == "__main__":
    main()
