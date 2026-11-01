# -*- coding: utf-8 -*-
"""
mc_portfolio.py — 1レースを何百万回もシミュレーションして、全券種の組み合わせの期待値と的中率を出す（2026-11-01新規）
=====================================================================================================
入力: 馬ごとの勝つ確率 p（cards_*.json の p_model）と、odds_snapshot の全券種オッズ
手順: λ-Harville（1着 p、2着 p^0.8、3着 p^0.7）で上位3頭を N 回サンプリング（Gumbel-max・分割実行でメモリ節約）
      → 3連単の出現回数から 馬単・馬連・3連複・ワイド・単勝・複勝 の確率を集計 → 期待値＝確率×オッズ
      --bb を付けると、レースごとに外枠有利の強さを N(0,1) で揺らす混合（mc_scenario_test.py: 検証で z≈+1.6＝有意でない）
🔴 サンプリングは入力の確率を再現するだけ。確率そのものが市場より正しい分しか期待値は出ない（確率が同じなら厳密計算と一致する）。
使い方: python mc_portfolio.py --card 20261101 --race 天皇賞 --snap 1350 [--N 2000000] [--bb 0.8]
"""
from __future__ import annotations
import argparse, itertools, json, sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"


def simulate(p, N=2_000_000, bb=0.0, seed=1, chunk=250_000):
    n = len(p)
    rng = np.random.default_rng(seed)
    logp = np.log(p / p.sum())
    u = np.arange(1, n + 1) / n - 0.5
    cnt = np.zeros(n ** 3, dtype=np.int64)
    done = 0
    while done < N:
        m = min(chunk, N - done)
        shift = (bb * rng.standard_normal((m, 1)) * u[None, :]) if bb else 0.0
        lp = logp[None, :] + shift
        g = lambda: rng.gumbel(size=(m, n))
        s1 = lp + g()
        a = s1.argmax(1)
        s2 = 0.8 * lp + g(); s2[np.arange(m), a] = -np.inf
        b = s2.argmax(1)
        s3 = 0.7 * lp + g(); s3[np.arange(m), a] = -np.inf; s3[np.arange(m), b] = -np.inf
        c = s3.argmax(1)
        cnt += np.bincount((a * n + b) * n + c, minlength=n ** 3)
        done += m
    return (cnt / N).reshape(n, n, n)


def fnum(x):
    return float(str(x).replace(",", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="20261101")
    ap.add_argument("--race", default="天皇賞")
    ap.add_argument("--snap", default="1350")
    ap.add_argument("--N", type=int, default=2_000_000)
    ap.add_argument("--bb", type=float, default=0.0)
    ap.add_argument("--rid", default="202605041111")
    a = ap.parse_args()
    cards = json.loads((BASE / a.card / "research" / f"cards_{a.card}.json").read_text(encoding="utf-8"))["cards"]
    c = next(x for x in cards if a.race in (x.get("name") or ""))
    H = {h["uma"]: h for h in c["horses"]}
    uma = sorted(H)
    p = np.array([H[u]["p_model"] for u in uma])
    snap = json.loads((BASE / "daily_pdca" / "db" / "odds_snapshots" / a.card / f"{a.rid}_{a.snap}.json").read_text(encoding="utf-8"))["odds"]
    n = len(uma)
    T = simulate(p, a.N, a.bb)
    idx = {u: i for i, u in enumerate(uma)}
    out = []                                      # (券種, 表記, 確率, オッズ, 期待値)

    def add(kind, combo, prob, key):
        o = snap[kind].get(key)
        if o:
            od = fnum(o[0])
            out.append((kind, combo, prob, od, prob * od))
    for u in uma:
        i = idx[u]
        add("単勝", f"{u}", T[i].sum(), f"{u:02d}")
    for x, y in itertools.permutations(uma, 2):
        add("馬単", f"{x}→{y}", T[idx[x], idx[y]].sum(), f"{x:02d}{y:02d}")
    for x, y in itertools.combinations(uma, 2):
        i, j = idx[x], idx[y]
        add("馬連", f"{x}-{y}", T[i, j].sum() + T[j, i].sum(), f"{x:02d}{y:02d}")
    for x, y, z in itertools.combinations(uma, 3):
        i, j, k = idx[x], idx[y], idx[z]
        pr = T[i, j, k] + T[i, k, j] + T[j, i, k] + T[j, k, i] + T[k, i, j] + T[k, j, i]
        add("3連複", f"{x}-{y}-{z}", pr, f"{x:02d}{y:02d}{z:02d}")
    for x, y, z in itertools.permutations(uma, 3):
        add("3連単", f"{x}→{y}→{z}", T[idx[x], idx[y], idx[z]], f"{x:02d}{y:02d}{z:02d}")
    print(f"{c.get('name')} N={a.N:,} bb={a.bb} 頭数={n}")
    for kind in ("単勝", "馬単", "馬連", "3連複", "3連単"):
        rows = [r for r in out if r[0] == kind]
        pos = [r for r in rows if r[4] >= 1.0]
        tot = sum(r[2] for r in pos)
        print(f"\n[{kind}] {len(rows)}通り／期待値≧1.0: {len(pos)}通り（的中確率の合計 {tot * 100:.1f}%）／全体の平均期待値 {np.mean([r[4] for r in rows]):.3f}")
        for r in sorted(rows, key=lambda r: -r[4])[:5]:
            print(f"   {r[1]:<12} 確率{r[2] * 100:6.2f}% オッズ{r[3]:>9.1f} 期待値{r[4]:.2f}")


if __name__ == "__main__":
    main()
