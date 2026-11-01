# -*- coding: utf-8 -*-
"""
axis_free_test.py — K13「軸自由＋保険」は、標準形K2より当たり方・回収率が良いか（2026-11-01新規・ユーザー指示の買い目の組み直し）
==============================================================================================================
ユーザー指示（口述5点目）: 買い目は固定せず、レースの期待値と印の重さで変える。軸は本命に限らず、穴の○▲が割安ならそこから◎へ流す。
外れたとき用に、対抗・単穴・大穴からも保険で買う。
pattern_backtest.py と同じ土台（印=bet_structure_test.marks・前向き予測・実払戻・1R1万円）で、K13 が当てはまるレースだけを
同じレースの K2 と比べる。pattern_segment_results.json は書かない（試験用）。
見る数字: 回収率［95%区間］／何か当たる／ガミ的中／ガミ無し的中／K2との差／穴軸(○▲が穴)と通常軸で分けた内訳
使い方: python axis_free_test.py [--from 2019]
"""
from __future__ import annotations
import argparse, collections, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import bet_engine as B
import kaime_compose as K
from bet_structure_test import marks, pay_of
from pattern_backtest import odds_fn_for, stats


def main(frm):
    preds, pay = C.predictions(), C.load_pay()
    rows = []                 # (年, K13の(賭,払), K2の(賭,払), 穴軸の印 or '-')
    seen = 0
    for pr in preds:
        k = pr["key"]
        if int(k[0][:4]) < frm:
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
        seen += 1
        ax = K.ana_axis_ctx(c)
        if ax is None:
            continue
        of = odds_fn_for(B.tables(q, uma))
        res = {}
        for pid in ("K13", "K2"):
            P = K.BY_ID[pid]
            plan = K.allocate(P["build"](M, c), of, P["alloc_exp"])
            st = sum(s for _, _, s in plan)
            if not st:
                break
            res[pid] = (st, sum(s / 100 * pay_of(pp, t, cb) for t, cb, s in plan))
        if len(res) == 2:
            rows.append((k[0][:4], res["K13"], res["K2"], ax, c["kind"]))
    print(f"検証レース {seen:,}／K13が当てはまる（○▲に6番人気以下で割安な馬）{len(rows):,}（{len(rows) / seen * 100:.1f}%）")
    for name, sel in (("全体", rows), ("穴が○", [r for r in rows if r[3] == "○"]), ("穴が▲", [r for r in rows if r[3] == "▲"]),
                      ("荒れ", [r for r in rows if r[4] == "荒れ"]), ("普通", [r for r in rows if r[4] == "普通"]), ("堅い", [r for r in rows if r[4] == "堅い"])):
        if len(sel) < 100:
            print(f"  {name}: {len(sel)}R（少なすぎ）"); continue
        a, b = stats([r[1] for r in sel]), stats([r[2] for r in sel])
        print(f"  {name:<6} {len(sel):>5,}R  K13 回収{a['roi'] * 100:5.1f}%［{a['lo'] * 100:.1f}〜{a['hi'] * 100:.1f}］ 当たる{a['hit'] * 100:5.1f}% ガミ的中{a['gami'] * 100:5.1f}% ガミ無し的中{a['clean'] * 100:5.1f}%"
              f" ｜ K2 回収{b['roi'] * 100:5.1f}% 当たる{b['hit'] * 100:5.1f}% ガミ無し的中{b['clean'] * 100:5.1f}% ｜差 {(a['roi'] - b['roi']) * 100:+.1f}pt")
    yr = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for y, a, b, _, _ in rows:
        yr[y][0][0] += a[0]; yr[y][0][1] += a[1]; yr[y][1][0] += b[0]; yr[y][1][1] += b[1]
    print("  年別（K13/K2 回収%）: " + " ".join(f"{y[2:]}:{v[0][1] / v[0][0] * 100:.0f}/{v[1][1] / v[1][0] * 100:.0f}" for y, v in sorted(yr.items())))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", type=int, default=2019)
    main(ap.parse_args().frm)
