# -*- coding: utf-8 -*-
"""bet_type_by_band_test.py — 全券種（単勝・複勝・馬連・馬単・ワイド・3連複・3連単）を、◎の割安さの帯ごとに比べる（2026-11-26 新設）

きっかけ: 2026-11-26 ユーザー指示「単勝とワイドもいいが、馬連・馬単・3連複・3連単・複勝など、いろいろな買い方を検討して」。
同日の race_select_test.py で、前半・後半とも100%を超えたのは「◎の割安さ1.30以上」のレースだけ（単勝110.7%・ワイド◎-○ 112.3%）だった。
ここでは同じ印（◎＝割安さ1位・確率8%以上／○▲＝5%以上で割安な順／△＝1〜3番人気で印なし）で、券種と形を変えて測る。
データ: 年ごとの前向き予測（combo_backtest.predictions・約2.5万レース）と実際の払戻。確定オッズ・1点100円の均等買い。
見るもの: 帯ごとに、各形の 点数・何か当たる率・回収率（全体／前半2019〜22／後半2023〜）と、最大の1本を除いた回収率。
注意: 3連単・3連複は1本の大きな配当で数字が動く。「最大の1本を除く」と前半・後半の両方で見る。区分×形で約50通り見るので、偶然の100%超が混ざる。
  python bet_type_by_band_test.py
"""
import collections, itertools, json, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E

OUT = E.DB / "bet_type_by_band_results.json"


def marks(pr):
    p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), list(pr["uma"])
    p, q = p / p.sum(), q / q.sum(); n = len(uma); ratio = p / q
    c = [i for i in range(n) if p[i] >= .08] or [int(np.argmax(p))]
    hon = max(c, key=lambda i: ratio[i])
    rest = sorted([i for i in range(n) if i != hon and p[i] >= .05], key=lambda i: -ratio[i])
    m = [hon] + rest[:2]; used = set(m); d = []
    for i in np.argsort(-q)[:3]:
        if int(i) not in used:
            d.append(int(i)); used.add(int(i))
    U = lambda i: int(uma[i])
    return U(hon), [U(i) for i in rest[:2]], [U(i) for i in d], float(ratio[hon])


def main():
    preds, pay = C.predictions(), C.load_pay()
    S = collections.defaultdict(lambda: [0, 0, 0, 0, 0])      # (帯, 形, 期) → [R, 点, 的中R, 払戻, 最大の1本]
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("単勝"):
            continue
        H, core, D, r = marks(pr)
        if len(core) < 2:
            continue
        o, t = core; aite = core + D
        T = lambda name, key=lambda k: tuple(sorted(map(int, k.split("-")))): {key(k): y for k, y in pp.get(name, {}).items()}
        tan, fuku = T("単勝", lambda k: int(k)), T("複勝", lambda k: int(k))
        ren, wide, trio = T("馬連"), T("ワイド"), T("3連複")
        ordered = lambda k: tuple(map(int, k.split("-")))
        utan, tri3 = T("馬単", ordered), T("3連単", ordered)
        s2 = lambda *c: tuple(sorted(c))
        F = {
            "単勝◎": (tan, [H]),
            "複勝◎": (fuku, [H]),
            "複勝◎＋複勝○": (fuku, [H, o]),
            "馬連◎-○": (ren, [s2(H, o)]),
            "馬連◎-○▲": (ren, [s2(H, o), s2(H, t)]),
            "馬連◎流し（印全部）": (ren, [s2(H, x) for x in aite]),
            "馬単◎→○": (utan, [(H, o)]),
            "馬単◎→○▲": (utan, [(H, o), (H, t)]),
            "馬単◎⇔○（表裏）": (utan, [(H, o), (o, H)]),
            "ワイド◎-○": (wide, [s2(H, o)]),
            "ワイド◎-○▲": (wide, [s2(H, o), s2(H, t)]),
            "ワイド◎流し（印全部）": (wide, [s2(H, x) for x in aite]),
            "3連複◎-○-▲（1点）": (trio, [s2(H, o, t)]),
            "3連複 ◎-○▲-印全部": (trio, list(dict.fromkeys(s2(H, x, y) for x in core for y in aite if y != x))),
            "3連単◎→○▲→印全部": (tri3, [(H, x, y) for x in core for y in aite if y != x]),
            "3連単◎→○→▲（1点）": (tri3, [(H, o, t)]),
            "3連単 ◎○▲BOX（6点）": (tri3, list(itertools.permutations((H, o, t)))),
        }
        band = "割安さ1.30以上" if r >= 1.30 else "割安さ1.15〜1.30" if r >= 1.15 else "割安さ1.15未満"
        half = "前" if pr["key"][0] < "20230101" else "後"
        for nm, (tbl, pts) in F.items():
            ret = sum(tbl.get(c, 0) for c in pts)
            for b in (band, "全レース"):
                for h in (half, "全"):
                    e = S[(b, nm, h)]; e[0] += 1; e[1] += len(pts); e[2] += ret > 0; e[3] += ret; e[4] = max(e[4], ret)
    out = {}
    forms = list(F)
    for b in ("割安さ1.30以上", "割安さ1.15〜1.30", "割安さ1.15未満", "全レース"):
        n = S[(b, forms[0], "全")][0]
        print(f"\n■ {b}（{n:,}レース）")
        print(f"  {'形':22} {'点/R':>5} {'当たる':>6} ｜ 回収 全体／前半／後半 ｜ 最大の1本を除く")
        rows = []
        for nm in forms:
            a, f, bk = S[(b, nm, "全")], S[(b, nm, "前")], S[(b, nm, "後")]
            g = lambda e: e[3] / (e[1] or 1)
            ex = (a[3] - a[4]) / (a[1] or 1)
            rows.append((nm, a[1] / a[0], a[2] / a[0] * 100, g(a), g(f), g(bk), ex))
            out[f"{b}|{nm}"] = dict(n=a[0], pts=a[1], hit=a[2], ret=a[3], all=g(a), front=g(f), back=g(bk), ex_max=ex)
        for nm, k, hit, ga, gf, gb, ex in rows:
            flag = " ★" if gf > 100 and gb > 100 and ex > 100 else ""
            print(f"  {nm:22} {k:5.1f} {hit:5.1f}% ｜ {ga:6.1f}／{gf:6.1f}／{gb:6.1f} ｜ {ex:6.1f}{flag}")
    OUT.write_text(json.dumps(dict(made="20261126", results=out), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n★＝前半・後半とも100%超で、最大の1本を除いても100%超\n保存:", OUT)


if __name__ == "__main__":
    main()
