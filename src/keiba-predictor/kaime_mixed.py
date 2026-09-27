# -*- coding: utf-8 -*-
"""
kaime_mixed.py — 承認済みルールで重賞の買い目を組む（2026-09-25）
==================================================================
ルール（2026-09-19ユーザー承認・[[keiba-review-20260919-aite]]）:
  ・◎は独自指数1位、**相手は◎を除いた単勝人気の上位4頭**（○▲△△もその順に付け替える）
  ・買い目は◎からのワイド流し。金額は推定配当に反比例（どれが当たってもほぼ同じ額が戻る）
  ・**Σ(1/配当)≦1** を守る。1点的中で損になる安い相手は、馬連に替える→それでも無理なら外す
  ・2点未満しか残らなければ見送り
  ・🔥穴は印としては出すが買い目の軸にしない／3連複・3連単は使わない

使い方:
  python kaime_mixed.py --score research/score20_20260925.json --race スプリンターズS \
      --odds ../20260927/odds_20260927.json --key 20260927_中山_11 --budget 8000 --out research/kaime_sprinters.json
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path.home() / "Desktop" / "競馬予想レポート"
sys.path.insert(0, str(HERE))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from payout_estimator import estimate

UNIT = 100


def design(index_order: list[dict], odds: dict[int, float], budget: int) -> dict:
    hon = index_order[0]["uma"]
    mkt = [u for u, _ in sorted(odds.items(), key=lambda kv: kv[1]) if u != hon]
    aite = mkt[:4]
    pts = [{"t": "ワイド", "u": u, "est": round(estimate("ワイド", [odds[hon], odds[u]]), 1)} for u in aite]
    dropped, re_added = [], []
    while len(pts) >= 2 and sum(1 / p["est"] for p in pts) > 1.0:
        lo = min(pts, key=lambda p: p["est"]); pts.remove(lo); dropped.append(lo)
    for d in sorted(dropped, key=lambda p: p["est"]):
        e2 = round(estimate("馬連", [odds[hon], odds[d["u"]]]), 1)
        if sum(1 / p["est"] for p in pts) + 1 / e2 <= 1.0:
            pts.append({"t": "馬連", "u": d["u"], "est": e2}); re_added.append(d["u"])
    dropped = [d for d in dropped if d["u"] not in re_added]
    if len(pts) < 2:
        return {"skip": True, "hon": hon, "aite": aite,
                "why": "◎が断然人気で、人気馬との組み合わせに配当がつかない（どう組んでも1点的中が損になる）"}
    w = [1 / p["est"] for p in pts]
    for p, x in zip(pts, w):
        p["amt"] = max(UNIT, int(round(budget * x / sum(w) / UNIT)) * UNIT)
    while sum(p["amt"] for p in pts) != budget:
        d = budget - sum(p["amt"] for p in pts)
        tgt = (min(pts, key=lambda p: p["amt"] * p["est"]) if d > 0
               else max((p for p in pts if p["amt"] > UNIT), key=lambda p: p["amt"] * p["est"]))
        tgt["amt"] += UNIT if d > 0 else -UNIT
    for p in pts:
        p["ret"] = round(p["amt"] * p["est"] / budget, 2)
    return {"skip": False, "hon": hon, "aite": aite, "bets": sorted(pts, key=lambda p: -p["amt"]),
            "over": round(sum(1 / p["est"] for p in pts), 2), "dropped": [d["u"] for d in dropped],
            "re_added": re_added, "budget": budget}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", required=True); ap.add_argument("--race", required=True)
    ap.add_argument("--odds", required=True); ap.add_argument("--key", required=True)
    ap.add_argument("--budget", type=int, default=8000); ap.add_argument("--out")
    a = ap.parse_args()
    sc_p = Path(a.score) if Path(a.score).is_absolute() else ROOT / "20260926" / a.score
    sc = json.loads(sc_p.read_text(encoding="utf-8"))
    horses = sc[a.race]["horses"]
    odds_p = Path(a.odds) if Path(a.odds).is_absolute() else ROOT / a.odds
    odds_all = json.loads(odds_p.read_text(encoding="utf-8"))
    odds = {int(k): float(v) for k, v in odds_all[a.key].items()}
    name = {h["uma"]: h["name"] for h in horses}
    pop = {u: i + 1 for i, (u, _) in enumerate(sorted(odds.items(), key=lambda kv: kv[1]))}
    d = design(horses, odds, a.budget)
    marks = {"◎": d["hon"], "○": d["aite"][0], "▲": d["aite"][1], "△": d["aite"][2:4]}
    print(f"═══ {a.race}（{sc[a.race]['type']}）═══")
    print(f"  ◎ {d['hon']:>2} {name[d['hon']]}（{pop[d['hon']]}番人気 {odds[d['hon']]}倍・指数1位）")
    for lab, u in zip(("○", "▲", "△", "△"), d["aite"]):
        h = next(x for x in horses if x["uma"] == u)
        print(f"  {lab} {u:>2} {name[u]}（{pop[u]}番人気 {odds[u]}倍・指数{horses.index(h)+1}位）")
    if d["skip"]:
        print("  → 見送り:", d["why"])
    else:
        print(f"  合計{a.budget:,}円 / Σ(1/配当)={d['over']}")
        for p in d["bets"]:
            print(f"    【{p['t']}】{d['hon']}-{p['u']} {p['amt']:,}円 推定{p['est']}倍 → 当たれば{p['ret']*100:.0f}%")
        if d["dropped"]:
            print("    外した相手:", "・".join(f"{name[u]}({pop[u]}人気)" for u in d["dropped"]), "※ワイドが安く1点的中で損になるため")
        if d["re_added"]:
            print("    馬連に替えた相手:", "・".join(name[u] for u in d["re_added"]))
    if a.out:
        p = Path(a.out) if Path(a.out).is_absolute() else ROOT / "20260926" / a.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"race": a.race, "marks": marks, "design": d,
                                 "name": {str(k): v for k, v in name.items()},
                                 "pop": {str(k): v for k, v in pop.items()},
                                 "odds": {str(k): v for k, v in odds.items()}}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        print("  saved", p.name)


if __name__ == "__main__":
    main()
