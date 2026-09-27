# -*- coding: utf-8 -*-
"""
rule_validation.py — 「買うレースを選ぶルール」の検証（毎週データが増えたら回し直す）2026-09-11
====================================================================================
policy_validation.py の結論:
  - 区分ごとに買い方を選ぶ方式は、時系列で当てると固定の買い方に負けた（過学習）
  - 旧ガード（◎ワイド必須 等）は足しても得にならない
  - 配分は推定配当に反比例が最良
  - 有望な手がかり: 「◎と○がどちらも1〜3番人気のレースだけ買う」で全期間106〜112%（ただし全期間を見て気付いた条件）

ここでは、その手がかりが本物かを確かめる。ルールは学習しない固定の条件なので、
「前半／後半」「3期間」のどこでも成り立つか、偶然の幅はどれくらいか、100%超えを主張するのに何レース要るかを出す。

使い方:
  python rule_validation.py          # 全ルール×買い方の表と、今週の3重賞の当てはまり
"""
from __future__ import annotations
import json, math, statistics, sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B
import structure_backtest as SB
import policy_validation as PV   # run_alloc / quick / 候補の買い方を登録済み

OUT = Path.home() / 'Desktop' / '競馬予想レポート' / '20260912' / 'research'
STRUCTS = ['馬連BOX3(◎○▲)', '今週の混成型(S型7点)', '馬連BOX3＋ワイド◎流し4(7点)', '馬連◎流し(相手4)', '複勝◎', '単勝◎']
RULES = {
    'すべて買う': lambda f: True,
    '◎1-3人気かつ○1-3人気': lambda f: f['hon'] <= 3 and f['tai'] <= 3,
    '◎1-2人気かつ○1-3人気': lambda f: f['hon'] <= 2 and f['tai'] <= 3,
    '◎○▲のうち市場上位3頭と2頭以上重なる': lambda f: f['ovl'] >= 2,
    '◎○▲が市場上位3頭と3頭とも重なる': lambda f: f['ovl'] == 3,
    '◎○▲のうち市場上位3頭と重なるのが1頭以下': lambda f: f['ovl'] <= 1,
}


def stats(lst):
    """lst=[(key, inv, ret)]（日付順）"""
    q = PV.quick(lst)
    if not q:
        return None
    n = len(lst)
    dates = sorted({k[0] for k, _, _ in lst})
    mid = dates[len(dates) // 2]
    first = [x for x in lst if x[0][0] < mid]; second = [x for x in lst if x[0][0] >= mid]
    thirds = [lst[:n // 3], lst[n // 3:2 * n // 3], lst[2 * n // 3:]]
    s = SB.metrics(lst)
    rr = [r / i for _, i, r in lst]
    mean, sd = statistics.mean(rr), (statistics.pstdev(rr) if n > 1 else 0.0)
    # 観測された平均が本当の値だと仮定したとき、95%区間の下限が100%を超えるのに必要なレース数
    need = math.ceil((1.96 * sd / (mean - 1)) ** 2) if mean > 1 else None
    return {**q, 'first_ex1': (PV.quick(first) or {}).get('ex1'), 'second_ex1': (PV.quick(second) or {}).get('ex1'),
            'first_roi': (PV.quick(first) or {}).get('roi'), 'second_roi': (PV.quick(second) or {}).get('roi'),
            'thirds_roi': [(PV.quick(t) or {}).get('roi') for t in thirds], 'lo': s['lo'], 'hi': s['hi'],
            'mean_race_roi': mean, 'sd_race_roi': sd, 'need_races': need}


def pct(x):
    return f"{x*100:>4.0f}%" if x is not None else "  — "


def main():
    # --leakfree: backfill_leakfree.py で作り直したレースだけで検証する（ルールを見つけた385Rを含まない＝hold-out）
    leakfree = '--leakfree' in sys.argv
    if leakfree:
        import load_leakfree as LF
        races = {k: v for k, v in LF.load_races_leakfree().items() if v['origin'] == 'leakfree'}
    else:
        races = B.drop_leaky(B.load_races(), verbose=False)
    marks_cache, feats = {}, {}
    for key, d in races.items():
        m = SB.race_marks(d, '印')
        if not m:
            continue
        marks_cache[key] = m
        order = sorted(d['odds'], key=lambda k: d['odds'][k])
        pr = {h: i + 1 for i, h in enumerate(order)}
        feats[key] = {'hon': pr[m['◎']], 'tai': pr[m['○']], 'ovl': len({m['◎'], m['○'], m['▲']} & set(order[:3]))}
    print(f"対象 {len(feats)}レース（{min(k[0] for k in feats)}〜{max(k[0] for k in feats)}）")
    report = {}
    for n in STRUCTS:
        alloc = 'flat' if len(SB.STRUCTS[n](PV.DUMMY)) == 1 else 'even'
        per = PV.run_alloc(races, n, alloc, marks_cache)
        print(f"\n■ {n}（配分: {'全点同額' if alloc == 'flat' else '推定配当に反比例'}）")
        print(f"   {'ルール':<34s}{'R':>5s}{'回収率':>7s}{'95%区間':>13s}{'上位1除外':>9s}{'上位3除外':>9s}{'的中':>7s}"
              f"{'前半/後半(上位1除外)':>20s}{'3期間の回収率':>18s}{'必要R':>7s}")
        for rn, rf in RULES.items():
            lst = sorted([(k, *per[k]) for k in per if rf(feats[k])], key=lambda x: x[0])
            s = stats(lst)
            if not s:
                continue
            report[f"{n}|{rn}"] = s
            th = "/".join(f"{x*100:.0f}" if x is not None else "-" for x in s['thirds_roi'])
            print(f"   {rn:<34s}{s['n']:>5d}{pct(s['roi'])}  [{s['lo']*100:>3.0f}〜{s['hi']*100:>3.0f}%]{pct(s['ex1']):>9s}{pct(s['ex3']):>9s}"
                  f"{s['hit']*100:>6.1f}%{(pct(s['first_ex1']) + '/' + pct(s['second_ex1'])):>20s}{th:>18s}"
                  f"{(str(s['need_races']) if s['need_races'] else '100%未満'):>8s}")

    if leakfree:
        OUT.mkdir(parents=True, exist_ok=True)
        json.dump({'report': report}, open(OUT / 'rule_validation_leakfree.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"\nsaved {OUT / 'rule_validation_leakfree.json'}")
        return

    # 今週の3重賞（予想オッズ 9/11 17時）の当てはまり
    base = OUT.parent
    yoso = json.load(open(base / 'yoso_odds_20260911.json', encoding='utf-8'))
    marks = {'チャレンジC': (9, 11, 13), 'セントライト記念': (8, 10, 9), 'ローズS': (7, 12, 2)}
    print("\n■ 今週の3重賞の当てはまり（予想オッズ）")
    week = {}
    for race, (h, t, a) in marks.items():
        hs = [x for x in yoso[race]['horses'] if x.get('uma') and x.get('pop')]
        pop = {x['uma']: x['pop'] for x in hs}
        top3 = {u for u, p in pop.items() if p <= 3}
        f = {'hon': pop[h], 'tai': pop[t], 'ovl': len({h, t, a} & top3)}
        hit_rules = [rn for rn, rf in RULES.items() if rf(f) and rn != 'すべて買う']
        week[race] = {**f, 'rules': hit_rules}
        print(f"   {race}: ◎{pop[h]}人気 ○{pop[t]}人気 ▲{pop[a]}人気 市場上位3頭との重なり{f['ovl']}頭 → 該当: {' / '.join(hit_rules) or 'なし'}")
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({'report': report, 'week': week}, open(OUT / 'rule_validation_20260911.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\nsaved {OUT / 'rule_validation_20260911.json'}")


if __name__ == '__main__':
    main()
