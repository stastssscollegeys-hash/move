# -*- coding: utf-8 -*-
"""
ticket_by_condition.py — レース条件ごとに「どの券種が有利か」を実払戻で測る（2026-09-04）
==========================================================================================
背景
----
4重賞すべてで3連複を本線にしてしまった。9/2の測定では券種別の無スキル基準線が
ワイド76.7% > 3連複71.7% > 馬連70.9% > 3連単67.5% で、3連複は不利な部類だったのに、
条件を見ずに一律で選んでいた。

そこで「レース条件 × 買い方」で実測ROIを出し、条件ごとの最適券種を決める。

条件軸:
  ① 頭数（少頭数ほど的中しやすく配当は安い）
  ② 1番人気のオッズ（堅いレースか混戦か）
  ③ 上位3頭のオッズ集中度（抜けた馬がいるか横一線か）

買い方（市場人気ベースで統一。印に依存しない素の性能を測る）:
  単勝1 / 複勝1 / ワイド1-2 / ワイドBOX3 / 馬連1-2 / 馬連BOX3
  / 3連複1-2-3 / 3連複BOX4 / 3連単1→2→3

使い方: python ticket_by_condition.py
"""
from __future__ import annotations
import json, io, sys, itertools, collections, statistics
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'


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
    if bt == '3連単':
        return rows[0]['yen'] if list(nums) == top3 else 0
    return None


def build_bets(order):
    """人気順リスト order（馬番）から各買い方の点を作る"""
    o = order
    B = {}
    if len(o) >= 1:
        B['単勝1番人気'] = [('単勝', [o[0]])]
        B['複勝1番人気'] = [('複勝', [o[0]])]
    if len(o) >= 2:
        B['ワイド1-2'] = [('ワイド', [o[0], o[1]])]
        B['馬連1-2'] = [('馬連', [o[0], o[1]])]
    if len(o) >= 3:
        B['ワイドBOX3'] = [('ワイド', list(p)) for p in itertools.combinations(o[:3], 2)]
        B['馬連BOX3'] = [('馬連', list(p)) for p in itertools.combinations(o[:3], 2)]
        B['3連複1-2-3'] = [('3連複', o[:3])]
        B['3連単1→2→3'] = [('3連単', o[:3])]
    if len(o) >= 4:
        B['3連複BOX4'] = [('3連複', list(p)) for p in itertools.combinations(o[:4], 3)]
        B['ワイドBOX4'] = [('ワイド', list(p)) for p in itertools.combinations(o[:4], 2)]
    return B


def main():
    pay_db = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    by = collections.defaultdict(list)
    for r in res:
        by[(r['date'], r['競馬場'], int(r['R']))].append(r)

    # レースごとに条件と各買い方の収支を作る
    rows = []
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
        if len(hs) < 8:
            continue
        fin = sorted([h for h in hs if h[3]], key=lambda h: h[3])
        if len(fin) < 3:
            continue
        top3 = [fin[0][0], fin[1][0], fin[2][0]]
        order = [h[0] for h in sorted(hs, key=lambda h: h[2])]
        odds1 = min(h[1] for h in hs)
        top3_odds = sorted(h[1] for h in hs)[:3]
        cond = {
            'n': len(hs),
            'odds1': odds1,
            'gap': top3_odds[1] / top3_odds[0] if top3_odds[0] else 1,  # 1番人気と2番人気の差
        }
        bets = build_bets(order)
        got = {}
        for name, legs in bets.items():
            inv = 100 * len(legs)
            ret = 0
            ok = True
            for bt, nums in legs:
                y = payout(bt, nums, v['payouts'], top3)
                if y is None:
                    ok = False
                    break
                ret += y
            if ok:
                got[name] = (inv, ret)
        rows.append((cond, got))

    print("=" * 104)
    print(f"■ レース条件 × 券種の実測ROI   {len(rows)}レース（市場人気ベース・印に依存しない素の性能）")
    print("=" * 104)

    NAMES = ['単勝1番人気', '複勝1番人気', 'ワイド1-2', 'ワイドBOX3', 'ワイドBOX4',
             '馬連1-2', '馬連BOX3', '3連複1-2-3', '3連複BOX4', '3連単1→2→3']

    def report(title, sel):
        if len(sel) < 60:
            return
        print()
        print(f"■ {title}（{len(sel)}レース）")
        print(f"{'買い方':>14s} {'点数':>4s} {'的中率':>7s} {'回収率':>8s}")
        print("-" * 60)
        out = []
        for nm in NAMES:
            inv = ret = hit = n = 0
            pts = 0
            for cond, got in sel:
                if nm not in got:
                    continue
                i, r = got[nm]
                inv += i; ret += r; n += 1
                pts = i // 100
                if r > 0:
                    hit += 1
            if n < 50:
                continue
            out.append((100 * ret / inv, nm, pts, 100 * hit / n))
        out.sort(reverse=True)
        for roi, nm, pts, h in out:
            mark = " ★" if roi == out[0][0] else ""
            print(f"{nm:>14s} {pts:4d} {h:6.1f}% {roi:7.1f}%{mark}")

    # ── 市場人気ベース vs うちの印ベース の直接比較 ──
    import engine_backtest as EB
    races_clean = EB.drop_leaky(EB.load_races(), verbose=False)
    import style_correction
    mrows = []
    for key, d in races_clean.items():
        recs = [dict(r) for r in d['recs']]
        style_correction.apply_style_correction(recs, enabled=True)
        recs.sort(key=lambda r: -(r.get('総合指数') or 0))
        order_mark = [str(r['馬番']) for r in recs]
        odds = d['odds']
        order_mkt = sorted(odds, key=lambda k: odds[k])
        pay = d['pay']; top3 = d['top3']
        if len(order_mark) < 4 or len(order_mkt) < 4:
            continue
        g = {}
        for label, od in (('印', order_mark), ('市場', order_mkt)):
            for nm, legs in build_bets(od).items():
                inv = 100 * len(legs); ret = 0; ok = True
                for bt, nums in legs:
                    y = payout(bt, nums, pay, top3)
                    if y is None:
                        ok = False; break
                    ret += y
                if ok:
                    g[f'{label}:{nm}'] = (inv, ret)
        mrows.append(g)

    print()
    print("=" * 104)
    print(f"■ 【最重要】うちの印 vs 市場の人気順   同じ買い方で比較（{len(mrows)}レース・汚染除去済み）")
    print("=" * 104)
    print(f"{'買い方':>14s} {'印ベース':>10s} {'市場ベース':>10s} {'差':>9s}   判定")
    print("-" * 104)
    for nm in NAMES:
        a = b = 0.0; ai = bi = 0.0
        for g in mrows:
            if f'印:{nm}' in g:
                i, r = g[f'印:{nm}']; ai += i; a += r
            if f'市場:{nm}' in g:
                i, r = g[f'市場:{nm}']; bi += i; b += r
        if ai < 5000 or bi < 5000:
            continue
        ra, rb = 100 * a / ai, 100 * b / bi
        d = ra - rb
        j = "★印が勝る" if d > 3 else ("印が劣る" if d < -3 else "差なし")
        print(f"{nm:>14s} {ra:9.1f}% {rb:9.1f}% {d:+8.1f}pt   {j}")

    report("全レース", rows)
    report("① 少頭数（12頭以下）", [x for x in rows if x[0]['n'] <= 12])
    report("① 多頭数（16頭以上）", [x for x in rows if x[0]['n'] >= 16])
    report("② 堅い（1番人気3倍未満）", [x for x in rows if x[0]['odds1'] < 3.0])
    report("② 中間（1番人気3〜5倍）", [x for x in rows if 3.0 <= x[0]['odds1'] < 5.0])
    report("② 混戦（1番人気5倍以上）", [x for x in rows if x[0]['odds1'] >= 5.0])
    report("③ 抜けた1番人気（2番人気が1.6倍以上のオッズ差）",
           [x for x in rows if x[0]['gap'] >= 1.6])
    report("③ 横一線（1-2番人気のオッズ差1.25倍未満）",
           [x for x in rows if x[0]['gap'] < 1.25])


if __name__ == '__main__':
    main()
