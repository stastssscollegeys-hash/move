# -*- coding: utf-8 -*-
"""
mark_scheme_test.py — 印の付け方を比べる（2026-10-07新規・ユーザー指摘「人気どおりに印を付けすぎ」）
================================================================================================
①人気どおりに決まるレースはどれくらいあるか（10年）
②印の付け方ごとに、◎の単勝・複勝、◎-○の馬連・ワイド、◎○▲の馬連BOX・3連複 を100円ずつ買った成績（実際の払戻）
   A 確率順（今）: 勝つ確率の高い順に◎○▲
   B 価値順    : 勝つ確率が一定以上（◎8%・○▲5%）の馬の中で、モデル÷市場 の高い順
   C 混合      : ◎は確率1位、○▲は価値順（◎以外）
   D 中穴寄り  : 4〜9番人気の中で確率の高い順に◎○▲
予測は年ごとの前向き（combo_backtest.predictions、2019〜）。どれも事前に決めた形で、結果を見て選び直さない
"""
from __future__ import annotations
import collections, itertools, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C

preds, pay = C.predictions(), C.load_pay()


def pick(pr, scheme):
    p, q, uma = pr["p"], pr["q"], pr["uma"]
    n = len(p)
    pop = np.argsort(-q)
    rank = {i: r + 1 for r, i in enumerate(pop)}
    if scheme == "A":
        order = list(np.argsort(-p))
    elif scheme == "B":
        hon = [i for i in np.argsort(-(p / q)) if p[i] >= 0.08]
        rest = [i for i in np.argsort(-(p / q)) if p[i] >= 0.05 and (not hon or i != hon[0])]
        order = (hon[:1] + rest)[:3] if hon else list(np.argsort(-p))
    elif scheme == "C":
        h = int(np.argmax(p))
        rest = [i for i in np.argsort(-(p / q)) if i != h and p[i] >= 0.05]
        order = [h] + rest
    else:
        mid = [i for i in np.argsort(-p) if 4 <= rank[i] <= 9]
        order = mid
    order = [i for i in order][:3]
    if len(order) < 3:
        order += [i for i in np.argsort(-p) if i not in order][:3 - len(order)]
    return [uma[i] for i in order], [rank[i] for i in order]


stat = collections.defaultdict(lambda: [0, 0.0, 0])
fav_exact = fav12 = n_r = 0
pop_win = collections.Counter()
ranks = collections.defaultdict(collections.Counter)
for pr in preds:
    k = pr["key"]
    pp = pay.get(f"{k[0]}|{k[1]}|{k[2]}")
    if not pp or "単勝" not in pp:
        continue
    n_r += 1
    q, uma = pr["q"], pr["uma"]
    pop = [uma[i] for i in np.argsort(-q)]
    win = int(next(iter(pp["単勝"])))
    pop_win[pop.index(win) + 1 if win in pop else 99] += 1
    um = next(iter(pp.get("馬連", {"0-0": 0})))
    if set(map(int, um.split("-"))) == set(pop[:2]):
        fav12 += 1
    sf = pp.get("3連複", {})
    if sf and set(map(int, next(iter(sf)).split("-"))) == set(pop[:3]):
        fav_exact += 1
    for sc in "ABCD":
        (h, o, t), rk = pick(pr, sc)
        for r_ in rk:
            ranks[sc][min(r_, 10)] += 1

        def buy(name, typ, combo):
            key = "-".join(map(str, sorted(combo))) if typ not in ("単勝", "複勝") else str(combo[0])
            got = pp.get(typ, {}).get(key, 0)
            s = stat[(sc, name)]
            s[0] += 1; s[1] += got; s[2] += got > 0
        buy("◎単勝", "単勝", [h]); buy("◎複勝", "複勝", [h])
        buy("◎-○馬連", "馬連", [h, o]); buy("◎-○ワイド", "ワイド", [h, o])
        for a_, b_ in itertools.combinations([h, o, t], 2):
            buy("◎○▲馬連BOX", "馬連", [a_, b_])
        buy("◎○▲3連複", "3連複", [h, o, t])
print(f"■ 10年（2019〜・{n_r:,}レース）の決まり方")
print(f"  1番人気が勝つ {pop_win[1]/n_r*100:.1f}% ／ 2番人気 {pop_win[2]/n_r*100:.1f}% ／ 3番人気 {pop_win[3]/n_r*100:.1f}% ／ 4〜6番人気 {sum(pop_win[i] for i in (4,5,6))/n_r*100:.1f}% ／ 7番人気以下 {sum(v for k_, v in pop_win.items() if k_ >= 7)/n_r*100:.1f}%")
print(f"  馬連が1・2番人気で決まる {fav12/n_r*100:.1f}% ／ 3連複が1〜3番人気で決まる {fav_exact/n_r*100:.1f}%")
names = {"A": "A 確率順（今）", "B": "B 価値順", "C": "C ◎確率・○▲価値", "D": "D 中穴（4〜9番人気）"}
for sc in "ABCD":
    tot = sum(ranks[sc].values())
    print(f"\n■ {names[sc]}  印の馬の人気: 1番{ranks[sc][1]/tot*100:.0f}% 2〜3番{(ranks[sc][2]+ranks[sc][3])/tot*100:.0f}% 4〜6番{sum(ranks[sc][i] for i in (4,5,6))/tot*100:.0f}% 7番以下{sum(ranks[sc][i] for i in range(7, 11))/tot*100:.0f}%")
    for nm in ("◎単勝", "◎複勝", "◎-○馬連", "◎-○ワイド", "◎○▲馬連BOX", "◎○▲3連複"):
        n, ret, hit = stat[(sc, nm)]
        print(f"  {nm:<10} {n:>7,}点  的中率 {hit/n*100:5.1f}%  回収率 {ret/n:6.1f}%")
