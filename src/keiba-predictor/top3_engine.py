# -*- coding: utf-8 -*-
"""
top3_engine.py — 「3着以内に来る確率」を直接学習するモデル（2026-10-05新規・提案1）
==================================================================================
なぜ: ev_engine は「勝つ確率」だけを学習している。ワイド・3連複・相手選び・穴拾いは3着以内の精度で決まる。
      当日の内枠の偏り（bias_carry_test.py）も3着以内に効く現象で、勝つ確率に入れても改善しなかった。
モデル: 馬ごとのロジスティック回帰
   logit P(3着内) = a + b・logit(市場の3着内確率) + w・x
   市場の3着内確率は 単勝オッズ→λ-Harville（λ2=0.80・λ3=0.70、keiba_harville_lambda）。x は ev_engine の特徴量（同日の結果は混ぜない）
検証: 年ごとの前向き（その年より前で学習→その年で測る・2019〜）
   ①対数損失の改善（市場の3着内確率を a,b だけで補正したものとの差）
   ②複勝で試す: モデル÷市場 ≧ しきい値 の馬を100円ずつ → 実際の複勝払戻（TARGET の HR）で回収率
使い方: python top3_engine.py --walk [--daybias]
        python top3_engine.py --fit            # 全期間で学習して db/top3_model.json に保存（予想で使う）
"""
from __future__ import annotations
import argparse, json, math, os, sys
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--walk", action="store_true")
ap.add_argument("--fit", action="store_true")
ap.add_argument("--daybias", action="store_true", help="当日の前半バイアスの特徴量も使う")
ap.add_argument("--l2", type=float, default=0.02)
A = ap.parse_args()
os.environ["DAYBIAS"] = "1"                      # 列は全部作り、使う列はここで選ぶ
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
from scipy.optimize import minimize

E.SOURCE = E.DB / "history_target"
L2, L3 = 0.80, 0.70
MODEL = E.DB / "top3_model.json"


def market_top3(q):
    """λ-Harville の3着内確率（全頭）"""
    n = len(q)
    q2, q3 = q ** L2, q ** L3
    p = q.copy()
    for i in range(n):
        for j in range(n):
            if j == i:
                continue
            d2 = q2.sum() - q2[j]
            p2 = q[j] * q2[i] / d2                      # j が1着、i が2着
            p[i] += p2
            for k in range(n):
                if k in (i, j):
                    continue
                d2k = q2.sum() - q2[j]
                pk2 = q[j] * q2[k] / d2k                # j 1着、k 2着
                d3 = q3.sum() - q3[j] - q3[k]
                p[i] += pk2 * q3[i] / d3                # i 3着
    return np.clip(p, 1e-4, 1 - 1e-4)


def logit(p):
    return np.log(p / (1 - p))


def dataset(races, cols):
    Z, y, g, keys = [], [], [], []
    for gi, r in enumerate(races):
        if r["part"] == "live" or any(f is None for f in r["fins"]):
            continue
        m3 = market_top3(r["q"])
        X = r["X"][:, cols]
        Z.append(np.column_stack([np.ones(len(m3)), logit(m3), X]))
        y.append(np.array([1.0 if (f and f <= 3) else 0.0 for f in r["fins"]]))
        g.append(np.full(len(m3), gi))
        keys.append(r["key"])
    return Z, y, g, keys


def fit(Z, y, l2, base_only=False):
    Zc = np.vstack(Z); yc = np.concatenate(y)
    if base_only:
        Zc = Zc[:, :2]
    d = Zc.shape[1]
    reg = np.r_[0.0, 0.0, np.full(d - 2, l2)]

    def f(w):
        u = Zc @ w
        ll = np.sum(yc * u - np.logaddexp(0, u))
        p = 1 / (1 + np.exp(-u))
        grad = Zc.T @ (yc - p)
        return -ll / len(yc) + 0.5 * np.sum(reg * w * w), -grad / len(yc) + reg * w
    w0 = np.zeros(d); w0[1] = 1.0
    return minimize(f, w0, jac=True, method="L-BFGS-B").x


def pred(Zr, w):
    return 1 / (1 + np.exp(-(Zr[:, :len(w)] @ w)))


def main():
    races, _ = E.build()
    names = E.F
    cols = [i for i, n in enumerate(names) if A.daybias or n not in E.DAYBIAS]
    used = [names[i] for i in cols]
    print(f"■ 3着内モデル  データ {len(races):,}レース  特徴量 {len(used)}（当日バイアス{'あり' if A.daybias else 'なし'}）")
    pay = {}
    for f in sorted((E.DB / "history_target").glob("payouts_*.json")):
        pay.update(json.loads(f.read_text(encoding="utf-8")))
    if A.fit:
        Z, y, g, keys = dataset(races, cols)
        w = fit(Z, y, A.l2)
        MODEL.write_text(json.dumps(dict(features=used, w=w.tolist(), l2=A.l2, lam=[L2, L3], daybias=A.daybias, n=len(Z),
                                         data_to=max(k[0] for k in keys)), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"保存 → {MODEL}")
        top = sorted(zip(used, w[2:]), key=lambda t: -abs(t[1]))[:12]
        for n_, v in top:
            print(f"  {v:+.3f} {n_}")
        return
    Z, y, g, keys = dataset(races, cols)
    years = sorted({k[0][:4] for k in keys})
    gains, bets = [], {t: [0, 0.0] for t in (1.0, 1.1, 1.2, 1.3, 1.5)}
    bets_y = {t: {} for t in bets}
    print(f"{'年':>5}{'学習R':>8}{'検証R':>7}{'対数損失の改善/頭':>18}{'  複勝 比≧1.2':>16}")
    for yv in years:
        if yv < "2019":
            continue
        tr = [i for i, k in enumerate(keys) if k[0][:4] < yv]
        te = [i for i, k in enumerate(keys) if k[0][:4] == yv]
        if len(tr) < 5000 or not te:
            continue
        w = fit([Z[i] for i in tr], [y[i] for i in tr], A.l2)
        w0 = fit([Z[i] for i in tr], [y[i] for i in tr], 0.0, base_only=True)
        per_race = []
        for i in te:
            pm, pb, yy = pred(Z[i], w), pred(Z[i][:, :2], w0), y[i]
            llm = np.mean(yy * np.log(pm) + (1 - yy) * np.log(1 - pm))
            llb = np.mean(yy * np.log(pb) + (1 - yy) * np.log(1 - pb))
            per_race.append(llm - llb)
            fk = pay.get(f"{keys[i][0]}|{keys[i][1]}|{keys[i][2]}", {}).get("複勝", {})
            m3 = 1 / (1 + np.exp(-Z[i][:, 1]))
            for j, r_ in enumerate(pm / m3):
                for t in bets:
                    if r_ >= t:
                        uma = races_by_key[keys[i]]["uma"][j]
                        got = fk.get(str(uma), 0) if yy[j] else 0
                        bets[t][0] += 1; bets[t][1] += got
                        bets_y[t].setdefault(yv, [0, 0.0]); bets_y[t][yv][0] += 1; bets_y[t][yv][1] += got
        gains.append(np.array(per_race))
        b = bets_y[1.2].get(yv, [1, 0])
        print(f"{yv:>5}{len(tr):>8,}{len(te):>7,}{np.mean(per_race):>+18.5f}   {b[0]:>6,}頭 {b[1]/max(b[0],1):6.1f}%")
    gg = np.concatenate(gains)
    rng = np.random.default_rng(1)
    bs = [rng.choice(gg, len(gg)).mean() for _ in range(2000)]
    print(f"\n  全年 対数損失の改善 {gg.mean():+.5f}/頭（レース平均） ［{np.percentile(bs, 2.5):+.5f}, {np.percentile(bs, 97.5):+.5f}］")
    for t, (n, ret) in bets.items():
        ys = " ".join(f"{yv[2:]}:{v[1]/max(v[0],1):.0f}%" for yv, v in sorted(bets_y[t].items()))
        print(f"  複勝 モデル÷市場≧{t:.1f}: {n:>7,}頭  回収率 {ret/max(n,1):6.1f}%   年別 {ys}")


if __name__ == "__main__":
    races_by_key = {}
    _b = E.build
    def _wrap(*a, **k):
        out = _b(*a, **k)
        for r in out[0]:
            races_by_key[r["key"]] = r
        return out
    E.build = _wrap
    main()
