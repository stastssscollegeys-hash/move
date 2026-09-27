# -*- coding: utf-8 -*-
"""
payout_validate.py — Harville近似の誤差を実配当で測る（2026-09-02 新規）
=========================================================================
何を測るか
----------
買い目の期待値は「想定オッズ = 控除率 / Harville確率」で計算してきた。
この想定オッズが実際の配当とどれだけズレているかを、確定払戻データで検証する。

    ratio = 実際の配当 / Harville想定オッズ

  ratio > 1 → 近似は配当を**過小評価**している（実際はもっと付く＝EVを取りこぼしている）
  ratio < 1 → 近似は配当を**過大評価**している（実際は付かない＝EVを過信している）

市場確率 q は確定単勝オッズから作る（q_i ∝ 1/odds_i を正規化）。
つまり「単勝オッズだけ分かっている状態で連系の配当をどれだけ当てられるか」の検証であり、
予想時点で使える情報だけを使っている。

出力
----
券種ごとの ratio の中央値＝そのまま補正係数として使える。

使い方
------
  python payout_validate.py
  python payout_validate.py --min-races 300   # データが揃うまでの下限チェック
"""
from __future__ import annotations
import argparse, itertools, json, statistics, sys, io, collections
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'

TAKEOUT = {'単勝': 0.80, '複勝': 0.80, '馬連': 0.775, 'ワイド': 0.775,
           '馬単': 0.75, '3連複': 0.75, '3連単': 0.725}


def market_probs(odds: list[float]) -> list[float]:
    """確定単勝オッズ → 市場勝率（正規化）"""
    raw = [1.0 / o if o and o > 0 else 0.0 for o in odds]
    s = sum(raw)
    return [r / s for r in raw] if s > 0 else [1.0 / len(odds)] * len(odds)


def trifecta_table(p: list[float]) -> dict:
    """全3連単の確率を1回で作る（Harville）"""
    n = len(p)
    tab = {}
    for i in range(n):
        pi = p[i]
        d1 = 1.0 - pi
        if d1 <= 1e-9:
            continue
        for j in range(n):
            if j == i:
                continue
            pj = p[j]
            d2 = d1 - pj
            if d2 <= 1e-9:
                continue
            base = pi * pj / d1
            for k in range(n):
                if k == i or k == j:
                    continue
                tab[(i, j, k)] = base * p[k] / d2
    return tab


def load():
    pay = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    by = collections.defaultdict(list)
    for r in res:
        by[(r['date'], r['競馬場'], int(r['R']))].append(r)
    return pay, by


BANDS = [('~5倍', 0, 5), ('5-15倍', 5, 15), ('15-50倍', 15, 50),
         ('50-200倍', 50, 200), ('200倍~', 200, 1e9)]
# 帯の代表値（幾何中央）。payout_correction._X と対応させること
BAND_X = [3.0, 8.66, 27.4, 100.0, 400.0]
TICKET_ORDER = ['単勝', '複勝', '馬連', 'ワイド', '馬単', '3連複', '3連単']


def band_of(x: float) -> str:
    for name, lo, hi in BANDS:
        if lo <= x < hi:
            return name
    return BANDS[-1][0]


def collect_ratio_records(pay: dict, by: dict, dates: set | None = None):
    """各レースの「実配当 / Harville想定オッズ」を集める。

    dates を渡すとその日付だけに限定する（train/valid分割用）。
    戻り値: (recs, 使用レース数)。recs = [(券種, 想定オッズ, 実配当, 日付), ...]
    """
    recs: list[tuple] = []
    used = 0

    for rid, v in pay.items():
        if dates is not None and v['date'] not in dates:
            continue
        rows = by.get((v['date'], v['venue'], v['R']))
        if not rows:
            continue
        # 単勝オッズが揃っている馬のみ
        rows = [r for r in rows if r.get('単勝オッズ') and r.get('馬番')]
        if len(rows) < 6:
            continue
        num2i = {}
        odds = []
        for i, r in enumerate(rows):
            num2i[str(int(float(r['馬番'])))] = i
            odds.append(float(r['単勝オッズ']))
        q = market_probs(odds)
        tab = trifecta_table(q)
        n = len(rows)

        # 着順1-3位
        fin = sorted([r for r in rows if r.get('着順int')], key=lambda r: r['着順int'])
        if len(fin) < 3:
            continue
        top3 = [str(int(float(r['馬番']))) for r in fin[:3]]
        if any(t not in num2i for t in top3):
            continue
        i1, i2, i3 = (num2i[t] for t in top3)

        # --- 各券種の的中確率を Harville で算出 ---
        est = {}
        est['単勝'] = q[i1]
        # 複勝: その馬が3着以内（8頭立て未満は2着以内だが払戻表側の実態に合わせ3着内で近似）
        place = collections.defaultdict(float)
        wide = collections.defaultdict(float)
        for (a, b, c), pr in tab.items():
            for x in (a, b, c):
                place[x] += pr
            wide[tuple(sorted((a, b)))] += pr
            wide[tuple(sorted((a, c)))] += pr
            wide[tuple(sorted((b, c)))] += pr
        est['複勝'] = place[i1]
        est['馬単'] = sum(pr for (a, b, c), pr in tab.items() if a == i1 and b == i2)
        est['馬連'] = est['馬単'] + sum(pr for (a, b, c), pr in tab.items() if a == i2 and b == i1)
        est['ワイド'] = wide[tuple(sorted((i1, i2)))]
        est['3連単'] = tab.get((i1, i2, i3), 0.0)
        est['3連複'] = sum(tab.get(pm, 0.0) for pm in itertools.permutations((i1, i2, i3)))

        # --- 実配当と突き合わせ ---
        hit = False
        for tname, prob in est.items():
            rows_p = v['payouts'].get(tname)
            if not rows_p or prob <= 1e-9:
                continue
            # 該当する組み合わせの払戻を選ぶ
            target = None
            if tname == '複勝':
                for x in rows_p:
                    if x['combo'] == top3[0]:
                        target = x
                        break
            elif tname == 'ワイド':
                want = {top3[0], top3[1]}
                for x in rows_p:
                    if set(x['combo'].split('-')) == want:
                        target = x
                        break
            else:
                target = rows_p[0]
            if not target:
                continue
            actual = target['yen'] / 100.0
            est_odds = TAKEOUT[tname] / prob
            if est_odds <= 0:
                continue
            recs.append((tname, est_odds, actual, v['date']))
            hit = True
        if hit:
            used += 1
    return recs, used


def band_medians(recs: list[tuple], min_n: int = 20) -> dict:
    """(券種, 帯) → ratio中央値。想定オッズで層別する（賭ける時点で分かる情報）。"""
    out = {}
    for t in TICKET_ORDER:
        for bname, _, _ in BANDS:
            sel = [a / e for (tt, e, a, d) in recs
                   if tt == t and band_of(e) == bname]
            if len(sel) >= min_n:
                out[(t, bname)] = statistics.median(sel)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-races', type=int, default=0)
    args = ap.parse_args()

    pay, by = load()
    print("=" * 92)
    print(f"■ Harville近似 vs 実配当（払戻DB {len(pay)}レース）")
    print("=" * 92)

    recs, used = collect_ratio_records(pay, by)

    print(f"検証できたレース: {used}")
    if used < args.min_races:
        print(f"⚠ {args.min_races}レース未満のため参考値")

    order = TICKET_ORDER

    def report(rows: list[tuple], title: str, by_est: bool = True) -> dict:
        """rows=(券種, est, actual, date)。by_est=True なら想定オッズで層別する。
        戻り値: {(券種, 帯): 補正係数}"""
        print()
        print("■ " + title)
        hdr = "".join(f"{b[0]:>12s}" for b in BANDS)
        print(f"{'券種':6s}{hdr}")
        print("-" * 92)
        out = {}
        for t in order:
            cells = []
            for bname, _, _ in BANDS:
                sel = [a / e for (tt, e, a, d) in rows
                       if tt == t and band_of(e if by_est else a) == bname]
                if len(sel) >= 20:
                    m = statistics.median(sel)
                    out[(t, bname)] = m
                    cells.append(f"{m:.2f}({len(sel)})")
                else:
                    cells.append("-")
            print(f"{t:6s}" + "".join(f"{c:>12s}" for c in cells))
        return out

    # ── 本命の分析: 想定オッズで層別（賭ける時点で分かる情報だけで層別する）──
    coef = report(recs, "【本命】想定オッズ帯ごとの ratio 中央値（＝そのまま補正係数）", by_est=True)

    print()
    print("  ratio<1 = 実際はその想定オッズほど付かない → 期待値を過大評価している")
    print("  ratio>1 = 想定より多く付く → 期待値を取りこぼしている")

    # ── 参考: 実配当で層別（選択バイアスがあるので判断には使わない）──
    report(recs, "【参考】実配当で層別した場合（結果を見てから分類＝選択バイアスあり・判断に使わない）",
           by_est=False)

    # ── 頑健性1: 期間3分割 ──
    dates = sorted({d for (_, _, _, d) in recs})
    th = len(dates) // 3
    seg = {d: (0 if i < th else 1 if i < 2 * th else 2) for i, d in enumerate(dates)}
    print()
    print("■ 頑健性①: 期間3分割（前期／中期／後期で同じ傾向が出るか）")
    print(f"{'券種':6s}{'帯':>12s}{'前期':>10s}{'中期':>10s}{'後期':>10s}   一貫性")
    print("-" * 92)
    for t in order:
        for bname, _, _ in BANDS:
            if (t, bname) not in coef:
                continue
            ms = []
            for s in (0, 1, 2):
                sel = [a / e for (tt, e, a, d) in recs
                       if tt == t and band_of(e) == bname and seg[d] == s]
                ms.append(statistics.median(sel) if len(sel) >= 8 else None)
            if any(m is None for m in ms):
                continue
            ok = "OK" if (all(m < 1.0 for m in ms) or all(m >= 1.0 for m in ms)) else "△ばらつく"
            print(f"{t:6s}{bname:>12s}" + "".join(f"{m:>10.2f}" for m in ms) + f"   {ok}")

    # ── 頑健性2: 実配当 上位1%を除外（大穴1本依存でないか）──
    print()
    print("■ 頑健性②: 実配当の上位1%を除外しても同じか（大穴依存の排除）")
    trimmed = []
    for t in order:
        sub = [r for r in recs if r[0] == t]
        if not sub:
            continue
        cut = sorted(r[2] for r in sub)[int(len(sub) * 0.99)]
        trimmed += [r for r in sub if r[2] < cut]
    tr = report(trimmed, "上位1%除外後の ratio 中央値", by_est=True)
    print()
    print(f"{'券種':6s}{'帯':>12s}{'全体':>10s}{'除外後':>10s}   差")
    print("-" * 92)
    for (t, b), m in coef.items():
        if (t, b) in tr:
            d = tr[(t, b)] - m
            print(f"{t:6s}{b:>12s}{m:>10.2f}{tr[(t,b)]:>10.2f}   {d:+.2f}"
                  + ("   ★大穴依存の疑い" if abs(d) > 0.15 else ""))

    # ── 補正係数をJSONで書き出す ──
    out_path = DB / 'payout_correction.json'
    payload = {"generated": "payout_validate.py",
               "races": used,
               "note": "想定オッズ帯ごとの 実配当/Harville想定オッズ の中央値。想定オッズに掛けて使う",
               "bands": [[b[0], b[1], b[2] if b[2] < 1e8 else None] for b in BANDS],
               "coef": {f"{t}|{b}": round(v, 4) for (t, b), v in coef.items()}}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print()
    print(f"補正係数を書き出しました → {out_path}")


if __name__ == '__main__':
    main()
