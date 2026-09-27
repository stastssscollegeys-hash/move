# -*- coding: utf-8 -*-
"""
pattern_by_segment.py — 「◎・○が何番人気か」で分けて、どの買い方が一番配当を取れるかを出す（2026-09-11）
==========================================================================================================
ユーザー指示: 「全部のレースを同じ買い目にするのは良くない。◎や○を何番人気にしているかで、
どう買えば配当が得られるかは変わる。レースによってパターンを決めてほしい」

データ: structure_backtest.py と同じ（レース前に作った印のみ・リーク除外・確定払戻）
印の基準: 印（脚質補正後のAI予測順位 1=◎ 2=○ 3=▲ 4,5=△ 6=穴）
配分: 2点以上の買い方は推定配当に反比例（どれが当たってもほぼ同額）／1点の買い方は全点同額
区分: ◎の人気（1／2-3／4-6／7以下）・○の人気（1-3／4以下）・その掛け合わせ
判断: 最高配当1レース除外の回収率（ex1）を主に、上位3レース除外（ex3）・的中率・件数を併記
⚠ 区分ごとの件数は30〜150と少ない。ex1とex3の両方で上位に来る買い方だけを採る

使い方:
  python pattern_by_segment.py
"""
from __future__ import annotations
import json, sys, io
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B
import structure_backtest as SB

OUT = Path.home() / 'Desktop' / '競馬予想レポート' / '20260912' / 'research'


def S(m, *k):
    return [m[x] for x in k]


EXTRA = {
    '馬連BOX3＋ワイドBOX3(6点)': lambda m: [('馬連', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)]
                                   + [('ワイド', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)],
    '馬連BOX3＋ワイド◎流し4(7点)': lambda m: [('馬連', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)]
                                   + [('ワイド', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')],
    '馬連◎流し4＋ワイド◎流し4(8点)': lambda m: [('馬連', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')]
                                   + [('ワイド', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')],
    '馬連BOX3＋ワイドBOX3＋ワイド◎-穴(7点)': lambda m: [('馬連', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)]
                                   + [('ワイド', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)] + [('ワイド', S(m, '◎', '穴'), 1)],
    '単勝◎＋複勝◎': lambda m: [('単勝', S(m, '◎'), 1), ('複勝', S(m, '◎'), 1)],
    '単勝◎＋ワイド◎流し3(○▲△)': lambda m: [('単勝', S(m, '◎'), 1)] + [('ワイド', S(m, '◎', k), 1) for k in ('○', '▲', '△1')],
    '複勝◎＋ワイド◎流し4': lambda m: [('複勝', S(m, '◎'), 1)] + [('ワイド', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')],
    'ワイド◎-○▲(2点)': lambda m: [('ワイド', S(m, '◎', k), 1) for k in ('○', '▲')],
    '馬連◎-○▲(2点)': lambda m: [('馬連', S(m, '◎', k), 1) for k in ('○', '▲')],
    '馬単◎→○▲(2点)＋馬連◎-○▲': lambda m: [('馬単', S(m, '◎', k), 1) for k in ('○', '▲')] + [('馬連', S(m, '◎', k), 1) for k in ('○', '▲')],
    '馬単◎→○▲△(3点)＋3連複◎○▲': lambda m: [('馬単', S(m, '◎', k), 1) for k in ('○', '▲', '△1')] + [('3連複', sorted(S(m, '◎', '○', '▲')), 1)],
    '馬連◎-○＋ワイド◎-▲＋ワイド◎-穴': lambda m: [('馬連', S(m, '◎', '○'), 1), ('ワイド', S(m, '◎', '▲'), 1), ('ワイド', S(m, '◎', '穴'), 1)],
    '3連複F◎-○▲-○▲△△穴(7)＋ワイド◎-○': lambda m: SB.tri_form(m, ['◎'], ['○', '▲'], ['○', '▲', '△1', '△2', '穴']) + [('ワイド', S(m, '◎', '○'), 1)],
}
SB.STRUCTS.update(EXTRA)
DUMMY = {k: str(i) for i, k in enumerate(['◎', '○', '▲', '△1', '△2', '穴'])}


def band_hon(p):
    return '1番人気' if p == 1 else '2-3番人気' if p <= 3 else '4-6番人気' if p <= 6 else '7番人気以下'


def main():
    races = B.drop_leaky(B.load_races(), verbose=False)
    feats = {}
    for key, d in races.items():
        m = SB.race_marks(d, '印')
        if not m:
            continue
        order = sorted(d['odds'], key=lambda k: d['odds'][k])
        pr = {h: i + 1 for i, h in enumerate(order)}
        feats[key] = {'hon': pr[m['◎']], 'tai': pr[m['○']], 'tan': pr[m['▲']], 'n': len(d['odds'])}

    per = {}
    for name in SB.STRUCTS:
        alloc = 'flat' if len(SB.STRUCTS[name](DUMMY)) == 1 else 'even'
        per[name] = {k: (i, r) for k, i, r in SB.run(races, name, '印', alloc)}

    segs = {
        '全体': lambda f: True,
        '◎1番人気': lambda f: f['hon'] == 1,
        '◎2-3番人気': lambda f: 2 <= f['hon'] <= 3,
        '◎4-6番人気': lambda f: 4 <= f['hon'] <= 6,
        '◎7番人気以下': lambda f: f['hon'] >= 7,
        '○1-3番人気': lambda f: f['tai'] <= 3,
        '○4番人気以下': lambda f: f['tai'] >= 4,
        '◎1番人気×○1-3番人気': lambda f: f['hon'] == 1 and f['tai'] <= 3,
        '◎1番人気×○4番人気以下': lambda f: f['hon'] == 1 and f['tai'] >= 4,
        '◎2-3番人気×○1-3番人気': lambda f: 2 <= f['hon'] <= 3 and f['tai'] <= 3,
        '◎2-3番人気×○4番人気以下': lambda f: 2 <= f['hon'] <= 3 and f['tai'] >= 4,
        '◎4番人気以下×○1-3番人気': lambda f: f['hon'] >= 4 and f['tai'] <= 3,
        '◎4番人気以下×○4番人気以下': lambda f: f['hon'] >= 4 and f['tai'] >= 4,
    }
    overall = {}
    result = {}
    for seg, f in segs.items():
        keys = sorted(k for k in feats if f(feats[k]))
        rows = []
        for name, d in per.items():
            lst = [(k, *d[k]) for k in keys if k in d]
            s = SB.metrics(lst) if len(lst) >= 10 else None
            if s:
                rows.append((name, s))
        if seg == '全体':
            overall = {n: s for n, s in rows}
        rows.sort(key=lambda x: -x[1]['roi_ex1'])
        # ex1 と ex3 の順位の平均で並べ直した「安定順位」も出す
        r1 = {n: i for i, (n, _) in enumerate(rows)}
        r3 = {n: i for i, (n, _) in enumerate(sorted(rows, key=lambda x: -x[1]['roi_ex3']))}
        stable = sorted(rows, key=lambda x: (r1[x[0]] + r3[x[0]]) / 2)
        result[seg] = {'n': len(keys), 'rows': [{'name': n, **{k: v for k, v in s.items() if k in ('races', 'roi', 'roi_ex1', 'roi_ex3', 'hit', 'gami', 'max_losing', 'roi_thirds')}} for n, s in stable]}
        print(f"\n■ {seg}（{len(keys)}レース）  並び=上位1除外と上位3除外の順位平均（安定順）")
        print(f"   {'買い方':<38s}{'上位1除外':>8s}{'上位3除外':>8s}{'的中率':>8s}{'損する率':>8s}{'連敗':>5s}{'全体(上位1除外)':>14s}")
        for n, s in stable[:8]:
            o = overall.get(n)
            print(f"   {n:<38s}{s['roi_ex1']*100:>7.0f}%{s['roi_ex3']*100:>7.0f}%{s['hit']*100:>7.1f}%{s['gami']*100:>7.0f}%{s['max_losing']:>5d}"
                  f"{(o['roi_ex1']*100 if o else 0):>12.0f}%")
        for ref in ('馬連BOX3＋ワイド◎流し4(7点)', '今週の混成型(S型7点)'):
            pos = next((i + 1 for i, (n, _) in enumerate(stable) if n == ref), None)
            s = dict(stable).get(ref)
            if s:
                print(f"   （参考）{ref}: 安定順{pos}位 上位1除外{s['roi_ex1']*100:.0f}% 的中{s['hit']*100:.1f}%")
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(OUT / 'pattern_by_segment_20260911.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\nsaved {OUT / 'pattern_by_segment_20260911.json'}")


if __name__ == '__main__':
    main()
