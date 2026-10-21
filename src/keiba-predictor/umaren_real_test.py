# -*- coding: utf-8 -*-
"""
umaren_real_test.py — 馬連の「市場との比」ルールを、実際の確定前オッズで約3年分（2023〜）検証し、補正と境目を決め直す（2026-10-07新規）
====================================================================================================================
オッズ: 2023〜2025/10/3 は umaren_hist.py（JV 0B42 の最後の発表）、2025/10/4〜 は jv_odds.OddsStore（O2）
予測  : combo_backtest.predictions()（年ごとの前向き。調教入りエンジン）
補正  : 確率を市場へ寄せる p_adj ∝ q^(1−a) × p^a（a=1 で補正なし）。モデルの「市場との差」を a 倍に縮める
選び方: 比 = p_adj(組) ÷ q(組)（どちらもλ-Harville）≧ しきい値、かつ 実オッズの期待値 p_adj×オッズ ≧ 下限
決め方: 2023〜2024 で a・しきい値を選び、2025〜2026 で確かめる（選び直さない）
"""
from __future__ import annotations
import collections, json, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import bet_engine as B
import jv_odds as J

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
VCODE = {v: k for k, v in J.VENUE.items()}


def load_odds():
    od = {}
    for y in ("2023", "2024", "2025"):
        f = DB / f"umaren_final_{y}.pkl"
        if f.exists():
            for k16, tab in pickle.loads(f.read_bytes()).items():
                od[(k16[:8], J.VENUE.get(k16[8:10]), int(k16[14:16]))] = tab
    store = J.OddsStore()
    for k in store.races():
        if k not in od:
            t = store.get(k, "O2")
            if t:
                od[k] = t["馬連"]
    return od


def main():
    preds, pay = C.predictions(), C.load_pay()
    od = load_odds()
    rows = []
    for pr in preds:
        k = tuple(pr["key"])
        if k[0] < "20230101" or k not in od:
            continue
        rows.append((k, pr))
    print(f"■ 馬連の実オッズつき {len(rows):,}レース（{rows[0][0][0]}〜{rows[-1][0][0]}）")
    grid = {}
    for a in (1.0, 0.7, 0.5):
        cache = []
        for k, pr in rows:
            p, q = pr["p"], pr["q"]
            pa = np.exp((1 - a) * np.log(q) + a * np.log(p)); pa /= pa.sum()
            km, prm = B.tables(pa, pr["uma"])["馬連"]
            _, prq = B.tables(q, pr["uma"])["馬連"]
            tab = od[k]
            pp = pay.get(f"{k[0]}|{k[1]}|{k[2]}", {}).get("馬連", {})
            items = []
            for key, x, y in zip(km, prm, prq):
                o = tab.get(key)
                if not o or y < 0.03:
                    continue
                items.append((x / y, x * o, o, pp.get("-".join(map(str, key)), 0)))
            cache.append((k[0][:4], items))
        for thr in (1.1, 1.2, 1.3, 1.5):
            for evmin in (0.0, 0.9, 1.0):
                st = collections.defaultdict(lambda: [0, 0.0])
                for y, items in cache:
                    for r_, ev, o, got in items:
                        if r_ >= thr and ev >= evmin:
                            st[y][0] += 1; st[y][1] += got
                grid[(a, thr, evmin)] = st
    print("  a=補正の強さ（1.0=補正なし）／比のしきい値／実オッズ期待値の下限 → 年別の回収率（各組100円）")
    best = None
    for (a, thr, evmin), st in grid.items():
        tr = [st[y] for y in ("2023", "2024")]
        te = [st[y] for y in ("2025", "2026")]
        ntr, rtr = sum(v[0] for v in tr), sum(v[1] for v in tr)
        nte, rte = sum(v[0] for v in te), sum(v[1] for v in te)
        if ntr < 300:
            continue
        line = f"  a={a:.1f} 比≧{thr:.1f} 期待値≧{evmin:.1f} | 決める期間 {ntr:>6,}点 {rtr/ntr:6.1f}% | 確かめる期間 {nte:>6,}点 {rte/max(nte,1):6.1f}% | 年別 " + \
               " ".join(f"{y[2:]}:{st[y][1]/st[y][0]:.0f}" for y in sorted(st) if st[y][0])
        print(line)
        if best is None or rtr / ntr > best[0]:
            best = (rtr / ntr, a, thr, evmin, nte, rte)
    r, a, thr, evmin, nte, rte = best
    print(f"\n■ 決める期間で最良: a={a} 比≧{thr} 期待値≧{evmin}（{r:.1f}%）→ 確かめる期間 {nte:,}点 {rte/max(nte,1):.1f}%")
    (DB / "umaren_real_test.json").write_text(json.dumps(dict(best=dict(a=a, thr=thr, evmin=evmin, train=r, test=rte / max(nte, 1), n_test=nte)), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
