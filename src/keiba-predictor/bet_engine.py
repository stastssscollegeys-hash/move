# -*- coding: utf-8 -*-
"""
bet_engine.py — 全券種から期待値で買い目を組む（レースごとに目標配当を変える）（2026-10-02新規）
==============================================================================================
ユーザー指示（2026-10-02）: 単勝・複勝・馬連・ワイド・馬単・3連複・3連単のすべてを期待値で検討し、
  レースごとに「当たったときの配当の目安」を変える。基本は予算の300〜500%、荒れそうなら1000%超、堅ければ200%前後。
  年間を通して収支がプラスになる形にする。目標は年間回収率120%。

設計
  1. 確率  : ev_engine の年ごとの前向きモデル p と、市場（単勝オッズ）の q。どちらも全頭λ-Harvilleで各券種の組み合わせ確率にする。
  2. 候補  : 各券種で「モデル確率／市場確率 ≧ しきい値」かつ「市場確率 ≧ 下限」の組。期待値(推定)＝払戻率×比。
  3. 型    : レースを3つに分け、当たったときの目標倍率 T を決める（市場の本命の強さで判定）
             堅い  （1番人気の市場確率≧0.35）: T=2.5   ／ 普通: T=4.0   ／ 荒れ（1番人気の市場確率<0.20）: T=8.0
  4. 配分  : 比の高い組から順に、Σ(1/オッズ) が 1/T になるまで足す。各組の賭け金は 1/オッズ に比例（どれが当たっても戻りが揃う）。
             → 当たれば予算のおよそ T 倍が戻る。期待回収率＝(Σ組のモデル確率)×T。100円単位。
  5. 見送り: 候補が足りない／期待回収率が EV_MIN 未満のレースは買わない。
注意: 過去には「当たった組の払戻」しか残っていない。賭け金の配分は **オッズ＝払戻率÷市場確率** で決め、精算は **確定払戻**。
      実際のオッズは市場確率とずれる（特に3連単の人気薄）ので、本番は発売中のオッズ（O1〜O6）で配分し直す。
使い方: python bet_engine.py [--budget 10000]   # 前向き予測（db/ev_walk_pred.pkl）で全期間を検証
"""
from __future__ import annotations
import argparse, collections, itertools, json, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C

TAKE = {"単勝": 0.80, "複勝": 0.80, "馬連": 0.775, "ワイド": 0.775, "馬単": 0.75, "3連複": 0.75, "3連単": 0.725}
MINQ = {"単勝": 0.03, "複勝": 0.10, "馬連": 0.03, "ワイド": 0.08, "馬単": 0.02, "3連複": 0.01, "3連単": 0.002}
TYPES = tuple(TAKE)
CAND_RATIO = 1.15                         # 候補として保存する最低の比
LAM = C.LAM


def tensor(p):
    n = len(p)
    w2, w3 = p ** LAM[1], p ** LAM[2]
    S2, S3 = w2.sum(), w3.sum()
    T = np.zeros((n, n, n))
    d2 = S2 - w2
    for a in range(n):
        d3 = S3 - w3[a] - w3                       # b ごとの分母
        for b in range(n):
            if a == b or d3[b] <= 1e-12:
                continue
            row = p[a] * w2[b] / d2[a] * w3 / d3[b]
            row[a] = row[b] = 0.0
            T[a, b] = row
    return T


def tables(p, uma):
    """{券種: (キーのリスト, 確率の配列)}"""
    n = len(p)
    T = tensor(p)
    out = {}
    out["単勝"] = ([(u,) for u in uma], p.copy())
    out["複勝"] = ([(u,) for u in uma], T.sum(axis=(1, 2)) + T.sum(axis=(0, 2)) + T.sum(axis=(0, 1)))
    S2, S1, S0 = T.sum(2), T.sum(1), T.sum(0)
    ia, ib = np.triu_indices(n, 1)
    out["馬連"] = ([tuple(sorted((uma[a], uma[b]))) for a, b in zip(ia, ib)], S2[ia, ib] + S2[ib, ia])
    out["ワイド"] = ([tuple(sorted((uma[a], uma[b]))) for a, b in zip(ia, ib)], (S2 + S2.T + S1 + S1.T + S0 + S0.T)[ia, ib])
    ja, jb = np.where(~np.eye(n, dtype=bool))
    out["馬単"] = ([(uma[a], uma[b]) for a, b in zip(ja, jb)], S2[ja, jb])
    tri = np.array(list(itertools.combinations(range(n), 3)))
    if len(tri):
        a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
        out["3連複"] = ([tuple(sorted((uma[x], uma[y], uma[z]))) for x, y, z in tri], T[a, b, c] + T[a, c, b] + T[b, a, c] + T[b, c, a] + T[c, a, b] + T[c, b, a])
        ta, tb, tc = np.where(T > 0)
        out["3連単"] = ([(uma[x], uma[y], uma[z]) for x, y, z in zip(ta, tb, tc)], T[ta, tb, tc])
    return out


def race_candidates(p, q, uma):
    """比≧CAND_RATIO・市場確率≧下限の組を、(券種, キー, モデル確率, 市場確率) で返す"""
    tm, tq = tables(p, uma), tables(q, uma)
    cands = []
    for t in TYPES:
        if t not in tm:
            continue
        keys, pm = tm[t]
        _, pq = tq[t]
        ok = (pq >= MINQ[t]) & (pm >= CAND_RATIO * pq)
        for i in np.where(ok)[0]:
            cands.append((t, keys[i], float(pm[i]), float(pq[i])))
    return cands


def race_kind(q):
    top = float(np.max(q))
    return "堅い" if top >= 0.35 else "荒れ" if top < 0.20 else "普通"


def design(cands, kind, budget, thr, target=None, ev_min=1.10, max_pts=12, take_scale=1.0):
    """候補から買い目を組む。戻り値: [(券種, キー, 賭け金, オッズ(推定), モデル確率)]、期待回収率、当たる確率の目安"""
    T = target or {"堅い": 2.5, "普通": 4.0, "荒れ": 8.0}[kind]
    cs = sorted((c for c in cands if c[2] / c[3] >= thr), key=lambda c: -(c[2] / c[3]))
    chosen, S = [], 0.0
    for t, k, pm, pq in cs:
        o = TAKE[t] * take_scale / pq
        if S + 1.0 / o > 1.0 / T * 1.15 and chosen:
            continue
        chosen.append((t, k, pm, pq, o))
        S += 1.0 / o
        if S >= 1.0 / T or len(chosen) >= max_pts:
            break
    if not chosen:
        return [], 0.0, 0.0
    w = np.array([1.0 / c[4] for c in chosen])
    amt = np.floor(budget * w / w.sum() / 100.0) * 100.0
    keep = amt >= 100
    chosen = [c for c, kp in zip(chosen, keep) if kp]
    amt = amt[keep]
    if not len(chosen):
        return [], 0.0, 0.0
    exp = sum(a * c[2] * c[4] for a, c in zip(amt, chosen)) / amt.sum()          # 賭け金あたりの期待戻り
    if exp < ev_min:
        return [], 0.0, 0.0
    return [(c[0], c[1], float(a), c[4], c[2]) for c, a in zip(chosen, amt)], exp, float(sum(c[2] for c in chosen))


def settle(bets, pay):
    ret = 0.0
    for t, k, a, o, pm in bets:
        key = "-".join(map(str, k))
        ret += a / 100.0 * pay.get(t, {}).get(key, 0)
    return ret


def boot(vals_st, vals_rt, n=3000, seed=1):
    st, rt = np.array(vals_st), np.array(vals_rt)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(st), size=(n, len(st)))
    s, r = st[idx].sum(axis=1), rt[idx].sum(axis=1)
    x = r[s > 0] / s[s > 0]
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    cache = C.CACHE.parent / "bet_engine_cands.pkl"
    preds, pay = C.predictions(), C.load_pay()
    if cache.exists() and not a.rebuild:
        data = pickle.loads(cache.read_bytes())
    else:
        data = []
        for i, pr in enumerate(preds):
            pk = f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}"
            pp = pay.get(pk)
            if not pp:
                continue
            data.append(dict(key=pr["key"], year=pr["key"][0][:4], kind=race_kind(pr["q"]), cands=race_candidates(pr["p"], pr["q"], pr["uma"]), pay=pp))
            if (i + 1) % 4000 == 0:
                print(f"  候補づくり {i+1:,}/{len(preds):,}", flush=True)
        cache.write_bytes(pickle.dumps(data))
    print(f"■ {len(data):,}レース（{data[0]['key'][0]}〜{data[-1]['key'][0]}）  予算 {a.budget:,}円/レース")
    kinds = collections.Counter(d["kind"] for d in data)
    print("  レースの型: " + " ／ ".join(f"{k} {v:,}（{v/len(data)*100:.0f}%）" for k, v in kinds.items()))

    def run(thr, ev_min, label, target=None, types=None, only_kind=None):
        st, rt, per_year, n_play, hits = [], [], collections.defaultdict(lambda: [0.0, 0.0]), 0, 0
        daily = collections.defaultdict(float)
        mult = []
        for d in data:
            if only_kind and d["kind"] != only_kind:
                continue
            cs = [c for c in d["cands"] if not types or c[0] in types]
            bets, exp, ph = design(cs, d["kind"], a.budget, thr, target, ev_min)
            if not bets:
                continue
            stake = sum(b[2] for b in bets)
            ret = settle(bets, d["pay"])
            st.append(stake); rt.append(ret)
            per_year[d["year"]][0] += stake; per_year[d["year"]][1] += ret
            daily[d["key"][0]] += ret - stake
            n_play += 1
            hits += ret > 0
            if ret > 0:
                mult.append(ret / stake)
        if not st:
            print(f"  {label:<34} 該当なし"); return None
        lo, hi = boot(st, rt)
        roi = sum(rt) / sum(st)
        d_arr = np.array([v for k, v in sorted(daily.items())])
        cum = np.cumsum(d_arr); dd = float((np.maximum.accumulate(cum) - cum).max())
        yrs = " ".join(f"{y[2:]}:{v[1]/v[0]*100:3.0f}" for y, v in sorted(per_year.items()))
        print(f"  {label:<34} {n_play:>6,}R買い({n_play/len(data)*100:4.1f}%) 回収 {roi*100:6.1f}% ［{lo*100:5.1f}〜{hi*100:5.1f}%］ 的中 {hits/n_play*100:4.1f}% "
              f"当たり時{(statistics_median(mult) if mult else 0):4.1f}倍 損益{(sum(rt)-sum(st))/10000:+8.0f}万円 最大DD{dd/10000:5.0f}万円 | {yrs}")
        return roi, lo, hi

    import statistics
    global statistics_median
    statistics_median = statistics.median
    print("\n■ A. 比のしきい値（全券種・型ごとの目標倍率）")
    for thr in (1.2, 1.3, 1.4, 1.6):
        run(thr, 1.10, f"比≧{thr}・全券種")
    print("\n■ B. 券種を限る（比≧1.3）")
    for ts in (("馬連",), ("ワイド",), ("馬連", "ワイド"), ("馬単",), ("3連複",), ("3連単",), ("単勝", "複勝"), ("馬連", "ワイド", "馬単", "3連複")):
        run(1.3, 1.10, "・".join(ts), types=ts)
    print("\n■ C. 型ごと（比≧1.3・全券種）")
    for k in ("堅い", "普通", "荒れ"):
        run(1.3, 1.10, f"{k}", only_kind=k)
    print("\n■ D. 目標倍率を変える（比≧1.3・全券種・全レースに同じ倍率）")
    for T in (2.0, 3.0, 4.0, 6.0, 10.0):
        run(1.3, 1.10, f"目標{T:.0f}倍", target=T)


if __name__ == "__main__":
    main()
