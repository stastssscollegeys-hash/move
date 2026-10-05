# -*- coding: utf-8 -*-
"""
distance_change_audit.py — 「前走からの距離変化」は市場に無い情報か（2026-09-29新規）
=========================================================================================
予想のたびに「前走は距離短縮での凡走だから度外視」「1800mに戻るのは好材料」と書いてきたが、
この因子は一度も検定していなかった（ユーザー指示「必要なファクターがあれば追加して」）。

レース前に確実に分かる情報（前走の距離と今回の距離）だけで作れるので、
蓄積DB全件で「同じ人気帯の中で差が出るか」を両関門にかける。

両関門（pdca_rounds と同じ）
  ① 全体で |z| >= 2
  ② 前半／後半に割っても同じ向きで、後半の |z| >= 1.5

使い方: python distance_change_audit.py
"""
from __future__ import annotations
import collections, json, math, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))


def meters(d):
    s = str(d or "")
    n = "".join(c for c in s if c.isdigit())
    return int(n) if n else None


def surf(d):
    s = str(d or "")
    return "芝" if s.startswith("芝") else ("ダ" if s.startswith("ダ") else None)


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "")
    return int(s) if s.isdigit() else None


def pop(r):
    try:
        return min(int(float(r.get("人気"))), 18)
    except (TypeError, ValueError):
        return None


# 馬ごとの時系列から「前走の距離」を作る（自分より前の出走だけ＝リークなし）
by_horse = collections.defaultdict(list)
for r in rows:
    if r.get("馬名") and r.get("date") and meters(r.get("距離")):
        by_horse[r["馬名"]].append(r)
for v in by_horse.values():
    v.sort(key=lambda r: (r["date"], r.get("競馬場", ""), int(float(r.get("R") or 0))))

use = []
for name, hs in by_horse.items():
    for i in range(1, len(hs)):
        cur, prev = hs[i], hs[i - 1]
        if not (fin(cur) and pop(cur)):
            continue
        cur = dict(cur)
        cur["_diff"] = meters(cur["距離"]) - meters(prev["距離"])
        cur["_same_surf"] = surf(cur["距離"]) == surf(prev["距離"])
        cur["_prev_fin"] = fin(prev)
        use.append(cur)

use.sort(key=lambda r: r["date"])
half = use[len(use) // 2]["date"]
print(f"■ 対象 {len(use):,}頭（前走が蓄積DBにある出走）／ 前半・後半の境 {half}\n")

base = collections.defaultdict(lambda: [0, 0])
for r in use:
    e = base[pop(r)]
    e[0] += 1
    e[1] += 1 if fin(r) <= 3 else 0
BASE = {k: v[1] / v[0] for k, v in base.items()}


def test(sel, label):
    def z_of(sub):
        if not sub:
            return None
        exp = sum(BASE[pop(r)] for r in sub)
        var = sum(BASE[pop(r)] * (1 - BASE[pop(r)]) for r in sub)
        obs = sum(1 for r in sub if fin(r) <= 3)
        if var <= 0:
            return None
        return ((obs - exp) / math.sqrt(var), (obs - exp) / len(sub) * 100, len(sub), obs / len(sub) * 100)
    a = z_of(sel)
    h1 = z_of([r for r in sel if r["date"] < half])
    h2 = z_of([r for r in sel if r["date"] >= half])
    if not (a and h1 and h2) or a[2] < 200:
        print(f"  {label:<30} n={a[2] if a else 0:>5}  （少なすぎ）")
        return False
    ok = abs(a[0]) >= 2 and (a[0] * h2[0] > 0) and abs(h2[0]) >= 1.5 and (h1[0] * h2[0] > 0)
    mark = "★両関門通過" if ok else ("（全体のみ）" if abs(a[0]) >= 2 else "")
    print(f"  {label:<30} n={a[2]:>5} 3着内{a[3]:5.1f}% 超過{a[1]:+5.2f}pt z={a[0]:+5.2f}"
          f" ｜前半z{h1[0]:+5.2f} 後半z{h2[0]:+5.2f}  {mark}")
    return ok


passed = []
print("■ 距離変化（同じ芝ダの中でのみ比較）")
same = [r for r in use if r["_same_surf"]]
bands = [(-9999, -401, "大幅短縮(-400m超)"), (-400, -201, "短縮(-200〜-400m)"),
         (-200, -1, "やや短縮(-1〜-200m)"), (0, 0, "同距離"),
         (1, 200, "やや延長(+1〜200m)"), (201, 400, "延長(+200〜400m)"),
         (401, 9999, "大幅延長(+400m超)")]
for lo, hi, lab in bands:
    if test([r for r in same if lo <= r["_diff"] <= hi], f"距離変化={lab}"):
        passed.append(lab)

print("\n■ 「前走が凡走(6着以下)＋距離変化」の組み合わせ（度外視の根拠になるか）")
bad = [r for r in same if r["_prev_fin"] and r["_prev_fin"] >= 6]
for lo, hi, lab in bands:
    if test([r for r in bad if lo <= r["_diff"] <= hi], f"前走6着以下×{lab}"):
        passed.append(f"前走6着以下×{lab}")

print("\n■ 芝ダの変更")
if test([r for r in use if not r["_same_surf"]], "芝ダ変更あり"):
    passed.append("芝ダ変更")

print("\n■ 結論")
if passed:
    for p in passed:
        print(f"  ★ {p} は市場に無い情報を持つ → 候補台帳に登録して前向き判定へ")
else:
    print("  両関門を通った区分なし。『距離短縮での凡走は度外視』等は**予想の説明には使えるが、確率には掛けない**")
