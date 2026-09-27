# -*- coding: utf-8 -*-
"""
gate_bias_audit.py — F06枠順バイアス表を実測で検証する（2026-09-04 新規）
==========================================================================
きっかけ: 紫苑S(中山芝2000m)の過去10年は3着内30頭のうち5-8枠が19頭・8枠だけで8頭と
**外枠が明確に有利**なのに、独自指数の GATE_BIAS['中山'] は
{1枠:76 … 8枠:54} と内枠に20点も高い配点をしていた。

GATE_BIAS は **競馬場単位** の1次元テーブルで、距離やコース形態（内回り/外回り）を
まったく区別していない。同じ中山でも芝1200mは内有利・芝2000mは外有利なので、
1つの表で代表させること自体に無理がある。

本スクリプトは蓄積DB（race_results.json）から
  競馬場 × 芝/ダート × 距離帯 ごとの「枠別3着内率」
を実測し、GATE_BIAS の向きと合っているかを検証する。

使い方: python gate_bias_audit.py
"""
from __future__ import annotations
import json, io, sys, collections, statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from collect_weekend_bigdata import GATE_BIAS

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'


def dist_band(d: str) -> str:
    import re
    m = re.search(r'(\d+)', str(d) or '')
    if not m:
        return '?'
    v = int(m.group(1))
    surf = '芝' if str(d).startswith('芝') else 'ダ'
    if v <= 1400:
        return f'{surf}短(〜1400)'
    if v <= 1800:
        return f'{surf}マ(〜1800)'
    if v <= 2200:
        return f'{surf}中(〜2200)'
    return f'{surf}長(2200〜)'


def slope(pairs):
    """枠→値 の傾き。正なら外枠有利、負なら内枠有利"""
    if len(pairs) < 4:
        return None
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None


def main():
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    print("=" * 100)
    print(f"■ F06枠順バイアスの実測検証   蓄積DB {len(res):,}行")
    print("=" * 100)

    # GATE_BIAS の傾き（表が示す向き）
    print()
    print("【1】GATE_BIAS表が示す向き（負=内枠有利／正=外枠有利）")
    print(f"{'競馬場':>6s} {'1枠':>4s} {'8枠':>4s} {'傾き':>7s}   表の主張")
    print("-" * 100)
    tbl_slope = {}
    for v, d in GATE_BIAS.items():
        pairs = sorted(d.items())
        s = slope([(k, val) for k, val in pairs])
        tbl_slope[v] = s
        print(f"{v:>6s} {d.get(1,0):4d} {d.get(8,0):4d} {s:+7.2f}   "
              f"{'内枠有利' if s < -0.5 else ('外枠有利' if s > 0.5 else 'ほぼ中立')}")

    # 実測: 競馬場 × 距離帯 ごとの枠別3着内率
    print()
    print("【2】実測（蓄積DB）: 競馬場×距離帯ごとの枠別3着内率の傾き")
    print(f"{'競馬場':>6s} {'距離帯':>12s} {'n':>6s} {'1-2枠':>7s} {'7-8枠':>7s} {'傾き':>7s}   実測   表   一致?")
    print("-" * 100)
    agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in res:
        try:
            w = int(float(r.get('枠')))
            fin = r.get('着順int')
        except (TypeError, ValueError):
            continue
        if not fin or not (1 <= w <= 8):
            continue
        key = (r['競馬場'], dist_band(r.get('距離')))
        a = agg[key][w]
        a[0] += 1
        if fin <= 3:
            a[1] += 1

    mismatch = []
    for key in sorted(agg):
        ven, band = key
        d = agg[key]
        n = sum(v[0] for v in d.values())
        if n < 300:
            continue
        pairs = [(w, 100 * d[w][1] / d[w][0]) for w in sorted(d) if d[w][0] >= 20]
        if len(pairs) < 5:
            continue
        s = slope(pairs)
        inn = statistics.mean([p[1] for p in pairs if p[0] <= 2]) if any(p[0] <= 2 for p in pairs) else 0
        out = statistics.mean([p[1] for p in pairs if p[0] >= 7]) if any(p[0] >= 7 for p in pairs) else 0
        real = '外枠有利' if s > 0.3 else ('内枠有利' if s < -0.3 else '中立')
        ts = tbl_slope.get(ven)
        tab = '外枠有利' if ts and ts > 0.5 else ('内枠有利' if ts and ts < -0.5 else '中立')
        ok = "OK" if real == tab or 'l中立' in (real + tab) or real == '中立' or tab == '中立' else "❌逆"
        if ok == "❌逆":
            mismatch.append((ven, band, real, tab, inn, out))
        print(f"{ven:>6s} {band:>12s} {n:6d} {inn:6.1f}% {out:6.1f}% {s:+7.2f}   "
              f"{real:>6s} {tab:>6s}   {ok}")

    print()
    print("=" * 100)
    print("■ 結論")
    print("=" * 100)
    if mismatch:
        print(f"表と実測が**逆向き**のコース: {len(mismatch)}件")
        for ven, band, real, tab, inn, out in mismatch:
            print(f"  ・{ven} {band}: 実測は{real}（1-2枠{inn:.1f}% vs 7-8枠{out:.1f}%）"
                  f"だが表は{tab}")
    else:
        print("  逆向きのコースは検出されず")
    print()
    print("※GATE_BIASは競馬場単位の1次元表で、距離・内外回りを区別していない。")
    print("　同じ競馬場でも距離帯で向きが変わるため、表の粒度そのものが不足している。")


if __name__ == '__main__':
    main()
