# -*- coding: utf-8 -*-
"""
target_120_design.py — 年間120%到達確率を最大化する買い方を選ぶ（2026-09-04）
==============================================================================
前提（実測で確定していること）:
  ・券種・人気順の組み合わせを896通り探しても、期待値120%を超える買い方は無かった
  ・通過候補2件はいずれも的中9〜10件で、95%区間が[69〜313%]と判定不能
  ・実測ROIの上限はおよそ85〜98%

したがって「期待値で120%」は現状の予想力では作れない。
だが目標が年間120%と明確なら、**期待値ではなく到達確率で選ぶ**のは筋が通る。

  期待値が同じでも、分散が大きい買い方ほど「平均を上回る目標」に届く確率は高い。
  （その代わり大きく負ける確率も上がる）

本スクリプトは実払戻データから各買い方の1レースあたり収支分布をとり、
年間ぶんブートストラップして
  P(年間回収率 >= 120%) / P(>= 100%) / 中央値 / 最悪ケース
を出す。目標に対してどの構成が最も合理的かを選ぶ材料にする。

使い方: python target_120_design.py [--races 500] [--sims 5000]
"""
from __future__ import annotations
import argparse, io, sys, random, itertools, statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from find_120 import load, payout


def series(races, bt, idxs):
    """1レースあたりの払戻倍率（賭け金1に対する戻り）の列"""
    out = []
    for r in races:
        if max(idxs) >= len(r['order']):
            continue
        nums = [r['order'][i] for i in idxs]
        y = payout(bt, nums, r['pay'], r['top3'])
        if y is None:
            continue
        out.append(y / 100.0)
    return out


def box_series(races, bt, top_n, pick):
    """上位top_n頭のBOX（pick頭組）を等額で買った場合の1レース収支"""
    out = []
    for r in races:
        if len(r['order']) < top_n:
            continue
        legs = list(itertools.combinations(range(top_n), pick))
        inv = len(legs)
        ret = 0
        ok = True
        for c in legs:
            nums = [r['order'][i] for i in c]
            y = payout(bt, nums, r['pay'], r['top3'])
            if y is None:
                ok = False
                break
            ret += y / 100.0
        if ok:
            out.append(ret / inv)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--races', type=int, default=500, help='年間の購入レース数')
    ap.add_argument('--sims', type=int, default=5000)
    args = ap.parse_args()

    races = load()
    print("=" * 100)
    print(f"■ 年間120%到達確率で買い方を選ぶ   実データ{len(races)}レース / "
          f"年間{args.races}レース購入を{args.sims:,}回シミュレーション")
    print("=" * 100)

    CANDS = {
        '複勝1番人気': series(races, '複勝', (0,)),
        '単勝1番人気': series(races, '単勝', (0,)),
        'ワイド1-2番人気': series(races, 'ワイド', (0, 1)),
        '馬連1-2番人気': series(races, '馬連', (0, 1)),
        'ワイドBOX上位3': box_series(races, 'ワイド', 3, 2),
        'ワイドBOX上位4': box_series(races, 'ワイド', 4, 2),
        '3連複BOX上位4': box_series(races, '3連複', 4, 3),
        '3連複1-2-3番人気': series(races, '3連複', (0, 1, 2)),
        '単勝3番人気': series(races, '単勝', (2,)),
        '単勝5番人気': series(races, '単勝', (4,)),
        'ワイド1-4番人気': series(races, 'ワイド', (0, 3)),
        '馬連1-4番人気': series(races, '馬連', (0, 3)),
        '3連複1-2-4番人気': series(races, '3連複', (0, 1, 3)),
    }

    print()
    print(f"{'買い方':>18s} {'n':>5s} {'期待ROI':>8s} {'中央値':>8s} "
          f"{'P(≥120%)':>9s} {'P(≥100%)':>9s} {'最悪5%':>8s}")
    print("-" * 100)
    rows = []
    rng = random.Random(7)
    for name, s in CANDS.items():
        if len(s) < 200:
            continue
        exp = 100 * statistics.mean(s)
        sims = []
        for _ in range(args.sims):
            tot = 0.0
            for _ in range(args.races):
                tot += s[rng.randrange(len(s))]
            sims.append(100 * tot / args.races)
        sims.sort()
        p120 = 100 * sum(1 for x in sims if x >= 120) / len(sims)
        p100 = 100 * sum(1 for x in sims if x >= 100) / len(sims)
        med = statistics.median(sims)
        worst = sims[int(0.05 * len(sims))]
        rows.append((p120, name, len(s), exp, med, p120, p100, worst))
    rows.sort(reverse=True)
    for _, name, n, exp, med, p120, p100, worst in rows:
        print(f"{name:>18s} {n:5d} {exp:7.1f}% {med:7.1f}% "
              f"{p120:8.1f}% {p100:8.1f}% {worst:7.1f}%")

    print()
    print("【読み方】")
    print("  ・期待ROIはどれも100%未満。これは控除率のぶんで、買い方では覆せない")
    print("  ・P(≥120%) は「年間120%に届く確率」。分散が大きい買い方ほど高くなるが、")
    print("    同時に最悪5%も悪化する（大きく負ける年が増える）")
    print("  ・的中率の高い買い方は結果が安定するぶん、目標に届く確率は下がる")


if __name__ == '__main__':
    main()
