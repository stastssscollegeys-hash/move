# -*- coding: utf-8 -*-
"""
course_trend.py — 蓄積DBからコース単位の傾向を出す
==========================================================================
なぜ必要か
----------
重賞は `race_history.py` でレース自体の過去10回を測れるが、
**OP特別・条件戦には特集ページが無い**（ラジオ日本賞で確認）。
その場合はコース単位で集計するしかない。

またコース傾向は外部サイトが有料（netkeibaプレミアム）・403（競馬ラボ/SPAIA）で
安定して取れないため、自前DBで出せる状態にしておく価値が高い。

⚠ 前提: `backfill_history.py` が距離・枠・通過順を取得していること。
   2026-09-09以前に取得したぶんは距離が None で集計に入らない
   （4月分3,984頭のうち309頭がこれに該当していた）。

使い方
------
    python course_trend.py 中山 ダート1200m
    python course_trend.py 阪神 芝1800m --min 100
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
FLAT_BASELINE = 0.72     # 等額買いの基準線（80%ではない）


def main(venue: str, dist: str, min_n: int) -> None:
    rows = json.load(open(DB / "race_results.json", encoding="utf-8"))
    rs = []
    for r in rows:
        if r.get("競馬場") != venue or str(r.get("距離")) != dist:
            continue
        try:
            rs.append({"rank": int(str(r["着順"]).strip()),
                       "pop": int(float(r["人気"])),
                       "odds": float(r["単勝オッズ"]),
                       "waku": r.get("枠"), "style": r.get("脚質", "?"),
                       "key": (str(r.get("date")), r.get("R"))})
        except (TypeError, ValueError, KeyError):
            continue
    if len(rs) < min_n:
        print(f"{venue}{dist}: {len(rs)}頭しかない（最低{min_n}頭必要）。")
        print("　backfill_history.py で該当開催を取得してください。")
        return

    races = len({x["key"] for x in rs})
    print(f"═══ {venue}{dist}  {races}レース / {len(rs)}頭 ═══\n")
    print("　単勝回収率は等額買いの基準線72%と比べる（80%ではない）\n")

    def agg(sel, label, order=None):
        g = defaultdict(lambda: {"n": 0, "w": 0, "t3": 0, "ret": 0.0})
        for x in rs:
            k = sel(x)
            if k in (None, "", "?"):
                continue
            a = g[k]
            a["n"] += 1
            if x["rank"] == 1:
                a["w"] += 1
                a["ret"] += x["odds"] * 100
            if x["rank"] <= 3:
                a["t3"] += 1
        if not g:
            return
        print(f"■ {label}")
        print(f"  {'区分':<10}{'頭数':>7}{'勝率':>8}{'複勝率':>9}{'単勝回収':>9}")
        print("  " + "─" * 44)
        keys = order or sorted(g, key=lambda k: -g[k]["n"])
        for k in keys:
            a = g.get(k)
            if not a or a["n"] < 15:
                continue
            warn = "  ←少数" if a["n"] < 40 else ""
            print(f"  {str(k):<10}{a['n']:>7}{a['w']/a['n']*100:>7.1f}%"
                  f"{a['t3']/a['n']*100:>8.1f}%{a['ret']/(a['n']*100)*100:>8.0f}%{warn}")
        print()

    agg(lambda x: x["style"], "脚質別", ["逃げ", "先行", "差し", "追込"])
    agg(lambda x: x["waku"], "枠別", list(range(1, 9)))
    agg(lambda x: min(x["pop"], 10) if x["pop"] else None, "人気別",
        list(range(1, 10)) + [10])

    # 決着の堅さ
    by_race = defaultdict(list)
    for x in rs:
        by_race[x["key"]].append(x)
    top3_all = sum(1 for v in by_race.values()
                   if sorted(y["pop"] for y in v if y["rank"] <= 3)[:3] and
                   max(y["pop"] for y in v if y["rank"] <= 3) <= 5)
    print(f"■ 決着の堅さ")
    print(f"  3着以内が全て5番人気以内: {top3_all}/{len(by_race)}レース "
          f"({top3_all/len(by_race)*100:.0f}%)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("venue")
    ap.add_argument("dist", help="例: ダート1200m / 芝1800m")
    ap.add_argument("--min", type=int, default=80)
    a = ap.parse_args()
    main(a.venue, a.dist, a.min)
