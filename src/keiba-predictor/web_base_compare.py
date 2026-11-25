# -*- coding: utf-8 -*-
"""web_base_compare.py — Web版の日（web_probs＋web_results がそろった日）で、軸の選び方と券種を横に並べて比べる（2026-11-26 新設）

  python web_base_compare.py            # そろっている日を全部
きっかけ: 2026-11-26 ユーザー指示「これまでの結果をもとに、的中率・回収率・買い目・予想の方法まで根本から見直す」。
見るもの（1点100円・確定払戻）:
  1) 軸の選び方 ＝ ◎（割安さ）／1番人気（確定人気）／P（モデル確率1位）／2番人気 の 勝率・3着内率・単勝回収・複勝回収
  2) ◎を「割安さの帯」「◎の人気」「頭数」「重賞か平場か」で分けたときの成績
  3) 券種 ＝ 同じ軸で 単勝・複勝・馬連（軸-相手）・ワイド（軸-相手）・3連複（軸-相手2頭）を買ったときの回収率
注意: 印は web_picks.marks_of（その日の web_probs の時点のオッズ）で付け直したもの。数十〜200レースでは何も決めない。
      10年の前向き検証（docs/keiba_2026_summary_20261118.md ほか）と向きが同じかどうかを見るための表。
"""
import itertools
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
import web_live as WL
import web_picks as WP


def days():
    ps = {re.match(r"(\d{8})", p.name).group(1) for p in WL.OUT.glob("*_web_probs.json")}
    rs = {re.match(r"(\d{8})", p.name).group(1) for p in WL.OUT.glob("*_web_results.json")}
    return sorted(ps & rs)


class Acc:
    def __init__(self): self.d = {}
    def add(self, key, n, hit, ret):
        e = self.d.setdefault(key, [0, 0, 0, 0]); e[0] += 1; e[1] += n; e[2] += bool(hit); e[3] += ret
    def show(self, title, order=None):
        print(f"\n## {title}")
        for k in (order or self.d):
            if k in self.d:
                rc, pt, hit, ret = self.d[k]
                print(f"  {k:26} {rc:3}R {pt:4}点 的中{hit/rc*100:5.1f}% 回収{(ret/pt if pt else 0):6.1f}%")


def main():
    ds = days()
    one, band, bets, daily = Acc(), Acc(), Acc(), {}
    for d in ds:
        pr = json.load(open(WL.OUT / f"{d}_web_probs.json", encoding="utf-8"))["races"]
        rs = json.load(open(WL.OUT / f"{d}_web_results.json", encoding="utf-8"))
        for k, r in pr.items():
            if k not in rs or not r.get("horses"):
                continue
            hs, marks = WP.marks_of(r)
            if not marks:
                continue
            rows = rs[k]["rows"]; pay = rs[k]["pay"]
            rank = {x["uma"]: x["rank"] for x in rows if isinstance(x.get("rank"), int)}
            pop = {x["uma"]: x.get("pop") for x in rows}
            win = {int(w["comb"]): w["yen"] for w in pay.get("単勝", [])}
            plc = {int(w["comb"]): w["yen"] for w in pay.get("複勝", [])}
            pair = lambda name: {tuple(sorted(map(int, w["comb"].split("-")))): w["yen"] for w in pay.get(name, [])}
            wide, ren, trio = pair("ワイド"), pair("馬連"), pair("3連複")
            M = [h["uma"] for _, h in marks]; H = M[0]
            hh = {h["uma"]: h for h in hs}
            P = max(hs, key=lambda h: h.get("p_model") or 0)["uma"]
            byp = sorted([u for u in pop if isinstance(pop[u], int)], key=lambda u: pop[u])
            if len(byp) < 3:
                continue
            F1, F2 = byp[0], byp[1]
            # 1) 軸の選び方
            for name, u in (("◎（割安さ）", H), ("1番人気（確定）", F1), ("P（モデル確率1位）", P), ("2番人気（確定）", F2)):
                one.add(name + " 単勝", 1, rank.get(u) == 1, win.get(u, 0))
                one.add(name + " 複勝", 1, rank.get(u, 99) <= 3, plc.get(u, 0))
            # 2) ◎の内訳
            h = hh[H]; ratio = (h["p_model"] / h["p_market"]) if h.get("p_market") else 0
            rb = "割安さ1.30以上" if ratio >= 1.30 else "割安さ1.15〜1.30" if ratio >= 1.15 else "割安さ1.15未満"
            pb = "◎が1番人気" if pop.get(H) == 1 else "◎が2〜3番人気" if pop.get(H) in (2, 3) else "◎が4〜5番人気" if pop.get(H) in (4, 5) else "◎が6番人気以下"
            nb = "11頭以下" if r["n"] <= 11 else "12〜15頭" if r["n"] <= 15 else "16頭以上"
            gb = "重賞" if re.search(r"G[123Ⅰ-Ⅲ]|GI", r.get("cond", "") + r.get("title", "")) else "平場・特別"
            for key in (rb, pb, nb, gb, "◎がP（確率1位）と同じ" if H == P else "◎とPが別の馬"):
                band.add(key + " ◎単勝", 1, rank.get(H) == 1, win.get(H, 0))
                band.add(key + " ◎複勝", 1, rank.get(H, 99) <= 3, plc.get(H, 0))
            # 3) 券種（軸ごと。相手は「印の馬（軸を除く）」）
            for an, ax in (("◎軸", H), ("1番人気軸", F1), ("P軸", P)):
                o = [x for x in M if x != ax][:4]
                if not o:
                    continue
                for bn, tbl, pts in (("馬連 軸-相手", ren, [tuple(sorted((ax, x))) for x in o]),
                                     ("ワイド 軸-相手", wide, [tuple(sorted((ax, x))) for x in o]),
                                     ("3連複 軸-相手2頭", trio, [tuple(sorted((ax, a, b))) for a, b in itertools.combinations(o, 2)])):
                    ret = sum(tbl.get(c, 0) for c in pts)
                    bets.add(f"{an} {bn}", len(pts), ret > 0, ret)
            # 人気どおり（比べる物差し）
            bets.add("物差し 馬連 1-2番人気", 1, tuple(sorted((F1, F2))) in ren, ren.get(tuple(sorted((F1, F2))), 0))
            bets.add("物差し ワイド 1-2番人気", 1, tuple(sorted((F1, F2))) in wide, wide.get(tuple(sorted((F1, F2))), 0))
            e = daily.setdefault(d, [0, 0, 0, 0, 0]); e[0] += 1; e[1] += win.get(H, 0); e[2] += win.get(F1, 0); e[3] += plc.get(P, 0); e[4] += plc.get(F1, 0)
    print("対象日:", ds)
    one.show("1) 軸の選び方（1頭に100円）")
    band.show("2) ◎の内訳")
    bets.show("3) 券種（相手は印の馬・最大4頭。1点100円）")
    print("\n## 日ごと（◎単勝／1番人気単勝／P複勝／1番人気複勝 の回収率）")
    for d, (n, a, b, c, e) in daily.items():
        print(f"  {d} {n:2}R  ◎単{a/n:5.0f}%  1人気単{b/n:5.0f}%  P複{c/n:5.0f}%  1人気複{e/n:5.0f}%")
    json.dump(dict(dates=ds, one=one.d, band=band.d, bets=bets.d, daily=daily), open(WL.OUT / "web_base_compare.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
