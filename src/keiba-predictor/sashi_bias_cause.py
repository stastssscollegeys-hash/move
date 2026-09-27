# -*- coding: utf-8 -*-
"""
sashi_bias_cause.py — 差し馬バイアスの「原因因子」を特定する（2026-08-31）
============================================================================
判明済みの現象:
  市場1-3番人気の差し馬 = 単勝回収率107%（先行は75%・逃げは73%）
  さらにエンジンが4位以下に落とした人気の差し馬は125〜148%
  → モデルは差し馬を系統的に過小評価している

本スクリプトの目的は「なぜ下がるのか」を因子レベルで突き止めること。
原因が1〜2個の因子に絞れれば、条件分岐ではなく**指数そのものを直せる**。

分析の考え方:
  市場評価（人気）を固定したうえで、差し馬と先行馬の因子値を比べる。
  同じ人気なのにモデルの評価が割れるなら、その差を作っている因子が犯人。
  さらに「その因子が本当に結果を予測できているか」も確認する。
  結果を予測できていないのに差し馬を下げている因子＝除去・修正すべき因子。
"""
from __future__ import annotations
import json, collections, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = Path.home() / 'Desktop' / '競馬予想レポート'

FACTORS = [
    'F01_後3F', 'F02_タイム', 'F03_着差', 'F04_騎手', 'F05_厩舎', 'F06_枠',
    'F07_馬番', 'F08_距離', 'F09_体重', 'F10_斤量', 'F12_年齢', 'F13_クラス',
    'F14_馬場', 'F15_EV', 'F16_乖離',
    'ML能力%', '独自指数', '総合指数',
    '近5走平均着', '近5走複勝率%', '平均上がり', '同距離複勝率%',
]


def load():
    db = json.load(open(BASE / 'daily_pdca' / 'db' / 'race_results.json', encoding='utf-8'))
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
                row = dict(odds=float(o), pop=int(pop), fin=a['着順int'],
                           rank=int(p.get('AI予測順位') or 99),
                           style=p.get('脚質') or '不明')
                for fc in FACTORS:
                    v = p.get(fc)
                    row[fc] = float(v) if isinstance(v, (int, float)) else None
                rows.append(row)
    return rows


def avg(sub, fc):
    vs = [r[fc] for r in sub if r.get(fc) is not None]
    return statistics.mean(vs) if vs else None


def roi(sub):
    if not sub:
        return 0, 0.0, 0.0
    n = len(sub)
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds']*100 for r in sub if r['fin'] == 1)
    return n, 100*w/n, 100*ret/(n*100)


def main():
    rows = load()
    print("=" * 108)
    print("■ 差し馬バイアスの原因因子を特定する（%d頭）" % len(rows))
    print("=" * 108)

    # 市場評価を固定（1-3番人気）して脚質別に比較
    p13 = [r for r in rows if r['pop'] <= 3]
    sashi = [r for r in p13 if r['style'] == '差し']
    senko = [r for r in p13 if r['style'] == '先行']

    n_s, w_s, r_s = roi(sashi)
    n_k, w_k, r_k = roi(senko)
    print("\n【前提】市場1-3番人気に絞った比較")
    print("  差し: n=%4d 勝率%.1f%% 回収率%.0f%%  ／  先行: n=%4d 勝率%.1f%% 回収率%.0f%%"
          % (n_s, w_s, r_s, n_k, w_k, r_k))
    print("  → 市場評価が同じなのに、実績は差しの方が上（回収率で+%.0fpt）" % (r_s - r_k))

    print("\n【1】同じ1-3番人気での因子平均の差（差し − 先行）")
    print("  マイナスが大きい因子ほど『差し馬を下げている』＝バイアスの容疑者")
    print("  %-16s %9s %9s %9s  %s" % ("因子", "差し平均", "先行平均", "差", "判定"))
    print("  " + "-" * 92)
    diffs = []
    for fc in FACTORS:
        a, b = avg(sashi, fc), avg(senko, fc)
        if a is None or b is None:
            continue
        diffs.append((fc, a, b, a - b))
    for fc, a, b, d in sorted(diffs, key=lambda x: x[3]):
        mark = ""
        if d < -3:
            mark = "★容疑者（差し馬を大きく下げている）"
        elif d > 3:
            mark = "（差し馬を上げている）"
        print("  %-16s %9.1f %9.1f %+9.1f  %s" % (fc, a, b, d, mark))

    # 容疑者因子が「実際に結果を予測できているか」
    print("\n【2】★容疑者因子は、本当に結果を予測できているのか")
    print("  差し馬だけを対象に、因子値の下位20%%と上位20%%で回収率を比べる。")
    print("  差がなければ『結果と無関係なのに差し馬を下げている』＝修正すべき因子。")
    print("  %-16s %6s | %9s %9s | %8s" % ("因子", "n", "下位回収", "上位回収", "回収差"))
    print("  " + "-" * 92)
    suspects = [fc for fc, a, b, d in sorted(diffs, key=lambda x: x[3])[:6]]
    allsashi = [r for r in rows if r['style'] == '差し']
    for fc in suspects:
        sub = [r for r in allsashi if r.get(fc) is not None]
        if len(sub) < 200:
            continue
        sub.sort(key=lambda r: r[fc])
        q = len(sub)//5
        _, _, rlo = roi(sub[:q])
        _, _, rhi = roi(sub[-q:])
        verdict = ""
        if abs(rhi - rlo) < 15:
            verdict = "★予測力なし → 差し馬を下げているだけの因子"
        elif rhi > rlo:
            verdict = "正しく効いている（高いほど良い）"
        else:
            verdict = "逆に効いている（高いほど悪い）"
        print("  %-16s %6d | %8.0f%% %8.0f%% | %+7.0f%%  %s" % (fc, len(sub), rlo, rhi, rhi-rlo, verdict))

    # 総合指数がどれだけ脚質で割れているか
    print("\n【3】総合指数そのものの脚質差（全馬）")
    for st in ('逃げ', '先行', '差し'):
        sub = [r for r in rows if r['style'] == st]
        n, w, rr = roi(sub)
        print("  %-4s n=%4d 総合指数平均%6.1f  ML能力%%平均%5.1f  独自指数平均%5.1f  勝率%.1f%% 回収%.0f%%"
              % (st, n, avg(sub, '総合指数') or 0, avg(sub, 'ML能力%') or 0,
                 avg(sub, '独自指数') or 0, w, rr))

    # 脚質別のエンジン順位分布
    print("\n【4】脚質別に見た『エンジン順位』の分布（市場1-3番人気に限定）")
    print("  市場が同じ評価をしている馬を、エンジンがどう並べているか")
    for st, sub in (('差し', sashi), ('先行', senko)):
        c = collections.Counter()
        for r in sub:
            c['1-3位' if r['rank'] <= 3 else ('4-6位' if r['rank'] <= 6 else '7位以下')] += 1
        tot = sum(c.values()) or 1
        print("  %-4s : 1-3位 %4.1f%% / 4-6位 %4.1f%% / 7位以下 %4.1f%%"
              % (st, 100*c['1-3位']/tot, 100*c['4-6位']/tot, 100*c['7位以下']/tot))
    print("  → 先行馬の方がエンジン上位に来やすければ、それが先行バイアスの実体")


if __name__ == '__main__':
    main()
