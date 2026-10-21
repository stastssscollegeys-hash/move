# -*- coding: utf-8 -*-
"""
fresh_test.py — 新しく入ったレース（まだどのモデルも見ていない区間）で、エンジンの版を比べる（2026-10-07新規・毎週のPDCA）
=====================================================================================================================
学習: --cut より前のすべて ／ 判定: --cut 以降（毎週データベースに足した分）
見るもの: ①市場に対する対数尤度の改善 ②ルールE2.1（馬連・ワイド・馬単・比≧1.3・実オッズ期待値≧0.9）を実オッズで買った場合の収支
使い方: python fresh_test.py --cut 20260919            # 今のエンジン（調教あり）
        CHOKYO=0 python fresh_test.py --cut 20260919   # 調教なしの旧版
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import bet_engine as B
import jv_odds as J

ap = argparse.ArgumentParser()
ap.add_argument("--cut", required=True)
ap.add_argument("--l2", type=float, default=0.01)
a = ap.parse_args()
E.SOURCE = E.DB / "history_target"
races, _ = E.build()
tr = [r for r in races if r["key"][0] < a.cut and r["part"] != "live"]
te = [r for r in races if r["key"][0] >= a.cut and r["part"] != "live"]
beta, w = E.fit(E.pack(tr), a.l2)
zero = np.zeros(len(E.F))
d = E.loglik(E.pack(te), beta, w) - E.loglik(E.pack(te), 1.0, zero)
lo, hi = E.boot_mean(d)
tag = "調教なし（旧）" if os.environ.get("CHOKYO") == "0" else "調教あり（今）"
print(f"■ {tag}  学習 {len(tr):,}R（〜{a.cut}前）／判定 {len(te):,}R（{a.cut}〜）")
print(f"  対数尤度の改善 {d.mean():+.5f}/レース ［{lo:+.5f}, {hi:+.5f}］")
pay = {}
for f in sorted((E.DB / "history_target").glob("payouts_2026.json")):
    pay.update(json.loads(f.read_text(encoding="utf-8")))
store = J.OddsStore(years=(2026,))
st = rt = 0.0
nr = 0
hon_top3 = fav_top3 = 0
for r in te:
    p = E.probs(r, beta, w)
    fins = r["fins"]
    i_h = int(np.argmax(p)); i_f = int(np.argmax(r["q"]))
    hon_top3 += bool(fins[i_h] and fins[i_h] <= 3); fav_top3 += bool(fins[i_f] and fins[i_f] <= 3)
    k = r["key"]
    odds = {}
    for oid in ("O2", "O3", "O4"):
        odds.update(store.get(k, oid) or {})
    if not odds:
        continue
    pm, pq = B.tables(p, r["uma"]), B.tables(r["q"], r["uma"])
    bets = []
    for t in ("馬連", "ワイド", "馬単"):
        if t not in odds:
            continue
        keys, prob = pm[t]
        probq = pq[t][1]
        for key, pp, qq in zip(keys, prob, probq):
            o = odds[t].get(key)
            if not o or qq <= 0 or B.TAKE[t] / o < B.MINQ[t]:
                continue
            if pp / qq >= 1.3 and pp * o >= 0.9:
                bets.append((t, key, o))
    if not bets:
        continue
    nr += 1
    T_ = {"堅い": 2.5, "普通": 4.0, "荒れ": 8.0}[B.race_kind(r["q"])]
    wts = np.array([1 / o for *_, o in bets])
    amt = np.floor(10000 * wts / wts.sum() / 100) * 100
    pp_ = pay.get(f"{k[0]}|{k[1]}|{k[2]}", {})
    for (t, key, o), am in zip(bets, amt):
        st += am
        rt += pp_.get(t, {}).get("-".join(map(str, key)), 0) * am / 100
print(f"  ◎（勝つ確率1位）の3着内 {hon_top3}/{len(te)}（1番人気 {fav_top3}/{len(te)}）")
print(f"  E2.1を実オッズで: {nr}レース 賭け金{int(st):,}円 → 払戻{int(rt):,}円（回収率{rt / st * 100 if st else 0:.0f}%）")
