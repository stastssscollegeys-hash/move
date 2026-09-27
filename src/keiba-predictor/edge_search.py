# -*- coding: utf-8 -*-
"""
edge_search.py — モデルが市場に勝てる条件を総当たりで探す（2026-08-30新設）
============================================================================
背景:
  事前予測（週末ビッグデータ records.json の総合指数）の単勝回収率は69.8%で、
  市場1番人気の85.3%に劣る。全体ではエッジがない。
  ただし「特定の条件下ではモデルが市場を上回る」可能性は残る。
  そこを総当たりで探し、過学習を排除して抽出するのが本スクリプト。

重要な設計（過学習対策）:
  ・**日付でtrain/validに分割**し、両方で基準を満たした条件だけを採用する。
    片方だけで回収率100%超なら偶然として棄却する（SKILL.md PDCA100で
    「大穴戦略はtrain545%もvalid0%で過学習として棄却」した実績と同じ手法）
  ・最低サンプル数を設ける（既定30頭）。少数セルの高回収率は偶然
  ・**事後スコア（race_results.jsonの独自指数）は一切使わない。**
    予測側は必ず records.json（レース前に計算された値）を使う

使い方:
  python edge_search.py                 # 既定（train=前半4開催 / valid=後半4開催）
  python edge_search.py --min-n 50      # 最低サンプル数を変える
"""
from __future__ import annotations
import json, argparse, itertools, collections
from pathlib import Path

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
RESULT_DB = BASE / 'daily_pdca' / 'db' / 'race_results.json'


# ══════════════════════════════════════════════════════════
def load_rows():
    """事前予測 × 結果 を結合した1頭1行のデータを作る"""
    db = json.load(open(RESULT_DB, encoding='utf-8'))
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
        # ── データ健全性フィルタ（2026-08-31追加）────────────────────
        # 過去分をバックフィルした際、スクレイプが途中で止まって一部の
        # レースしか取れていない日がある（5/16=10R・5/17=10R・5/30=24R）。
        # その日の一部だけを混ぜると開催・会場に偏りが出て集計が歪むため、
        # 1日あたり30レース未満しか無い日は丸ごと除外する（通常は36レース）。
        if len(by) < 30:
            continue
        for k, prs in by.items():
            rr = res.get(k)
            if not rr:
                continue
            prs.sort(key=lambda r: int(r.get('AI予測順位') or 99))
            n_head = len(prs)
            for p in prs:
                a = rr.get(p['馬名'])
                if not a:
                    continue
                odds = a.get('単勝オッズ')
                pop = a.get('人気')
                if not odds or not pop:
                    continue
                dist = str(p.get('距離') or '')
                surf = '芝' if '芝' in dist else ('ダート' if 'ダ' in dist else '他')
                try:
                    dm = int(''.join(ch for ch in dist if ch.isdigit()))
                except Exception:
                    dm = 0
                rows.append(dict(
                    date=k[0], venue=k[1], r=k[2],
                    rank=int(p.get('AI予測順位') or 99),
                    pop=int(pop), odds=float(odds), fin=a['着順int'],
                    n=n_head, surf=surf, dist=dm,
                    cls=race_class(p.get('レース名') or ''),
                    style=p.get('脚質') or '不明',
                    baba=a.get('馬場状態') or '不明',
                    ml=float(p.get('ML能力%') or 0),
                    sogo=float(p.get('総合指数') or 0),
                    dokuji=float(p.get('独自指数') or 0),
                ))
    return rows


def race_class(name):
    for key, lab in (('新馬', '新馬'), ('未勝利', '未勝利'), ('１勝', '1勝'), ('1勝', '1勝'),
                     ('２勝', '2勝'), ('2勝', '2勝'), ('３勝', '3勝'), ('3勝', '3勝')):
        if key in name:
            return lab
    return 'OP/特別'


# ══════════════════════════════════════════════════════════
def bucket(v, edges, labels):
    for e, l in zip(edges, labels):
        if v <= e:
            return l
    return labels[-1]


def add_buckets(rows):
    for r in rows:
        r['b_rank'] = ('1位' if r['rank'] == 1 else '2-3位' if r['rank'] <= 3
                       else '4-6位' if r['rank'] <= 6 else '7位以下')
        r['b_pop'] = ('1-3人気' if r['pop'] <= 3 else '4-6人気' if r['pop'] <= 6
                      else '7-9人気' if r['pop'] <= 9 else '10人気以下')
        r['b_n'] = bucket(r['n'], [10, 13, 16], ['〜10頭', '11-13頭', '14-16頭', '17頭〜'])
        r['b_dist'] = bucket(r['dist'], [1400, 1800, 2200], ['〜1400m', '1401-1800m', '1801-2200m', '2201m〜'])
        # モデル順位 − 市場人気（負＝モデルの方が高く買っている＝妙味候補）
        r['b_gap'] = ('モデル優位+5以上' if r['pop'] - r['rank'] >= 5
                      else 'モデル優位+2〜4' if r['pop'] - r['rank'] >= 2
                      else '一致±1' if abs(r['pop'] - r['rank']) <= 1
                      else '市場優位')
    return rows


AXES = ['b_rank', 'b_pop', 'b_n', 'b_dist', 'b_gap', 'venue', 'surf', 'cls', 'style', 'baba']


def stats(sub):
    n = len(sub)
    if n == 0:
        return None
    w = sum(1 for r in sub if r['fin'] == 1)
    ret = sum(r['odds'] * 100 for r in sub if r['fin'] == 1)
    t3 = sum(1 for r in sub if r['fin'] in (1, 2, 3))
    return dict(n=n, win=100 * w / n, roi=100 * ret / (n * 100), top3=100 * t3 / n)


def search(rows, min_n, max_axes=3):
    """1〜3軸の組み合わせを総当たりし、条件ごとの成績を返す"""
    out = {}
    for k in range(1, max_axes + 1):
        for axes in itertools.combinations(AXES, k):
            groups = collections.defaultdict(list)
            for r in rows:
                groups[tuple(r[a] for a in axes)].append(r)
            for key, sub in groups.items():
                if len(sub) < min_n:
                    continue
                cond = ' × '.join(f"{v}" for v in key)
                out[(axes, key)] = (cond, stats(sub))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-n', type=int, default=30, help='各条件の最低サンプル数（train/validそれぞれ）')
    ap.add_argument('--roi-min', type=float, default=100.0, help='採用する単勝回収率の下限%%')
    args = ap.parse_args()

    rows = add_buckets(load_rows())
    days = sorted({r['date'] for r in rows})
    half = len(days) // 2
    train_days, valid_days = set(days[:half]), set(days[half:])
    tr = [r for r in rows if r['date'] in train_days]
    va = [r for r in rows if r['date'] in valid_days]

    print("=" * 100)
    print("■ エッジ探索（モデルが市場に勝てる条件を総当たりで探す）")
    print("=" * 100)
    print("全データ: %d頭 / %d開催" % (len(rows), len(days)))
    print("  train : %s （%d頭）" % ('・'.join(sorted(train_days)), len(tr)))
    print("  valid : %s （%d頭）" % ('・'.join(sorted(valid_days)), len(va)))
    print("  条件: 単勝回収率%.0f%%以上 かつ train/valid 双方で%d頭以上" % (args.roi_min, args.min_n))
    print()

    base_all = stats(rows)
    base_pop1 = stats([r for r in rows if r['pop'] == 1])
    # 🔴訂正(2026-09-06): 「控除率20%だから理論値80%」は誤り。
    #   80%は**売上比例（オッズ比例）で買った場合の上限**であり、全馬に等額を張ると
    #   Favorite-Longshot Bias のぶん必然的に下回る。文献実測では単勝の等額買いは
    #   **71〜72.5%**（JRA平地1993-2025・芝72.51%/ダート71.69%）。
    #   基準線を80%だと思っていると、実力ゼロの構成を「善戦している」と誤読する。
    print("【比較基準】全馬 回収率%.1f%% ／ 市場1番人気 回収率%.1f%%"
          "（等額買いの基準線は71〜72.5%%。80%%はオッズ比例で買った場合の上限であり等額買いの基準ではない）"
          % (base_all['roi'], base_pop1['roi']))
    print()

    st = search(tr, args.min_n)
    sv = search(va, args.min_n)

    hits = []
    for key, (cond, s_tr) in st.items():
        if s_tr['roi'] < args.roi_min:
            continue
        pair = sv.get(key)
        if not pair:
            continue
        s_va = pair[1]
        if s_va['roi'] < args.roi_min:
            continue
        hits.append((key[0], cond, s_tr, s_va))

    if not hits:
        print("★ train/valid の両方で回収率%.0f%%以上を満たす条件は見つかりませんでした。" % args.roi_min)
        print("  → 現時点でモデルに再現性のあるエッジは確認できない、というのが結論です。")
    else:
        hits.sort(key=lambda x: -min(x[2]['roi'], x[3]['roi']))
        print("★ train/valid 双方で基準を満たした条件: %d件" % len(hits))
        print()
        print("%-46s %18s %18s" % ("条件", "train", "valid"))
        print("%-46s %5s %6s %6s %5s %6s %6s" % ("", "n", "勝率", "回収率", "n", "勝率", "回収率"))
        print("-" * 100)
        for axes, cond, a, b in hits[:30]:
            print("%-46s %5d %5.1f%% %5.0f%% %5d %5.1f%% %5.0f%%" % (
                cond[:46], a['n'], a['win'], a['roi'], b['n'], b['win'], b['roi']))

    # 参考: trainだけで良かった条件（過学習の例）
    only_tr = [(k[0], c, s) for k, (c, s) in st.items()
               if s['roi'] >= 150 and (k not in sv or sv[k][1]['roi'] < 80)]
    if only_tr:
        only_tr.sort(key=lambda x: -x[2]['roi'])
        print()
        print("【参考】trainでは良かったがvalidで崩れた条件（＝過学習。採用してはいけない例）")
        for axes, cond, s in only_tr[:8]:
            vs = sv.get(next((k for k in st if st[k][0] == cond), None))
            v = vs[1]['roi'] if vs else None
            print("  %-44s train %5.0f%% (n=%d) → valid %s" % (
                cond[:44], s['roi'], s['n'], ("%.0f%%" % v) if v is not None else "サンプル不足"))


if __name__ == '__main__':
    main()
