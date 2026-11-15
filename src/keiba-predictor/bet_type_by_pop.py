# -*- coding: utf-8 -*-
"""bet_type_by_pop.py — 同じ2頭を買うなら ワイド・馬連・馬単 のどれが回収率が良いか（2026-11-07新規・ユーザーの問い）
2頭の人気の組み合わせ（人気=1〜3番人気／中穴=4〜8番人気／穴=9番人気以下）ごとに、全ての組を100円ずつ買ったときの実際の払戻で比べる。
馬単は「人気が上の馬→下の馬」（表）と「下→上」（裏）を別に集計。モデルで割安な組（λ-Harvilleの組の確率が市場の1.2倍以上）に絞った場合も出す。
データ: db/mc_slim.pkl（2019〜2026・年ごと前向きのモデル p・市場 q・着順）＋ history_target/payouts_*.json"""
import json, pickle, collections, sys
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
import bet_engine as B
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
races = pickle.loads((DB / "mc_slim.pkl").read_bytes())
pay = {}
for f in sorted((DB / "history_target").glob("payouts_*.json")): pay.update(json.loads(f.read_text(encoding="utf-8")))
cls = lambda r: "人気" if r <= 3 else "中穴" if r <= 8 else "穴"
def pairprob(T):
    S2 = T.sum(2); return S2 + S2.T   # 馬連（1・2着の組）
# key: (区分, フィルタ) → 券種 → [投資, 払戻, 的中数]
R = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
Y = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))  # 年別（区分×券種）
for rc in races:
    k = f"{rc['key'][0]}|{rc['key'][1]}|{rc['key'][2]}"; P = pay.get(k)
    if not P or "馬連" not in P or "ワイド" not in P or "馬単" not in P: continue
    uma = rc["uma"]; n = len(uma)
    if n < 8: continue
    q = rc["q"] / rc["q"].sum(); p = rc["p"] / rc["p"].sum()
    rank = {i: r + 1 for r, i in enumerate(np.argsort(-q))}
    fin = {int(uma[i]): int(rc["fins"][i]) for i in range(n)} if "fins" in rc else None
    Tq, Tp = B.tensor(q), B.tensor(p); Pq, Pp = pairprob(Tq), pairprob(Tp)
    yr = rc["key"][0][:4]
    top = [i for i in range(n) if rank[i] <= 12]
    for a_ in range(len(top)):
        for b_ in range(a_ + 1, len(top)):
            i, j = top[a_], top[b_]
            hi, lo = (i, j) if rank[i] < rank[j] else (j, i)
            cat = "-".join(sorted([cls(rank[i]), cls(rank[j])], key=["人気", "中穴", "穴"].index))
            ui, uj = uma[hi], uma[lo]
            key2 = f"{min(ui, uj)}-{max(ui, uj)}"
            pu = P["馬連"].get(key2, 0); pw = P["ワイド"].get(key2, 0)
            ph = P["馬単"].get(f"{ui}-{uj}", 0); pr = P["馬単"].get(f"{uj}-{ui}", 0)
            val = Pp[i, j] / Pq[i, j] if Pq[i, j] > 0 else 0
            for flt in (["全部"] + (["割安(組1.2倍以上)"] if val >= 1.2 else [])):
                for bt, g in (("ワイド", pw), ("馬連", pu), ("馬単 表(人気上→下)", ph), ("馬単 裏(下→上)", pr)):
                    x = R[(cat, flt)][bt]; x[0] += 100; x[1] += g; x[2] += g > 0
                    if flt == "全部": y = Y[(cat, bt)][yr] if False else None
            for bt, g in (("ワイド", pw), ("馬連", pu)):
                yy = Y[(cat, bt)]; yy[yr] = yy.get(yr, [0, 0]) if isinstance(yy.get(yr), list) else [0, 0]
                yy[yr][0] += 100; yy[yr][1] += g
out = []
pr_ = lambda s: (print(s), out.append(s))
for flt in ("全部", "割安(組1.2倍以上)"):
    pr_(f"\n■ {flt}（2019〜2026・100円ずつ・実際の払戻）")
    for cat in ("人気-人気", "人気-中穴", "人気-穴", "中穴-中穴", "中穴-穴", "穴-穴"):
        if (cat, flt) not in R: continue
        row = R[(cat, flt)]; n_ = row["ワイド"][0] // 100
        s = f"{cat:<6} {n_:>7}組 | " + " | ".join(f"{bt} 回収{v[1]/v[0]:5.1%} 的中{v[2]/(v[0]/100):5.1%} 当たり平均{(v[1]/max(1,v[2])):>7,.0f}円" for bt, v in row.items())
        pr_(s)
pr_("\n■ 年別の回収（全部・ワイドと馬連）")
for cat in ("人気-人気", "人気-中穴", "中穴-中穴", "中穴-穴"):
    for bt in ("ワイド", "馬連"):
        yy = Y[(cat, bt)]
        pr_(f"{cat} {bt}: " + " ".join(f"{y[2:]}:{v[1]/v[0]:.0%}" for y, v in sorted(yy.items())))
(DB / "bet_type_by_pop.txt").write_text("\n".join(out), encoding="utf-8")
