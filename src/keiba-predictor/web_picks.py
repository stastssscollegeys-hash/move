# -*- coding: utf-8 -*-
"""web_picks.py — 当日朝の「期待値の取れる注目レース」選び・印・買い目の比較（2026-11-08 新設・Web版）

流れ（SKILL §3f）: web_live.py（当日朝に再実行）→ このスクリプト → web_facts/web_recent/course_profile → build_picks2_{日付}.py → 画像 → 下書き
  python web_picks.py --date 20261108 --rank                 # 全レースを ◎の「モデル÷市場」順に並べる（発走 --after 以降）
  python web_picks.py --date 20261108 --race 福島7 東京12 …  # 印と、印と一致する買い目の候補を実オッズで比べる
出力: 標準出力と {OUT}/{日付}_web_picks.json（印・候補の買い目・採用）

印の付け方（SKILL §2）: ◎=勝つ確率8%以上で最も割安／○▲=5%以上で割安な順／1〜3番人気で印のない馬は必ず△（印なしで切らない）。
買い目の採用: 印の馬だけで組んだ候補（ワイド◎流し・◎流し+相手同士・印BOX・馬連◎流し・3連複など）と web_frontier の自動候補から、
  的中率35%以上・最小戻り1倍以上（ガミなし）の中で期待回収率（モデル）が最大。無ければ下限を30%に下げる。採用は印と買い目の馬が一致するものだけ。
注意: 朝のオッズは薄い。期待回収率が1を大きく超える組は歪みの可能性。投稿には「朝のオッズで計算・発走までに変わる」と書く。
"""
import argparse
import itertools
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
import web_frontier as F
import web_live as WL


def marks_of(race):
    hs = sorted([h for h in race["horses"] if h.get("odds")], key=lambda h: h["odds"])
    for i, h in enumerate(hs):
        h["pop"] = i + 1
    ratio = lambda h: h["p_model"] / h["p_market"]
    c = [h for h in hs if h["p_model"] >= .08]
    if not c:
        return hs, []
    hon = max(c, key=ratio)
    rest = sorted([h for h in hs if h["p_model"] >= .05 and h is not hon], key=lambda h: -ratio(h))
    marks = [("◎", hon)] + list(zip(("○", "▲"), rest[:2]))
    used = {h["uma"] for _, h in marks}
    for h in hs[:3]:
        if h["uma"] not in used:
            marks.append(("△", h)); used.add(h["uma"])
    return hs, marks


def rank(d, after):
    rows = []
    for k, r in d.items():
        if r["start"] < after or not r["horses"]:
            continue
        hs, mk = marks_of(r)
        if not mk:
            continue
        h = mk[0][1]
        rows.append((h["p_model"] / h["p_market"], k, r, h, sum(x.get("new", False) for x in hs)))
    rows.sort(key=lambda x: -x[0])
    for ra, k, r, h, nn in rows:
        print(f"{k:5} {r['start']:>5} {r['title'][:14]:14} {r['dist']:7} {r['n']:2}頭 新馬{nn:2} ◎{h['uma']}{h['name'][:8]} {h['pop']}人 {h['odds']}倍 "
              f"勝{h['p_model']*100:.1f}%/市{h['p_market']*100:.1f}% 比{ra:.2f}")


def evaluate(k, r):
    hs, marks = marks_of(r)
    M = [h["uma"] for _, h in marks]
    H = M[0]
    o = [u for u in M if u != H]
    ex = {"ワイド◎流し": [("ワイド", (H, x)) for x in o],
          "ワイド印BOX": [("ワイド", c) for c in itertools.combinations(M, 2)],
          "馬連◎流し": [("馬連", (H, x)) for x in o],
          "3連複◎軸": [("3連複", (H,) + c) for c in itertools.combinations(o, 2)]}
    if len(M) <= 5:
        ex["3連複印BOX"] = [("3連複", c) for c in itertools.combinations(M, 3)]
    if len(o) >= 2:
        ex["馬連◎流し+ワイド◎流し"] = ex["馬連◎流し"] + ex["ワイド◎流し"]
    for a in itertools.combinations(o, 3):                    # ◎流し＋相手3頭どうしのワイド（11/8 福島7・8・11で採用）
        ex["ワイド◎流し+相手(" + ",".join(map(str, a)) + ")"] = ex["ワイド◎流し"] + [("ワイド", c) for c in itertools.combinations(a, 2)]
    for ax in o:                                               # 軸を本命と決めない（K13）: 3着内の見込みが高い印の馬を軸に印へ馬連
        ex[f"馬連{ax}軸→印"] = [("馬連", (ax, x)) for x in M if x != ax]
    best, rows, t3, order = F.run(r, extra=ex, verbose=False)
    idx = {h["uma"]: i for i, h in enumerate(r["horses"])}
    Ms = set(M)
    ok = lambda x: {u for _, c, _ in x["pts"] for u in c} == Ms
    pick = None
    for lo in (0.35, 0.30):
        good = [x for x in rows if ok(x) and x["hit"] >= lo and x["minret"] >= 1.0]
        if good:
            pick = max(good, key=lambda x: x["evp"]); break
    print("■", k, r["title"], r["start"], r["dist"], r["baba"], f"{r['n']}頭")
    for mk, h in marks:
        print(f"  {mk} {h['uma']:2} {h['name'][:10]:10} {h['pop']}人 {h['odds']:5}倍 勝{h['p_model']*100:4.1f}%/市{h['p_market']*100:4.1f}% "
              f"比{h['p_model']/h['p_market']:.2f} 3着内{t3[idx[h['uma']]]*100:3.0f}% {h['jockey']}/{h['trainer']}")
    for x in sorted([x for x in rows if ok(x)], key=lambda x: -x["evp"])[:6]:
        print("   %-24s %2d点 %6d円 的中%5.1f%% 期待(モデル)%.2f 期待(市場)%.2f 最小戻り%.2f" % (x["name"], len(x["pts"]), x["tot"], x["hit"] * 100, x["evp"], x["evq"], x["minret"]))
    if pick:
        print("  → 採用:", pick["name"], " / ".join(f"{t}{'-'.join(map(str, c))} {s}円" for t, c, s in pick["pts"]),
              f"| 的中{pick['hit']*100:.0f}% 期待{pick['evp']:.2f} 最小{pick['minret']:.1f}倍")
    else:
        print("  → 採用なし（的中30%以上・ガミなしの形が無い）＝注目レースから外す候補")
    return dict(race={kk: r[kk] for kk in r if kk != "horses"},
                marks=[dict(mark=m, uma=h["uma"], name=h["name"], pop=h["pop"], odds=h["odds"], p_model=h["p_model"], p_market=h["p_market"],
                            top3=round(float(t3[idx[h["uma"]]]), 3), jockey=h["jockey"], trainer=h["trainer"]) for m, h in marks],
                pick=pick and dict(name=pick["name"], pts=pick["pts"], tot=pick["tot"], hit=pick["hit"], evp=pick["evp"], evq=pick["evq"], minret=pick["minret"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--rank", action="store_true")
    ap.add_argument("--after", default="12:00", help="--rank でこの時刻以降の発走だけ")
    ap.add_argument("--race", nargs="*", default=[])
    a = ap.parse_args()
    d = json.load(open(WL.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))
    print("オッズ取得:", d.get("made_at"))
    if a.rank:
        rank(d["races"], a.after)
    out = {}
    for k in a.race:
        out[k] = evaluate(k, d["races"][k]); print()
    if out:
        p = WL.OUT / f"{a.date}_web_picks.json"
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("保存:", p)


if __name__ == "__main__":
    main()
