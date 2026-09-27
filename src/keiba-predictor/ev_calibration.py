# -*- coding: utf-8 -*-
"""
ev_calibration.py — 期待値の較正検証（2026-09-02 新規）
========================================================
「モデルが言う期待値」と「実際の回収率」が一致するかを、確定払戻で直接測る。

    予測EV = モデル的中確率 x 想定オッズ
    実測ROI = 実際に当たった配当の合計 / 賭け金の合計

予測EVが1.5なら実測ROIも150%になるはずで、そうならなければ期待値が壊れている。
payout_correction を入れる前と後で、この一致度がどう変わるかを比較する。

これが補正の可否を決める唯一の判断材料。「想定オッズが下がった」だけでは意味がなく、
**EVの較正が良くなったか**で判断する。

使い方:
  python ev_calibration.py
  python ev_calibration.py --top 6      # 候補を絞る頭数
"""
from __future__ import annotations
import argparse, collections, itertools, json, sys, io, statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import payout_correction
import gen_kaime_v5 as G

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
DB = BASE / 'daily_pdca' / 'db'


def market_probs(odds):
    raw = [1.0 / o if o and o > 0 else 0.0 for o in odds]
    s = sum(raw)
    return [r / s for r in raw] if s > 0 else [1.0 / len(odds)] * len(odds)


def hit_and_payout(bt, nums, pay, top3):
    """その買い目が的中したか、した場合の配当（倍）を返す。"""
    rows = pay.get(bt)
    if not rows:
        return None
    s = set(nums)
    if bt == '馬連':
        if s != set(top3[:2]):
            return 0.0
        return rows[0]['yen'] / 100.0
    if bt == 'ワイド':
        if not s <= set(top3):
            return 0.0
        for x in rows:
            if set(x['combo'].split('-')) == s:
                return x['yen'] / 100.0
        return 0.0
    if bt == '3連複':
        if s != set(top3):
            return 0.0
        return rows[0]['yen'] / 100.0
    if bt == '3連単':
        if list(nums) != list(top3):
            return 0.0
        return rows[0]['yen'] / 100.0
    return None


def make_interpolator(coef: dict):
    """{(券種,帯): 係数} → apply(btype, odds) 相当の関数を作る（train期間の値で補正するため）"""
    import payout_validate as PV
    tbl = {}
    for t in PV.TICKET_ORDER:
        pts = [(x, coef[(t, b[0])]) for x, b in zip(PV.BAND_X, PV.BANDS)
               if (t, b[0]) in coef]
        if pts:
            tbl[t] = pts

    def f(bt, odds):
        pts = tbl.get(bt)
        if not pts:
            return odds
        if len(pts) == 1:
            c = pts[0][1]
        else:
            import math
            lx = math.log(max(odds, 1.01))
            if lx <= math.log(pts[0][0]):
                c = pts[0][1]
            elif lx >= math.log(pts[-1][0]):
                c = pts[-1][1]
            else:
                c = pts[-1][1]
                for (x0, c0), (x1, c1) in zip(pts, pts[1:]):
                    if math.log(x0) <= lx <= math.log(x1):
                        tt = (lx - math.log(x0)) / (math.log(x1) - math.log(x0))
                        c = c0 + tt * (c1 - c0)
                        break
        c = min(1.60, max(0.50, c))
        return max(1.1, odds * c)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=7)
    ap.add_argument('--split', action='store_true',
                    help='前半で補正値を作り後半だけで評価する（out-of-sample検証）')
    args = ap.parse_args()

    payouts = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    res_by = collections.defaultdict(list)
    for r in res:
        res_by[(r['date'], r['競馬場'], int(r['R']))].append(r)

    # 事前予測レコード
    pre_by = {}
    for f in sorted(BASE.glob('**/週末ビッグデータ_*_records.json')):
        try:
            data = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        for r in data.get('records', []):
            pre_by.setdefault((r['date'], r['競馬場'], int(r['R'])), []).append(r)

    # out-of-sample: 前半の日付だけで補正値を作り、後半の評価に使う
    corr_fn = None
    valid_dates = None
    if args.split:
        import payout_validate as PV
        all_dates = sorted({v['date'] for v in payouts.values()})
        half = len(all_dates) // 2
        train_d, valid_d = set(all_dates[:half]), set(all_dates[half:])
        valid_dates = valid_d
        pv_pay, pv_by = PV.load()
        tr_recs, tr_used = PV.collect_ratio_records(pv_pay, pv_by, dates=train_d)
        coef = PV.band_medians(tr_recs)
        corr_fn = make_interpolator(coef)
        print(f"[out-of-sample] train {len(train_d)}日/{tr_used}レースで補正値を算出 "
              f"→ valid {len(valid_d)}日で評価")
        print(f"  train由来の係数（抜粋）: "
              f"3連複200倍~={coef.get(('3連複','200倍~')):.2f} / "
              f"ワイド50-200倍={coef.get(('ワイド','50-200倍')):.2f}")
        print()

    # bets: (券種, EV_raw, EV_cor, 実配当倍率)
    bets = []
    used = 0
    for rid, v in payouts.items():
        if valid_dates is not None and v['date'] not in valid_dates:
            continue
        key = (v['date'], v['venue'], v['R'])
        recs = pre_by.get(key)
        rows = res_by.get(key)
        if not recs or not rows or len(recs) < 8:
            continue
        # 馬番→確定オッズ・着順
        info = {}
        for r in rows:
            try:
                info[str(int(float(r['馬番'])))] = (float(r['単勝オッズ']), r.get('着順int'))
            except (TypeError, ValueError):
                continue
        nums = []
        odds = []
        ok = True
        for r in recs:
            n = str(r.get('馬番') or '')
            try:
                n = str(int(float(n)))
            except ValueError:
                ok = False
                break
            if n not in info:
                ok = False
                break
            nums.append(n)
            odds.append(info[n][0])
        if not ok or len(nums) < 8:
            continue
        fin = sorted([(n, info[n][1]) for n in info if info[n][1]], key=lambda x: x[1])
        if len(fin) < 3:
            continue
        top3 = [fin[0][0], fin[1][0], fin[2][0]]

        try:
            p = G.model_probs(recs)
        except Exception:
            continue
        q = market_probs(odds)
        n = len(recs)
        idx = sorted(range(n), key=lambda i: -q[i])[:args.top]

        cand = []
        cand += [('馬連', c) for c in itertools.combinations(idx[:6], 2)]
        cand += [('ワイド', c) for c in itertools.combinations(idx[:6], 2)]
        cand += [('3連複', c) for c in itertools.combinations(idx, 3)]
        cand += [('3連単', c) for c in itertools.permutations(idx[:5], 3)]

        for bt, hs in cand:
            pb = G.bet_prob(p, bt, hs)
            qb = G.bet_prob(q, bt, hs)
            if pb <= 1e-9 or qb <= 1e-9:
                continue
            raw = max(1.1, G.TAKEOUT[bt] / qb)
            cor = corr_fn(bt, raw) if corr_fn else payout_correction.apply(bt, raw, enabled=True)
            got = hit_and_payout(bt, [nums[i] for i in hs], v['payouts'], top3)
            if got is None:
                continue
            bets.append((bt, pb * raw, pb * cor, got))
        used += 1

    print("=" * 96)
    print(f"■ 期待値の較正検証（{used}レース / 候補{len(bets):,}点）")
    print("=" * 96)
    print("予測EVが正しければ、そのEV帯の実測ROIは予測値と一致するはず。")
    print()

    BUCKETS = [(0.0, 0.8), (0.8, 1.0), (1.0, 1.15), (1.15, 1.4), (1.4, 2.0), (2.0, 99)]

    def calib(which: int, label: str):
        print(f"■ {label}")
        print(f"{'予測EV帯':>12s} {'点数':>9s} {'予測EV平均':>11s} {'実測ROI':>10s} {'誤差':>9s}")
        print("-" * 96)
        rows_out = []
        for lo, hi in BUCKETS:
            sel = [b for b in bets if lo <= b[which] < hi]
            if len(sel) < 200:
                continue
            pred = statistics.mean(b[which] for b in sel)
            roi = sum(b[3] for b in sel) / len(sel)
            rows_out.append((pred, roi, len(sel)))
            name = f"{lo:.2f}-{hi:.2f}" if hi < 90 else f"{lo:.2f}+"
            print(f"{name:>12s} {len(sel):9,d} {pred:11.2f} {roi:10.2f} {roi-pred:+9.2f}")
        # 較正誤差（点数で重み付けした絶対誤差）
        tot = sum(r[2] for r in rows_out)
        mae = sum(abs(r[1] - r[0]) * r[2] for r in rows_out) / tot if tot else 0
        print(f"{'加重平均絶対誤差':>12s} {mae:.3f}")
        return mae

    mae_raw = calib(1, "補正なし（従来のHarville想定オッズ）")
    print()
    mae_cor = calib(2, "補正あり（payout_correction v6.1）")

    print()
    print("=" * 96)
    print(f"較正誤差  補正なし {mae_raw:.3f} → 補正あり {mae_cor:.3f}  "
          f"（{100*(mae_cor/mae_raw-1):+.1f}%）")
    print("★ 補正ありの方が小さければ、期待値が実測に近づいた＝補正は正しい")

    # 実運用の判断: EV>=1.15 で買った場合の実測ROI
    print()
    print("=" * 96)
    print("■ 実運用に直結する比較: 「EV>=1.15 なら買う」で選ばれた点の実測ROI")
    print("=" * 96)
    print(f"{'方式':>16s} {'選ばれた点数':>13s} {'実測ROI':>10s}")
    print("-" * 96)
    base = sum(b[3] for b in bets) / len(bets) if bets else 0
    print(f"{'【基準線】全候補を機械的に買う':>16s} {len(bets):13,d} {100*base:9.1f}%")
    for bt in ('馬連', 'ワイド', '3連複', '3連単'):
        sub = [b for b in bets if b[0] == bt]
        if sub:
            print(f"{'  └ ' + bt:>16s} {len(sub):13,d} "
                  f"{100*sum(b[3] for b in sub)/len(sub):9.1f}%")
    for which, label in ((1, "補正なし"), (2, "補正あり")):
        sel = [b for b in bets if b[which] >= 1.15]
        if sel:
            roi = sum(b[3] for b in sel) / len(sel)
            print(f"{label:>16s} {len(sel):13,d} {100*roi:9.1f}%")
    print()
    print("券種別（EV>=1.15で選ばれた点の実測ROI）")
    print(f"{'券種':6s} {'補正なし点数':>12s} {'ROI':>8s} {'補正あり点数':>13s} {'ROI':>8s}")
    print("-" * 96)
    for bt in ('馬連', 'ワイド', '3連複', '3連単'):
        line = [bt]
        for which in (1, 2):
            sel = [b for b in bets if b[0] == bt and b[which] >= 1.15]
            if sel:
                line.append(f"{len(sel):,}")
                line.append(f"{100*sum(b[3] for b in sel)/len(sel):.1f}%")
            else:
                line += ["0", "-"]
        print(f"{line[0]:6s} {line[1]:>12s} {line[2]:>8s} {line[3]:>13s} {line[4]:>8s}")


if __name__ == '__main__':
    main()
