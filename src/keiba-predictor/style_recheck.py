# -*- coding: utf-8 -*-
"""
style_recheck.py — 脚質補正v6.0を「汚染なしデータ」で検証し直す（2026-09-02）
==============================================================================
なぜ必要か
----------
脚質補正v6.0（逃げ-6.7 / 先行-3.1 / 差し+2.8）は 13開催・6,269頭から作った。
しかし 2026-09-02 に、そのうち6日分（5/16,5/17,5/23,5/24,5/30,7/26）が
backfill_records.py によるレース後再構築＝**結果リーク**だと判明した。

印が AI予測順位 の純粋な関数（◎=1位…）である以上、印が結果由来なら
**総合指数も結果由来**。つまり補正値の算出も、その効果検証も汚染されている疑いがある。

本スクリプトは「レース前に作られた records」だけを使って以下を測り直す:
  ① 脚質バイアスは本当に存在するか（脚質別の総合指数平均・1位に選ばれる割合）
  ② 補正値を汚染なしデータから再計算するとどうなるか
  ③ 補正を当てると単勝回収率は上がるか（train/valid分割）

使い方:
  python style_recheck.py
"""
from __future__ import annotations
import collections, statistics, sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B

STYLES = ('逃げ', '先行', '差し')


def collect(races):
    """レース単位の [(脚質, 総合指数, オッズ, 着順), ...] を作る。"""
    out = []
    for k, d in races.items():
        hs = []
        for r in d['recs']:
            num = str(r.get('馬番'))
            o = d['odds'].get(num)
            if o is None:
                continue
            fin = 1 if num == d['top3'][0] else (
                2 if num == d['top3'][1] else (3 if num == d['top3'][2] else 9))
            hs.append({'style': r.get('脚質') or '不明',
                       'idx': float(r.get('総合指数') or 0),
                       'odds': float(o), 'fin': fin, 'date': k[0]})
        if len(hs) >= 5:
            out.append(hs)
    return out


def offsets_from(races_list):
    """脚質別の総合指数平均を全体平均に揃えるオフセット。"""
    by = collections.defaultdict(list)
    for hs in races_list:
        for h in hs:
            if h['style'] in STYLES:
                by[h['style']].append(h['idx'])
    allv = [v for lst in by.values() for v in lst]
    if not allv:
        return {}
    g = statistics.mean(allv)
    return {s: round(g - statistics.mean(lst), 1)
            for s, lst in by.items() if len(lst) >= 30}


def evaluate(races_list, off=None):
    """各レースの総合指数1位を単勝で買った場合の1着率と回収率。"""
    tops = []
    for hs in races_list:
        best = max(hs, key=lambda h: h['idx'] + (off.get(h['style'], 0.0) if off else 0.0))
        tops.append(best)
    n = len(tops)
    if not n:
        return None
    win = sum(1 for t in tops if t['fin'] == 1)
    ret = sum(t['odds'] * 100 for t in tops if t['fin'] == 1)
    c = collections.Counter(t['style'] for t in tops)
    return {'n': n, 'win': 100 * win / n, 'roi': 100 * ret / (n * 100),
            'mix': {s: 100 * c[s] / n for s in STYLES}}


def main():
    all_races = B.load_races()
    clean = B.drop_leaky(all_races, verbose=False)
    dirty_keys = {k for k in all_races if k not in clean}
    dirty = {k: all_races[k] for k in dirty_keys}

    cl, dt = collect(clean), collect(dirty)
    print("=" * 94)
    print(f"■ 脚質補正v6.0の再検証  汚染なし{len(cl)}レース / 汚染あり{len(dt)}レース")
    print("=" * 94)

    # ── ① バイアスは実在するか ──
    print()
    print("【①】脚質バイアスは汚染なしデータでも存在するか")
    print(f"{'データ':>14s} {'指標':>18s} " + "".join(f"{s:>9s}" for s in STYLES))
    print("-" * 94)
    for label, lst in (("汚染あり(5月等)", dt), ("汚染なし(8月)", cl)):
        if not lst:
            continue
        by = collections.defaultdict(list)
        for hs in lst:
            for h in hs:
                if h['style'] in STYLES:
                    by[h['style']].append(h['idx'])
        print(f"{label:>14s} {'総合指数の平均':>18s} "
              + "".join(f"{statistics.mean(by[s]):9.1f}" if by[s] else f"{'-':>9s}" for s in STYLES))
        e = evaluate(lst)
        print(f"{'':>14s} {'1位に選ばれる割合':>18s} "
              + "".join(f"{e['mix'][s]:8.1f}%" for s in STYLES))
        real = collections.Counter(h['style'] for hs in lst for h in hs)
        tot = sum(real[s] for s in STYLES) or 1
        print(f"{'':>14s} {'実際の出走構成':>18s} "
              + "".join(f"{100*real[s]/tot:8.1f}%" for s in STYLES))
        print()

    # ── ② 補正値の再計算 ──
    print("【②】補正値を再計算すると")
    print(f"{'算出元':>22s} " + "".join(f"{s:>10s}" for s in STYLES))
    print("-" * 94)
    print(f"{'v6.0（汚染込みで算出）':>22s} " + "".join(f"{v:>10.1f}" for v in (-6.7, -3.1, 2.8)))
    for label, lst in (("汚染あり分のみ", dt), ("汚染なし分のみ", cl)):
        o = offsets_from(lst)
        if o:
            print(f"{label:>22s} " + "".join(f"{o.get(s, 0):>10.1f}" for s in STYLES))

    # ── ③ 効果検証（汚染なしデータでtrain/valid分割）──
    print()
    print("【③】汚染なしデータで補正の効果を測る（前半で補正値を作り後半で評価）")
    dates = sorted({hs[0]['date'] for hs in cl})
    half = len(dates) // 2
    tr = [hs for hs in cl if hs[0]['date'] in set(dates[:half])]
    va = [hs for hs in cl if hs[0]['date'] not in set(dates[:half])]
    off_tr = offsets_from(tr)
    print(f"   train {len(tr)}レース({len(dates[:half])}日) → 補正値 "
          + " / ".join(f"{s}{off_tr.get(s,0):+.1f}" for s in STYLES))
    print(f"   valid {len(va)}レース({len(dates[half:])}日) で評価")
    print()
    print(f"{'方式':>26s} {'n':>6s} {'1着率':>8s} {'単勝回収':>10s}   1位の脚質構成")
    print("-" * 94)
    for label, off in (("補正なし", None),
                       ("v6.0の固定値(-6.7/-3.1/+2.8)", {'逃げ': -6.7, '先行': -3.1, '差し': 2.8}),
                       ("汚染なしtrainから再計算", off_tr)):
        e = evaluate(va, off)
        if e:
            mix = " / ".join(f"{s}{e['mix'][s]:.0f}%" for s in STYLES)
            print(f"{label:>26s} {e['n']:6d} {e['win']:7.1f}% {e['roi']:9.1f}%   {mix}")
    real = collections.Counter(h['style'] for hs in va for h in hs)
    tot = sum(real[s] for s in STYLES) or 1
    print(f"{'（実際の出走構成）':>26s} {'':6s} {'':8s} {'':10s}   "
          + " / ".join(f"{s}{100*real[s]/tot:.0f}%" for s in STYLES))

    print()
    print("【判定】汚染なしデータで補正の効果が消えていれば、v6.0は結果リークの産物。")
    print("　　　　その場合は style_correction.ENABLED = False にすること。")


if __name__ == '__main__':
    main()
