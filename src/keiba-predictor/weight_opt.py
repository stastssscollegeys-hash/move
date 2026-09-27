# -*- coding: utf-8 -*-
"""
weight_opt.py — 総合指数の重み配分を検証する（2026-09-01）
===========================================================
現行の計算式（collect_weekend_bigdata.py L387-389）:

    ml_scaled = min(100, ML能力% × 2.5)
    総合指数  = 独自指数 × 0.55 + ml_scaled × 0.45

判明している問題:
  ① 脚質バイアスの98%がML能力%由来
     （脚質別のML能力%平均 逃げ13.1 / 先行9.4 / 差し4.9 に対し、
       独自指数は 64.6 / 65.1 / 63.5 とほぼ中立）
  ② 予測力は独自指数の方が高い
     （下位20%→上位20%の回収率差 独自指数+25pt vs ML能力%+9pt）
  → 予測力の低い方に45%の重みが乗っている疑い

本スクリプトは重み比率を振って、どこが最適かを train/valid 分割で測る。
併せて「ML能力%を脚質内で標準化する」案も試す。
"""
from __future__ import annotations
import json, collections, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = Path.home() / 'Desktop' / '競馬予想レポート'


def load_races():
    db = json.load(open(BASE / 'daily_pdca' / 'db' / 'race_results.json', encoding='utf-8'))
    res = collections.defaultdict(dict)
    for r in db:
        res[(r['date'], r['競馬場'], int(r['R']))][r['馬名']] = r
    races = []
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
            hs = []
            for p in prs:
                a = rr.get(p['馬名'])
                if not a:
                    continue
                o, pop = a.get('単勝オッズ'), a.get('人気')
                if not o or not pop:
                    continue
                hs.append(dict(
                    date=k[0], odds=float(o), pop=int(pop), fin=a['着順int'],
                    style=p.get('脚質') or '不明',
                    dokuji=float(p.get('独自指数') or 0),
                    ml=float(p.get('ML能力%') or 0),
                ))
            if len(hs) >= 5:
                races.append(hs)
    return races


def roi(sub):
    if not sub:
        return 0, 0.0, 0.0
    n = len(sub)
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds']*100 for r in sub if r['fin'] == 1)
    return n, 100*w/n, 100*ret/(n*100)


def score(h, w_dokuji, ml_z=None, style_off=None):
    """総合指数を再計算する。ml_z を渡すと ML能力%を脚質内Zに置き換える。"""
    if ml_z is not None:
        ms = ml_z.get(h['style'])
        ml_part = ((h['ml'] - ms[0]) / ms[1]) * 25 + 50 if ms else 50.0
    else:
        ml_part = min(100.0, h['ml'] * 2.5)
    s = h['dokuji'] * w_dokuji + ml_part * (1 - w_dokuji)
    if style_off:
        s += style_off.get(h['style'], 0.0)
    return s


def evaluate(races, **kw):
    tops = [max(hs, key=lambda h: score(h, **kw)) for hs in races]
    n, w, r = roi(tops)
    c = collections.Counter(t['style'] for t in tops)
    tot = sum(c.values()) or 1
    return n, w, r, {s: 100*c[s]/tot for s in ('逃げ', '先行', '差し')}


def main():
    races = load_races()
    allh = [h for hs in races for h in hs]
    days = sorted({h['date'] for h in allh})
    half = len(days) // 2
    tr_days = set(days[:half])
    tr = [hs for hs in races if hs[0]['date'] in tr_days]
    va = [hs for hs in races if hs[0]['date'] not in tr_days]

    print("=" * 100)
    print("■ 総合指数の重み配分の検証（%dレース / %d頭）" % (len(races), len(allh)))
    print("=" * 100)
    print("現行: 独自指数55%% + ML能力%%45%%")
    real = {s: 100*sum(1 for h in allh if h['style'] == s)/len(allh) for s in ('逃げ', '先行', '差し')}
    print("実際の全馬構成: 逃げ%.1f%% / 先行%.1f%% / 差し%.1f%%" % (real['逃げ'], real['先行'], real['差し']))
    print()

    print("【1】独自指数の重みを振る（全データ）")
    print("%-24s %7s %9s | %7s %7s %7s" % ("重み配分", "1着率", "単勝回収", "逃げ", "先行", "差し"))
    print("-" * 84)
    best = None
    for wd in (0.0, 0.3, 0.45, 0.55, 0.7, 0.85, 1.0):
        n, w, r, st = evaluate(races, w_dokuji=wd)
        lab = "独自%d%% + ML%d%%" % (wd*100, (1-wd)*100)
        mark = "  ← 現行" if abs(wd - 0.55) < 0.01 else ""
        print("%-24s %6.1f%% %8.1f%% | %6.1f%% %6.1f%% %6.1f%%%s" %
              (lab, w, r, st['逃げ'], st['先行'], st['差し'], mark))
        if best is None or r > best[1]:
            best = (wd, r)

    print()
    print("【2】ML能力%%を脚質内で標準化する（重み配分は現行の55:45のまま）")
    ml_z = {}
    for s in ('逃げ', '先行', '差し'):
        vs = [h['ml'] for h in allh if h['style'] == s]
        if len(vs) > 30:
            ml_z[s] = (statistics.mean(vs), statistics.pstdev(vs) or 1.0)
    n, w, r, st = evaluate(races, w_dokuji=0.55, ml_z=ml_z)
    print("%-24s %6.1f%% %8.1f%% | %6.1f%% %6.1f%% %6.1f%%" %
          ("ML脚質内Z化", w, r, st['逃げ'], st['先行'], st['差し']))

    print()
    print("【3】昨日導入した脚質補正（-6.7/-3.1/+2.8）との比較")
    off = {'逃げ': -6.7, '先行': -3.1, '差し': 2.8}
    n, w, r, st = evaluate(races, w_dokuji=0.55, style_off=off)
    print("%-24s %6.1f%% %8.1f%% | %6.1f%% %6.1f%% %6.1f%%" %
          ("現行55:45 + 脚質補正", w, r, st['逃げ'], st['先行'], st['差し']))
    n, w, r, st = evaluate(races, w_dokuji=best[0], style_off=off)
    print("%-24s %6.1f%% %8.1f%% | %6.1f%% %6.1f%% %6.1f%%" %
          ("最良重み + 脚質補正", w, r, st['逃げ'], st['先行'], st['差し']))

    print()
    print("=" * 100)
    print("■ 過学習チェック（train %dレースで最良を選び、valid %dレースで評価）" % (len(tr), len(va)))
    print("=" * 100)
    cands = []
    for wd in (0.0, 0.3, 0.45, 0.55, 0.7, 0.85, 1.0):
        _, _, r, _ = evaluate(tr, w_dokuji=wd)
        cands.append((r, wd))
    cands.sort(reverse=True)
    best_wd = cands[0][1]
    print("train での最良重み: 独自%d%% + ML%d%%（train回収率%.1f%%）"
          % (best_wd*100, (1-best_wd)*100, cands[0][0]))
    print()
    print("%-30s %7s %9s" % ("方式（validで評価）", "1着率", "単勝回収"))
    print("-" * 50)
    for wd, lab in ((0.55, "現行 独自55% + ML45%"),
                    (best_wd, "train最良 独自%d%% + ML%d%%" % (best_wd*100, (1-best_wd)*100))):
        n, w, r, _ = evaluate(va, w_dokuji=wd)
        print("%-30s %6.1f%% %8.1f%%" % (lab, w, r))
    # 脚質補正あり
    for wd, lab in ((0.55, "現行 + 脚質補正"),
                    (best_wd, "train最良 + 脚質補正")):
        n, w, r, _ = evaluate(va, w_dokuji=wd, style_off=off)
        print("%-30s %6.1f%% %8.1f%%" % (lab, w, r))

    # ML脚質内Z化も valid で評価（train期間の統計だけで標準化する）
    tr_h = [h for hs in tr for h in hs]
    ml_z_tr = {}
    for s in ('逃げ', '先行', '差し'):
        vs = [h['ml'] for h in tr_h if h['style'] == s]
        if len(vs) > 30:
            ml_z_tr[s] = (statistics.mean(vs), statistics.pstdev(vs) or 1.0)
    n, w, r, st = evaluate(va, w_dokuji=0.55, ml_z=ml_z_tr)
    print("%-30s %6.1f%% %8.1f%%" % ("ML脚質内Z化（train統計）", w, r))
    print("   1位の脚質構成: 逃げ%.1f%% / 先行%.1f%% / 差し%.1f%%" % (st['逃げ'], st['先行'], st['差し']))

    print()
    print("【結論】validで最も良い方式を採用すること。")
    print("  train最良をそのまま使うと過学習になる実例が出ている")
    print("  （独自100%%はtrain94.4%%→valid85.3%%、脚質補正と併用すると73.4%%まで劣化）")


if __name__ == '__main__':
    main()
