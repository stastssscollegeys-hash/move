# -*- coding: utf-8 -*-
"""
prob_calib_audit.py — 3着内・馬連・ワイドの確率の作り方を実測と突き合わせる（2026-10-02）
======================================================================================
コードベースに「単勝オッズ → 3着内／組み合わせの確率」の作り方が3通りあり、同じ買い目でも数字が違っていた。
  A  prob_core.top3_scenarios        … 上位8頭だけ列挙し合計を0.80に揃える（9番人気以下の3着内確率は0になる）
  B  kaime_select.top3_prob 系       … 2着・3着の確率に 0.80／0.70 を掛ける。組は t3a×t3b×0.80、馬連は Harville×0.80
  C  全頭の λ-Harville（切り捨てなし）… 2着は q^0.80、3着は q^0.70 を重みに全頭で正確に計算する
どれが実測に合うかを、蓄積DBの確定オッズと着順で測る（使うのはオッズと着順だけなので結果リークは無い）。

指標: 人気順ごとの「想定 vs 実測」と、対数損失（小さいほど正確）。組み合わせは人気1〜6位どうしの15組。
使い方: python prob_calib_audit.py
"""
from __future__ import annotations
import collections, itertools, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from prob_core import market_probs, top3_scenarios, ticket_probs, LAMBDA
from kaime_select import top3_prob, p_quinella, p_pair_top3

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"


def exact(q: dict, lam=LAMBDA):
    """全頭の λ-Harville。戻り値: (3着内確率, 馬連確率{(a,b)}, ワイド確率{(a,b)}, 3連複確率{(a,b,c)})"""
    us = list(q)
    w2 = {u: q[u] ** lam[1] for u in us}
    w3 = {u: q[u] ** lam[2] for u in us}
    S2, S3 = sum(w2.values()), sum(w3.values())
    t3 = collections.defaultdict(float)
    uren, wide, trio = collections.defaultdict(float), collections.defaultdict(float), collections.defaultdict(float)
    for a in us:
        for b in us:
            if b == a:
                continue
            pab = q[a] * w2[b] / (S2 - w2[a])
            uren[tuple(sorted((a, b)))] += pab
            d3 = S3 - w3[a] - w3[b]
            for c in us:
                if c == a or c == b:
                    continue
                p = pab * w3[c] / d3
                t3[a] += p; t3[b] += p; t3[c] += p
                for x, y in ((a, b), (a, c), (b, c)):
                    wide[tuple(sorted((x, y)))] += p
                trio[tuple(sorted((a, b, c)))] += p
    return t3, uren, wide, trio


def load():
    races = collections.defaultdict(dict)
    for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8")):
        try:
            o, u = float(r.get("単勝オッズ")), int(float(r.get("馬番")))
        except (TypeError, ValueError):
            continue
        f = r.get("着順int") or (int(str(r.get("着順")).strip()) if str(r.get("着順") or "").strip().isdigit() else None)
        if o > 0 and f:
            races[(r["date"], r["競馬場"], int(float(r["R"])))][u] = (o, int(f))
    out = []
    for k, hs in sorted(races.items()):
        fins = sorted(f for o, f in hs.values())
        if len(hs) < 8 or fins[:3] != [1, 2, 3]:
            continue
        if not 1.15 <= sum(1 / o for o, f in hs.values()) <= 1.40:
            continue
        out.append((k, {u: o for u, (o, f) in hs.items()}, {u: f for u, (o, f) in hs.items()}))
    return out


def logloss(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -(math.log(p) if y else math.log(1 - p))


def main():
    races = load()
    print(f"■ 対象 {len(races):,}レース")
    t3_tab = {m: collections.defaultdict(lambda: [0, 0.0, 0]) for m in "ABC"}     # pop → [n, Σp, 実測]
    ll = {m: 0.0 for m in "ABC"}
    pair = {t: {m: collections.defaultdict(lambda: [0, 0.0, 0]) for m in "ABC"} for t in ("馬連", "ワイド")}
    pll = {t: {m: 0.0 for m in "ABC"} for t in ("馬連", "ワイド")}
    npair = 0
    nh = 0
    for k, tan, fin in races:
        q = market_probs(tan)
        pop = {u: i + 1 for i, u in enumerate(sorted(tan, key=lambda u: tan[u]))}
        tpA = ticket_probs(top3_scenarios(q), q)
        tB = top3_prob(q)
        tC, uC, wC, _ = exact(q)
        top = {u for u, f in fin.items() if f <= 3}
        first2 = {u for u, f in fin.items() if f <= 2}
        for u in q:
            y = u in top
            nh += 1
            for m, p in (("A", tpA["複勝"].get((u,), 0.0)), ("B", tB[u]), ("C", tC[u])):
                c = t3_tab[m][min(pop[u], 12)]
                c[0] += 1; c[1] += p; c[2] += y
                ll[m] += logloss(p, y)
        top6 = sorted(tan, key=lambda u: tan[u])[:6]
        for a, b in itertools.combinations(top6, 2):
            key = tuple(sorted((a, b)))
            band = "1-3人気どうし" if max(pop[a], pop[b]) <= 3 else "4-6人気を含む"
            npair += 1
            yq, yw = set(key) == first2, set(key) <= top
            for m, pq_, pw_ in (("A", tpA["馬連"].get(key, 0.0), tpA["ワイド"].get(key, 0.0)),
                                ("B", p_quinella(a, b, q) * 0.80, p_pair_top3(a, b, tB)),
                                ("C", uC[key], wC[key])):
                for t, p, y in (("馬連", pq_, yq), ("ワイド", pw_, yw)):
                    c = pair[t][m][band]
                    c[0] += 1; c[1] += p; c[2] += y
                    pll[t][m] += logloss(p, y)

    print("\n■ 3着内確率（人気順ごと・想定 vs 実測）")
    print(f"{'人気':<6}{'頭数':>7}{'実測':>8}{'A 上位8頭':>10}{'B 掛け算':>9}{'C 全頭':>8}")
    for p in sorted(t3_tab["C"]):
        n = t3_tab["C"][p][0]
        print(f"{(str(p) if p < 12 else '12〜'):<6}{n:>8,}{t3_tab['C'][p][2]/n*100:>7.1f}%"
              + "".join(f"{t3_tab[m][p][1]/n*100:>9.1f}%" for m in "ABC"))
    print("  対数損失（小さいほど正確）: " + " / ".join(f"{m} {ll[m]/nh:.5f}" for m in "ABC"))
    for t in ("馬連", "ワイド"):
        print(f"\n■ {t}（人気1〜6位どうしの15組・想定 vs 実測）")
        print(f"{'帯':<12}{'組数':>8}{'実測':>8}{'A':>8}{'B':>8}{'C':>8}")
        for band in ("1-3人気どうし", "4-6人気を含む"):
            n = pair[t]["C"][band][0]
            print(f"{band:<12}{n:>8,}{pair[t]['C'][band][2]/n*100:>7.2f}%"
                  + "".join(f"{pair[t][m][band][1]/n*100:>7.2f}%" for m in "ABC"))
        print("  対数損失: " + " / ".join(f"{m} {pll[t][m]/npair:.5f}" for m in "ABC"))


if __name__ == "__main__":
    main()
