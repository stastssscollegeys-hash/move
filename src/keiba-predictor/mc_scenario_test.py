# -*- coding: utf-8 -*-
"""
mc_scenario_test.py — 「展開（ペース）と当日の馬場バイアスを潜在シナリオとして何万回も回す」と、予想は良くなるか（2026-11-01新規）
=====================================================================================================
問い: レースごとに「速い流れ／遅い流れ」「内有利／外有利」を確率的に引き（モンテカルロ）、
      前で運ぶ馬・外枠の馬の強さをシナリオごとに傾ける混合モデルは、素の確率（ev_engine の前向き予測 p）より
      実際の着順（上位3頭）をよく当てるか。当てるなら、その確率で買う組み合わせの払戻は市場より上か。
手順（すべて前向き: 学習=2019〜2022のレース、検証=2023〜）:
  1) 素のモデル  : p（ev_engine 年ごと前向き）→ λ-Harville（1.00/0.80/0.70）の上位3頭の順序確率
  2) 混合モデル  : シナリオ s=(Zp, Zb)~N(0,1)² を M回引き、馬の強さ w_i = p_i·exp(bp·Zp·(f_i−f̄) + bb·Zb·(u_i−0.5)) を
                   正規化して λ-Harville。M回の平均＝混合確率（レースの潜在要因で、同じ型の馬が一緒に来る相関が入る）
                   f_i = 前で運ぶ割合（直近5走）, u_i = 馬番/頭数（外ほど大）
  3) (bp, bb) を学習期間の対数尤度で決め、検証期間で素のモデルと比べる（検証で良くならなければ「効かない」）
  4) 検証期間で、混合確率の上位 k 組（馬単・3連複）を100円ずつ買った払戻を、素のモデルと並べる
使い方: python mc_scenario_test.py [--M 200]
"""
from __future__ import annotations
import argparse, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E

SLIM = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "mc_slim.pkl"
LAM = (1.0, 0.8, 0.7)
F30 = E.F.index("前で運ぶ割合（直近5走）")


def build_slim():
    if SLIM.exists():
        return pickle.loads(SLIM.read_bytes())
    preds = {tuple(p["key"]): p for p in C.predictions()}
    E.SOURCE = C.SRC
    races, _ = E.build()
    out = []
    for r in races:
        k = tuple(r["key"])
        if k not in preds:
            continue
        p = preds[k]
        fins = np.asarray(r["fins"])
        if len(p["uma"]) != len(fins) or len(fins) < 8:
            continue
        out.append(dict(key=k, uma=list(p["uma"]), p=np.asarray(p["p"], float), q=np.asarray(p["q"], float),
                        fins=fins, f=np.asarray(r["X"])[:, F30].astype(float)))
    SLIM.write_bytes(pickle.dumps(out))
    return out


def order_prob(w, top):
    """強さ w（シナリオ別 shape=(M,n)）での上位3頭 (a,b,c) の順序確率 shape=(M,)"""
    w = w / w.sum(1, keepdims=True)
    w2, w3 = w ** LAM[1], w ** LAM[2]
    a, b, c = top
    pa = w[:, a]
    pb = w2[:, b] / (w2.sum(1) - w2[:, a])
    pc = w3[:, c] / (w3.sum(1) - w3[:, a] - w3[:, b])
    return pa * pb * pc


def race_ll(rc, bp, bb, M, rng):
    fins = rc["fins"]
    order = np.argsort(fins)
    top = tuple(order[:3])
    p = rc["p"] / rc["p"].sum()
    n = len(p)
    f = rc["f"] - np.nanmean(rc["f"])
    f = np.nan_to_num(f)
    u = np.arange(1, n + 1) / n - 0.5
    if bp == 0 and bb == 0:
        return float(np.log(order_prob(p[None, :], top)[0]))
    z = rng.standard_normal((M, 2))
    w = p[None, :] * np.exp(bp * z[:, :1] * f[None, :] + bb * z[:, 1:] * u[None, :])
    return float(np.log(order_prob(w, top).mean()))


def total_ll(rs, bp, bb, M, seed=7):
    rng = np.random.default_rng(seed)
    return sum(race_ll(r, bp, bb, M, rng) for r in rs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--M", type=int, default=200)
    ap.add_argument("--sub", type=int, default=6000, help="学習レース数（速度のため）")
    a = ap.parse_args()
    rs = build_slim()
    tr = [r for r in rs if r["key"][0][:4] <= "2022"]
    te = [r for r in rs if r["key"][0][:4] >= "2023"]
    rng = np.random.default_rng(1)
    trs = [tr[i] for i in rng.choice(len(tr), min(a.sub, len(tr)), replace=False)]
    print(f"学習 {len(tr):,}R（うち{len(trs):,}Rで格子探索）／検証 {len(te):,}R", flush=True)
    base_tr = total_ll(trs, 0, 0, a.M)
    best = (0.0, 0, 0)
    for bp in (0.0, 0.5, 1.0, 1.5, 2.0):
        for bb in (0.0, 0.3, 0.6, 1.0):
            ll = total_ll(trs, bp, bb, a.M) - base_tr
            print(f"  bp={bp} bb={bb}: 学習の対数尤度 {ll:+.1f}（素のモデルとの差・1Rあたり {ll / len(trs) * 1000:+.2f}‰）", flush=True)
            if ll > best[0]:
                best = (ll, bp, bb)
    _, bp, bb = best
    print(f"採用候補: bp={bp} bb={bb}", flush=True)
    base_te = total_ll(te, 0, 0, a.M)
    mix_te = total_ll(te, bp, bb, a.M)
    d = mix_te - base_te
    print(f"検証 {len(te):,}R: 素 {base_te:.1f} ／ 混合 {mix_te:.1f} ／ 差 {d:+.1f}（1Rあたり {d / len(te) * 1000:+.3f}‰）")
    # レースごとの差のばらつきで有意性（符号の割合・標準誤差）
    rng2 = np.random.default_rng(7)
    diffs = np.array([race_ll(r, bp, bb, a.M, rng2) - race_ll(r, 0, 0, a.M, rng2) for r in te])
    se = diffs.std(ddof=1) / np.sqrt(len(diffs))
    print(f"  レース別差の平均 {diffs.mean() * 1000:+.3f}‰ ／ 標準誤差 {se * 1000:.3f}‰ ／ z={diffs.mean() / se:+.2f} ／ 改善したレース {np.mean(diffs > 0) * 100:.1f}%")


if __name__ == "__main__":
    main()
