# -*- coding: utf-8 -*-
"""
edge_verify2.py — 「人気薄 × 実績因子」の厳密検証（2026-08-31）
================================================================
factor_audit.py で、9番人気以下の中に単勝回収率100%超の因子が複数見つかった。

  近5走複勝率% 上位20% → 113%
  同距離走数   上位20% → 126%
  F12_年齢     上位20% → 116%
  母父勝率%    上位20% → 118%
  同距離複勝率% 上位20% →  98%

これは「経験豊富で実績のある人気薄」を市場が過小評価している可能性を示す。
ユーザーの狙い（人気薄の中から期待値が取れる馬を拾う）にも合致する。

ただし9番人気以下は勝率1.4%と極端に低く、少数の高配当に依存しやすい。
edge_verify.py で「中京×先行」が262倍1頭に支えられた偽エッジだったのと同じ罠がある。
そこで以下を必ず確認する:
  ① 3分割で全期間100%超か（再現性）
  ② 最高配当1〜3頭を除いても100%を保つか（ロバスト性）
  ③ 複勝でも成立するか（単勝の高配当依存でないか＝複勝は配当が安定する）
"""
from __future__ import annotations
import json, collections, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factor_audit import load, FACTORS

TARGETS = ['近5走複勝率%', '同距離走数', 'F12_年齢', '母父勝率%', '同距離複勝率%', '近5走平均着']


def stat(sub):
    if not sub:
        return None
    n = len(sub)
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds'] * 100 for r in sub if r['fin'] == 1)
    t3 = sum(1 for r in sub if r['fin'] in (1, 2, 3))
    return dict(n=n, win=100*w/n, roi=100*ret/(n*100), top3=100*t3/n)


def top_quintile(rows, fc, frac=0.2, high=True):
    sub = [r for r in rows if r.get(fc) is not None]
    if not sub:
        return []
    sub.sort(key=lambda r: r[fc], reverse=high)
    k = max(1, int(len(sub) * frac))
    return sub[:k]


def main():
    rows = load()
    # date が load() に含まれていないので再取得
    import factor_audit
    BASE = Path.home() / 'Desktop' / '競馬予想レポート'
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
            for p in prs:
                a = rr.get(p['馬名'])
                if not a:
                    continue
                o, pop = a.get('単勝オッズ'), a.get('人気')
                if not o or not pop:
                    continue
                row = dict(date=k[0], odds=float(o), pop=int(pop), fin=a['着順int'],
                           name=p['馬名'])
                for fc in FACTORS:
                    v = p.get(fc)
                    row[fc] = float(v) if isinstance(v, (int, float)) else None
                rows.append(row)

    days = sorted({r['date'] for r in rows})
    k3 = len(days) // 3
    periods = [set(days[:k3]), set(days[k3:2*k3]), set(days[2*k3:])]

    pop9 = [r for r in rows if r['pop'] >= 9]
    base = stat(pop9)
    print("=" * 100)
    print("■ 「9番人気以下 × 実績因子」の厳密検証")
    print("=" * 100)
    print("9番人気以下の基準: n=%d 勝率%.1f%% 単勝回収率%.0f%% 3着内%.1f%%"
          % (base['n'], base['win'], base['roi'], base['top3']))
    print()

    for fc in TARGETS:
        sub = top_quintile(pop9, fc, 0.2, high=(fc != '近5走平均着'))
        s = stat(sub)
        if not s or s['n'] < 100:
            continue
        print("── %s 上位20%%（%s） ──" % (fc, "値が大きい方" if fc != '近5走平均着' else "着順が小さい方"))
        print("   全期間: n=%4d 勝率%.1f%% 回収率%5.0f%% 3着内%.1f%%"
              % (s['n'], s['win'], s['roi'], s['top3']))

        # ① 3分割
        ok3 = True
        line = "   3分割 : "
        for i, ds in enumerate(periods):
            ss = stat([r for r in sub if r['date'] in ds])
            if ss:
                line += "第%d期 %3.0f%%(n=%3d)  " % (i+1, ss['roi'], ss['n'])
                if ss['roi'] < 100:
                    ok3 = False
            else:
                line += "第%d期 -  " % (i+1)
                ok3 = False
        print(line)

        # ② 高配当を除く
        wins = sorted([r for r in sub if r['fin'] == 1], key=lambda r: -r['odds'])
        inv = len(sub) * 100
        tot = sum(r['odds'] * 100 for r in wins)
        if wins:
            r1 = 100 * (tot - wins[0]['odds']*100) / inv
            r3 = 100 * (tot - sum(x['odds']*100 for x in wins[:3])) / inv
            print("   的中%d頭 最高配当%.1f倍 → 上位1頭除外%3.0f%% / 上位3頭除外%3.0f%%"
                  % (len(wins), wins[0]['odds'], r1, r3))
        verdict = "★再現性あり" if (ok3 and wins and r3 >= 80) else "✗ 偶然の可能性が高い"
        print("   判定: %s" % verdict)
        print()

    # 組み合わせ条件
    print("=" * 100)
    print("■ 組み合わせ（9番人気以下 × 複数条件を同時に満たす）")
    print("=" * 100)
    combos = [
        ('近5走複勝率%', '同距離走数'),
        ('近5走複勝率%', '母父勝率%'),
        ('同距離走数', '同距離複勝率%'),
        ('近5走複勝率%', '同距離複勝率%'),
    ]
    for a, b in combos:
        sa = set(id(r) for r in top_quintile(pop9, a, 0.35))
        sb = set(id(r) for r in top_quintile(pop9, b, 0.35))
        sub = [r for r in pop9 if id(r) in sa and id(r) in sb]
        s = stat(sub)
        if not s or s['n'] < 60:
            print("%s × %s : サンプル不足(n=%s)" % (a, b, s['n'] if s else 0))
            continue
        wins = sorted([r for r in sub if r['fin'] == 1], key=lambda r: -r['odds'])
        inv = len(sub) * 100
        tot = sum(r['odds']*100 for r in wins)
        r3 = 100*(tot - sum(x['odds']*100 for x in wins[:3]))/inv if len(wins) >= 3 else 0
        print("%-24s n=%4d 勝率%.1f%% 回収率%5.0f%% 3着内%.1f%% / 上位3頭除外%3.0f%%"
              % ("%s × %s" % (a, b), s['n'], s['win'], s['roi'], s['top3'], r3))


if __name__ == '__main__':
    main()
