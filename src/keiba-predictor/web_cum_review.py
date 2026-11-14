# -*- coding: utf-8 -*-
"""web_cum_review.py — Web版の日（web_probs＋web_results がそろった日）を全部足して、印と買い方の形を採点する（2026-11-14 新設）

  python web_cum_review.py            # そろっている日を全部
  python web_cum_review.py --dates 20261107 20261108
見るもの: 印ごとの勝率・3着内率・単勝回収／同じ印でワイドの形を変えたときの成績（◎流し・印BOX・◎流し＋相手同士）／
          ◎が3着を外したレースで「印の馬同士」のワイドが決まった割合（＝◎の単独軸が全滅する頻度）。
注意: 印は web_picks.marks_of（その日の web_probs の時点のオッズ）で付け直したもの。払戻は確定払戻。1点100円の均等買いで比べる
      （公開した買い目の金額配分とは違う）。数十〜百レースでは何も決めない＝毎週足して眺める。
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="*")
    a = ap.parse_args()
    ds = a.dates or days()
    mk = {}                                   # 印 → [頭数, 勝, 3着内, 単勝払戻]
    st = {}                                   # 形 → [レース, 点, 的中レース, 払戻]
    miss = [0, 0, 0]                          # ◎が3着外 / うち印同士のワイドが決着 / うち印2頭以上が3着内
    per = {}
    for d in ds:
        pr = json.load(open(WL.OUT / f"{d}_web_probs.json", encoding="utf-8"))["races"]
        rs = json.load(open(WL.OUT / f"{d}_web_results.json", encoding="utf-8"))
        dd = per.setdefault(d, {})
        for k, r in pr.items():
            if k not in rs or not r.get("horses"):
                continue
            hs, marks = WP.marks_of(r)
            if not marks:
                continue
            rows = rs[k]["rows"]
            rank = {x["uma"]: x["rank"] for x in rows if isinstance(x.get("rank"), int)}
            win = {int(w["comb"]): w["yen"] for w in rs[k]["pay"].get("単勝", [])}
            wide = {tuple(sorted(map(int, w["comb"].split("-")))): w["yen"] for w in rs[k]["pay"].get("ワイド", [])}
            M = [h["uma"] for _, h in marks]
            for m, h in marks:
                u = h["uma"]; e = mk.setdefault(m, [0, 0, 0, 0])
                e[0] += 1; e[1] += rank.get(u) == 1; e[2] += rank.get(u, 99) <= 3; e[3] += win.get(u, 0)
            H, o = M[0], M[1:]
            forms = {"ワイド◎流し": [(H, x) for x in o],
                     "ワイド印BOX": list(itertools.combinations(M, 2)),
                     "◎流し＋○▲の1点": [(H, x) for x in o] + ([tuple(o[:2])] if len(o) >= 2 else []),
                     "◎抜きの印BOX": list(itertools.combinations(o, 2))}
            for n, pts in forms.items():
                pts = [tuple(sorted(c)) for c in pts]
                if not pts:
                    continue
                ret = sum(wide.get(c, 0) for c in pts)
                for key in (n, ):
                    e = st.setdefault(key, [0, 0, 0, 0]); e[0] += 1; e[1] += len(pts); e[2] += ret > 0; e[3] += ret
                e = dd.setdefault(n, [0, 0, 0, 0]); e[0] += 1; e[1] += len(pts); e[2] += ret > 0; e[3] += ret
            if rank.get(H, 99) > 3:
                miss[0] += 1
                miss[1] += any(tuple(sorted(c)) in wide for c in itertools.combinations(o, 2))
                miss[2] += sum(rank.get(u, 99) <= 3 for u in o) >= 2
    print("対象日:", ds)
    print("\n## 印ごと（頭数・勝率・3着内率・単勝回収）")
    for m in "◎○▲△":
        if m in mk:
            n, w, t, y = mk[m]
            print(f"  {m} {n:3}頭 勝{w/n*100:4.0f}% 3着内{t/n*100:4.0f}% 単勝回収{y/n:5.0f}%")
    print("\n## ワイドの形（1点100円の均等買い・確定払戻）")
    for n, (rc, pt, hit, ret) in st.items():
        print(f"  {n:12} {rc:3}R {pt:4}点 何か当たる{hit/rc*100:4.0f}% 回収{ret/pt:5.1f}%")
    print("\n## 日ごとの回収率")
    for d, v in per.items():
        print(" ", d, " / ".join(f"{n} {ret/pt:.0f}%({hit}/{rc})" for n, (rc, pt, hit, ret) in v.items()))
    if miss[0]:
        print(f"\n## ◎が3着を外した {miss[0]}R のうち、印の馬2頭以上が3着内 {miss[2]}R（{miss[2]/miss[0]*100:.0f}%）＝◎流しだけだと取れない")
    json.dump(dict(dates=ds, marks=mk, forms=st, per_day=per, honmei_miss=miss),
              open(WL.OUT / "web_cum_review.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
