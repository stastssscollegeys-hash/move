# -*- coding: utf-8 -*-
"""
edge_style_bias.py — 「モデルが過小評価した人気の差し馬」を掘る（2026-08-31）
==============================================================================
edge_verify3.py で唯一まともに生き残った候補:

  モデル7位以下 × 市場1-3番人気 × 差し
    n=85 勝率29.4% 回収率148% 3着内45.9%
    3分割 140/136/159%（全期間100%超）
    最高配当10.1倍・上位3頭除外でも118%（大穴依存でない）

これは「モデルが差し馬を系統的に過小評価している」可能性を示す。
本スクリプトでは条件を段階的に緩めてサンプルを増やし、
①どこまで有効か ②本当に脚質バイアスなのか を切り分ける。
"""
from __future__ import annotations
import sys
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


def line(lab, sub, periods, indent="  "):
    s = stat(sub)
    if not s or s['n'] < 30:
        print("%s%-40s n=%3d （サンプル不足）" % (indent, lab, s['n'] if s else 0))
        return
    wins = sorted([r for r in sub if r['fin'] == 1], key=lambda r: -r['odds'])
    inv = len(sub) * 100
    tot = sum(r['odds']*100 for r in wins)
    r3 = 100*(tot - sum(x['odds']*100 for x in wins[:3]))/inv if len(wins) >= 3 else 0
    ps = []
    for ds in periods:
        ss = stat([r for r in sub if r['date'] in ds])
        ps.append("%4.0f" % ss['roi'] if ss and ss['n'] >= 10 else "  - ")
    mark = ""
    if s['roi'] >= 110 and r3 >= 100 and all(p.strip() not in ('-', '') and float(p) >= 100 for p in ps if p.strip() != '-'):
        mark = "  ★★"
    elif s['roi'] >= 110:
        mark = "  ★"
    print("%s%-40s n=%4d 勝率%5.1f%% 回収%5.0f%% 3着内%5.1f%% | 3分割 %s | 3頭除外%4.0f%%%s"
          % (indent, lab, s['n'], s['win'], s['roi'], s['top3'], "/".join(ps), r3, mark))


def main():
    rows = add_buckets(load_rows())
    days = sorted({r['date'] for r in rows})
    k3 = max(1, len(days)//3)
    periods = [set(days[:k3]), set(days[k3:2*k3]), set(days[2*k3:])]

    print("=" * 118)
    print("■ 「モデルが過小評価した人気馬」の脚質別分解（%d頭 / %d開催）" % (len(rows), len(days)))
    print("=" * 118)
    line("全馬（基準）", rows, periods)
    line("市場1-3番人気（基準）", [r for r in rows if r['pop'] <= 3], periods)
    print()

    print("【1】モデル順位のしきい値を動かす（市場1-3番人気 × 差し）")
    for th in (4, 5, 6, 7, 8):
        line("モデル%d位以下 × 1-3人気 × 差し" % th,
             [r for r in rows if r['rank'] >= th and r['pop'] <= 3 and r['style'] == '差し'], periods)

    print()
    print("【2】人気帯を動かす（モデル7位以下 × 差し）")
    for lo, hi, lab in ((1, 2, '1-2人気'), (1, 3, '1-3人気'), (1, 4, '1-4人気'),
                        (1, 5, '1-5人気'), (4, 6, '4-6人気')):
        line("モデル7位以下 × %s × 差し" % lab,
             [r for r in rows if r['rank'] >= 7 and lo <= r['pop'] <= hi and r['style'] == '差し'], periods)

    print()
    print("【3】★脚質バイアスの検証（モデル7位以下 × 1-3人気 を脚質で分ける）")
    for st in ('差し', '先行', '逃げ'):
        line("モデル7位以下 × 1-3人気 × %s" % st,
             [r for r in rows if r['rank'] >= 7 and r['pop'] <= 3 and r['style'] == st], periods)

    print()
    print("【4】比較: モデルが高評価の人気馬（＝モデルと市場が一致）")
    for st in ('差し', '先行'):
        line("モデル1-3位 × 1-3人気 × %s" % st,
             [r for r in rows if r['rank'] <= 3 and r['pop'] <= 3 and r['style'] == st], periods)

    print()
    print("【5】脚質そのものの成績（モデル順位を問わない）")
    for st in ('逃げ', '先行', '差し'):
        line("脚質 %s（全馬）" % st, [r for r in rows if r['style'] == st], periods)
        line("　うち 1-3番人気", [r for r in rows if r['style'] == st and r['pop'] <= 3], periods)

    print()
    print("=" * 118)
    print("読み方: ★★= 全期間100%超 かつ 上位3頭を除いても100%超（大穴依存でない）")
    print("        ★  = 全体の回収率は110%超だが、期間または配当分散で不安あり")


if __name__ == '__main__':
    main()
