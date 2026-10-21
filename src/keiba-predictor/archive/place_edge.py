# -*- coding: utf-8 -*-
"""
place_edge.py — 複勝圏（3着以内）ベースでエッジを探す（2026-08-31）
====================================================================
単勝で見てきた検証は、勝率1〜3%の帯で高配当1頭に結果が振り回されていた
（262倍の1頭が複数条件の「エッジ」を作っていた）。
複勝圏なら試行回数が3倍になり、判定が安定する。

複勝配当は結果DBに無いため、**単勝オッズから複勝配当を近似**する。
JRAの実勢に近い簡易式を使う:
    複勝配当 ≒ 1 + (単勝オッズ − 1) × k  （kは頭数で変わる分配率）
  ここでは保守的に k=0.22（8〜13頭）、k=0.25（14頭以上）、k=0.18（7頭以下）とし、
  下限を1.0倍（元返し）とする。
※ 近似なので絶対値は参考。**条件間の比較**に使う。

比較の軸:
  ・モデル予測順位
  ・モデルと市場の乖離（ここが最重要。単勝では逆相関だった）
  ・人気帯
"""
from __future__ import annotations
import json, collections, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = Path.home() / 'Desktop' / '競馬予想レポート'


def place_odds(win_odds, n_head):
    k = 0.18 if n_head <= 7 else (0.22 if n_head <= 13 else 0.25)
    return max(1.0, 1.0 + (win_odds - 1.0) * k)


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
        for k, prs in by.items():
            rr = res.get(k)
            if not rr:
                continue
            nh = len(prs)
            prs.sort(key=lambda r: int(r.get('AI予測順位') or 99))
            for p in prs:
                a = rr.get(p['馬名'])
                if not a:
                    continue
                o, pop = a.get('単勝オッズ'), a.get('人気')
                if not o or not pop:
                    continue
                rows.append(dict(
                    date=k[0], name=p['馬名'], n=nh,
                    rank=int(p.get('AI予測順位') or 99), pop=int(pop),
                    win_odds=float(o), pl_odds=place_odds(float(o), nh),
                    fin=a['着順int'], style=p.get('脚質') or '不明',
                ))
    return rows


def pstat(sub):
    if not sub:
        return None
    n = len(sub)
    t3 = sum(1 for r in sub if r['fin'] in (1, 2, 3))
    ret = sum(r['pl_odds'] * 100 for r in sub if r['fin'] in (1, 2, 3))
    return dict(n=n, top3=100*t3/n, roi=100*ret/(n*100))


def show(lab, sub, indent="  "):
    s = pstat(sub)
    if not s:
        print("%s%-34s サンプルなし" % (indent, lab)); return None
    print("%s%-34s n=%5d  3着内%5.1f%%  複勝回収率%6.1f%%" % (indent, lab, s['n'], s['top3'], s['roi']))
    return s


def main():
    rows = load()
    days = sorted({r['date'] for r in rows})
    k3 = max(1, len(days)//3)
    periods = [set(days[:k3]), set(days[k3:2*k3]), set(days[2*k3:])]

    print("=" * 96)
    print("■ 複勝圏ベースのエッジ検証（複勝配当は単勝オッズからの近似）")
    print("=" * 96)
    print("対象 %d頭 / %d開催" % (len(rows), len(days)))
    show("全馬（基準）", rows)
    show("市場1番人気（基準）", [r for r in rows if r['pop'] == 1])
    print()

    print("【1】モデル予測順位別")
    for i, lab in ((1, 'モデル1位'), (2, 'モデル2位'), (3, 'モデル3位')):
        show(lab, [r for r in rows if r['rank'] == i])
    show("モデル4-6位", [r for r in rows if 4 <= r['rank'] <= 6])
    show("モデル7位以下", [r for r in rows if r['rank'] >= 7])

    print()
    print("【2】★モデルと市場の乖離別（単勝では逆相関だった。複勝でも同じか）")
    def gap(r): return r['pop'] - r['rank']
    for lab, f in (("モデル優位 +5以上", lambda r: gap(r) >= 5),
                   ("モデル優位 +2〜4", lambda r: 2 <= gap(r) <= 4),
                   ("一致 ±1", lambda r: abs(gap(r)) <= 1),
                   ("市場優位 -2以下", lambda r: gap(r) <= -2)):
        show(lab, [r for r in rows if f(r)])

    print()
    print("【3】人気帯別")
    for lab, f in (("1-3番人気", lambda r: r['pop'] <= 3),
                   ("4-6番人気", lambda r: 4 <= r['pop'] <= 6),
                   ("7-9番人気", lambda r: 7 <= r['pop'] <= 9),
                   ("10番人気以下", lambda r: r['pop'] >= 10)):
        show(lab, [r for r in rows if f(r)])

    print()
    print("【4】脚質別（単勝では先行が101%だった）")
    for st in ('逃げ', '先行', '差し'):
        show("脚質 %s" % st, [r for r in rows if r['style'] == st])

    print()
    print("【5】複勝回収率が100%を超えた条件の3分割チェック")
    cands = [
        ("モデル1位", lambda r: r['rank'] == 1),
        ("脚質 先行", lambda r: r['style'] == '先行'),
        ("1-3番人気", lambda r: r['pop'] <= 3),
        ("市場優位 -2以下", lambda r: (r['pop'] - r['rank']) <= -2),
    ]
    for lab, f in cands:
        sub = [r for r in rows if f(r)]
        s = pstat(sub)
        if not s or s['roi'] < 95:
            continue
        line = "  %-20s 全期間%5.1f%% → " % (lab, s['roi'])
        for i, ds in enumerate(periods):
            ss = pstat([r for r in sub if r['date'] in ds])
            line += "第%d期%5.1f%%  " % (i+1, ss['roi']) if ss else "第%d期 -  " % (i+1)
        print(line)


if __name__ == '__main__':
    main()
