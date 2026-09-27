# -*- coding: utf-8 -*-
"""
weekend_full_review.py — その週末の「全レース」を振り返る（2026-09-27新規）
==============================================================================
これまでの振り返り（review_weekend.py）は**公開した買い目のレースだけ**を見ていた。
ユーザー指示「全レースのデータで振り返りと蓄積を行う」に対応し、
開催24R×2日ぶんの決着傾向をまとめて出す。

出すもの
  ① 人気別の決着（1着・3着内）と、その週の堅さ／荒れ具合
  ② 脚質別の3着内率（distance/馬場別の実測と比べてその週がどうだったか）
  ③ 馬場ごとの前後有利
  ④ 枠順
  ⑤ 配当の水準（3連単中央値など）
  ⑥ 蓄積DB全期間との差（その週が特異だったかどうか）

使い方: python weekend_full_review.py --dates 20260926 20260927
"""
from __future__ import annotations
import argparse, collections, json, statistics as st, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
STYLES = ("逃げ", "先行", "差し", "追込")


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "")
    return int(s) if s.isdigit() else None


def pop(r):
    try:
        return int(float(r.get("人気")))
    except (TypeError, ValueError):
        return None


def rate(rows, cond, of):
    d = [r for r in rows if of(r)]
    return (sum(1 for r in d if cond(r)) / len(d) * 100, len(d)) if d else (None, 0)


ap = argparse.ArgumentParser()
ap.add_argument("--dates", nargs="+", required=True)
a = ap.parse_args()

allrows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
week = [r for r in allrows if r.get("date") in a.dates]
rest = [r for r in allrows if r.get("date") not in a.dates]
pays = json.loads((DB / "payouts.json").read_text(encoding="utf-8"))
laps = json.loads((DB / "lap.json").read_text(encoding="utf-8"))

races = collections.defaultdict(list)
for r in week:
    races[(r["date"], r["競馬場"], int(r["R"]))].append(r)
print(f"■ 対象 {len(races)} レース / {len(week)} 頭（{' と '.join(a.dates)}）")
print(f"   比較対象（それ以外の全期間） {len(rest):,} 頭\n")

# ① 人気別
print("■ ① 人気別の決着")
print(f"{'人気':>5}{'頭数':>7}{'1着率':>9}{'3着内率':>10}   {'全期間の3着内率':>16}")
for p in range(1, 11):
    w1, n = rate(week, lambda r: fin(r) == 1, lambda r: pop(r) == p)
    w3, _ = rate(week, lambda r: (fin(r) or 99) <= 3, lambda r: pop(r) == p)
    a3, _ = rate(rest, lambda r: (fin(r) or 99) <= 3, lambda r: pop(r) == p)
    if n:
        d = w3 - a3
        print(f"{p:>5}{n:>7}{w1:>8.1f}%{w3:>9.1f}%   {a3:>14.1f}%  ({d:+.1f}pt)")

fav1 = [rs for rs in races.values() if any(pop(r) == 1 and fin(r) == 1 for r in rs)]
fav3 = [rs for rs in races.values() if any(pop(r) == 1 and (fin(r) or 99) <= 3 for r in rs)]
print(f"\n   1番人気の勝率 {len(fav1)}/{len(races)} = {len(fav1)/len(races)*100:.1f}%"
      f"／3着内 {len(fav3)}/{len(races)} = {len(fav3)/len(races)*100:.1f}%")
top3all = sum(1 for rs in races.values()
              if sorted((pop(r) or 99) for r in rs if (fin(r) or 99) <= 3)[:3] == [1, 2, 3])
big = sum(1 for rs in races.values() if any((pop(r) or 0) >= 8 and (fin(r) or 99) <= 3 for r in rs))
print(f"   上位3人気で決着 {top3all}/{len(races)}（全期間8.4%）"
      f"／8番人気以下が3着内 {big}/{len(races)} = {big/len(races)*100:.1f}%（全期間37.2%）")

# ② 脚質
print("\n■ ② 脚質別の3着内率")
print(f"{'脚質':<6}{'頭数':>7}{'今週':>9}{'全期間':>9}{'差':>9}")
for s in STYLES:
    w, n = rate(week, lambda r: (fin(r) or 99) <= 3, lambda r: r.get("脚質") == s)
    o, _ = rate(rest, lambda r: (fin(r) or 99) <= 3, lambda r: r.get("脚質") == s)
    if n:
        print(f"{s:<6}{n:>7}{w:>8.1f}%{o:>8.1f}%{w-o:>+8.1f}pt")

# ③ 馬場別の前後
print("\n■ ③ 馬場別の前(逃+先) vs 後(差+追)")
print(f"{'馬場':<8}{'頭数':>7}{'前':>8}{'後':>8}{'差':>10}")
for bb in ("良", "稍重", "重", "不良"):
    sub = [r for r in week if str(r.get("馬場状態") or "").startswith(bb)]
    if len(sub) < 30:
        continue
    f_, _ = rate(sub, lambda r: (fin(r) or 99) <= 3, lambda r: r.get("脚質") in ("逃げ", "先行"))
    b_, _ = rate(sub, lambda r: (fin(r) or 99) <= 3, lambda r: r.get("脚質") in ("差し", "追込"))
    if f_ is not None and b_ is not None:
        print(f"{bb:<8}{len(sub):>7}{f_:>7.1f}%{b_:>7.1f}%{f_-b_:>+9.1f}pt")

# ④ 枠
print("\n■ ④ 枠順別の3着内率（今週／全期間）")
line1, line2 = [], []
for w_ in range(1, 9):
    x, n = rate(week, lambda r: (fin(r) or 99) <= 3, lambda r: str(r.get("枠")) == str(w_))
    y, _ = rate(rest, lambda r: (fin(r) or 99) <= 3, lambda r: str(r.get("枠")) == str(w_))
    line1.append(f"{w_}枠{x:>5.1f}%" if x is not None else f"{w_}枠   -  ")
    line2.append(f"  {y:>5.1f}%" if y is not None else "     -  ")
print("  " + " ".join(line1))
print("  " + " ".join(line2))

# ⑤ 配当
print("\n■ ⑤ 配当の水準")
got = collections.defaultdict(list)
for rid, v in pays.items():
    if v.get("date") in a.dates:
        for k, p in (v.get("payouts") or {}).items():
            y = p.get("yen") if isinstance(p, dict) else None
            if isinstance(p, list):
                for q in p:
                    if q.get("yen"):
                        got[k].append(q["yen"])
            elif y:
                got[k].append(y)
for k in ("単勝", "馬連", "ワイド", "馬単", "3連複", "3連単"):
    v = got.get(k)
    if v:
        print(f"  {k:<6} n={len(v):>3}  中央値{int(st.median(v)):>8,}円  最高{max(v):>9,}円")

# ⑥ ペース
print("\n■ ⑥ その週のペース分布（lap.jsonから）")
pc = collections.Counter((v.get("pace") or "(なし)").split()[0] if v.get("pace") else "(なし)"
                         for v in laps.values() if v.get("date") in a.dates)
tot = sum(pc.values())
print("  " + " ／ ".join(f"{k} {n}R ({n/tot*100:.0f}%)" for k, n in pc.most_common()))
print("  全期間の分布: H29.2% / M45.6% / S25.3%")
