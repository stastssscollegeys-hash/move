# -*- coding: utf-8 -*-
"""
index_audit_leakfree.py — 指数の予測力を「レース前records」だけで測る（2026-09-27）
======================================================================================
蓄積DB（race_results.json）の AI予測順位 は結果リーク（F01〜F03が着順由来）で
3着内93%・単勝回収424%という不可能な数字を出す。**評価にはレース前に作られた
records しか使えない**（engine_backtest.drop_leaky と同じ素性判定＝ファイル更新時刻）。

測ること
  ① 総合指数1位／独自指数1位／ML能力%1位／市場1番人気 の 1着率・3着内率・単勝回収率
  ② 同じ人気帯の中で「指数1位」は他より走るか（＝市場に無い情報を持つか）
  ③ 独自指数とML能力%の合成比率（現行55:45）を動かすと何が最良か
  ④ 順位テーブル方式（gen_kaime_v5.model_probs）が指数の大きさを捨てている損失
使い方: python index_audit_leakfree.py
"""
from __future__ import annotations
import collections, datetime, glob, json, math, os, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
DB = BASE / "daily_pdca" / "db"

# ── レース前records（素性チェック付き）──────────────────────────────
pre, prov = {}, {}
for f in sorted(BASE.glob("**/週末ビッグデータ_*_records.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    rs = d.get("records", [])
    if not rs:
        continue
    mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).date()
    last = max(r["date"] for r in rs)
    leaky = mtime > datetime.date(int(last[:4]), int(last[4:6]), int(last[6:8]))
    for r in rs:
        k = (r["date"], r["競馬場"], int(r["R"]))
        if leaky:
            prov[k] = "leaky"
            continue
        prov.setdefault(k, "ok")
        pre.setdefault(k, {})[int(float(r["馬番"]))] = r

# ── 結果を結合 ──────────────────────────────────────────────────────
res = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
by = collections.defaultdict(dict)
for r in res:
    try:
        by[(r["date"], r["競馬場"], int(r["R"]))][int(float(r["馬番"]))] = r
    except (TypeError, ValueError):
        pass


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "")
    return int(s) if s.isdigit() else None


races = []
for k, horses in pre.items():
    rows = by.get(k)
    if not rows or len(horses) < 8:
        continue
    joined = []
    for uma, p in horses.items():
        q = rows.get(uma)
        if not q or not fin(q):
            continue
        try:
            joined.append(dict(uma=uma, sogo=float(p["総合指数"]), dokuji=float(p["独自指数"]),
                               ml=float(p["ML能力%"]), pop=int(float(q["人気"])),
                               odds=float(q["単勝オッズ"]), fin=fin(q)))
        except (TypeError, ValueError, KeyError):
            continue
    if len(joined) >= 8:
        races.append(joined)

n_leaky = sum(1 for v in prov.values() if v == "leaky")
print(f"■ レース前records {len(races)}レース / {sum(len(x) for x in races):,}頭"
      f"（結果リーク疑いで除外 {n_leaky}レース）\n")


def top(race, key):
    return max(race, key=lambda h: h[key] if key != "pop" else -h["pop"])


def stats(picks):
    n = len(picks)
    w = sum(1 for h in picks if h["fin"] == 1)
    p3 = sum(1 for h in picks if h["fin"] <= 3)
    roi = sum(h["odds"] * 100 for h in picks if h["fin"] == 1) / (n * 100) * 100
    avgpop = sum(h["pop"] for h in picks) / n
    return n, w / n * 100, p3 / n * 100, roi, avgpop


print("■ ① 各指数の1位馬 vs 市場1番人気（同じレース群）")
print(f"{'選び方':<14}{'n':>5}{'1着率':>8}{'3着内':>8}{'単勝回収':>9}{'平均人気':>9}")
for label, key in (("総合指数1位", "sogo"), ("独自指数1位", "dokuji"), ("ML能力%1位", "ml"), ("市場1番人気", "pop")):
    n, w, p3, roi, ap = stats([top(r, key) for r in races])
    print(f"{label:<14}{n:>5}{w:>7.1f}%{p3:>7.1f}%{roi:>8.1f}%{ap:>9.2f}")

print("\n■ ② 同じ人気帯の中で、総合指数1位の馬は他より走るか（市場に無い情報の有無）")
print(f"{'人気':>4}{'指数1位n':>9}{'3着内':>8}{'それ以外n':>10}{'3着内':>8}{'差':>8}  1位の単勝回収")
for p in range(1, 8):
    a, b = [], []
    for r in races:
        t = top(r, "sogo")
        for h in r:
            if h["pop"] != p:
                continue
            (a if h is t else b).append(h)
    if len(a) < 25:
        continue
    ra = sum(1 for h in a if h["fin"] <= 3) / len(a) * 100
    rb = sum(1 for h in b if h["fin"] <= 3) / len(b) * 100
    roi = sum(h["odds"] * 100 for h in a if h["fin"] == 1) / (len(a) * 100) * 100
    print(f"{p:>4}{len(a):>9}{ra:>7.1f}%{len(b):>10}{rb:>7.1f}%{ra-rb:>+7.1f}pt  {roi:>6.1f}%")

print("\n■ ③ 独自指数とML能力%の合成比率（現行は独自55:ML45）")


def z(vals):
    m = sum(vals) / len(vals)
    s = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5 or 1
    return [(v - m) / s for v in vals]


print(f"{'独自の比率':>8}{'1着率':>8}{'3着内':>8}{'単勝回収':>9}{'平均人気':>9}")
for w in (0.0, 0.25, 0.5, 0.55, 0.75, 1.0):
    picks = []
    for r in races:
        zd, zm = z([h["dokuji"] for h in r]), z([h["ml"] for h in r])
        sc = [w * a + (1 - w) * b for a, b in zip(zd, zm)]
        picks.append(r[max(range(len(r)), key=lambda i: sc[i])])
    n, w1, p3, roi, ap = stats(picks)
    print(f"{w:>8.2f}{w1:>7.1f}%{p3:>7.1f}%{roi:>8.1f}%{ap:>9.2f}")

print("\n■ ④ 指数の『差』は情報か（1位と2位の差が大きいレースほど1位が来るか）")
buckets = collections.defaultdict(list)
for r in races:
    s = sorted(r, key=lambda h: -h["sogo"])
    gap = s[0]["sogo"] - s[1]["sogo"]
    b = "〜1" if gap < 1 else "1〜3" if gap < 3 else "3〜6" if gap < 6 else "6〜"
    buckets[b].append(s[0])
print(f"{'1位-2位の差':<10}{'n':>5}{'1着率':>8}{'3着内':>8}{'単勝回収':>9}")
for b in ("〜1", "1〜3", "3〜6", "6〜"):
    if buckets[b]:
        n, w1, p3, roi, ap = stats(buckets[b])
        print(f"{b:<10}{n:>5}{w1:>7.1f}%{p3:>7.1f}%{roi:>8.1f}%")
print("  → 差に応じて1着率が単調に上がるなら、順位だけ見る model_probs はその情報を捨てている")
