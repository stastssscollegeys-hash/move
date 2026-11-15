# -*- coding: utf-8 -*-
"""mc_wide_backtest.py — 明日使う「ワイドで的中35%以上・期待値最大」の買い方を、過去24,927レース（2019〜2026・前向き予測）で実際の払戻で検証（2026-11-07新規）
入力: db/mc_slim.pkl（年ごと前向きのモデル確率 p・市場確率 q・着順）／history_target/payouts_*.json（実際のワイド払戻）
確率: p_a ∝ q^(1−a)·p^a（a=0 市場だけ／0.5 半分／1 モデルそのまま）→ λ-Harville（シミュレーションを無限回回したのと同じ厳密計算）
ワイドの事前オッズは過去分が無い → 市場確率から推定 O≈0.775/P市場(組)（控除率22.5%）。選ぶのは推定、払うのは実際の払戻
戦略: F=frontier（BOX上位3/4/5・軸流し3/4/5から的中35%以上で期待値最大・1万円・戻り均等配分）／V=期待値1.1以上の組を上位5点・各1,000円／M=市場上位3頭のワイドBOX
"""
import json, pickle, sys, collections
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
import bet_engine as B
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
races = pickle.loads((DB / "mc_slim.pkl").read_bytes())
pay = {}
for f in sorted((DB / "history_target").glob("payouts_*.json")):
    pay.update(json.loads(f.read_text(encoding="utf-8")))

def wide(T):
    S2, S1, S0 = T.sum(2), T.sum(1), T.sum(0)
    return S2 + S2.T + S1 + S1.T + S0 + S0.T

def alloc(pairs, O, budget=10000):
    inv = np.array([1 / O[i, j] for i, j in pairs]); w = inv / inv.sum()
    return [max(100, int(round(budget * x / 100)) * 100) for x in w]

def hit_ev(pairs, st, W, T, O, n):
    # 的中率（どれか1点）と期待回収率（モデル）を3着内の組から厳密に
    m = T > 1e-9
    top = np.argwhere(m); pr = T[m]
    r = np.zeros(len(pr))
    for (i, j), sk in zip(pairs, st):
        r += (((top == i).any(1)) & ((top == j).any(1))) * sk * O[i, j]
    return float(pr[r > 0].sum()), float((pr * r).sum() / sum(st))

res = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0, 0, 0]))  # 戦略→年→[投資, 払戻, 的中R, R]
for R in races:
    key = "|".join([R["key"][0], R["key"][1], str(R["key"][2])])
    pw = pay.get(key, {}).get("ワイド")
    if not pw: continue
    uma, n = R["uma"], len(R["uma"])
    if n < 6: continue
    yr = R["key"][0][:4]
    q = R["q"] / R["q"].sum(); Tq = B.tensor(q); Wq = wide(Tq)
    O = np.where(Wq > 1e-6, 0.775 / np.maximum(Wq, 1e-6), 0); O = np.clip(O, 1.0, 999)
    real = lambda i, j: pw.get(f"{min(uma[i], uma[j])}-{max(uma[i], uma[j])}", 0)
    def book(name, pairs, st):
        if not pairs: return
        x = res[name][yr]; x[0] += sum(st); g = sum(s * real(i, j) / 100 for (i, j), s in zip(pairs, st)); x[1] += g; x[2] += g > 0; x[3] += 1
    # 市場上位3頭BOX
    om = list(np.argsort(-q)[:3]); pm = [(a, b) for k, a in enumerate(om) for b in om[k + 1:]]
    book("M 市場上位3頭BOX", pm, alloc(pm, O))
    for a in (0.0, 0.5, 1.0):
        p = (q ** (1 - a)) * (R["p"] ** a); p = p / p.sum()
        T = B.tensor(p) if a else Tq; W = wide(T)
        t3 = T.sum(axis=(1, 2)) + T.sum(axis=(0, 2)) + T.sum(axis=(0, 1))
        order = list(np.argsort(-t3)); ax = int(np.argmax(p))
        cands = []
        for k in (3, 4, 5):
            top = order[:k]; cands.append([(x, y) for m, x in enumerate(top) for y in top[m + 1:]])
            rest = [u for u in order if u != ax][:k]; cands.append([(ax, y) for y in rest])
        best = None
        for c in cands:
            c = [(min(i, j), max(i, j)) for i, j in c]; st = alloc(c, O)
            h, ev = hit_ev(c, st, W, T, O, n)
            sc = (h >= 0.35, ev if h >= 0.35 else h * ev)
            if best is None or sc > best[0]: best = (sc, c, st)
        book(f"F frontier a={a}", best[1], best[2])
        if a == 1.0:
            evb = best[0][1] if best[0][0] else None
            if evb is not None:
                b_ = "1.00以上" if evb >= 1.0 else "0.90〜1.00" if evb >= 0.9 else "0.80〜0.90" if evb >= 0.8 else "0.80未満"
                book(f"F a=1 見込み期待値{b_}", best[1], best[2])
            kind = "BOX" if len({x for pr_ in best[1] for x in pr_}) > len(best[1]) else "流し"
            book(f"F a=1 形={'流し' if all(ax in pr_ for pr_ in best[1]) else 'BOX'}", best[1], best[2])
        iu = np.triu_indices(n, 1); evs = W[iu] * O[iu]
        sel = [(int(iu[0][k]), int(iu[1][k])) for k in np.argsort(-evs)[:5] if evs[k] >= 1.1]
        book(f"V 期待値1.1以上の上位5点 a={a}", sel, [1000] * len(sel))

def ci(name):
    ys = sorted(res[name]); inv = sum(res[name][y][0] for y in ys); ret = sum(res[name][y][1] for y in ys)
    # 年ごとのブートストラップ（レース単位の代わりに年合計の比で簡易表示）
    return inv, ret
out = []
for name in sorted(res):
    ys = sorted(res[name]); inv, ret = ci(name)
    h = sum(res[name][y][2] for y in ys); nR = sum(res[name][y][3] for y in ys)
    early = sum(res[name][y][1] for y in ys if y <= "2022") / max(1, sum(res[name][y][0] for y in ys if y <= "2022"))
    late = sum(res[name][y][1] for y in ys if y >= "2023") / max(1, sum(res[name][y][0] for y in ys if y >= "2023"))
    line = f"{name:<26} {nR:>6}R 回収{ret/inv:6.1%} 何か当たる{h/nR:5.1%} ／ 2019-22 {early:5.1%} ／ 2023-26 {late:5.1%} ／ 年別 " + " ".join(f"{y[2:]}:{res[name][y][1]/res[name][y][0]:.0%}" for y in ys)
    print(line); out.append(line)
(DB / "mc_wide_backtest.txt").write_text("\n".join(out), encoding="utf-8")
