# -*- coding: utf-8 -*-
"""mark_slot_test.py — 印の枠ごと（◎○▲△・穴）の成績を10年分で測り、▲と穴（🔥）の付け方の候補を比べる（2026-11-18 新設）

きっかけ: 今年の総まとめで ▲（単勝回収43%・137R）と 🔥（145頭で3勝）が弱い。10年分で「たまたま」か「付け方の問題」かを見る。
現行: ◎＝勝つ確率8%以上で割安さ1位／○▲＝勝つ確率5%以上で割安さ2・3位／△＝1〜3番人気で印の無い馬。
比べる ▲ の候補: 現行（割安さ3位）／残りのうちモデル確率1位／残りのうち「確率×割安さ」1位／割安さ3位だが勝つ確率8%以上に限る
穴（🔥）の候補: 6番人気以下で 割安さ≧1.2・1.3・1.5（勝つ確率2%以上・3%以上・5%以上）のうち割安さ1位
見るもの: 頭数・勝率・3着内率・単勝回収・複勝回収・◎とのワイド回収（前半/後半）
  python mark_slot_test.py
"""
import collections, json, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as M

OUT = E.DB / "mark_slot_results.json"


def main():
    preds, pay = C.predictions(), C.load_pay()
    R = collections.defaultdict(lambda: collections.defaultdict(list))
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("複勝") or not pp.get("単勝"):
            continue
        k2 = lambda k: tuple(sorted(map(int, str(k).split("-"))))
        wide = {k2(k): y / 100 for k, y in pp["ワイド"].items()}
        fuku = {int(k): y / 100 for k, y in pp["複勝"].items()}; tan = {int(k): y / 100 for k, y in pp["単勝"].items()}
        uma = [int(u) for u in pr["uma"]]; n = len(uma)
        p = np.asarray(pr["p"], float); q = np.asarray(pr["q"], float); p, q = p / p.sum(), q / q.sum()
        ratio = p / q; pop = np.empty(n, int); pop[np.argsort(-q)] = np.arange(1, n + 1)
        m = M.mark(pr, {}, "A"); idx = {a: [] for a in "◎○▲△"}
        for a, u, _ in m: idx[a].append(uma.index(u))
        hon = idx["◎"][0]; used = {i for v in idx.values() for i in v}
        half = "前" if pr["key"][0] < "20230101" else "後"
        def add(nm, i):
            u = uma[i]
            rec = (tan.get(u, 0), fuku.get(u, 0), wide.get(tuple(sorted((u, uma[hon]))), 0) if i != hon else None, pop[i])
            R[nm][half].append(rec); R[nm]["全"].append(rec)
        add("◎（現行）", hon)
        for a in "○▲":
            for i in idx[a]: add(f"{a}（現行・割安さ{'2' if a=='○' else '3'}位）", i)
        for i in idx["△"]: add("△（現行・人気上位で印なし）", i)
        o = idx["○"][0] if idx["○"] else None
        rest = [i for i in range(n) if i != hon and i != o]
        if rest and o is not None:
            c5 = [i for i in rest if p[i] >= .05]
            if c5:
                add("▲候補A 残りでモデル確率1位", max(c5, key=lambda i: p[i]))
                add("▲候補B 残りで確率×割安さ1位", max(c5, key=lambda i: p[i] * ratio[i]))
            c8 = [i for i in rest if p[i] >= .08]
            if c8: add("▲候補C 割安さ順・勝つ確率8%以上に限る", max(c8, key=lambda i: ratio[i]))
            c10 = [i for i in rest if p[i] >= .10]
            if c10: add("▲候補D 割安さ順・勝つ確率10%以上に限る", max(c10, key=lambda i: ratio[i]))
        for lo_r in (1.2, 1.3, 1.5):
            for lo_p in (.02, .03, .05):
                c = [i for i in range(n) if pop[i] >= 6 and ratio[i] >= lo_r and p[i] >= lo_p and i not in (hon,)]
                if c: add(f"穴 6番人気以下・割安さ{lo_r}以上・確率{int(lo_p*100)}%以上", max(c, key=lambda i: ratio[i]))
        # 印の無い馬（参考）
        for i in range(n):
            if i not in used: add("無印（全部）", i)
    print(f"{'枠':36s} {'頭数':>7s} {'平均人気':>5s} {'勝率':>6s} {'3着内':>6s} {'単勝':>7s} {'(前/後)':>9s} {'複勝':>7s} {'(前/後)':>9s} {'◎とのワイド':>8s} {'(前/後)':>9s}")
    out = {}
    for nm, d in R.items():
        a = d["全"]; f = d["前"]; b = d["後"]
        mm = lambda x, k: np.mean([r[k] for r in x if r[k] is not None]) * 100 if x else float("nan")
        hasw = a[0][2] is not None
        print(f"{nm:36s} {len(a):7,d} {np.mean([r[3] for r in a]):5.1f} {np.mean([r[0]>0 for r in a])*100:5.1f}% {np.mean([r[1]>0 for r in a])*100:5.1f}% {mm(a,0):6.1f}% {mm(f,0):4.0f}/{mm(b,0):<4.0f} {mm(a,1):6.1f}% {mm(f,1):4.0f}/{mm(b,1):<4.0f} "
              + (f"{mm(a,2):6.1f}% {mm(f,2):4.0f}/{mm(b,2):<4.0f}" if hasw else "      —"))
        out[nm] = dict(n=len(a), pop=float(np.mean([r[3] for r in a])), win=float(np.mean([r[0] > 0 for r in a])), top3=float(np.mean([r[1] > 0 for r in a])), tan=mm(a, 0), tan_f=mm(f, 0), tan_b=mm(b, 0), fuku=mm(a, 1), fuku_f=mm(f, 1), fuku_b=mm(b, 1), wide=mm(a, 2) if hasw else None)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
