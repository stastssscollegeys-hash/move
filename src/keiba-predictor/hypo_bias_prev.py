# -*- coding: utf-8 -*-
"""
hypo_bias_prev.py — 「前走は馬場・展開（バイアス）が向かなくて負けただけの馬は過小評価されているか／恵まれて好走しただけの馬は過大評価か」（2026-11-01新規）
==========================================================================================================================
ユーザーの核心（口述4点目）: 不利・ペース・トラックバイアスが合わず負けた実力馬を、人気薄のうちに拾う。恵まれて好走しただけの人気馬を軽視する。
前走の逆風度 D を、前走と同じ「開催日×競馬場×芝ダ」の【他のレース】の成績から作る（そのレース自身は除く＝リークなし。結果から後で分かる偏りだが、
次走の時点では既に分かっている情報）:
  脚質グループ（前=最初のコーナーが頭数の25%以内／後ろ=65%以上／中）の 3着内率÷人気から期待される値（比）
  枠グループ（内=馬番が前1/3／外=後ろ1/3／中）の同じ比
  D = 脚質比 × 枠比（各比は pop 期待に3を足して縮める）。D≦0.75=逆風、D≧1.30=追い風
  逆風で負けた  : D≦0.75 かつ 前走6着以下        追い風で好走 : D≧1.30 かつ 前走3着以内
検定: ① 同じ人気帯の中で次走の3着内率が期待よりずれるか（前半・後半の両関門）／ 単勝回収率
      ② モデルの勝率 p（ev_engine 前向き2019〜）に対する勝ち数のずれ（モデルに無い情報か）
使い方: python hypo_bias_prev.py
"""
from __future__ import annotations
import collections, json, math, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
KEEP = ("date", "競馬場", "R", "距離", "馬名", "馬番", "人気", "単勝オッズ", "着順int", "コーナー通過", "頭数")
K = 3.0


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def surf(d):
    s = str(d or "")
    return "芝" if s.startswith("芝") else ("ダ" if s.startswith("ダ") else None)


rows = []
for f in sorted((DB / "history_target").glob("results_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        o = {k: r.get(k) for k in KEEP}
        o["fin"] = int(num(o["着順int"])) if num(o["着順int"]) else None
        o["pop"] = min(int(num(o["人気"])), 18) if num(o["人気"]) else None
        o["n"] = int(num(o["頭数"]) or 0)
        o["uma"] = int(num(o["馬番"]) or 0)
        o["R"] = int(num(o["R"]) or 0)
        o["sf"] = surf(o["距離"])
        try:
            cs = [int(x) for x in str(o["コーナー通過"] or "").split("-") if x]
        except ValueError:
            cs = []
        c0 = cs[0] if cs else None
        o["sty"] = None if not (c0 and o["n"]) else ("F" if c0 / o["n"] <= 0.25 else ("B" if c0 / o["n"] >= 0.65 else "M"))
        o["wk"] = None if not (o["uma"] and o["n"]) else ("I" if o["uma"] / o["n"] <= 1 / 3 else ("O" if o["uma"] / o["n"] >= 2 / 3 else "M"))
        rows.append(o)

# 人気別の3着内率（期待値の基準）
cnt = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r["fin"] and r["pop"]:
        e = cnt[r["pop"]]; e[0] += 1; e[1] += r["fin"] <= 3
BASE = {k: v[1] / v[0] for k, v in cnt.items()}

# 日×場×芝ダ の グループ別 (期待, 実際) をレース別に持ち、除外して引く
day = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))     # (d,v,sf) → ("s",F)/("w",I) → [exp, obs]
race = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))    # (d,v,sf,R) → 同上
for r in rows:
    if not (r["fin"] and r["pop"] and r["sf"]):
        continue
    e, o = BASE[r["pop"]], float(r["fin"] <= 3)
    for key in (("s", r["sty"]), ("w", r["wk"])):
        if key[1]:
            for tab, k in ((day, (r["date"], r["競馬場"], r["sf"])), (race, (r["date"], r["競馬場"], r["sf"], r["R"]))):
                t = tab[k][key]; t[0] += e; t[1] += o


def ratio(dk, rk, key):
    a, b = day[dk][key], race[rk][key]
    ex, ob = a[0] - b[0], a[1] - b[1]
    return (ob + K) / (ex + K)             # 期待に3を足して縮める（他のレースが少ない日は1に寄る）


by = collections.defaultdict(list)
for r in rows:
    if r["馬名"] and r["fin"] and r["pop"] and num(r["単勝オッズ"]):
        by[r["馬名"]].append(r)
use, flags = [], {}
for hs in by.values():
    hs.sort(key=lambda r: (r["date"], r["競馬場"], r["R"]))
    for i in range(1, len(hs)):
        cur, prev = hs[i], hs[i - 1]
        if not (prev["sty"] and prev["wk"] and prev["sf"]):
            continue
        dk, rk = (prev["date"], prev["競馬場"], prev["sf"]), (prev["date"], prev["競馬場"], prev["sf"], prev["R"])
        D = ratio(dk, rk, ("s", prev["sty"])) * ratio(dk, rk, ("w", prev["wk"]))
        c = dict(cur)
        c["head"] = D <= 0.75 and prev["fin"] >= 6
        c["tail"] = D >= 1.30 and prev["fin"] <= 3
        use.append(c)
        flags[(cur["date"], cur["競馬場"], cur["R"], cur["uma"])] = (c["head"], c["tail"])
use.sort(key=lambda r: r["date"])
half = use[len(use) // 2]["date"]
print(f"■ 対象 {len(use):,}頭／前半・後半の境 {half}")
print(f"  逆風で負けた {sum(r['head'] for r in use):,}頭／追い風で好走 {sum(r['tail'] for r in use):,}頭\n")


def z_of(sub):
    if not sub:
        return None
    exp = sum(BASE[r["pop"]] for r in sub)
    var = sum(BASE[r["pop"]] * (1 - BASE[r["pop"]]) for r in sub)
    obs = sum(r["fin"] <= 3 for r in sub)
    return ((obs - exp) / math.sqrt(var), (obs - exp) / len(sub) * 100, len(sub), obs / len(sub) * 100) if var > 0 else None


def roi(sub):
    return sum(num(r["単勝オッズ"]) for r in sub if r["fin"] == 1) / len(sub) * 100 if sub else 0


def test(sel, label):
    a, h1, h2 = z_of(sel), z_of([r for r in sel if r["date"] < half]), z_of([r for r in sel if r["date"] >= half])
    if not (a and h1 and h2) or a[2] < 200:
        print(f"  {label:<18} n={a[2] if a else 0:>6}（少なすぎ）"); return
    ok = abs(a[0]) >= 2 and a[0] * h2[0] > 0 and abs(h2[0]) >= 1.5 and h1[0] * h2[0] > 0
    print(f"  {label:<18} n={a[2]:>6} 3着内{a[3]:5.1f}% 超過{a[1]:+5.2f}pt z={a[0]:+5.2f} ｜前半z{h1[0]:+5.2f} 後半z{h2[0]:+5.2f} ｜単勝回収{roi(sel):5.1f}% {'★両関門通過' if ok else ('（全体のみ）' if abs(a[0]) >= 2 else '')}")


print("① 同じ人気帯の中で（次走の3着内率）")
for key, lab in (("head", "逆風で負けた"), ("tail", "追い風で好走")):
    sel = [r for r in use if r[key]]
    test(sel, lab)
    for lo, hi, nm in ((1, 3, "1〜3人気"), (4, 9, "4〜9人気"), (10, 18, "10人気以下")):
        test([r for r in sel if lo <= r["pop"] <= hi], f"  └ {nm}")

print("\n② モデルの勝率 p との比較（2019〜・前向き予測）")
import mc_scenario_test as T
acc = {0: dict(n=0, win=0, sp=0.0, sq=0.0, var=0.0), 1: dict(n=0, win=0, sp=0.0, sq=0.0, var=0.0)}
for r in T.build_slim():
    d, v, R = r["key"]
    p = r["p"] / r["p"].sum(); q = r["q"] / r["q"].sum(); w = r["fins"] == 1
    for j, u in enumerate(r["uma"]):
        fl = flags.get((d, v, int(R), int(u)))
        if not fl:
            continue
        for i in (0, 1):
            if fl[i]:
                a = acc[i]; a["n"] += 1; a["win"] += int(w[j]); a["sp"] += p[j]; a["sq"] += q[j]; a["var"] += p[j] * (1 - p[j])
for i, nm in ((0, "逆風で負けた"), (1, "追い風で好走")):
    a = acc[i]
    if a["n"] < 200:
        print(f"  {nm}: n={a['n']}（少なすぎ）"); continue
    print(f"  {nm}: n={a['n']:>6} 勝ち{a['win']:>5} ／ モデル期待{a['sp']:7.1f}（z={(a['win'] - a['sp']) / math.sqrt(a['var']):+.2f}）／ 市場期待{a['sq']:7.1f}")
