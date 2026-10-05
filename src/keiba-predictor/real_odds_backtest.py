# -*- coding: utf-8 -*-
"""
real_odds_backtest.py — 実際の確定オッズ（JV-Link O1〜O6）を使って、全券種の買い目エンジンを検証する（2026-10-02）
================================================================================================
bet_engine.py の検証は「オッズ＝払戻率÷市場確率」の仮定つきだった。ここでは **実際の組み合わせオッズ** を使う:
  期待値 EV ＝ モデル確率 × 実オッズ（モデルは ev_engine の年ごと前向き予測＝その年より前だけで学習）
  対象: 2025年10月〜2026年9月の3,480レース（JV-Link で全券種のオッズが取れた期間。すべて学習に使っていない年）。
  選び方: EV≧しきい値 かつ 市場確率（払戻率÷オッズ）≧下限 の組を、EVの高い順に Σ(1/オッズ)=1/T まで足す（T＝目標倍率）。
  精算: 実際の払戻（TARGET の HR）。確定オッズで選ぶので、発売中のオッズで選ぶ本番より有利な条件である点に注意。
使い方: python real_odds_backtest.py
"""
from __future__ import annotations
import collections, statistics, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import bet_engine as B
import jv_odds as J


def main():
    preds, pay = C.predictions(), C.load_pay()
    store = J.OddsStore()
    have = set(store.races())
    rows = []
    for i, pr in enumerate(preds):
        k = (pr["key"][0], pr["key"][1], pr["key"][2])
        if k not in have:
            continue
        pm = B.tables(pr["p"], pr["uma"])
        pqh = B.tables(pr["q"], pr["uma"])
        odds = {}
        o1 = store.get(k, "O1") or {}
        odds.update(o1)
        for oid in ("O2", "O3", "O4", "O5", "O6"):
            odds.update(store.get(k, oid) or {})
        cands = []
        for t in B.TYPES:
            if t not in pm or t not in odds:
                continue
            keys, prob = pm[t]
            probq = pqh[t][1]
            tab = odds[t]
            for key, p_, pqh_ in zip(keys, prob, probq):
                o = tab.get(key)
                if not o or o <= 1.0:
                    continue
                pq = B.TAKE[t] / o
                if pq < B.MINQ[t]:
                    continue
                ev = p_ * o
                rh = p_ / pqh_ if pqh_ > 0 else 0.0
                if rh >= 1.15 or ev >= 1.05:
                    cands.append((t, key, float(p_), float(pq), float(o), float(ev), float(rh)))
        rows.append(dict(key=k, year=k[0][:4], kind=B.race_kind(pr["q"]), cands=cands, pay=pay.get(f"{k[0]}|{k[1]}|{k[2]}", {})))
        if len(rows) % 500 == 0:
            print(f"  準備 {len(rows):,}", flush=True)
    print(f"■ 実オッズつきレース {len(rows):,}（{rows[0]['key'][0]}〜{rows[-1]['key'][0]}）／候補（EV≧1.05）のあるレース {sum(1 for r in rows if r['cands']):,}")

    def run(label, thr, T_mode, types=None, budget=10000, ev_min=1.12, only=None, max_pts=12, rmin=0.0, evmax=None, sortby=5):
        st, rt, hit_r, mult = [], [], 0, []
        per_type = collections.defaultdict(lambda: [0.0, 0.0])
        daily = collections.defaultdict(float)
        for r in rows:
            if only and r["kind"] != only:
                continue
            cs = sorted((c for c in r["cands"] if c[5] >= thr and c[6] >= rmin and (evmax is None or c[5] <= evmax) and (not types or c[0] in types)), key=lambda c: -c[sortby])
            if not cs:
                continue
            T = T_mode if isinstance(T_mode, (int, float)) else {"堅い": 2.5, "普通": 4.0, "荒れ": 8.0}[r["kind"]]
            chosen, S = [], 0.0
            for c in cs:
                if chosen and S + 1.0 / c[4] > 1.0 / T * 1.15:
                    continue
                chosen.append(c); S += 1.0 / c[4]
                if S >= 1.0 / T or len(chosen) >= max_pts:
                    break
            w = np.array([1.0 / c[4] for c in chosen])
            amt = np.floor(budget * w / w.sum() / 100.0) * 100.0
            keep = amt >= 100
            chosen = [c for c, k in zip(chosen, keep) if k]; amt = amt[keep]
            if not len(chosen):
                continue
            if sum(a * c[2] * c[4] for a, c in zip(amt, chosen)) / amt.sum() < ev_min:
                continue
            stake = float(amt.sum()); ret = 0.0
            for a, c in zip(amt, chosen):
                got = r["pay"].get(c[0], {}).get("-".join(map(str, c[1])), 0) * a / 100.0
                ret += got
                per_type[c[0]][0] += a; per_type[c[0]][1] += got
            st.append(stake); rt.append(ret); daily[r["key"][0]] += ret - stake
            hit_r += ret > 0
            if ret > 0:
                mult.append(ret / stake)
        if not st:
            print(f"  {label:<30} 該当なし"); return
        lo, hi = B.boot(st, rt)
        cum = np.cumsum([v for _, v in sorted(daily.items())]); dd = float((np.maximum.accumulate(cum) - cum).max())
        pt = " ".join(f"{t}{v[1]/v[0]*100:.0f}%" for t, v in per_type.items() if v[0] >= 20000)
        print(f"  {label:<30} {len(st):>5,}R買い({len(st)/len(rows)*100:4.1f}%) 回収 {sum(rt)/sum(st)*100:6.1f}% ［{lo*100:5.1f}〜{hi*100:5.1f}%］ 的中 {hit_r/len(st)*100:4.1f}% "
              f"当たり時{statistics.median(mult) if mult else 0:4.1f}倍 損益{(sum(rt)-sum(st))/10000:+6.0f}万円 最大DD{dd/10000:4.0f}万円 | {pt}")

    print("")
    print("■ E. 市場（単勝オッズ由来）に対する比 ≧1.3 を必須にし、実オッズの期待値と組み合わせる（全券種・型ごとの目標倍率）")
    for lab, kw in (("比≧1.3（実オッズの期待値は問わない）", dict(thr=0.0, rmin=1.3, sortby=6, ev_min=0.0)),
                    ("比≧1.3 かつ 実EV≧1.0", dict(thr=1.0, rmin=1.3, sortby=6, ev_min=0.0)),
                    ("比≧1.3 かつ 実EV≧1.1", dict(thr=1.1, rmin=1.3, sortby=6, ev_min=0.0)),
                    ("比≧1.3 かつ 実EV≧1.3", dict(thr=1.3, rmin=1.3, sortby=6, ev_min=0.0)),
                    ("比≧1.3 かつ 実EV＜1.0", dict(thr=0.0, rmin=1.3, evmax=0.999, sortby=6, ev_min=0.0)),
                    ("比≧1.5（実オッズの期待値は問わない）", dict(thr=0.0, rmin=1.5, sortby=6, ev_min=0.0))):
        run(lab, kw.pop("thr"), "型", **kw)
    print("")
    print("■ F. 比≧1.3・券種別")
    for ts in (("単勝",), ("複勝",), ("馬連",), ("ワイド",), ("馬単",), ("3連複",), ("3連単",)):
        run("・".join(ts), 0.0, "型", types=ts, rmin=1.3, sortby=6, ev_min=0.0)
    print("")
    print("■ G. 候補ルールE2（馬連・ワイド・馬単・比≧1.3）の型・目標倍率・予算の違い")
    E2 = ("馬連", "ワイド", "馬単")
    run("E2 型ごとの目標倍率", 0.0, "型", types=E2, rmin=1.3, sortby=6, ev_min=0.0)
    run("E2 型ごと・実EV≧0.9も要求", 0.9, "型", types=E2, rmin=1.3, sortby=6, ev_min=0.0)
    for T in (2.0, 4.0, 8.0):
        run(f"E2 目標{T:.0f}倍", 0.0, T, types=E2, rmin=1.3, sortby=6, ev_min=0.0)
    for k in ("堅い", "普通", "荒れ"):
        run(f"E2 {k}のみ", 0.0, "型", types=E2, rmin=1.3, sortby=6, ev_min=0.0, only=k)
    for mp in (3, 6, 12):
        run(f"E2 最大{mp}点", 0.0, "型", types=E2, rmin=1.3, sortby=6, ev_min=0.0, max_pts=mp)



if __name__ == "__main__":
    main()
