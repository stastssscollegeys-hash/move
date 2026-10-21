# -*- coding: utf-8 -*-
"""
bet_structure_test.py — 印は同じまま「買い方」だけを変えて、実際の払戻で比べる（2026-10-10新規）
==========================================================================================
ユーザー指摘（2026-10-10）: 「印は当たっているのに馬券が当たっていないことが多い」「中穴に印が集まったレースで3連複1点1,000円は重い。
軸・フォーメーションで広く、ワイドで相手を広く、のほうが良いのでは」→ 買い方を検証して積み重ね、ベストの買い目を極める。

・印は predict_day.marks_and_bets と同じ決め方（◎8%以上で最も割安／○▲5%以上で割安順／△△3%以上／🔥6番人気以下・2%以上で最も割安）。
  ただし過去の予測には想定脚質が無いので「後ろから型×20倍以上を△🔥から除く」は適用していない
・予測は年ごとの前向き（combo_backtest.predictions・2019〜）。払戻は実際の払戻（db/history_target/payouts_*.json）
・どの買い方も1レース10,000円前後（100円単位）。回収率はレース単位のブートストラップで95%区間、年別も出す
・区分: 全レース ／ 人気馬が印なし（1〜3番人気に◎○▲が付かない馬がいて、◎が2番人気以下）／ ◎が1番人気
・「印は当たったが馬券は外れ」: 3着以内の3頭のうち2頭以上が印（◎○▲△△🔥）なのに、その買い方の払戻が0のレースの割合
結果は db/bet_structure_results.json に日付つきで積み上げる（同じ形を何度も測り直して選び直さない）。
使い方: python bet_structure_test.py [--from 2019]
"""
from __future__ import annotations
import argparse, collections, datetime, itertools, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C

OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "bet_structure_results.json"


def marks(pr):
    p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), pr["uma"]
    p, q = p / p.sum(), q / q.sum()
    pop = {i: r + 1 for r, i in enumerate(np.argsort(-q))}
    val = list(np.argsort(-(p / q)))
    m = {}
    hon = [i for i in val if p[i] >= 0.08] or [int(np.argmax(p))]
    m[hon[0]] = "◎"
    for mk, fl in (("○", .05), ("▲", .05), ("△1", .03), ("△2", .03)):
        c = [i for i in val if i not in m and p[i] >= fl] or [i for i in np.argsort(-p) if i not in m]
        if c:
            m[c[0]] = mk
    a = [i for i in val if i not in m and pop[i] >= 6 and p[i] >= .02]
    if a:
        m[a[0]] = "🔥"
    return {v: uma[k] for k, v in m.items()}, {uma[i]: pop[i] for i in range(len(uma))}


def plans(M):
    h, o, t, d1, d2, a = (M.get(k) for k in ("◎", "○", "▲", "△1", "△2", "🔥"))
    aite = [x for x in (o, t, d1, d2, a) if x]
    sub = [x for x in (o, t, a) if x]
    w = a or t
    P = {}
    P["V1 今の形"] = [("単勝", [h], 2000), ("馬連", [h, o], 3000)] + (
        [("ワイド", [h, a], 3000), ("3連複", [h, o, a], 1000), ("3連複", [h, o, t], 1000)] if a else [("ワイド", [h, t], 3000), ("3連複", [h, o, t], 2000)])
    P["V2 3連複を◎軸流し（相手5頭10点×200）"] = [("単勝", [h], 2000), ("馬連", [h, o], 3000), ("ワイド", [h, w], 3000)] + \
        [("3連複", [h, x, y], 200) for x, y in itertools.combinations(aite, 2)]
    P["V3 3連複フォーメーション（◎-○▲🔥-相手5頭）"] = [("単勝", [h], 2000), ("馬連", [h, o], 3000), ("ワイド", [h, w], 3000)] + \
        [("3連複", [h, x, y], 200) for x, y in itertools.combinations(aite, 2) if x in sub or y in sub]
    P["V4 ワイド◎流し（相手5頭×1,000）"] = [("単勝", [h], 2000), ("馬連", [h, o], 3000)] + [("ワイド", [h, x], 1000) for x in aite]
    P["V5 馬連◎流し（相手5頭×1,000）＋ワイド◎-🔥"] = [("単勝", [h], 2000)] + [("馬連", [h, x], 1000) for x in aite] + [("ワイド", [h, w], 3000)]
    P["V6 3連複を外してワイド◎-○▲🔥"] = [("単勝", [h], 2000), ("馬連", [h, o], 3000)] + [("ワイド", [h, x], 5000 // len(sub) // 100 * 100) for x in sub]
    return {k: [(ty, c, s) for ty, c, s in v if None not in c and s >= 100] for k, v in P.items()}


UNIT = {  # 1点100円で、券種ごとの素の回収率
    "◎単勝": lambda M: [("単勝", [M["◎"]])],
    "◎複勝": lambda M: [("複勝", [M["◎"]])],
    "◎-○馬連": lambda M: [("馬連", [M["◎"], M["○"]])],
    "◎→○馬単": lambda M: [("馬単", [M["◎"], M["○"]])],
    "◎-🔥ワイド": lambda M: [("ワイド", [M["◎"], M["🔥"]])] if "🔥" in M else [],
    "◎-相手ワイド（5点）": lambda M: [("ワイド", [M["◎"], M[k]]) for k in ("○", "▲", "△1", "△2", "🔥") if k in M],
    "◎-相手馬連（5点）": lambda M: [("馬連", [M["◎"], M[k]]) for k in ("○", "▲", "△1", "△2", "🔥") if k in M],
    "◎○▲3連複（1点）": lambda M: [("3連複", [M["◎"], M["○"], M["▲"]])],
    "◎○🔥3連複（1点）": lambda M: [("3連複", [M["◎"], M["○"], M["🔥"]])] if "🔥" in M else [],
    "◎軸3連複流し（10点）": lambda M: [("3連複", [M["◎"], x, y]) for x, y in itertools.combinations([M[k] for k in ("○", "▲", "△1", "△2", "🔥") if k in M], 2)],
}


def pay_of(pp, ty, combo):
    if ty in ("単勝", "複勝"):
        k = str(combo[0])
    elif ty == "馬単":
        k = f"{combo[0]}-{combo[1]}"
    else:
        k = "-".join(map(str, sorted(combo)))
    return pp.get(ty, {}).get(k, 0)


def main(A):
    preds, pay = C.predictions(), C.load_pay()
    seg_names = ("全レース", "人気馬が印なし（◎2番人気以下）", "◎が1番人気")
    R = collections.defaultdict(lambda: collections.defaultdict(list))   # R[区分][買い方] = [(年, 賭け, 払戻, 印当たり外れ)]
    U = collections.defaultdict(lambda: collections.defaultdict(list))   # U[区分][券種] = [(年, 賭け, 払戻, 的中点数)]
    n_seen = 0
    for pr in preds:
        k = pr["key"]
        if int(k[0][:4]) < A.frm:
            continue
        pp = pay.get(f"{k[0]}|{k[1]}|{k[2]}")
        if not pp or "3連複" not in pp or not pp["3連複"] or len(pr["uma"]) < 8:
            continue
        M, pop = marks(pr)
        if not all(x in M for x in ("◎", "○", "▲")):
            continue
        n_seen += 1
        top3 = set(map(int, next(iter(pp["3連複"])).split("-")))
        marked = set(M.values())
        mark_hit = len(top3 & marked) >= 2
        segs = ["全レース"]
        top_unmarked = any(pop[u] <= 3 and u not in (M["◎"], M["○"], M["▲"]) for u in pop)
        if top_unmarked and pop[M["◎"]] >= 2:
            segs.append(seg_names[1])
        if pop[M["◎"]] == 1:
            segs.append(seg_names[2])
        for name, plan in plans(M).items():
            st = sum(s for _, _, s in plan)
            ret = sum(s / 100 * pay_of(pp, ty, c) for ty, c, s in plan)
            for sg in segs:
                R[sg][name].append((k[0][:4], st, ret, mark_hit))
        for name, f in UNIT.items():
            bs = f(M)
            if not bs:
                continue
            gs = [pay_of(pp, ty, c) for ty, c in bs]
            for sg in segs:
                U[sg][name].append((k[0][:4], 100 * len(bs), sum(gs), sum(1 for g in gs if g)))
    res = dict(run=datetime.date.today().isoformat(), races=n_seen, from_year=A.frm, segments={})
    for sg in seg_names:
        rows = R[sg]
        if not rows:
            continue
        n = len(next(iter(rows.values())))
        print(f"\n■ {sg}（{n:,}レース）")
        print(f"  {'買い方':<36} 回収率   95%区間         何か当たる  印は当たったのに外れ  年別")
        out = {}
        for name, L in rows.items():
            st, rt = [x[1] for x in L], [x[2] for x in L]
            lo, hi = C.ci(st, rt)
            roi = sum(rt) / sum(st)
            hit = sum(1 for x in L if x[2] > 0) / len(L)
            mh = [x for x in L if x[3]]
            miss = sum(1 for x in mh if x[2] == 0) / max(1, len(mh))
            yr = collections.defaultdict(lambda: [0, 0])
            for y, s, r_, _ in L:
                yr[y][0] += s; yr[y][1] += r_
            ys = " ".join(f"{y[2:]}:{v[1]/v[0]*100:.0f}" for y, v in sorted(yr.items()))
            print(f"  {name:<36} {roi*100:5.1f}%  [{lo*100:5.1f}〜{hi*100:5.1f}]  {hit*100:5.1f}%     {miss*100:5.1f}%（{len(mh):,}R）   {ys}")
            out[name] = dict(roi=round(roi, 4), ci=[round(lo, 4), round(hi, 4)], hit=round(hit, 4), mark_hit_but_miss=round(miss, 4), mark_hit_races=len(mh),
                             years={y: round(v[1] / v[0], 4) for y, v in sorted(yr.items())})
        print("  券種ごと（1点100円）")
        uo = {}
        for name, L in U[sg].items():
            s, g, h = sum(x[1] for x in L), sum(x[2] for x in L), sum(x[3] for x in L)
            lo, hi = C.ci([x[1] for x in L], [x[2] for x in L])
            yr = collections.defaultdict(lambda: [0, 0])
            for y, a_, b_, _ in L:
                yr[y][0] += a_; yr[y][1] += b_
            ys = " ".join(f"{y[2:]}:{v[1]/v[0]*100:.0f}" for y, v in sorted(yr.items()))
            print(f"    {name:<20} {s//100:>7,}点  的中 {h/(s/100)*100:5.1f}%  回収率 {g/s*100:6.1f}% [{lo*100:5.1f}〜{hi*100:5.1f}]  {ys}")
            uo[name] = dict(points=s // 100, hit=round(h / (s / 100), 4), roi=round(g / s, 4), ci=[round(lo, 4), round(hi, 4)],
                            years={y: round(v[1] / v[0], 4) for y, v in sorted(yr.items())})
        res["segments"][sg] = dict(races=n, plans=out, units=uo)
    hist = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    hist.append(res)
    OUT.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存: {OUT}（{len(hist)}回目）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", type=int, default=2019)
    main(ap.parse_args())
