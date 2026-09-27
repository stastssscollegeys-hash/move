# -*- coding: utf-8 -*-
"""
find_value_horses.py — 過小評価されている馬の条件を探す（2026-09-04）
=====================================================================
【方針転換】
これまで「全レースで人気順に機械的に買う」戦略を測っていたが、それは市場が正しく
値付けした馬に控除率を払い続ける行為で、80%前後になるのは当然だった。測る意味が薄い。

競馬で利益を出すには「市場が過小評価している馬」を見つけ、**その馬がいるレースだけ買う**。
堅いレースは買わない（リスクとリターンが見合わない）。重賞だからという理由でも買わない。

そこで馬単位で条件を切り、単勝・複勝の実測回収率を測る。
狙える馬の条件が定まれば、その馬を軸に買い目を組み、条件を満たす馬がいないレースは見送る。

【偽エッジ対策（3回踏んだ反省・最初から組み込む）】
  ① 期間3分割で全区分100%超
  ② 払戻上位1件・3件を除いても100%超
  ③ n>=80（馬単位なのでレース単位より緩めるが下限は課す）
  ④ 最後にブートストラップ95%区間が100%を上回るか

使い方: python find_value_horses.py
"""
from __future__ import annotations
import io, sys, json, random, statistics, collections, itertools
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as EB
import style_correction

MIN_N = 80


def build():
    """汚染なしレースから馬単位のレコードを作る"""
    races = EB.drop_leaky(EB.load_races(), verbose=False)
    rows = []
    for key, d in races.items():
        recs = [dict(r) for r in d['recs']]
        style_correction.apply_style_correction(recs, enabled=True)
        recs.sort(key=lambda r: -(r.get('総合指数') or 0))
        rank = {str(r['馬番']): i + 1 for i, r in enumerate(recs)}
        odds = d['odds']
        pop = {n: i + 1 for i, n in enumerate(sorted(odds, key=lambda k: odds[k]))}
        top3 = d['top3']
        n = len(recs)
        # 複勝の払戻
        show = {}
        for x in d['pay'].get('複勝', []):
            show[x['combo']] = x['yen']
        win = d['pay'].get('単勝', [{}])[0]
        for r in recs:
            num = str(r['馬番'])
            if num not in odds or num not in pop:
                continue
            rows.append({
                'date': key[0], 'race': key, 'num': num,
                'odds': odds[num], 'pop': pop[num], 'mrank': rank[num], 'n': n,
                'style': r.get('脚質') or '不明',
                'idx': r.get('総合指数') or 0,
                'dokuji': r.get('独自指数') or 0,
                'ml': r.get('ML能力%') or 0,
                'rest': r.get('中日数') or 0,
                'fin1': num == top3[0],
                'fin3': num in top3,
                'win_yen': (win.get('yen', 0) if win.get('combo') == num else 0),
                'show_yen': show.get(num, 0),
                # 市場とモデルのズレ（正なら市場の方が高く評価＝モデルは低評価）
                'gapf': rank[num] - pop[num],
            })
    return rows


def roi(sub, kind):
    if not sub:
        return 0, 0, 0, []
    key = 'win_yen' if kind == '単勝' else 'show_yen'
    ret = sum(r[key] for r in sub)
    inv = 100 * len(sub)
    hit = sum(1 for r in sub if r[key] > 0)
    return 100 * ret / inv, 100 * hit / len(sub), len(sub), [r[key] for r in sub]


def check(sub, kind, dates3):
    r, h, n, det = roi(sub, kind)
    if n < MIN_N:
        return None
    segs = []
    for s in range(3):
        ss = [x for x in sub if dates3.get(x['date']) == s]
        segs.append(roi(ss, kind)[0] if len(ss) >= 15 else None)
    det_s = sorted(det, reverse=True)
    cut1 = 100 * (sum(det) - det_s[0]) / (100 * (n - 1)) if n > 1 else 0
    cut3 = 100 * (sum(det) - sum(det_s[:3])) / (100 * (n - 3)) if n > 3 else 0
    return {'roi': r, 'hit': h, 'n': n, 'segs': segs, 'cut1': cut1, 'cut3': cut3, 'det': det}


def boot(det, sims=4000, seed=5):
    rng = random.Random(seed)
    out = []
    for _ in range(sims):
        s = sum(det[rng.randrange(len(det))] for _ in range(len(det)))
        out.append(100 * s / (100 * len(det)))
    out.sort()
    return out[int(0.025 * sims)], out[int(0.975 * sims)]


def main():
    rows = build()
    dates = sorted({r['date'] for r in rows})
    t = len(dates) // 3
    dates3 = {d: (0 if i < t else 1 if i < 2 * t else 2) for i, d in enumerate(dates)}
    print("=" * 104)
    print(f"■ 過小評価されている馬の条件を探す   {len(rows):,}頭 / {len(dates)}日（汚染除去済み）")
    print("=" * 104)
    print(f"基準: n>={MIN_N} ／ 期間3分割すべて100%超 ／ 上位3件除外でも100%超")
    print()

    # 条件の定義（解釈できるものだけ。当日オッズで判定可能なもの）
    CONDS = {}
    for p in ('1-3人気', '4-6人気', '7-9人気', '10人気以下'):
        CONDS[f'市場{p}'] = {
            '1-3人気': lambda r: r['pop'] <= 3, '4-6人気': lambda r: 4 <= r['pop'] <= 6,
            '7-9人気': lambda r: 7 <= r['pop'] <= 9, '10人気以下': lambda r: r['pop'] >= 10}[p]
    for st in ('逃げ', '先行', '差し', '追込'):
        CONDS[f'脚質{st}'] = (lambda s: (lambda r: r['style'] == s))(st)
    CONDS['モデルが市場より高評価(gap<=-3)'] = lambda r: r['gapf'] <= -3
    CONDS['モデルが市場より低評価(gap>=+3)'] = lambda r: r['gapf'] >= 3
    CONDS['モデル1位'] = lambda r: r['mrank'] == 1
    CONDS['独自指数75以上'] = lambda r: r['dokuji'] >= 75
    CONDS['休み明け(中日90超)'] = lambda r: r['rest'] > 90
    CONDS['詰めローテ(中日28以下)'] = lambda r: 0 < r['rest'] <= 28

    print("【単独条件】")
    print(f"{'条件':>30s} {'券種':>4s} {'n':>5s} {'的中':>6s} {'ROI':>7s} "
          f"{'3分割':>20s} {'上3除':>7s}")
    print("-" * 104)
    singles = []
    for name, f in CONDS.items():
        sub = [r for r in rows if f(r)]
        for kind in ('単勝', '複勝'):
            s = check(sub, kind, dates3)
            if not s:
                continue
            seg = "/".join('—' if x is None else f"{x:.0f}" for x in s['segs'])
            ok = (s['roi'] >= 100 and all(x is not None and x >= 100 for x in s['segs'])
                  and s['cut3'] >= 100)
            print(f"{name:>30s} {kind:>4s} {s['n']:5d} {s['hit']:5.1f}% {s['roi']:6.1f}% "
                  f"{seg:>20s} {s['cut3']:6.1f}%{'  ★' if ok else ''}")
            if ok:
                singles.append((name, kind, s))
        singles_seen = True

    # 2条件の組み合わせ
    print()
    print("【2条件の組み合わせ】基準を通ったものだけ表示")
    print(f"{'条件':>44s} {'券種':>4s} {'n':>5s} {'的中':>6s} {'ROI':>7s} "
          f"{'3分割':>20s} {'上3除':>7s}")
    print("-" * 104)
    combos = []
    names = list(CONDS)
    for a, b in itertools.combinations(names, 2):
        fa, fb = CONDS[a], CONDS[b]
        sub = [r for r in rows if fa(r) and fb(r)]
        for kind in ('単勝', '複勝'):
            s = check(sub, kind, dates3)
            if not s:
                continue
            if not (s['roi'] >= 110 and all(x is not None and x >= 100 for x in s['segs'])
                    and s['cut3'] >= 100):
                continue
            seg = "/".join(f"{x:.0f}" for x in s['segs'])
            print(f"{a + ' × ' + b:>44s} {kind:>4s} {s['n']:5d} {s['hit']:5.1f}% "
                  f"{s['roi']:6.1f}% {seg:>20s} {s['cut3']:6.1f}%")
            combos.append((f"{a} × {b}", kind, s))

    print()
    print("=" * 104)
    print("■ 最終判定（ブートストラップ95%区間が100%を上回るか）")
    print("=" * 104)
    allc = singles + combos
    if not allc:
        print("  基準を通った条件なし")
        return
    print(f"{'条件':>44s} {'券種':>4s} {'n':>5s} {'ROI':>7s} {'95%区間':>18s}  判定")
    print("-" * 104)
    for name, kind, s in sorted(allc, key=lambda x: -x[2]['roi']):
        lo, hi = boot(s['det'])
        j = "★採用候補" if lo > 100 else "判定不能"
        print(f"{name:>44s} {kind:>4s} {s['n']:5d} {s['roi']:6.1f}% "
              f"[{lo:5.0f}〜{hi:5.0f}%]  {j}")


if __name__ == '__main__':
    main()
