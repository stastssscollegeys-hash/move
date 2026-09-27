# -*- coding: utf-8 -*-
"""
ticket_mix_test.py — 券種構成の差をペアード検定する（2026-09-02）
==================================================================
engine_backtest.py の券種制限は、条件ごとに独立した信頼区間を出しているため
区間が大きく重なって見える。しかし**同じレースを共有した比較**なので、
「差」そのものをブートストラップすれば遥かに鋭く判定できる。

  各ブートストラップ標本で同じレース集合を使い、ROI(A) − ROI(B) を計算し、
  その分布の95%区間が0を含まなければ「差がある」と言える。

併せて、エンジンが実際にどの券種をどれだけ使っているかを集計する。

使い方:
  python ticket_mix_test.py
"""
from __future__ import annotations
import collections, random, statistics, sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B

ALL = {'単勝', '複勝', '馬連', 'ワイド', '馬単', '3連複', '3連単'}
BUDGET = 10000
BOOT = 4000

CONDS = [
    ('現行（全券種）',            None),
    ('3連複を除く',              ALL - {'3連複'}),
    ('ワイド・馬連のみ',          {'ワイド', '馬連'}),
    ('ワイド・馬連・3連複のみ',    {'ワイド', '馬連', '3連複'}),
    ('ワイドのみ',               {'ワイド'}),
]


def usage(races):
    """エンジンが選ぶ買い目の券種内訳（点数ベース・金額ベース）。"""
    pts = collections.Counter()
    amt = collections.Counter()
    for key, d in races.items():
        recs = [dict(r) for r in d['recs']]
        B.style_correction.apply_style_correction(recs, enabled=True)
        for r in recs:
            r['AI印'] = B.RANK_TO_MARK.get(r.get('AI予測順位'), '')
        try:
            out = B.G.choose_pattern(recs, BUDGET, odds_override=d['odds'])
        except Exception:
            continue
        res = out[2]
        if not res:
            continue
        for bt, _i, a, _o in res['bets']:
            pts[bt] += 1
            amt[bt] += a
    return pts, amt


def main():
    races = B.drop_leaky(B.load_races(), verbose=False)
    keys = list(races.keys())
    print("=" * 92)
    print(f"■ 券種構成の検証（汚染なし {len(keys)}レース・脚質補正ON）")
    print("=" * 92)

    # ── エンジンが実際に使っている券種 ──
    pts, amt = usage(races)
    tot_p, tot_a = sum(pts.values()) or 1, sum(amt.values()) or 1
    print()
    print("【エンジンが実際に選んでいる券種】")
    print(f"{'券種':>8s} {'点数':>8s} {'点数比':>8s} {'金額':>12s} {'金額比':>8s}")
    print("-" * 92)
    for bt, _ in sorted(amt.items(), key=lambda x: -x[1]):
        print(f"{bt:>8s} {pts[bt]:8d} {100*pts[bt]/tot_p:7.1f}% "
              f"{amt[bt]:12,d} {100*amt[bt]/tot_a:7.1f}%")

    # ── 各条件のレース別 (投資, 払戻) を1回だけ計算して保持 ──
    per = {}
    for label, allow in CONDS:
        rows = B.run_engine_types(races, BUDGET, allow)
        per[label] = {k: (i, r) for k, i, r in rows}

    def roi_of(label, sample):
        inv = ret = 0.0
        d = per[label]
        for k in sample:
            i, r = d.get(k, (0, 0))
            inv += i
            ret += r
        return ret / inv if inv > 0 else 0.0

    print()
    print("【ペアード検定】現行との差（同じレースで比較・ブートストラップ%d回）" % BOOT)
    print(f"{'条件':>22s} {'回収率':>9s} {'現行との差':>11s} {'差の95%区間':>20s}  判定")
    print("-" * 92)
    base = roi_of('現行（全券種）', keys)
    rng = random.Random(7)
    samples = [[keys[rng.randrange(len(keys))] for _ in range(len(keys))] for _ in range(BOOT)]
    for label, _ in CONDS:
        r = roi_of(label, keys)
        if label == '現行（全券種）':
            print(f"{label:>22s} {100*r:8.1f}% {'—':>11s} {'—':>20s}  基準")
            continue
        diffs = sorted(roi_of(label, s) - roi_of('現行（全券種）', s) for s in samples)
        lo, hi = diffs[int(0.025 * BOOT)], diffs[int(0.975 * BOOT)]
        if lo > 0:
            j = "★現行より有意に良い"
        elif hi < 0:
            j = "現行より有意に悪い"
        else:
            j = "差があるとは言えない"
        print(f"{label:>22s} {100*r:8.1f}% {100*(r-base):+10.1f}pt "
              f"{'[%+.1f〜%+.1f pt]' % (100*lo, 100*hi):>20s}  {j}")

    print()
    print("※ 独立した信頼区間の重なりでは判定できないが、同じレースでの差なら判定できる。")

    # ================================================================
    # 頑健性3点セット（偽エッジを3回踏んだ反省から確立した必須手順）
    # ================================================================
    TARGET = '3連複を除く'
    print()
    print("=" * 92)
    print(f"■ 頑健性検証: 「{TARGET}」は本物か（5条件を探索した結果なので必須）")
    print("=" * 92)

    def paired(sub_keys, label, n_boot=3000):
        if len(sub_keys) < 30:
            print(f"{label:>26s}  レース数不足({len(sub_keys)})")
            return
        b = roi_of('現行（全券種）', sub_keys)
        t = roi_of(TARGET, sub_keys)
        r2 = random.Random(11)
        ds = sorted(
            roi_of(TARGET, s) - roi_of('現行（全券種）', s)
            for s in ([sub_keys[r2.randrange(len(sub_keys))] for _ in range(len(sub_keys))]
                      for _ in range(n_boot)))
        lo, hi = ds[int(0.025 * n_boot)], ds[int(0.975 * n_boot)]
        mark = "★維持" if lo > 0 else ("消滅" if hi < 0 else "△判定不能")
        print(f"{label:>26s} {len(sub_keys):5d}R  現行{100*b:6.1f}% → {100*t:6.1f}% "
              f"({100*(t-b):+6.1f}pt)  [{100*lo:+.1f}〜{100*hi:+.1f}]  {mark}")

    print(f"{'区分':>26s} {'R数':>6s}  {'現行 → 3連複除外':>26s}  {'差の95%区間':>18s}  判定")
    print("-" * 92)
    paired(keys, "全期間")

    # ① 期間分割（3分割は1区分が115Rと小さいので2分割も併記）
    dates = sorted({k[0] for k in keys})
    h = len(dates) // 2
    paired([k for k in keys if k[0] in set(dates[:h])], "① 前半")
    paired([k for k in keys if k[0] not in set(dates[:h])], "① 後半")
    t3 = len(dates) // 3
    for i, (lo_i, hi_i) in enumerate([(0, t3), (t3, 2 * t3), (2 * t3, len(dates))]):
        seg = set(dates[lo_i:hi_i])
        paired([k for k in keys if k[0] in seg], f"① 3分割{i+1}")

    # ② 大穴依存の排除（払戻が大きいレースを除く）
    by_ret = sorted(keys, key=lambda k: -max(per['現行（全券種）'].get(k, (0, 0))[1],
                                             per[TARGET].get(k, (0, 0))[1]))
    for cut in (1, 3, 5):
        paired(by_ret[cut:], f"② 高配当{cut}レース除外")

    # ③ 条件の動かし方（3連複を減らす別の方法でも同じ向きに出るか）
    print()
    print("③ 3連複を使う構成と使わない構成で差が出るか")
    print(f"{'条件':>26s} {'回収率':>9s} {'現行との差':>11s}  3連複")
    print("-" * 92)
    USES_3F = {'現行（全券種）': True, '3連複を除く': False, 'ワイド・馬連のみ': False,
               'ワイド・馬連・3連複のみ': True, 'ワイドのみ': False}
    for label, _ in CONDS:
        if label == '現行（全券種）':
            continue
        r = roi_of(label, keys)
        print(f"{label:>26s} {100*r:8.1f}% {100*(r-base):+10.1f}pt  "
              f"{'使う' if USES_3F[label] else '使わない'}")

    # ── メカニズム検証: エンジンの3連複は高オッズ帯に偏っているか ──
    # 今日の測定で 3連複は想定オッズ200倍超で実配当が想定の0.54倍しか付かない。
    # エンジンの3連複がその帯に偏っているなら、除外が効く理由が説明できる。
    print()
    print("■ メカニズム: エンジンが買う券種の想定オッズ分布")
    print("   （3連複は200倍超で実配当が想定の0.54倍。そこに偏っていれば除外が効く理由になる）")
    odds_by = collections.defaultdict(list)
    for key, d in races.items():
        recs = [dict(r) for r in d['recs']]
        B.style_correction.apply_style_correction(recs, enabled=True)
        for r in recs:
            r['AI印'] = B.RANK_TO_MARK.get(r.get('AI予測順位'), '')
        try:
            res = B.G.choose_pattern(recs, BUDGET, odds_override=d['odds'])[2]
        except Exception:
            continue
        if res:
            for bt, _i, _a, o in res['bets']:
                odds_by[bt].append(o)
    print(f"{'券種':>8s} {'点数':>7s} {'中央値':>9s} {'50倍超':>9s} {'200倍超':>9s}")
    print("-" * 92)
    for bt in ('ワイド', '3連複', '馬連', '単勝'):
        v = odds_by.get(bt)
        if not v:
            continue
        print(f"{bt:>8s} {len(v):7d} {statistics.median(v):8.1f}倍 "
              f"{100*sum(1 for x in v if x > 50)/len(v):8.1f}% "
              f"{100*sum(1 for x in v if x > 200)/len(v):8.1f}%")

    print()
    print("【判定基準】①全区分で符号が同じ ②高配当を除いても残る ③3連複を使わない構成が")
    print("　　　　　　 揃って上に来る、の3つが揃って初めて採用を検討する。")


if __name__ == '__main__':
    main()
