# -*- coding: utf-8 -*-
"""
find_120.py — 年間回収率120%に届く買い方が実在するか総当たりで探す（2026-09-04）
==================================================================================
目的（ユーザー設定）: 年間回収率120%以上。
目安: 堅いレース200%＋／中位300〜500%＋／大穴狙い1000%＋

現状: 今日までの測定で100%超えは皆無（最良で馬連1-2×抜けた1番人気98.5%）。
配分では期待値を作れないので、「120%を超える条件」が実在するかを探す。

探索空間（人気順の組み合わせ。解釈しやすく、当日オッズだけで判定できる）:
  単勝/複勝  : 1〜8番人気の単独
  ワイド/馬連: 人気順のペア（1-2 〜 6-8）
  3連複      : 人気順の3つ組（上位8番人気まで）
条件層: 全体 / 頭数 / 1番人気オッズ / 1-2番人気のオッズ差

★偽エッジ対策を最初から組み込む（3回踏んだ反省）:
  ① 期間3分割で符号が一致するか
  ② 払戻上位1件・3件を除いても残るか
  ③ 最低サンプル数を課す（n>=150）
3つを通ったものだけを「候補」として報告する。

使い方: python find_120.py
"""
from __future__ import annotations
import json, io, sys, itertools, collections, statistics
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'
MIN_N = 150


def payout(bt, nums, pay, top3):
    rows = pay.get(bt)
    if not rows:
        return None
    s = set(nums)
    if bt == '単勝':
        return rows[0]['yen'] if nums[0] == top3[0] else 0
    if bt == '複勝':
        for x in rows:
            if x['combo'] == nums[0]:
                return x['yen']
        return 0
    if bt == '馬連':
        return rows[0]['yen'] if s == set(top3[:2]) else 0
    if bt == 'ワイド':
        if not s <= set(top3):
            return 0
        for x in rows:
            if set(x['combo'].split('-')) == s:
                return x['yen']
        return 0
    if bt == '3連複':
        return rows[0]['yen'] if s == set(top3) else 0
    return None


def load():
    pay_db = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    by = collections.defaultdict(list)
    for r in res:
        by[(r['date'], r['競馬場'], int(r['R']))].append(r)
    out = []
    for rid, v in pay_db.items():
        rs = by.get((v['date'], v['venue'], v['R']))
        if not rs:
            continue
        hs = []
        for r in rs:
            try:
                hs.append((str(int(float(r['馬番']))), float(r['単勝オッズ']),
                           int(float(r['人気'])), r.get('着順int')))
            except (TypeError, ValueError):
                continue
        if len(hs) < 10:
            continue
        fin = sorted([h for h in hs if h[3]], key=lambda h: h[3])
        if len(fin) < 3:
            continue
        order = [h[0] for h in sorted(hs, key=lambda h: h[2])]
        od = sorted(h[1] for h in hs)
        out.append({
            'date': v['date'], 'n': len(hs), 'order': order,
            'top3': [fin[0][0], fin[1][0], fin[2][0]],
            'pay': v['payouts'], 'odds1': od[0],
            'gap': od[1] / od[0] if od[0] else 1,
        })
    return out


def evaluate(races, bt, idxs):
    """人気順 idxs（0始まり）を買った場合の (n, 的中数, 投資, 払戻, 各レース払戻)"""
    n = hit = 0
    inv = ret = 0
    detail = []
    for r in races:
        if max(idxs) >= len(r['order']):
            continue
        nums = [r['order'][i] for i in idxs]
        y = payout(bt, nums, r['pay'], r['top3'])
        if y is None:
            continue
        n += 1
        inv += 100
        ret += y
        detail.append((r['date'], y))
        if y > 0:
            hit += 1
    return n, hit, inv, ret, detail


def robust(races, bt, idxs, dates3):
    """①期間3分割 ②上位除外 を通す"""
    n, hit, inv, ret, det = evaluate(races, bt, idxs)
    if n < MIN_N or inv == 0:
        return None
    roi = 100 * ret / inv
    # ① 3分割
    segs = []
    for s in range(3):
        sub = [r for r in races if dates3.get(r['date']) == s]
        n2, _, i2, r2, _ = evaluate(sub, bt, idxs)
        segs.append(100 * r2 / i2 if i2 else 0)
    # ② 上位除外
    det.sort(key=lambda x: -x[1])
    cut1 = 100 * (ret - det[0][1]) / (inv - 100) if len(det) > 1 else 0
    cut3 = 100 * (ret - sum(x[1] for x in det[:3])) / (inv - 300) if len(det) > 3 else 0
    return {'n': n, 'hit': 100 * hit / n, 'roi': roi, 'segs': segs,
            'cut1': cut1, 'cut3': cut3}


def main():
    races = load()
    dates = sorted({r['date'] for r in races})
    t = len(dates) // 3
    dates3 = {d: (0 if i < t else 1 if i < 2 * t else 2) for i, d in enumerate(dates)}
    print("=" * 100)
    print(f"■ 年間120%に届く買い方の探索   {len(races)}レース / {len(dates)}日")
    print("=" * 100)
    print(f"条件: n>={MIN_N} かつ 期間3分割すべて100%超 かつ 上位3件除外でも100%超")
    print()

    CAND = []
    for i in range(8):
        CAND.append(('単勝', (i,)))
        CAND.append(('複勝', (i,)))
    for a, b in itertools.combinations(range(8), 2):
        CAND.append(('ワイド', (a, b)))
        CAND.append(('馬連', (a, b)))
    for c3 in itertools.combinations(range(8), 3):
        CAND.append(('3連複', c3))

    LAYERS = [
        ('全体', lambda r: True),
        ('少頭数(〜12)', lambda r: r['n'] <= 12),
        ('多頭数(16〜)', lambda r: r['n'] >= 16),
        ('堅い(1人気<3倍)', lambda r: r['odds1'] < 3.0),
        ('混戦(1人気5倍〜)', lambda r: r['odds1'] >= 5.0),
        ('抜けた1人気(差1.6倍〜)', lambda r: r['gap'] >= 1.6),
        ('横一線(差<1.25倍)', lambda r: r['gap'] < 1.25),
    ]

    found = []
    for lname, f in LAYERS:
        sub = [r for r in races if f(r)]
        if len(sub) < MIN_N:
            continue
        best = []
        for bt, idxs in CAND:
            s = robust(sub, bt, idxs, dates3)
            if not s:
                continue
            best.append((s['roi'], bt, idxs, s))
        best.sort(reverse=True)
        print(f"■ {lname}（{len(sub)}レース）  上位5件")
        print(f"   {'買い方':>18s} {'n':>5s} {'的中':>6s} {'ROI':>7s} "
              f"{'3分割':>22s} {'上位1除':>7s} {'上位3除':>7s}")
        for roi, bt, idxs, s in best[:5]:
            nm = f"{bt}{'-'.join(str(i+1) for i in idxs)}人気"
            seg = "/".join(f"{x:.0f}" for x in s['segs'])
            ok = (roi >= 120 and all(x >= 100 for x in s['segs']) and s['cut3'] >= 100)
            print(f"   {nm:>18s} {s['n']:5d} {s['hit']:5.1f}% {roi:6.1f}% "
                  f"{seg:>22s} {s['cut1']:6.1f}% {s['cut3']:6.1f}%"
                  f"{'  ★候補' if ok else ''}")
            if ok:
                found.append((lname, nm, s))
        print()

    print("=" * 100)
    print("■ 結論")
    print("=" * 100)
    if found:
        print(f"120%以上かつ頑健性を通過した買い方: {len(found)}件")
        for lname, nm, s in found:
            print(f"  ★ {lname} × {nm}: ROI {s['roi']:.1f}% "
                  f"(n={s['n']}, 的中{s['hit']:.1f}%, 3分割"
                  f"{'/'.join(f'{x:.0f}' for x in s['segs'])})")
    else:
        print("  120%以上かつ頑健な買い方は**見つからなかった**。")
        print("  → 券種・人気順の組み合わせだけでは目標に届かない。")
        print("     予想そのもので市場を上回る必要がある。")


if __name__ == '__main__':
    main()
