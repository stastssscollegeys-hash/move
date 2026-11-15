# -*- coding: utf-8 -*-
"""web_review.py — その日の全レースを、前夜のモデル（web_live）と照合する（2026-11-07 新設・JRA-VAN終了後の「全レース採点」）
  python web_review.py --date 20261107   （先に web_results.py → web_to_db.py）
出力: 標準出力と {OUT}/{日付}_web_review.md
  ・◎相当＝前夜のモデル確率8%以上で最も割安（モデル÷市場）／1番人気／モデル確率1位 の 勝率・3着内率・単勝回収（確定オッズ）
  ・場×芝ダごとの 1番人気の勝ち・勝ち馬の人気・内外枠の3着内率・3連単の中央値（荒れる/堅いの偏り）
  ・激走＝最終6番人気以下で3着内に来た馬と、前夜のモデルがどう見ていたか（確率・割安度・順位）
注意: 市場確率は前夜（前売り）のオッズ。確定オッズで払うので、◎相当の単勝回収は参考値"""
import argparse, collections, json, statistics as S, sys
sys.stdout.reconfigure(encoding="utf-8")
import web_live as W

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    R = json.load(open(W.OUT / f"{a.date}_web_results.json", encoding="utf-8"))
    P = json.load(open(W.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"]
    out = []; pr = lambda *x: (print(*x), out.append(" ".join(map(str, x))))
    rows, up = [], []
    g = collections.defaultdict(lambda: dict(n=0, favw=0, fav3=0, pops=[], inn=[0, 0], out=[0, 0], t3=[]))
    for k, r in R.items():
        if not r["rows"]: continue
        hs = P[k]["horses"]; res = {h["uma"]: h for h in r["rows"]}
        for h in hs: h["ratio"] = h["p_model"] / h["p_market"] if h["p_market"] else 0
        cand = [h for h in hs if h["p_model"] >= 0.08 and h["uma"] in res]
        maru = max(cand, key=lambda h: h["ratio"]) if cand else None
        live = [h for h in hs if h["uma"] in res]
        fav, topm = min(live, key=lambda h: h["odds"]), max(live, key=lambda h: h["p_model"])
        st = lambda h: None if not h else (res[h["uma"]]["rank"] == 1, res[h["uma"]]["rank"] <= 3, res[h["uma"]]["odds"] if res[h["uma"]]["rank"] == 1 else 0)
        win = [h for h in r["rows"] if h["rank"] == 1][0]
        wr = sorted(hs, key=lambda h: -h["ratio"]); wrank = [i + 1 for i, h in enumerate(wr) if h["uma"] == win["uma"]]
        rows.append((st(maru), st(fav), st(topm), wrank[0] if wrank else None, len(hs)))
        surf = "芝" if r["dist"].startswith("芝") else "ダ"; x = g[(r["venue"], surf)]; x["n"] += 1
        f2 = min(r["rows"], key=lambda h: h["odds"]); x["favw"] += f2["rank"] == 1; x["fav3"] += f2["rank"] <= 3
        x["pops"].append(win["pop"]); x["t3"].append(r["pay"]["3連単"][0]["yen"])
        for h in r["rows"]:
            side = x["inn"] if h["waku"] <= 4 else x["out"]; side[0] += 1; side[1] += h["rank"] <= 3
            if h["rank"] <= 3 and h["pop"] >= 6:
                m = [q for q in hs if q["uma"] == h["uma"]][0]
                rk = [i + 1 for i, q in enumerate(sorted(hs, key=lambda q: -q["p_model"])) if q["uma"] == h["uma"]][0]
                up.append((k, r["title"][:10], h["rank"], h["uma"], h["name"], h["pop"], h["odds"], round(m["p_model"] * 100, 1), round(m["ratio"], 2), rk, h["jockey"]))
    def agg(i, lab):
        v = [r[i] for r in rows if r[i]]; n = len(v); w = sum(a_ for a_, b, c in v); t = sum(b for a_, b, c in v)
        pr(f"{lab}: {n}R 勝{w}({w/n:.0%}) 3着内{t}({t/n:.0%}) 単勝回収{sum(c for a_, b, c in v)/n:.0%}")
    pr(f"## {a.date} 全{len(rows)}レースの採点（前夜のモデル×確定結果）")
    agg(0, "◎相当（p>=8%で最も割安）"); agg(1, "1番人気（前夜）"); agg(2, "モデル確率1位")
    pr(f"勝ち馬の割安順位 中央値{S.median([r[3] for r in rows if r[3]])}（頭数の中央値{S.median([r[4] for r in rows])}）")
    pr("\n## 場×芝ダ（1番人気勝ち／勝ち馬の人気 中央・平均／内(1-4枠)・外(5-8枠)の3着内率／3連単の中央値）")
    for key, x in sorted(g.items()):
        pr(f"{key[0]}{key[1]} {x['n']}R: 1人気勝{x['favw']}・3着内{x['fav3']} ／ 勝ち馬人気 {S.median(x['pops'])}・{S.mean(x['pops']):.1f} ／ 内{x['inn'][1]}/{x['inn'][0]}={x['inn'][1]/x['inn'][0]:.0%} 外{x['out'][1]}/{x['out'][0]}={x['out'][1]/x['out'][0]:.0%} ／ 3連単 {int(S.median(x['t3'])):,}円")
    n3 = sum(1 for r in R.values() if r["rows"] and r["pay"]["3連単"][0]["yen"] >= 10000)
    pr(f"3連単1万円以上: {n3}/{len(rows)}レース")
    pr(f"\n## 激走（最終6番人気以下で3着内）{len(up)}頭 ／ うち前夜の割安度1.0以上 {sum(1 for u in up if u[8] >= 1.0)}頭")
    for u in sorted(up, key=lambda u: -u[6]): pr(" ", u)
    (W.OUT / f"{a.date}_web_review.md").write_text("\n".join(out), encoding="utf-8")

if __name__ == "__main__":
    main()
