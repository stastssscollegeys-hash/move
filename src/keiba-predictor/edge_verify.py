# -*- coding: utf-8 -*-
"""
edge_verify.py — エッジ候補の厳密検証（2026-08-30新設）
========================================================
edge_search.py が挙げた候補は「1〜3軸の総当たり」なので多重検定の偶然を含む。
ここでは有力候補に絞って以下を確認する。

  ① 3分割（期間を3つに割る）で全期間100%超か ＝ 再現性
  ② 的中の内訳（1頭の大穴に依存していないか）＝ ロバスト性
  ③ **モデルの寄与があるか** ＝ そもそも「モデルのエッジ」なのか、
     それとも「中京の先行馬」のようなファクター自体のエッジで
     モデルは無関係なのかを切り分ける（ここが最重要）
"""
from __future__ import annotations
import json, collections, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from edge_search import load_rows, add_buckets, stats


def show(label, sub):
    s = stats(sub)
    if not s:
        print("  %-38s サンプルなし" % label)
        return None
    print("  %-38s n=%4d  勝率%5.1f%%  回収率%6.0f%%  3着内%5.1f%%" %
          (label, s['n'], s['win'], s['roi'], s['top3']))
    return s


def main():
    rows = add_buckets(load_rows())
    days = sorted({r['date'] for r in rows})
    k = len(days) // 3
    p1, p2, p3 = set(days[:k]), set(days[k:2*k]), set(days[2*k:])

    # ── 候補1: 中京 × 先行 ─────────────────────────────
    print("=" * 96)
    print("■ 候補1「中京 × 先行」の検証")
    print("=" * 96)
    cond = lambda r: r['venue'] == '中京' and r['style'] == '先行'

    print("\n[1] 3分割での再現性")
    for lab, ds in (("第1期 " + '・'.join(sorted(p1)), p1),
                    ("第2期 " + '・'.join(sorted(p2)), p2),
                    ("第3期 " + '・'.join(sorted(p3)), p3)):
        show(lab[:38], [r for r in rows if cond(r) and r['date'] in ds])

    print("\n[2] モデルの寄与があるか（＝モデルのエッジかファクターのエッジか）")
    base = [r for r in rows if cond(r)]
    show("中京×先行 全馬（モデル無関係）", base)
    for lab, f in (("　うち モデル1位", lambda r: r['rank'] == 1),
                   ("　うち モデル2-3位", lambda r: 2 <= r['rank'] <= 3),
                   ("　うち モデル4-6位", lambda r: 4 <= r['rank'] <= 6),
                   ("　うち モデル7位以下", lambda r: r['rank'] >= 7)):
        show(lab, [r for r in base if f(r)])

    print("\n[3] 比較: 中京以外の先行馬／中京の先行以外")
    show("中京以外 × 先行", [r for r in rows if r['venue'] != '中京' and r['style'] == '先行'])
    show("中京 × 先行以外", [r for r in rows if r['venue'] == '中京' and r['style'] != '先行'])
    show("全馬（基準）", rows)
    show("市場1番人気（基準）", [r for r in rows if r['pop'] == 1])

    print("\n[4] 的中の内訳（1頭の大穴に依存していないか）")
    wins = sorted([r for r in base if r['fin'] == 1], key=lambda r: -r['odds'])
    tot = sum(r['odds'] * 100 for r in wins)
    inv = len(base) * 100
    print("  的中%d頭 / 総投資%s円 / 総回収%s円" % (len(wins), f"{inv:,}", f"{int(tot):,}"))
    print("  配当上位5頭: " + " / ".join("%.1f倍" % r['odds'] for r in wins[:5]))
    if wins:
        top1 = wins[0]['odds'] * 100
        print("  最高配当1頭を除いた回収率: %.0f%%" % (100 * (tot - top1) / inv))
        top3 = sum(r['odds'] * 100 for r in wins[:3])
        print("  上位3頭を除いた回収率:     %.0f%%" % (100 * (tot - top3) / inv))

    # ── 候補2: 先行そのもの ─────────────────────────────
    print()
    print("=" * 96)
    print("■ 候補2「脚質＝先行」そのものにエッジがあるのか")
    print("=" * 96)
    for st_ in ('逃げ', '先行', '差し', '追込'):
        show("脚質 %s（全場）" % st_, [r for r in rows if r['style'] == st_])

    print("\n  ※ records.json の『脚質』は前走までの脚質。レース前に分かる情報なので")
    print("     予測に使ってよい（結果リークではない）")

    # ── 候補3: モデル順位と人気の一致度 ────────────────────
    print()
    print("=" * 96)
    print("■ 候補3「モデルと市場の一致度」別")
    print("=" * 96)
    for g in ('モデル優位+5以上', 'モデル優位+2〜4', '一致±1', '市場優位'):
        show(g, [r for r in rows if r['b_gap'] == g])


if __name__ == '__main__':
    main()
