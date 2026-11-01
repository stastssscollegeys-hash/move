# -*- coding: utf-8 -*-
"""
hypo_audit_20261101.py — ネットの予想家・解説記事で語られる考え方を、自前DB（history_target 2016〜2026・約45万頭）で検定する（2026-11-01新規）
==============================================================================================================
出典はいずれも第三者検証のない解説（根拠は弱い）。検証は distance_change_audit.py と同じ両関門:
  ① 同じ人気帯の中で、3着内率が期待より |z|>=2 ずれる  ② 前半・後半で同じ向き、後半 |z|>=1.5
あわせて、該当馬を単勝100円ずつ買った回収率を出す（参考。採否は両関門で決める）
仮説（すべて「前走の情報だけ」で作る＝リーク無し）:
  H1 前走ハイペース逃げ失速: 前走で最初のコーナー2番手以内、前走の前半3Fが同じ距離帯の中央値より0.5秒以上速い、前走6着以下
  H2 前走展開負け: 前走の上がり順位3位以内なのに着順6着以下（届かなかった）
  H3 前走4角で後方（10番手以下）なのに上がり最速級＝詰めの甘さ／H3b 前走4角先頭付近で着順が良い＝押し切り
  H4 オッズ帯: 単勝オッズ帯ごとの回収率（人気帯の歪み。一般論の確認）
使い方: python hypo_audit_20261101.py
"""
from __future__ import annotations
import collections, json, math, statistics, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
KEEP = ("date", "競馬場", "R", "距離", "馬名", "馬番", "人気", "単勝オッズ", "着順int", "コーナー通過", "前3F_レース", "後3F順位")
rows = []
for f in sorted((DB / "history_target").glob("results_*.json")):     # 2016〜2026の10年分（race_results.json は2026年だけ）
    for r in json.loads(f.read_text(encoding="utf-8")):
        rows.append({k: r.get(k) for k in KEEP})


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def meters(d):
    s = "".join(c for c in str(d or "") if c.isdigit())
    return int(s) if s else None


def surf(d):
    s = str(d or "")
    return "芝" if s.startswith("芝") else ("ダ" if s.startswith("ダ") else None)


def fin(r):
    v = r.get("着順int")
    return int(float(v)) if v not in (None, "") else None


def pop(r):
    v = num(r.get("人気"))
    return min(int(v), 18) if v else None


def corners(r):
    try:
        return [int(x) for x in str(r.get("コーナー通過") or "").split("-") if x]
    except ValueError:
        return []


by = collections.defaultdict(list)
for r in rows:
    if r.get("馬名") and r.get("date") and meters(r.get("距離")):
        by[r["馬名"]].append(r)
for v in by.values():
    v.sort(key=lambda r: (r["date"], r.get("競馬場", ""), int(num(r.get("R")) or 0)))

# 前半3Fの距離帯別中央値（ペースの速い・遅いの基準）
pace = collections.defaultdict(list)
for r in rows:
    f3 = num(r.get("前3F_レース"))
    if f3 and surf(r.get("距離")):
        pace[(surf(r["距離"]), meters(r["距離"]))].append(f3)
PMED = {k: statistics.median(v) for k, v in pace.items() if len(v) >= 30}

use = []
for hs in by.values():
    for i in range(1, len(hs)):
        cur, prev = hs[i], hs[i - 1]
        if not (fin(cur) and pop(cur) and num(cur.get("単勝オッズ"))):
            continue
        c = dict(cur)
        cs = corners(prev)
        pf = fin(prev)
        f3 = num(prev.get("前3F_レース"))
        med = PMED.get((surf(prev["距離"]), meters(prev["距離"])))
        c["H1"] = bool(cs and cs[0] <= 2 and f3 and med and f3 <= med - 0.5 and pf and pf >= 6)
        c["H2"] = bool(num(prev.get("後3F順位")) and num(prev.get("後3F順位")) <= 3 and pf and pf >= 6)
        c["H3"] = bool(len(cs) >= 4 and cs[-1] >= 10 and num(prev.get("後3F順位")) and num(prev.get("後3F順位")) <= 2)
        c["H3b"] = bool(len(cs) >= 4 and cs[-1] <= 2 and pf and pf <= 3)
        use.append(c)
use.sort(key=lambda r: r["date"])
half = use[len(use) // 2]["date"]
print(f"■ 対象 {len(use):,}頭／前半・後半の境 {half}\n")

base = collections.defaultdict(lambda: [0, 0])
for r in use:
    e = base[pop(r)]
    e[0] += 1
    e[1] += fin(r) <= 3
BASE = {k: v[1] / v[0] for k, v in base.items()}


def z_of(sub):
    if not sub:
        return None
    exp = sum(BASE[pop(r)] for r in sub)
    var = sum(BASE[pop(r)] * (1 - BASE[pop(r)]) for r in sub)
    obs = sum(fin(r) <= 3 for r in sub)
    return ((obs - exp) / math.sqrt(var), (obs - exp) / len(sub) * 100, len(sub), obs / len(sub) * 100) if var > 0 else None


def roi(sub):
    return sum(num(r["単勝オッズ"]) * 100 for r in sub if fin(r) == 1) / (len(sub) * 100) * 100 if sub else 0


def test(sel, label):
    a, h1, h2 = z_of(sel), z_of([r for r in sel if r["date"] < half]), z_of([r for r in sel if r["date"] >= half])
    if not (a and h1 and h2) or a[2] < 200:
        print(f"  {label:<26} n={a[2] if a else 0:>5} （少なすぎ）")
        return
    ok = abs(a[0]) >= 2 and a[0] * h2[0] > 0 and abs(h2[0]) >= 1.5 and h1[0] * h2[0] > 0
    print(f"  {label:<26} n={a[2]:>6} 3着内{a[3]:5.1f}% 超過{a[1]:+5.2f}pt z={a[0]:+5.2f} ｜前半z{h1[0]:+5.2f} 後半z{h2[0]:+5.2f} ｜単勝回収{roi(sel):5.1f}%  {'★両関門通過' if ok else ('（全体のみ）' if abs(a[0]) >= 2 else '')}")


for key, lab in (("H1", "H1 前走ハイペース逃げ失速"), ("H2", "H2 前走 上がり上位で凡走"),
                 ("H3", "H3 前走 後方から上がり最速級"), ("H3b", "H3b 前走 先頭付近で3着内")):
    sel = [r for r in use if r[key]]
    test(sel, lab)
    for lo, hi, nm in ((1, 3, "1〜3人気"), (4, 9, "4〜9人気"), (10, 18, "10人気以下")):
        test([r for r in sel if lo <= pop(r) <= hi], f"   └ {nm}")
print("\n■ H4 単勝オッズ帯ごとの単勝回収率（全出走）")
for lo, hi in ((1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 30), (30, 60), (60, 9999)):
    sub = [r for r in use if lo <= num(r["単勝オッズ"]) < hi]
    print(f"  {lo}〜{hi}倍 n={len(sub):>6} 単勝回収 {roi(sub):5.1f}% 勝率 {sum(fin(r) == 1 for r in sub) / len(sub) * 100:4.1f}%")

# 該当フラグを保存（モデルの確率との比較 hypo_vs_model.py が読む）
import pickle
flags = {(r["date"], r["競馬場"], int(num(r["R"]) or 0), int(num(r.get("馬番")) or 0)): (r["H1"], r["H2"], r["H3"], r["H3b"]) for r in use}
(DB / "hypo_flags.pkl").write_bytes(pickle.dumps(flags))
