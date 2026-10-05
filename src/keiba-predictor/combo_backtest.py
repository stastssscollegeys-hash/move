# -*- coding: utf-8 -*-
"""
combo_backtest.py — 単勝以外の券種（複勝・馬連・ワイド・馬単・3連複）で、モデルの確率が市場より儲かるかを確定払戻で測る（2026-10-02）
==============================================================================================================
過去の組み合わせオッズは残っていない（当たった組の払戻しか無い）。そこで **払戻そのもの** で精算する:
  モデル確率 p（ev_engine の年ごと前向き・その年より前で学習）と、市場確率 q（単勝オッズ）の2通りで、
  同じλ-Harville（1.00/0.80/0.70・全頭）から組み合わせの確率を作る。
  (a) 各レースで確率上位k組を100円ずつ買う → モデル版と市場版の回収率を並べる（同じ点数・同じレース）
  (b) 「モデル確率／市場確率」が大きい組だけを買う（市場に対して割安な組。単勝のEV≧1と同じ考え方）
市場の組み合わせ確率は 払戻率÷オッズ に等しい（パリミュチュエル）ので、比が1.15なら期待値1.15×払戻率とみなせる。
使い方: python combo_backtest.py [--rebuild]      # --rebuild で予測キャッシュを作り直す
"""
from __future__ import annotations
import argparse, itertools, json, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E

SRC = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history_target"
CACHE = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "ev_walk_pred.pkl"
LAM = (1.0, 0.8, 0.7)
TAKE = {"複勝": 0.80, "馬連": 0.775, "ワイド": 0.775, "馬単": 0.75, "3連複": 0.75}


def predictions(first=2019, l2=0.01):
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    E.SOURCE = SRC
    races, _ = E.build()
    out = []
    for y in sorted({r["key"][0][:4] for r in races}):
        if int(y) < first:
            continue
        tr = [r for r in races if r["key"][0][:4] < y]
        te = [r for r in races if r["key"][0][:4] == y]
        beta, w = E.fit(E.pack(tr), l2)
        for r in te:
            out.append(dict(key=r["key"], uma=r["uma"], q=r["q"], p=E.probs(r, beta, w)))
        print(f"  {y}年 予測 {len(te):,}レース", flush=True)
    CACHE.write_bytes(pickle.dumps(out))
    return out


def tensor(p):
    n = len(p)
    w2, w3 = p ** LAM[1], p ** LAM[2]
    S2, S3 = w2.sum(), w3.sum()
    T = np.zeros((n, n, n))
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            d3 = S3 - w3[a] - w3[b]
            if d3 <= 1e-12:
                continue
            row = p[a] * w2[b] / (S2 - w2[a]) * w3 / d3
            row[a] = row[b] = 0.0
            T[a, b] = row
    return T


def combos(p, uma):
    """各券種の {組(馬番のタプル): 確率}"""
    n = len(p)
    T = tensor(p)
    res = {"複勝": {}, "馬連": {}, "ワイド": {}, "馬単": {}, "3連複": {}}
    for a in range(n):
        res["複勝"][(uma[a],)] = float(T[a].sum() + T[:, a].sum() + T[:, :, a].sum())
    for a, b in itertools.combinations(range(n), 2):
        k = tuple(sorted((uma[a], uma[b])))
        res["馬連"][k] = float(T[a, b].sum() + T[b, a].sum())
        res["ワイド"][k] = float(T[a, b].sum() + T[b, a].sum() + T[a, :, b].sum() + T[b, :, a].sum() + T[:, a, b].sum() + T[:, b, a].sum())
    for a in range(n):
        for b in range(n):
            if a != b:
                res["馬単"][(uma[a], uma[b])] = float(T[a, b].sum())
    for a, b, c in itertools.combinations(range(n), 3):
        res["3連複"][tuple(sorted((uma[a], uma[b], uma[c])))] = float(T[a, b, c] + T[a, c, b] + T[b, a, c] + T[b, c, a] + T[c, a, b] + T[c, b, a])
    return res


def load_pay():
    pay = {}
    for f in sorted(SRC.glob("payouts_*.json")):
        pay.update(json.loads(f.read_text(encoding="utf-8")))
    return pay


def ci(st, rt, n=3000, seed=1):
    st, rt = np.array(st), np.array(rt)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(st), size=(n, len(st)))
    s, r = st[idx].sum(axis=1), rt[idx].sum(axis=1)
    x = r[s > 0] / s[s > 0]
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    if a.rebuild and CACHE.exists():
        CACHE.unlink()
    preds = predictions()
    pay = load_pay()
    print(f"■ 前向き予測 {len(preds):,}レース（{preds[0]['key'][0]}〜{preds[-1]['key'][0]}）")
    stat = {}                                                    # (券種, 方式) → レースごとの (賭け, 払戻)
    for i, pr in enumerate(preds):
        pk = f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}"
        pp = pay.get(pk)
        if not pp:
            continue
        uma = pr["uma"]
        cm, cq = combos(pr["p"], uma), combos(pr["q"], uma)
        for t in ("複勝", "馬連", "ワイド", "馬単", "3連複"):
            table = pp.get(t, {})
            keyf = (lambda c: "-".join(map(str, c)))
            for name, k, src in (("モデル上位", None, cm), ("市場上位", None, cq)):
                for kk in ((1, 2, 3) if t == "複勝" else (3, 5) if t != "3連複" else (5, 10)):
                    top = sorted(src[t], key=lambda c: -src[t][c])[:kk]
                    stat.setdefault((t, f"{name}{kk}点"), []).append((100.0 * kk, sum(table.get(keyf(c), 0) for c in top)))
            for thr in (1.10, 1.20, 1.30):
                sel = [c for c in cm[t] if cq[t][c] > 0 and cm[t][c] / cq[t][c] >= thr and cq[t][c] >= {"複勝": 0.15, "馬連": 0.03, "ワイド": 0.08, "馬単": 0.02, "3連複": 0.01}[t]]
                stat.setdefault((t, f"割安(比≧{thr:.2f})"), []).append((100.0 * len(sel), sum(table.get(keyf(c), 0) for c in sel)))
        if (i + 1) % 5000 == 0:
            print(f"  {i+1:,}/{len(preds):,}", flush=True)
    print(f"\n{'券種':<6}{'買い方':<20}{'点数':>9}{'回収率':>9}{'95%区間':>18}")
    for (t, name), v in sorted(stat.items()):
        st, rt = [x[0] for x in v], [x[1] for x in v]
        if sum(st) == 0:
            continue
        lo, hi = ci(st, rt)
        print(f"{t:<6}{name:<20}{int(sum(st)/100):>9,}{sum(rt)/sum(st)*100:>8.1f}%   ［{lo*100:>5.1f}〜{hi*100:>5.1f}%］  払戻率{TAKE[t]*100:.1f}%")
    Path(CACHE.parent / "combo_backtest_last.json").write_text(json.dumps({f"{t}|{n}": [sum(x[0] for x in v), sum(x[1] for x in v)] for (t, n), v in stat.items()}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
