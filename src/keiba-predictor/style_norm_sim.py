# -*- coding: utf-8 -*-
"""
style_norm_sim.py — 脚質内標準化の効果をシミュレーションする（2026-08-31）
==========================================================================
判明した原因:
  差し馬は近走複勝率が構造的に低く出る（市場1-3番人気で 差し39.5 vs 先行52.2）。
  モデルはそれを「能力が低い」と解釈し、同じ人気でも差し馬を7位以下に落とす割合が
  1.6倍（差し20.1% vs 先行12.8%）。結果、総合指数の平均は 逃げ50.0 / 先行46.4 / 差し40.5。

修正案:
  因子を「全体の中での位置」ではなく「同じ脚質の中での相対位置」で評価すれば、
  脚質による下駄が消えるはず。

本スクリプトは指数を本格的に作り直す前に、既存データ上で補正を当てて効果を測る。
  ベースライン : 現行の総合指数の並び
  補正A        : 脚質ごとの総合指数の平均を全体平均に揃える（下駄を外すだけ）
  補正B        : 近走複勝率系の因子を脚質内でZ標準化し、指数に足し戻す

評価軸:
  ① モデル1位の1着率・単勝回収率（予測精度そのもの）
  ② 差し馬と先行馬の回収率差が縮まるか（バイアスが消えたか）
  ③ レース内で1位に選ばれる馬がどう変わるか
"""
from __future__ import annotations
import json, collections, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = Path.home() / 'Desktop' / '競馬予想レポート'


def load_races():
    """レース単位で（事前予測 × 結果）を返す"""
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
            horses = []
            for p in prs:
                a = rr.get(p['馬名'])
                if not a:
                    continue
                o, pop = a.get('単勝オッズ'), a.get('人気')
                if not o or not pop:
                    continue
                horses.append(dict(
                    name=p['馬名'], odds=float(o), pop=int(pop), fin=a['着順int'],
                    style=p.get('脚質') or '不明',
                    sogo=float(p.get('総合指数') or 0),
                    fuku5=float(p.get('近5走複勝率%') or 0),
                    fukud=float(p.get('同距離複勝率%') or 0),
                ))
            if len(horses) >= 5:
                races.append(horses)
    return races


def roi(sub):
    if not sub:
        return 0, 0.0, 0.0
    n = len(sub)
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds']*100 for r in sub if r['fin'] == 1)
    return n, 100*w/n, 100*ret/(n*100)


def evaluate(races, key, label):
    """key で各レースを並べ替え、1位馬の成績と脚質別回収率を出す"""
    tops = []
    for hs in races:
        tops.append(max(hs, key=lambda r: r[key]))
    n, w, r = roi(tops)
    allh = [h for hs in races for h in hs]
    out = dict(label=label, n=n, win=w, roi=r)
    # 脚質バイアス: 市場1-3番人気の差し vs 先行（この差が縮まれば補正成功）
    p13 = [h for h in allh if h['pop'] <= 3]
    _, _, rs = roi([h for h in p13 if h['style'] == '差し'])
    _, _, rk = roi([h for h in p13 if h['style'] == '先行'])
    out['sashi_roi'], out['senko_roi'] = rs, rk
    # 1位に選ばれた馬の脚質構成
    c = collections.Counter(t['style'] for t in tops)
    tot = sum(c.values()) or 1
    out['top_style'] = {s: 100*c[s]/tot for s in ('逃げ', '先行', '差し')}
    return out


def main():
    races = load_races()
    allh = [h for hs in races for h in hs]
    print("=" * 100)
    print("■ 脚質内標準化シミュレーション（%dレース / %d頭）" % (len(races), len(allh)))
    print("=" * 100)

    # ── 補正A: 脚質ごとの総合指数の下駄を外す ──────────────────
    by_style = collections.defaultdict(list)
    for h in allh:
        by_style[h['style']].append(h['sogo'])
    gmean = statistics.mean([h['sogo'] for h in allh])
    offset = {s: gmean - statistics.mean(v) for s, v in by_style.items() if v}
    print("\n【補正A】脚質ごとの総合指数の下駄（全体平均 %.1f に揃える）" % gmean)
    for s in ('逃げ', '先行', '差し'):
        if s in offset:
            print("  %-4s 平均%.1f → 補正 %+.1f" % (s, statistics.mean(by_style[s]), offset[s]))
    for h in allh:
        h['sogo_A'] = h['sogo'] + offset.get(h['style'], 0.0)

    # ── 補正B: 近走複勝率系を脚質内でZ標準化して指数に足す ─────────
    stats_b = {}
    for fc in ('fuku5', 'fukud'):
        for s in by_style:
            vs = [h[fc] for h in allh if h['style'] == s]
            if len(vs) > 30:
                m = statistics.mean(vs)
                sd = statistics.pstdev(vs) or 1.0
                stats_b[(fc, s)] = (m, sd)
    for h in allh:
        z = 0.0
        for fc in ('fuku5', 'fukud'):
            ms = stats_b.get((fc, h['style']))
            if ms:
                z += (h[fc] - ms[0]) / ms[1]
        # 全体でのZも引いて「脚質内での相対位置」に置き換える
        h['sogo_B'] = h['sogo'] + offset.get(h['style'], 0.0) + z * 3.0

    print("\n【結果】各方式でレース内1位に選んだ馬の成績")
    print("%-28s %6s %8s %9s | %9s %9s %8s" %
          ("方式", "n", "1着率", "単勝回収", "1-3人気差し", "1-3人気先行", "差"))
    print("-" * 100)
    rows = []
    for key, lab in (('sogo', 'ベースライン（現行）'),
                     ('sogo_A', '補正A 脚質の下駄を外す'),
                     ('sogo_B', '補正B A＋複勝率を脚質内Z化')):
        d = evaluate(races, key, lab)
        rows.append(d)
        print("%-28s %6d %7.1f%% %8.1f%% | %8.0f%% %8.0f%% %+7.0f%%" %
              (lab, d['n'], d['win'], d['roi'], d['sashi_roi'], d['senko_roi'],
               d['sashi_roi'] - d['senko_roi']))

    print("\n【1位に選ばれた馬の脚質構成】")
    print("%-28s %8s %8s %8s" % ("方式", "逃げ", "先行", "差し"))
    for d in rows:
        ts = d['top_style']
        print("%-28s %7.1f%% %7.1f%% %7.1f%%" % (d['label'], ts['逃げ'], ts['先行'], ts['差し']))
    print("\n  ※ 実際の全馬構成: 逃げ%.1f%% / 先行%.1f%% / 差し%.1f%%" % (
        100*sum(1 for h in allh if h['style'] == '逃げ')/len(allh),
        100*sum(1 for h in allh if h['style'] == '先行')/len(allh),
        100*sum(1 for h in allh if h['style'] == '差し')/len(allh)))

    print("\n【判定】")
    base = rows[0]
    for d in rows[1:]:
        dw = d['win'] - base['win']
        dr = d['roi'] - base['roi']
        print("  %-26s 1着率 %+.1fpt / 回収率 %+.1fpt" % (d['label'], dw, dr))

    # ══════════════════════════════════════════════════════
    # 過学習チェック: train期間で補正値を作り、valid期間で評価する
    # ══════════════════════════════════════════════════════
    print()
    print("=" * 100)
    print("■ 過学習チェック（train期間で補正値を作り、valid期間だけで評価）")
    print("=" * 100)
    # レースを日付順に半分に割る
    dated = []
    for hs in races:
        dated.append(hs)
    half = len(dated) // 2
    tr_races, va_races = dated[:half], dated[half:]
    tr_h = [h for hs in tr_races for h in hs]
    va_h = [h for hs in va_races for h in hs]

    # train だけで補正値を算出
    bs = collections.defaultdict(list)
    for h in tr_h:
        bs[h['style']].append(h['sogo'])
    gm = statistics.mean([h['sogo'] for h in tr_h])
    off_tr = {s: gm - statistics.mean(v) for s, v in bs.items() if v}
    st_tr = {}
    for fc in ('fuku5', 'fukud'):
        for s in bs:
            vs = [h[fc] for h in tr_h if h['style'] == s]
            if len(vs) > 30:
                st_tr[(fc, s)] = (statistics.mean(vs), statistics.pstdev(vs) or 1.0)

    # valid に適用
    for h in va_h:
        h['sogo_A2'] = h['sogo'] + off_tr.get(h['style'], 0.0)
        z = 0.0
        for fc in ('fuku5', 'fukud'):
            ms = st_tr.get((fc, h['style']))
            if ms:
                z += (h[fc] - ms[0]) / ms[1]
        h['sogo_B2'] = h['sogo_A2'] + z * 3.0

    print("train %dレース で補正値を作成 → valid %dレース で評価" % (len(tr_races), len(va_races)))
    print()
    print("%-28s %6s %8s %9s" % ("方式", "n", "1着率", "単勝回収"))
    print("-" * 60)
    vbase = None
    for key, lab in (('sogo', 'ベースライン（現行）'),
                     ('sogo_A2', '補正A 脚質の下駄を外す'),
                     ('sogo_B2', '補正B A＋複勝率を脚質内Z化')):
        tops = [max(hs, key=lambda r: r[key]) for hs in va_races]
        n, w, r = roi(tops)
        if vbase is None:
            vbase = (w, r)
            print("%-28s %6d %7.1f%% %8.1f%%" % (lab, n, w, r))
        else:
            print("%-28s %6d %7.1f%% %8.1f%%   （%+.1fpt / %+.1fpt）" %
                  (lab, n, w, r, w - vbase[0], r - vbase[1]))
    print()
    print("  ここで改善が再現すれば、補正は過学習ではなく本物。")


if __name__ == '__main__':
    main()
