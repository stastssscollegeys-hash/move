# -*- coding: utf-8 -*-
"""
pattern_backtest.py — 買い目パターン集（kaime_compose.PATTERNS）を、型（区分）ごとに実払戻で測る（2026-10-30新規）
=====================================================================================================
・印は predict_day.marks_and_bets と同じ決め方（bet_structure_test.marks）、予測は年ごとの前向き（combo_backtest.predictions）、
  払戻は実際の払戻（db/history_target/payouts_*.json）。1レース10,000円・100円単位
・区分は kaime_compose.seg_of（堅い/普通/荒れ × ◎の人気）。各区分で「そのパターンが当てはまるレース」だけを測り、
  同じレースを標準形 K2（ワイド◎流し）で買った場合と並べる
・見る数字: 回収率［95%区間］／何か当たる／当たったのに元が取れない割合（ガミ的中）／K2との差（同じレース）
・🔴回収率は買い方では動かない（24,927Rの先行検証で 90〜93%）。ここで見たいのは「当たり方」と「型に合っているか」。
    データの使い道は安全装置だけ: 回収率が標準形より5ポイント以上悪い型は、その区分では avoid（使わない）にする
・最後に「レースごとに型を当てはめる運用」と「全レース標準形」を、同じレースで比べる（使われ方の分布つき）
・結果は db/pattern_segment_results.json に日付つきで積む（kaime_compose.compose の seg_stats として読む）
使い方: python pattern_backtest.py [--from 2019]
"""
from __future__ import annotations
import argparse, collections, datetime, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import bet_engine as B
import kaime_compose as K
from bet_structure_test import marks, pay_of

OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "pattern_segment_results.json"
MIN_N = 150


def odds_fn_for(tq):
    keyed = {t: dict(zip(ks, pq)) for t, (ks, pq) in tq.items()}

    def f(t, combo):
        if t in ("単勝", "複勝"):
            k = (combo[0],)
        elif t in ("馬単", "3連単"):
            k = tuple(combo)
        else:
            k = tuple(sorted(combo))
        pq = keyed.get(t, {}).get(k)
        return K.TAKE[t] / pq if pq and pq > 1e-9 else None
    return f


def stats(L):
    n = len(L)
    st, rt = [x[0] for x in L], [x[1] for x in L]
    lo, hi = C.ci(st, rt)
    roi = sum(rt) / sum(st)
    hits = [x for x in L if x[1] > 0]
    return dict(n=n, roi=roi, lo=lo, hi=hi, hit=len(hits) / n, gami=sum(1 for x in hits if x[1] < x[0]) / max(1, len(hits)),
                clean=sum(1 for x in L if x[1] >= x[0]) / n)


def main(A):
    preds, pay = C.predictions(), C.load_pay()
    RACES = []        # (区分, {パターンID: (賭け, 払戻)}, 年)
    seen = 0
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
        p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), list(pr["uma"])
        p, q = p / p.sum(), q / q.sum()
        c = K.make_ctx(p, q, uma, M, pop)
        of = odds_fn_for(B.tables(q, uma))
        seen += 1
        out = {}
        for P in K.PATTERNS:
            if not P["applies"](c):
                continue
            plan = K.allocate(P["build"](M, c), of, P["alloc_exp"])
            st = sum(s for _, _, s in plan)
            if st:
                out[P["id"]] = (st, sum(s / 100 * pay_of(pp, t, cb) for t, cb, s in plan))
        if "K2" in out:
            RACES.append(("|".join(K.seg_of(c)), out, k[0][:4]))
    print(f"検証レース {seen:,}")

    R = collections.defaultdict(lambda: collections.defaultdict(list))
    for sg, out, y in RACES:
        s2, r2 = out["K2"]
        for pid, (st, rt) in out.items():
            R[sg][pid].append((st, rt, s2, r2, y))
    res = dict(run=datetime.date.today().isoformat(), races=seen, from_year=A.frm, segments={}, select={})
    for sg in sorted(R):
        base = R[sg]["K2"]
        print(f"\n■ 区分 {sg}（{len(base):,}レース）")
        print(f"  {'パターン':<34} {'R数':>6} 回収率   95%区間         何か当たる ガミ的中 ガミ無し的中  K2との差")
        sel, segout = {}, {}
        for pid in [p["id"] for p in K.PATTERNS]:
            L = R[sg].get(pid)
            if not L:
                continue
            S = stats([x[:2] for x in L])
            d = S["roi"] - sum(x[3] for x in L) / sum(x[2] for x in L)
            avoid = bool(pid != "K2" and S["n"] >= MIN_N and d <= -0.05)
            print(f"  {pid+' '+K.BY_ID[pid]['name']:<34} {S['n']:>6,} {S['roi']*100:6.1f}% [{S['lo']*100:5.1f}〜{S['hi']*100:5.1f}]  {S['hit']*100:5.1f}%  {S['gami']*100:5.1f}%   {S['clean']*100:5.1f}%     {d*100:+6.1f}pt{'  ←回避' if avoid else ''}")
            segout[pid] = dict(n=S["n"], roi=round(S["roi"], 4), ci=[round(S["lo"], 4), round(S["hi"], 4)], hit=round(S["hit"], 4),
                               gami_hit=round(S["gami"], 4), clean=round(S["clean"], 4), d_vs_k2=round(d, 4), avoid=avoid)
            sel[pid] = dict(avoid=avoid, n=S["n"])
        res["segments"][sg] = dict(races=len(base), patterns=segout)
        res["select"][sg] = sel

    # 型を当てはめる運用（先頭の当てはまる型・avoidは除く）と、全レース標準形K2の比較
    chosen = collections.defaultdict(list)
    comp, fixed, use = [], [], collections.Counter()
    by_year = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for sg, out, y in RACES:
        st_ = res["select"].get(sg, {})
        order = [p["id"] for p in sorted(K.PATTERNS, key=lambda p: p["prio"]) if p["id"] in out and (p["id"] == "K2" or not st_.get(p["id"], {}).get("avoid"))]
        pid = order[0]
        use[pid] += 1
        comp.append(out[pid] + (0,))
        fixed.append(out["K2"] + (0,))
        chosen[pid].append(out[pid])
        by_year[y][0][0] += out[pid][0]; by_year[y][0][1] += out[pid][1]
        by_year[y][1][0] += out["K2"][0]; by_year[y][1][1] += out["K2"][1]
    print("\n■ 型を当てはめる運用 vs 全レース標準形（K2）— 同じレース")
    print(f"  使われ方: " + " ／ ".join(f"{pid} {use[pid]/len(RACES)*100:.1f}%" for pid, _ in use.most_common()))
    for name, L in (("型を当てはめる", comp), ("全レース標準形K2", fixed)):
        S = stats([x[:2] for x in L])
        print(f"  {name:<14} 回収率 {S['roi']*100:5.1f}% [{S['lo']*100:5.1f}〜{S['hi']*100:5.1f}]  何か当たる {S['hit']*100:5.1f}%  ガミ的中 {S['gami']*100:5.1f}%  ガミ無し的中 {S['clean']*100:5.1f}%")
    print("  年別（型を当てはめる / 標準形）: " + " ".join(f"{y[2:]}:{v[0][1]/v[0][0]*100:.0f}/{v[1][1]/v[1][0]*100:.0f}" for y, v in sorted(by_year.items())))
    res["composed"] = dict(use={k: round(v / len(RACES), 4) for k, v in use.items()},
                           composed=stats([x[:2] for x in comp]), fixed_k2=stats([x[:2] for x in fixed]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    hist = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    hist.append(res)
    OUT.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存: {OUT}（{len(hist)}回目）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", type=int, default=2019)
    main(ap.parse_args())
