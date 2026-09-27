# -*- coding: utf-8 -*-
"""
edge_verify3.py — 拡張データ(13開催・6,269頭)で出た候補の厳密検証（2026-08-31）
================================================================================
5/23・5/24・7/26 を追加した再探索で、前回と違う傾向の候補が出た。
特に注目は「モデル7位以下 × 市場1-3番人気」＝**モデルが過小評価している人気馬**。
前回判明した「市場優位の馬ほど回収率が高い(84%)」と整合する方向で、
モデルの弱点を裏返して使える可能性がある。

検証手順（偽エッジを弾くために毎回同じ手順を踏む）:
  ① 3分割で全期間100%超か
  ② 最高配当1〜3頭を除いても保つか
  ③ サンプルが十分か
"""
from __future__ import annotations
import json, collections, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from edge_search import load_rows, add_buckets


def stat(sub):
    if not sub:
        return None
    n = len(sub)
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds'] * 100 for r in sub if r['fin'] == 1)
    t3 = sum(1 for r in sub if r['fin'] in (1, 2, 3))
    return dict(n=n, win=100*w/n, roi=100*ret/(n*100), top3=100*t3/n)


CONDS = [
    ("モデル7位以下 × 1-3番人気 × 差し",
     lambda r: r['rank'] >= 7 and r['pop'] <= 3 and r['style'] == '差し'),
    ("モデル7位以下 × 1-3番人気（脚質不問）",
     lambda r: r['rank'] >= 7 and r['pop'] <= 3),
    ("モデル4-6位 × モデル優位+2〜4 × 1801-2200m",
     lambda r: 4 <= r['rank'] <= 6 and r['b_gap'] == 'モデル優位+2〜4' and 1801 <= r['dist'] <= 2200),
    ("10頭以下 × モデル優位+2〜4",
     lambda r: r['n'] <= 10 and r['b_gap'] == 'モデル優位+2〜4'),
    ("4-6番人気 × 2201m以上",
     lambda r: 4 <= r['pop'] <= 6 and r['dist'] >= 2201),
    ("4-6番人気 × 17頭以上 × 差し",
     lambda r: 4 <= r['pop'] <= 6 and r['n'] >= 17 and r['style'] == '差し'),
]


def main():
    rows = add_buckets(load_rows())
    days = sorted({r['date'] for r in rows})
    k3 = max(1, len(days) // 3)
    periods = [set(days[:k3]), set(days[k3:2*k3]), set(days[2*k3:])]

    base = stat(rows)
    pop1 = stat([r for r in rows if r['pop'] == 1])
    print("=" * 96)
    print("■ 拡張データでの候補検証（%d頭 / %d開催）" % (len(rows), len(days)))
    print("=" * 96)
    print("基準: 全馬 回収率%.1f%% ／ 市場1番人気 %.1f%%（単勝の理論値80%%）"
          % (base['roi'], pop1['roi']))
    print()

    survivors = []
    for label, f in CONDS:
        sub = [r for r in rows if f(r)]
        s = stat(sub)
        if not s or s['n'] < 60:
            print("── %s" % label)
            print("   サンプル不足 (n=%d) → 判定不能" % (s['n'] if s else 0))
            print()
            continue

        print("── %s" % label)
        print("   全期間: n=%4d 勝率%5.1f%% 回収率%5.0f%% 3着内%5.1f%%"
              % (s['n'], s['win'], s['roi'], s['top3']))

        # ① 3分割
        ok3 = True
        line = "   3分割 : "
        for i, ds in enumerate(periods):
            ss = stat([r for r in sub if r['date'] in ds])
            if ss and ss['n'] >= 15:
                line += "第%d期%4.0f%%(n=%3d) " % (i+1, ss['roi'], ss['n'])
                if ss['roi'] < 100:
                    ok3 = False
            else:
                line += "第%d期 n不足 " % (i+1)
                ok3 = False
        print(line)

        # ② 高配当除外
        wins = sorted([r for r in sub if r['fin'] == 1], key=lambda r: -r['odds'])
        inv = len(sub) * 100
        tot = sum(r['odds'] * 100 for r in wins)
        r1 = r3 = 0
        if len(wins) >= 3:
            r1 = 100 * (tot - wins[0]['odds']*100) / inv
            r3 = 100 * (tot - sum(x['odds']*100 for x in wins[:3])) / inv
            print("   的中%d頭 最高%.1f倍 → 1頭除外%4.0f%% / 3頭除外%4.0f%%"
                  % (len(wins), wins[0]['odds'], r1, r3))
        else:
            print("   的中%d頭（少なすぎて配当分散の判定不能）" % len(wins))

        ok = ok3 and r3 >= 85 and s['n'] >= 100
        print("   判定: %s" % ("★★ 生き残り（要追試）" if ok else "✗ 棄却"))
        if ok:
            survivors.append((label, s, r3))
        print()

    print("=" * 96)
    if survivors:
        print("★ 3分割・配当除外を通過した条件: %d件" % len(survivors))
        for label, s, r3 in survivors:
            print("   %-44s n=%4d 回収率%5.0f%% (3頭除外%4.0f%%)" % (label, s['n'], s['roi'], r3))
        print()
        print("   ※ ただし『次の開催で通用するか』は別問題。実戦投入前に")
        print("      さらに新しいデータ（9月以降）で追試すること。")
    else:
        print("★ すべて棄却。拡張データでもエッジは確認できず。")


if __name__ == '__main__':
    main()
