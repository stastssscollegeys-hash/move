# -*- coding: utf-8 -*-
"""
band_hitrate.py — 人気帯ごとの「実際の的中率」を確定払戻から作る（2026-09-26新規）
====================================================================================
なぜ必要か
----------
kaime_select.py の的中率は Harville 近似で出していたが、相手が人気薄に寄ると
実際よりかなり楽観的な数字が出る（馬連BOX3で的中率10.6%＝実測より高すぎ）。
推定式を係数で殴るのではなく、**払戻データで直接数える**。

出力: daily_pdca/db/band_hitrate.json
  {"馬連": {"2-6": {"n":…, "hit":…, "rate":…, "mean_yen":…}, …}, "ワイド": {...},
   "単勝": {"2": {...}}, "馬単": {"2>6": {...}}, "3連複": {"1-3-8": {...}}}
使い方: python band_hitrate.py
"""
from __future__ import annotations
import collections, itertools, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
MAXPOP = 14           # これより下の人気は帯を作らない（サンプルが薄い）

pays = json.loads((DB / "payouts.json").read_text(encoding="utf-8"))
res = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))

pop = collections.defaultdict(dict)
for r in res:
    try:
        pop[(r["date"], r["競馬場"], int(r["R"]))][int(float(r["馬番"]))] = int(float(r["人気"]))
    except (TypeError, ValueError, KeyError):
        continue

acc = {t: collections.defaultdict(lambda: [0, 0, 0]) for t in ("単勝", "馬連", "ワイド", "馬単", "3連複")}
n_race = 0
for rid, v in pays.items():
    p = pop.get((v.get("date"), v.get("venue"), int(v.get("R", 0))))
    if not p or "単勝" not in v["payouts"]:
        continue
    n_race += 1
    P = v["payouts"]
    hit = {}
    for t in ("単勝", "馬連", "ワイド", "馬単", "3連複"):
        for x in P.get(t, []):
            c = x["combo"]
            nums = tuple(int(y) for y in c.split("-")) if "-" in c else (int(c),)
            key = nums if t == "馬単" else tuple(sorted(nums))
            hit[(t, key)] = x["yen"]
    umas = [u for u in sorted(p) if p[u] <= MAXPOP]
    # 単勝
    for u in umas:
        e = acc["単勝"][str(p[u])]
        e[0] += 1
        y = hit.get(("単勝", (u,)))
        if y:
            e[1] += 1; e[2] += y
    # 2頭組（馬連・ワイド・馬単）
    for a, b in itertools.combinations(umas, 2):
        i, j = sorted((p[a], p[b]))
        for t in ("馬連", "ワイド"):
            e = acc[t][f"{i}-{j}"]
            e[0] += 1
            y = hit.get((t, tuple(sorted((a, b)))))
            if y:
                e[1] += 1; e[2] += y
        for x, y_ in ((a, b), (b, a)):
            e = acc["馬単"][f"{p[x]}>{p[y_]}"]
            e[0] += 1
            yy = hit.get(("馬単", (x, y_)))
            if yy:
                e[1] += 1; e[2] += yy
    # 3頭組（人気10位まで・組合せ数を抑える）
    t3 = [u for u in umas if p[u] <= 10]
    for a, b, c in itertools.combinations(t3, 3):
        k = "-".join(str(x) for x in sorted((p[a], p[b], p[c])))
        e = acc["3連複"][k]
        e[0] += 1
        y = hit.get(("3連複", tuple(sorted((a, b, c)))))
        if y:
            e[1] += 1; e[2] += y

out = {}
for t, d in acc.items():
    out[t] = {k: {"n": n, "hit": h, "rate": round(h / n, 5), "mean_yen": round(y / max(h, 1), 1),
                  "roi": round(y / n, 1)}
              for k, (n, h, y) in d.items() if n >= 100}
p = DB / "band_hitrate.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{n_race}レースから較正 → {p}")
for t in out:
    print(f"  {t}: {len(out[t])}帯")
print("\n■ サンプル（馬連・人気帯別の実測的中率）")
for k in ("1-2", "1-3", "2-3", "2-6", "3-9", "6-9", "2-9"):
    if k in out["馬連"]:
        d = out["馬連"][k]
        print(f"  馬連 {k}人気  n={d['n']:>5}  的中{d['rate']*100:>5.2f}%  平均{d['mean_yen']:>8.0f}円  回収{d['roi']:>4.0f}%")
