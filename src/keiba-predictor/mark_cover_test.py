# -*- coding: utf-8 -*-
"""mark_cover_test.py — 印を1頭足すと「無印の勝ち馬」がどれだけ減るか、その1頭は買う価値があるかを10年分で測る（2026-11-18 新設）

きっかけ: 今年の総まとめで、勝ち馬の約5頭に1頭が無印（10月195Rで42頭）。現行の印（◎○▲＋1〜3番人気の△）に、あと1頭足す候補を比べる。
  候補: 印なしでモデル確率1位／印なしで割安さ1位（勝つ確率3%以上）／印なしで人気最上位（＝4番人気以下の最上位）／印なしで「確率×割安さ」1位
見るもの: 足した馬の 勝率・3着内率・単勝回収・複勝回収・◎とのワイド回収（前半/後半）／足したあとの「勝ち馬が無印」の割合・「3着内3頭のうち無印が1頭以上」の割合
  python mark_cover_test.py
"""
import collections, json, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as M

OUT = E.DB / "mark_cover_results.json"


def main():
    preds, pay = C.predictions(), C.load_pay()
    R = collections.defaultdict(lambda: collections.defaultdict(list)); cov = collections.defaultdict(lambda: [0, 0, 0]); N = 0; nm_marks = []
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("複勝") or not pp.get("単勝"):
            continue
        k2 = lambda k: tuple(sorted(map(int, str(k).split("-"))))
        wide = {k2(k): y / 100 for k, y in pp["ワイド"].items()}
        fuku = {int(k): y / 100 for k, y in pp["複勝"].items()}; tan = {int(k): y / 100 for k, y in pp["単勝"].items()}
        uma = [int(u) for u in pr["uma"]]; n = len(uma)
        p = np.asarray(pr["p"], float); q = np.asarray(pr["q"], float); p, q = p / p.sum(), q / q.sum()
        ratio = p / q
        m = M.mark(pr, {}, "A"); used = [uma.index(u) for _, u, _ in m]; hon = used[0]
        free = [i for i in range(n) if i not in used]
        winner = next(iter(tan)); top3 = set(fuku)
        N += 1; nm_marks.append(len(used))
        half = "前" if pr["key"][0] < "20230101" else "後"
        base = {uma[i] for i in used}
        cov["現行（足さない）"][0] += winner not in base; cov["現行（足さない）"][1] += len(top3 - base) >= 1; cov["現行（足さない）"][2] += 1
        if not free:
            continue
        c3 = [i for i in free if p[i] >= .03] or free
        cand = {"印なしでモデル確率1位": max(free, key=lambda i: p[i]), "印なしで割安さ1位（確率3%以上）": max(c3, key=lambda i: ratio[i]),
                "印なしで人気最上位": max(free, key=lambda i: q[i]), "印なしで確率×割安さ1位": max(free, key=lambda i: p[i] * ratio[i])}
        for nm, i in cand.items():
            u = uma[i]
            rec = (tan.get(u, 0), fuku.get(u, 0), wide.get(tuple(sorted((u, uma[hon]))), 0), int((q > q[i]).sum()) + 1)
            R[nm][half].append(rec); R[nm]["全"].append(rec)
            s = base | {u}; cov[nm][0] += winner not in s; cov[nm][1] += len(top3 - s) >= 1; cov[nm][2] += 1
    print(f"対象 {N:,}レース ／ 現行の印は平均 {np.mean(nm_marks):.1f}頭")
    print(f"\n{'足す馬':26s} {'平均人気':>5s} {'勝率':>6s} {'3着内':>6s} {'単勝':>7s} {'(前/後)':>9s} {'複勝':>7s} {'(前/後)':>9s} {'◎とのワイド':>8s} {'(前/後)':>9s} {'勝ち馬が無印':>8s} {'3着内に無印あり':>8s}")
    c = cov["現行（足さない）"]; print(f"{'現行（足さない）':26s} {'':5s} {'':6s} {'':6s} {'':7s} {'':9s} {'':7s} {'':9s} {'':8s} {'':9s} {c[0]/c[2]*100:7.1f}% {c[1]/c[2]*100:7.1f}%")
    out = {"現行": dict(win_unmarked=c[0] / c[2], top3_has_unmarked=c[1] / c[2])}
    for nm, d in R.items():
        a, f, b = d["全"], d["前"], d["後"]; mm = lambda x, k: np.mean([r[k] for r in x]) * 100; c = cov[nm]
        print(f"{nm:26s} {np.mean([r[3] for r in a]):5.1f} {np.mean([r[0]>0 for r in a])*100:5.1f}% {np.mean([r[1]>0 for r in a])*100:5.1f}% {mm(a,0):6.1f}% {mm(f,0):4.0f}/{mm(b,0):<4.0f} {mm(a,1):6.1f}% {mm(f,1):4.0f}/{mm(b,1):<4.0f} {mm(a,2):6.1f}% {mm(f,2):4.0f}/{mm(b,2):<4.0f} {c[0]/c[2]*100:7.1f}% {c[1]/c[2]*100:7.1f}%")
        out[nm] = dict(pop=float(np.mean([r[3] for r in a])), win=float(np.mean([r[0] > 0 for r in a])), top3=float(np.mean([r[1] > 0 for r in a])), tan=mm(a, 0), fuku=mm(a, 1), wide=mm(a, 2), wide_f=mm(f, 2), wide_b=mm(b, 2), win_unmarked=c[0] / c[2], top3_has_unmarked=c[1] / c[2])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
