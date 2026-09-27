# -*- coding: utf-8 -*-
"""
factor_audit.py — 事前予測の因子ごとに「市場を超える情報があるか」を測る（2026-08-31新設）
==========================================================================================
指数の作り直しに向けた第一歩。

考え方:
  単に「因子値が高い馬は勝率が高い」だけでは意味がない。それは市場（オッズ）も
  知っている情報で、すでに人気に織り込まれているから。
  価値があるのは **同じ人気帯の中で、その因子が結果を分けられるか**。
  ここを測れば「市場が見落としている因子」＝エッジの源泉が特定できる。

出力:
  ① 因子ごとの5分位別 勝率・単勝回収率（全体）
  ② **人気帯を固定したうえでの因子の効き**（本命の指標）
     例: 1-3番人気の中で ML能力% 上位20% と 下位20% で回収率がどれだけ違うか
"""
from __future__ import annotations
import json, collections, sys, statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
RESULT_DB = BASE / 'daily_pdca' / 'db' / 'race_results.json'

# 検証する因子（records.json のキー）。レース前に確定している値のみ。
FACTORS = [
    'ML能力%', '独自指数', '総合指数',
    '近5走平均着', '近5走複勝率%', '平均上がり', '中日数',
    '同距離走数', '同距離複勝率%',
    '騎手勝率%', '厩舎勝率%', '父勝率%', '母父勝率%',
    'F01_後3F', 'F02_タイム', 'F03_着差', 'F04_騎手', 'F05_厩舎', 'F06_枠',
    'F07_馬番', 'F08_距離', 'F09_体重', 'F10_斤量', 'F12_年齢', 'F13_クラス',
    'F14_馬場', 'F15_EV', 'F16_乖離',
]


def load():
    db = json.load(open(RESULT_DB, encoding='utf-8'))
    res = collections.defaultdict(dict)
    for r in db:
        res[(r['date'], r['競馬場'], int(r['R']))][r['馬名']] = r
    rows = []
    for f in sorted(BASE.glob('2026*/週末ビッグデータ_*_records.json')):
        try:
            pre = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        by = collections.defaultdict(list)
        for r in pre.get('records', []):
            by[(r['date'], r['競馬場'], int(r['R']))].append(r)
        # データ健全性フィルタ: スクレイプ途中で止まった日（30R未満）は除外
        if len(by) < 30:
            continue
        for k, prs in by.items():
            rr = res.get(k)
            if not rr:
                continue
            for p in prs:
                a = rr.get(p['馬名'])
                if not a:
                    continue
                o, pop = a.get('単勝オッズ'), a.get('人気')
                if not o or not pop:
                    continue
                row = dict(odds=float(o), pop=int(pop), fin=a['着順int'])
                for fc in FACTORS:
                    v = p.get(fc)
                    row[fc] = float(v) if isinstance(v, (int, float)) else None
                rows.append(row)
    return rows


def roi(sub):
    if not sub:
        return (0, 0.0, 0.0)
    n = len(sub)
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds'] * 100 for r in sub if r['fin'] == 1)
    return n, 100 * w / n, 100 * ret / (n * 100)


def quintile_report(rows, fc, pop_filter=None, label=''):
    sub = [r for r in rows if r.get(fc) is not None]
    if pop_filter:
        sub = [r for r in sub if pop_filter(r)]
    if len(sub) < 200:
        return None
    sub.sort(key=lambda r: r[fc])
    q = len(sub) // 5
    lo, hi = sub[:q], sub[-q:]
    n_lo, w_lo, r_lo = roi(lo)
    n_hi, w_hi, r_hi = roi(hi)
    return dict(fc=fc, label=label, n=len(sub),
                lo_win=w_lo, lo_roi=r_lo, hi_win=w_hi, hi_roi=r_hi,
                spread=r_hi - r_lo)


def main():
    rows = load()
    print("=" * 104)
    print("■ 因子監査 — 各因子に「市場を超える情報」があるか")
    print("=" * 104)
    print("対象: %d頭" % len(rows))
    n, w, r = roi(rows)
    # 🔴訂正(2026-09-06): 「控除率20%だから理論値80%」は誤り。
    #   80%はオッズ比例で買った場合の上限であり、等額買いはFLBのぶん必ず下回る。
    #   文献実測の等額買い基準線は 71〜72.5%（JRA平地1993-2025）。
    print("全体基準: 勝率%.1f%% / 単勝回収率%.1f%%"
          "（等額買いの基準線は71〜72.5%%。80%%はオッズ比例買いの上限）" % (w, r))
    print()

    # ① 全体での5分位
    print("【1】因子値の下位20%% vs 上位20%%（全馬）")
    print("%-16s %6s | %8s %8s | %8s %8s | %8s" %
          ("因子", "n", "下位勝率", "下位回収", "上位勝率", "上位回収", "回収差"))
    print("-" * 104)
    res = []
    for fc in FACTORS:
        d = quintile_report(rows, fc)
        if d:
            res.append(d)
    for d in sorted(res, key=lambda x: -abs(x['spread']))[:20]:
        print("%-16s %6d | %7.1f%% %7.0f%% | %7.1f%% %7.0f%% | %+7.0f%%" %
              (d['fc'], d['n'], d['lo_win'], d['lo_roi'], d['hi_win'], d['hi_roi'], d['spread']))

    # ② 人気帯を固定して因子の効きを見る（ここが本命）
    print()
    print("【2】★人気帯を固定したうえでの因子の効き（市場が織り込んでいない情報かを見る）")
    for plabel, pf in (("1-3番人気の中で", lambda r: r['pop'] <= 3),
                       ("4-8番人気の中で", lambda r: 4 <= r['pop'] <= 8),
                       ("9番人気以下の中で", lambda r: r['pop'] >= 9)):
        print()
        print("  ── %s ──" % plabel)
        base_n, base_w, base_r = roi([r for r in rows if pf(r)])
        print("     この帯の基準: n=%d 勝率%.1f%% 回収率%.0f%%" % (base_n, base_w, base_r))
        res2 = []
        for fc in FACTORS:
            d = quintile_report(rows, fc, pf, plabel)
            if d:
                res2.append(d)
        if not res2:
            print("     （サンプル不足）")
            continue
        print("     %-16s %6s | %8s | %8s | %8s" % ("因子", "n", "下位回収", "上位回収", "回収差"))
        for d in sorted(res2, key=lambda x: -x['spread'])[:6]:
            mark = "  ★" if d['hi_roi'] >= 100 and d['spread'] >= 20 else ""
            print("     %-16s %6d | %7.0f%% | %7.0f%% | %+7.0f%%%s" %
                  (d['fc'], d['n'], d['lo_roi'], d['hi_roi'], d['spread'], mark))
        print("     （逆に効く＝上位ほど悪い因子）")
        for d in sorted(res2, key=lambda x: x['spread'])[:3]:
            print("     %-16s %6d | %7.0f%% | %7.0f%% | %+7.0f%%" %
                  (d['fc'], d['n'], d['lo_roi'], d['hi_roi'], d['spread']))


if __name__ == '__main__':
    main()
