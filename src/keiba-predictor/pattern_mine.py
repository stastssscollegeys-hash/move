# -*- coding: utf-8 -*-
"""
pattern_mine.py — 型 × 買い方 の実測ROIを過去レースから出す（2026-09-26新規）
===============================================================================
「この型にはまったらこの買い方」を、勘ではなく確定払戻で決めるための集計器。

データ: engine_backtest.load_races()（レース前に作った records のみ・リーク除外）
        ＋ daily_pdca/db/payouts.json（確定払戻）
手順:  1レースごとに
        ① kaime_patterns.classify で型を判定
        ② kaime_select.build_candidates で全買い方の候補を作る
        ③ 各買い方に1レース10,000円を反比例配分し、確定払戻で回収額を出す
       型×買い方で集計し、**発見用（前半）と検証用（後半）に分けて**両方を出す。
       片方だけ良い型は採用しない（帯スキャンで全滅した教訓）。

出力: daily_pdca/db/pattern_roi.json
使い方: python pattern_mine.py [--budget 10000]
"""
from __future__ import annotations
import argparse, collections, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import engine_backtest as B
from kaime_patterns import classify, PATTERNS
from kaime_select import build_candidates, allocate

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
ap = argparse.ArgumentParser()
ap.add_argument("--budget", type=int, default=10000)
a = ap.parse_args()

races = B.drop_leaky(B.load_races(), verbose=False)
print(f"対象 {len(races)} レース（レース前に作った records のみ）")


def payout_of(pay, t, combo):
    rows = pay.get(t)
    if not rows:
        return None
    want = sorted(int(x) for x in combo)
    for x in rows:
        got = [int(v) for v in x["combo"].split("-")]
        if t in ("馬単", "3連単"):
            if got == list(combo):
                return x["yen"]
        elif sorted(got) == want:
            return x["yen"]
    return 0


dates = sorted({k[0] for k in races})
mid = dates[len(dates) // 2]
agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0, 0]))
#              pattern      structure   [n, hit, 投資, 払戻, 後半n]  ※前後半は別keyで持つ
half = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))

for key, v in races.items():
    recs, odds_s, pay = v["recs"], v["odds"], v["pay"]
    odds = {int(k): float(x) for k, x in odds_s.items()}
    # 事前の指数（AI予測順位の逆順をスコアにする＝順位しか無い行があるため）
    ranked = sorted(recs, key=lambda r: r.get("AI予測順位") or 99)
    score = {}
    for i, r in enumerate(ranked):
        try:
            score[int(r["馬番"])] = 100.0 - i
        except (TypeError, ValueError, KeyError):
            continue
    score = {u: score.get(u, 0.0) for u in odds}
    if len(odds) < 8 or not any(score.values()):
        continue
    try:
        hit_pat, ctx = classify(score, odds)
    except Exception:
        continue
    pat = hit_pat[0]["id"]
    try:
        cands, *_ = build_candidates(score, odds, {u: str(u) for u in odds})
    except Exception:
        continue
    late = key[0] >= mid
    for c in cands:
        pts = sorted(c.points, key=lambda p: -p["p"])[:10]
        if not pts:
            continue
        allocate(pts, a.budget)
        ret = 0
        won = False
        for p in pts:
            y = payout_of(pay, p["t"], p["combo"])
            if y:
                ret += p["amt"] * y / 100
                won = True
        for store in (agg[pat][c.name], agg["ALL"][c.name]):
            store[0] += 1
            store[1] += won
            store[2] += a.budget
            store[3] += ret
        h = half[(pat, "後半" if late else "前半")][c.name]
        h[0] += 1; h[1] += won; h[2] += a.budget; h[3] += ret

NAMES = {p["id"]: p["name"] for p in PATTERNS}
NAMES["ALL"] = "全レース"
out = {}
for pat in sorted(agg, key=lambda x: (x != "ALL", x)):
    rows = []
    for st, (n, h, inv, ret, _) in agg[pat].items():
        if n < 25:
            continue
        roi = ret / inv * 100
        f = half[(pat, "前半")].get(st)
        l = half[(pat, "後半")].get(st)
        rf = f[3] / f[2] * 100 if f and f[2] else None
        rl = l[3] / l[2] * 100 if l and l[2] else None
        both = rf is not None and rl is not None and rf >= 100 and rl >= 100
        rows.append(dict(structure=st, n=n, hit=round(h / n * 100, 1), roi=round(roi, 1),
                         first=round(rf, 1) if rf is not None else None,
                         last=round(rl, 1) if rl is not None else None, both_over100=both))
    rows.sort(key=lambda r: -r["roi"])
    out[pat] = dict(name=NAMES.get(pat, pat), n_race=max((r["n"] for r in rows), default=0), rows=rows)
    if not rows:
        continue
    print("\n" + "=" * 92)
    print(f"■ {pat} {NAMES.get(pat, pat)}　{rows[0]['n']}レース")
    print("=" * 92)
    print(f"{'買い方':<16}{'R':>5}{'的中率':>8}{'回収率':>8}{'前半':>8}{'後半':>8}  判定")
    for r in rows:
        mark = "◎両期間100%超" if r["both_over100"] else ("○" if r["roi"] >= 100 else "")
        f = f"{r['first']:.0f}%" if r["first"] is not None else "-"
        l = f"{r['last']:.0f}%" if r["last"] is not None else "-"
        print(f"{r['structure']:<16}{r['n']:>5}{r['hit']:>7.1f}%{r['roi']:>7.0f}%{f:>8}{l:>8}  {mark}")

p = DB / "pattern_roi.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n保存: {p}")
print("\n※ 採用は『両期間100%超』のみ。片方だけ良い型は偶然とみなす（帯スキャンで全滅した教訓）")
