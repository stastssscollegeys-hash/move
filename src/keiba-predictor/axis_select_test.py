# -*- coding: utf-8 -*-
"""axis_select_test.py — ◎（割安さ1位）を軸にしたとき、「どのレースなら買うか」で回収率がどう変わるかを測る（2026-11-18 新設）

axis_stake_test.py の結論: 軸・券種・金額の配り方を変えても回収率は 82〜91% の間（◎軸がいちばん高い）。
残る手は「買うレースを選ぶ」。◎の 割安さ（モデル÷市場）・モデルの勝つ確率・人気 の帯ごとに、単勝・複勝・ワイド◎流し（均等）の回収率を出す。
前半（2019〜22）と後半（2023〜）の両方で同じ向きの帯だけを候補にする。
  python axis_select_test.py
"""
import collections, json, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as M

OUT = E.DB / "axis_select_results.json"


def main():
    preds, pay = C.predictions(), C.load_pay()
    rows = []
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("複勝") or not pp.get("単勝"):
            continue
        k2 = lambda k: tuple(sorted(map(int, str(k).split("-"))))
        wide = {k2(k): y / 100 for k, y in pp["ワイド"].items()}
        fuku = {int(k): y / 100 for k, y in pp["複勝"].items()}; tan = {int(k): y / 100 for k, y in pp["単勝"].items()}
        uma = [int(u) for u in pr["uma"]]
        p = np.asarray(pr["p"], float); q = np.asarray(pr["q"], float); p, q = p / p.sum(), q / q.sum()
        m = M.mark(pr, {}, "A"); marks = [u for _, u, _ in m]; hon = marks[0]; i = uma.index(hon)
        pop = int((q > q[i]).sum()) + 1
        others = marks[1:]
        w = np.mean([wide.get(tuple(sorted((hon, u))), 0) for u in others]) if others else 0.0
        rows.append(dict(half="前" if pr["key"][0] < "20230101" else "後", ratio=p[i] / q[i], p=p[i], pop=pop, n=len(uma),
                         tan=tan.get(hon, 0), fuku=fuku.get(hon, 0), wide=float(w)))
    def table(title, key, bins, labels):
        print(f"\n■ {title}\n{'帯':14s} {'レース':>7s} {'単勝':>7s} {'(前/後)':>12s} {'複勝':>7s} {'(前/後)':>12s} {'ワイド流し':>7s} {'(前/後)':>12s} {'◎3着内':>6s}")
        res = {}
        for (lo, hi), lb in zip(bins, labels):
            g = [r for r in rows if lo <= r[key] < hi]
            if len(g) < 200:
                continue
            f = [r for r in g if r["half"] == "前"]; b = [r for r in g if r["half"] == "後"]
            def mm(x, k): return np.mean([r[k] for r in x]) * 100 if x else float("nan")
            print(f"{lb:14s} {len(g):7,d} {mm(g,'tan'):6.1f}% {mm(f,'tan'):5.0f}/{mm(b,'tan'):<5.0f} {mm(g,'fuku'):6.1f}% {mm(f,'fuku'):5.0f}/{mm(b,'fuku'):<5.0f} {mm(g,'wide'):6.1f}% {mm(f,'wide'):5.0f}/{mm(b,'wide'):<5.0f} {np.mean([r['fuku']>0 for r in g])*100:5.1f}%")
            res[lb] = dict(n=len(g), tan=mm(g, 'tan'), tan_f=mm(f, 'tan'), tan_b=mm(b, 'tan'), fuku=mm(g, 'fuku'), fuku_f=mm(f, 'fuku'), fuku_b=mm(b, 'fuku'), wide=mm(g, 'wide'), wide_f=mm(f, 'wide'), wide_b=mm(b, 'wide'))
        return res
    out = {}
    out["ratio"] = table("◎の割安さ（モデル÷市場）", "ratio", [(0, 1.0), (1.0, 1.05), (1.05, 1.10), (1.10, 1.15), (1.15, 1.20), (1.20, 1.30), (1.30, 1.50), (1.50, 9)],
                         ["1.00未満", "1.00〜1.05", "1.05〜1.10", "1.10〜1.15", "1.15〜1.20", "1.20〜1.30", "1.30〜1.50", "1.50以上"])
    out["p"] = table("◎のモデルの勝つ確率", "p", [(0, .10), (.10, .15), (.15, .20), (.20, .30), (.30, .40), (.40, 1)], ["10%未満", "10〜15%", "15〜20%", "20〜30%", "30〜40%", "40%以上"])
    out["pop"] = table("◎の人気", "pop", [(1, 2), (2, 3), (3, 4), (4, 6), (6, 9), (9, 99)], ["1番人気", "2番人気", "3番人気", "4〜5番人気", "6〜8番人気", "9番人気以下"])
    out["n"] = table("頭数", "n", [(0, 10), (10, 13), (13, 16), (16, 99)], ["9頭以下", "10〜12頭", "13〜15頭", "16頭以上"])
    # 組み合わせ: 割安さ1.15以上 × 人気
    for lb, cond in (("割安さ1.15以上 かつ 1〜3番人気", lambda r: r["ratio"] >= 1.15 and r["pop"] <= 3), ("割安さ1.15以上 かつ 4〜8番人気", lambda r: r["ratio"] >= 1.15 and 4 <= r["pop"] <= 8),
                     ("割安さ1.30以上 かつ 4〜8番人気", lambda r: r["ratio"] >= 1.30 and 4 <= r["pop"] <= 8), ("割安さ1.30以上 かつ 勝つ確率10%以上", lambda r: r["ratio"] >= 1.30 and r["p"] >= .10),
                     ("割安さ1.20以上 かつ 勝つ確率15%以上", lambda r: r["ratio"] >= 1.20 and r["p"] >= .15)):
        g = [r for r in rows if cond(r)]; f = [r for r in g if r["half"] == "前"]; b = [r for r in g if r["half"] == "後"]
        mm = lambda x, k: np.mean([r[k] for r in x]) * 100 if x else float("nan")
        print(f"{lb:28s} {len(g):6,d}R 単勝 {mm(g,'tan'):5.1f}%（前{mm(f,'tan'):.0f}/後{mm(b,'tan'):.0f}） 複勝 {mm(g,'fuku'):5.1f}%（前{mm(f,'fuku'):.0f}/後{mm(b,'fuku'):.0f}） ワイド流し {mm(g,'wide'):5.1f}%（前{mm(f,'wide'):.0f}/後{mm(b,'wide'):.0f}）")
        out[lb] = dict(n=len(g), tan=mm(g, 'tan'), tan_f=mm(f, 'tan'), tan_b=mm(b, 'tan'), fuku=mm(g, 'fuku'), wide=mm(g, 'wide'), wide_f=mm(f, 'wide'), wide_b=mm(b, 'wide'))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
