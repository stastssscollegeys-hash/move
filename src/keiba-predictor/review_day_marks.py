# -*- coding: utf-8 -*-
"""
review_day_marks.py — その日の「レース前の指数順位」と結果を全レースで突き合わせる（2026-09-19新規）
=====================================================================================================
review_weekend.py は公開した5レース前後しか見ないため、「○▲が外れて△が2・3着に来る」ような
印の組み方の傾向を全レースで確かめるのに使う。入力はレース前に作った records（リークなし）と確定結果。

  python review_day_marks.py --date 20260919
出力: 指数1〜6位・市場1〜3番人気それぞれの 1着率／3着内率、3着内馬の指数順位の分布
"""
from __future__ import annotations
import argparse, json, sys, io, glob
from collections import Counter, defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path.home() / "Desktop" / "競馬予想レポート"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    d = a.date
    recs = []
    for f in glob.glob(str(ROOT / "**" / "週末ビッグデータ_*_records.json"), recursive=True):
        rs = json.load(open(f, encoding="utf-8")).get("records", [])
        if any(r["date"] == d for r in rs):
            recs = [r for r in rs if r["date"] == d]
    res = json.load(open(ROOT / "daily_pdca" / "db" / "race_results.json", encoding="utf-8"))
    fin = {(r["競馬場"], int(r["R"]), int(float(r["馬番"]))): (r.get("着順int"), r.get("単勝オッズ")) for r in res if r["date"] == d}
    by = defaultdict(list)
    for r in recs:
        by[(r["競馬場"], int(r["R"]))].append(r)
    model = defaultdict(lambda: [0, 0, 0])   # rank -> [n, win, top3]
    market = defaultdict(lambda: [0, 0, 0])
    top3_rank = Counter()
    n_race = 0
    for key, rs in sorted(by.items()):
        rows = []
        for r in rs:
            f = fin.get((key[0], key[1], int(r["馬番"])))
            if not f or not f[0]:
                continue
            try:
                o = float(f[1])
            except (TypeError, ValueError):
                continue
            rows.append((r, f[0], o))
        if len(rows) < 5:
            continue
        n_race += 1
        by_model = sorted(rows, key=lambda x: -float(x[0]["総合指数"]))
        by_pop = sorted(rows, key=lambda x: x[2])
        for i, (r, pos, o) in enumerate(by_model[:6], 1):
            model[i][0] += 1; model[i][1] += pos == 1; model[i][2] += pos <= 3
        for i, (r, pos, o) in enumerate(by_pop[:3], 1):
            market[i][0] += 1; market[i][1] += pos == 1; market[i][2] += pos <= 3
        for i, (r, pos, o) in enumerate(by_model, 1):
            if pos <= 3:
                top3_rank[min(i, 7)] += 1
    print(f"■ {d} レース前の指数 × 結果（{n_race}レース）")
    print(" 指数順位   1着率   3着内率")
    for i in range(1, 7):
        n, w, t = model[i]
        print(f"   {i}位     {w/n*100:5.1f}%  {t/n*100:5.1f}%" if n else f"   {i}位  —")
    print(" 市場人気   1着率   3着内率")
    for i in range(1, 4):
        n, w, t = market[i]
        print(f"   {i}番人気  {w/n*100:5.1f}%  {t/n*100:5.1f}%")
    tot = sum(top3_rank.values())
    print(" 3着内に来た馬の指数順位: " + " / ".join(f"{'7位以下' if k == 7 else f'{k}位'} {v}頭({v/tot*100:.0f}%)" for k, v in sorted(top3_rank.items())))


if __name__ == "__main__":
    main()
