# -*- coding: utf-8 -*-
"""
factor_audit.py — 従来の20ファクター（アスメシ式）を10年分のデータで検証する（2026-10-02新規）
==============================================================================================
従来の指数は F01〜F17（＋コース実績 sc18・基準タイム sc19）。各ファクターを **レース前に分かる情報だけ**（その日より前の履歴）で
再現し、10年・約3万5千レースで「市場の確率に加えて、そのファクターが勝ち馬を当てる力を持つか」を測る。

測り方（ファクターごと）
  レース内で標準化（平均0・標準偏差1）した値 x を、条件付きロジット  強さ = ln(市場確率) + w·x  に入れて w を最尤で推定する。
  w>0 なら「そのファクターが高い馬ほど、市場の評価より勝つ」。LR（尤度比）の z と、年ごとの向き（何年で同じ向きか）を出す。
  再現できないもの: F15 EV・F16 人気乖離（オッズ由来＝市場そのもの）、F13 クラス・F17 頭数（レース内で全馬同じ値）、sc20 外部指数、sc9 追い切り（蓄積が少ない）。
出力: 標準出力と docs/keiba_factor_audit.md
使い方: python factor_audit.py
"""
from __future__ import annotations
import collections, datetime, json, math, re, statistics, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E

SRC = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history_target"
OUT_MD = Path(__file__).resolve().parents[2] / "docs" / "keiba_factor_audit.md"
sys.path.insert(0, str(Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca"))
from config import GATE_BIAS, SURFACE_SC

NAMES = ["F01_後3F", "F02_タイム(旧式)", "F02_タイム(実測基準)", "F03_着差", "F04_騎手", "F05_厩舎", "F06_枠(旧表)", "F07_馬番内外", "F08_距離適性",
         "F09_馬体重", "F10_斤量", "F11_性別", "F12_年齢", "F14_馬場適性", "sc18_コース実績"]


def day(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def main():
    E.SOURCE = SRC
    rows = E.load_rows()
    races = collections.defaultdict(list)
    for r in rows:
        try:
            r["_o"] = float(r["単勝オッズ"])
            r["_u"] = int(float(r["馬番"]))
        except (TypeError, ValueError, KeyError):
            continue
        r["_f"] = E.fin(r)
        if r["_o"] > 0:
            races[(r["date"], r["競馬場"], int(r["R"]))].append(r)
    keys = sorted(k for k, hs in races.items() if len(hs) >= 6 and sum(1 for h in hs if h["_f"] == 1) == 1 and 1.10 <= sum(1 / h["_o"] for h in hs) <= 1.45)
    by_date = collections.defaultdict(list)
    for k in keys:
        by_date[k[0]].append(k)

    # 基準タイム（全期間の中央値。点数のスケール合わせ用でレース前情報との差は無視できる）
    tm = collections.defaultdict(list)
    for r in rows:
        t = E.sec(r.get("タイム"))
        if t and E.fin(r):
            tm[(E.surf(r.get("距離")), E.meters(r.get("距離")))].append(t)
    std = {k: statistics.median(v) for k, v in tm.items() if len(v) >= 30}

    hist = collections.defaultdict(list)
    jk = collections.defaultdict(lambda: [0, 0])
    tr = collections.defaultdict(lambda: [0, 0])
    data = []                                  # レースごと: dict(q, X(n×15), win, year)
    for d in sorted(by_date):
        pend = []
        for k in by_date[d]:
            hs = races[k]
            n = len(hs)
            s = sum(1 / h["_o"] for h in hs)
            kins = [E.num(h.get("斤量_kg")) for h in hs]
            ka = statistics.mean([x for x in kins if x]) if any(kins) else None
            sf, mt = E.surf(hs[0].get("距離")), E.meters(hs[0].get("距離"))
            venue = k[1]
            X = np.full((n, len(NAMES)), np.nan)
            for i, (h, kg) in enumerate(zip(hs, kins)):
                hk = h.get("horse_id") or h.get("馬名")
                past = hist.get(hk, [])[-5:][::-1]            # 新しい順・直近5走
                f3 = [p["l3"] for p in past if p["l3"]]
                X[i, 0] = max(0.0, min(100.0, (36.0 - min(f3)) / 3.0 * 100.0)) if f3 else 50.0
                same = [p for p in past if p["m"] and mt and abs(p["m"] - mt) <= 200 and p["t"]]
                X[i, 1] = max(0.0, min(100.0, (mt / 1000.0 * 61.0 + 3 - min(p["t"] for p in same)) / 3.0 * 100.0)) if same and mt else 50.0
                figs = [(std[(p["sf"], p["m"])] - p["t"]) / std[(p["sf"], p["m"])] * 100 for p in past if p["t"] and (p["sf"], p["m"]) in std and p["sf"] == sf][:3]
                X[i, 2] = max(0.0, min(100.0, 50.0 + max(figs) * 12.5)) if figs else 50.0
                rk = [p["fin"] for p in past[:3] if p["fin"]]
                if rk:
                    dd = lambda r_: 0.0 if r_ <= 1 else 0.3 if r_ == 2 else 0.6 if r_ == 3 else min(5.0, 0.6 + (r_ - 3) * 0.5)
                    v = max(0.0, 100.0 - sum(dd(x) for x in rk) / len(rk) * 15.0)
                    X[i, 3] = min(100.0, v + 5.0 * sum(1 for p in past if p["fin"] == 1))
                else:
                    X[i, 3] = 50.0
                a = jk.get(h.get("騎手"))
                X[i, 4] = min(100.0, 50.0 + (a[1] / a[0]) * 280.0) if a and a[0] >= 30 else 50.0
                b = tr.get(h.get("厩舎"))
                X[i, 5] = min(100.0, 50.0 + (b[1] / b[0]) * 280.0) if b and b[0] >= 30 else 50.0
                w = h.get("枠")
                X[i, 6] = float(GATE_BIAS.get(venue, {}).get(int(w), 65)) if w else 65.0
                inner = 1.0 - (h["_u"] - 1) / max(n - 1, 1)
                X[i, 7] = {"東京": 55 + inner * 25, "京都": 60 + inner * 35, "中山": 60 + inner * 30, "阪神": 58 + inner * 28}.get(venue, 60 + inner * 15)
                f08 = 72.0 if mt <= 1200 else 75.0 if mt <= 1600 else 78.0 if mt <= 2000 else 74.0 if mt <= 2400 else 70.0
                if same:
                    f08 = f08 * 0.6 + sum(1 for p in same if p["fin"] and p["fin"] <= 3) / len(same) * 100 * 0.4
                X[i, 8] = f08
                m = re.search(r"\(([+-]?\d+)\)", str(h.get("馬体重") or ""))
                if m:
                    wc = abs(int(m.group(1)))
                    X[i, 9] = 92.0 if wc <= 4 else 77.0 if wc <= 8 else 60.0 if wc <= 14 else 40.0
                else:
                    X[i, 9] = 70.0
                X[i, 10] = max(0.0, min(100.0, 65.0 + (ka - kg) * 4.0)) if (kg and ka) else 60.0
                sa = str(h.get("性齢") or "")
                X[i, 11] = {"牡": 60.0, "牝": 62.0, "セ": 58.0}.get(sa[:1], 60.0)
                try:
                    X[i, 12] = {2: 80, 3: 88, 4: 98, 5: 95, 6: 85, 7: 75}.get(int(sa[1:]), 68.0)
                except ValueError:
                    X[i, 12] = 68.0
                sp = [p for p in past if p["sf"] == sf]
                base = float(SURFACE_SC.get(("芝" if sf == "芝" else "ダート", venue), 70))
                X[i, 13] = base * 0.7 + (sum(1 for p in sp if p["fin"] and p["fin"] <= 3) / len(sp) * 100 * 0.3 if sp else 0.0) if sp else base
                allp = hist.get(hk, [])
                vv = [p for p in allp if p["venue"] == venue and p["sf"] == sf]
                X[i, 14] = (sum(1 for p in vv if p["fin"] and p["fin"] <= 3) / len(vv) * 100) if len(vv) >= 2 else 50.0
                pend.append((h, hk, n))
            data.append(dict(q=np.array([(1 / h["_o"]) / s for h in hs]), X=X, win=[h["_f"] == 1 for h in hs].index(True), year=d[:4]))
        for h, hk, n in pend:
            f = h["_f"]
            if f:
                if h.get("騎手"):
                    jk[h["騎手"]][0] += 1; jk[h["騎手"]][1] += f == 1
                if h.get("厩舎"):
                    tr[h["厩舎"]][0] += 1; tr[h["厩舎"]][1] += f == 1
            if hk:
                hist[hk].append(dict(fin=f, l3=h.get("後3F"), m=E.meters(h.get("距離")), t=E.sec(h.get("タイム")), sf=E.surf(h.get("距離")), venue=h.get("競馬場")))

    # レース内標準化 → 1ファクターずつ条件付きロジット
    def zscore(X):
        mu, sd = X.mean(axis=0), X.std(axis=0)
        return np.where(sd > 1e-9, (X - mu) / np.where(sd > 1e-9, sd, 1), 0.0)
    for r in data:
        r["Z"] = zscore(r["X"])
    H = max(len(r["q"]) for r in data)

    def pack(rs, col):
        R = len(rs)
        LQ, Z, M, W = np.full((R, H), -1e9), np.zeros((R, H)), np.zeros((R, H), dtype=bool), np.zeros(R, dtype=int)
        for i, r in enumerate(rs):
            n = len(r["q"]); LQ[i, :n], Z[i, :n], M[i, :n], W[i] = np.log(r["q"]), r["Z"][:, col], True, r["win"]
        return LQ, Z, M, W

    def ll(P, W):
        return float(np.log(np.maximum(P[np.arange(len(W)), W], 1e-300)).sum())

    def fit1(pk):
        LQ, Z, M, W = pk
        from scipy.optimize import minimize_scalar

        def nll(w):
            U = np.where(M, LQ + w * Z, -1e9); U -= U.max(axis=1, keepdims=True)
            E_ = np.exp(U) * M; P = E_ / E_.sum(axis=1, keepdims=True)
            return -ll(P, W)
        res = minimize_scalar(nll, bounds=(-2, 2), method="bounded")
        return res.x, -res.fun, -nll(0.0)

    years = sorted({r["year"] for r in data})
    out = []
    print(f"■ {len(data):,}レース（{years[0]}〜{years[-1]}）で、ファクター1つずつの「市場に対する追加の予測力」")
    print(f"{'ファクター':<20}{'係数w':>9}{'LR z':>8}{'対数尤度/R':>12}   年ごとの向き（＋の年数/全年数）")
    for c, name in enumerate(NAMES):
        pk = pack(data, c)
        w, l1, l0 = fit1(pk)
        z = math.copysign(math.sqrt(max(0.0, 2 * (l1 - l0))), w)
        pos = 0
        for y in years:
            sub = [r for r in data if r["year"] == y]
            wy, _, _ = fit1(pack(sub, c))
            pos += wy > 0
        out.append((name, w, z, (l1 - l0) / len(data), pos, len(years)))
        print(f"{name:<20}{w:>+9.4f}{z:>+8.1f}{(l1 - l0) / len(data):>+12.5f}   {pos}/{len(years)}")
    # 全部入り
    md = ["# 20ファクター（アスメシ式）の10年検証\n", f"対象: {data[0]['year']}〜{data[-1]['year']}・{len(data):,}レース。各ファクターをレース前の情報だけで再現し、市場の確率に追加で効くかを測った。",
          "w＞0: 高い馬ほど市場の評価より勝つ／w＜0: 高い馬ほど市場に過大評価されている。|z|＜3 は偶然の範囲。年ごとの向きが半々なら安定していない。\n",
          "| ファクター | 係数w | z | 1レースあたりの対数尤度 | ＋の年 |\n|---|---|---|---|---|"]
    for name, w, z, g, pos, ny in out:
        md.append(f"| {name} | {w:+.4f} | {z:+.1f} | {g:+.5f} | {pos}/{ny} |")
    md += ["\n再現できなかったもの: F15 EV・F16 人気乖離（オッズ由来で市場そのもの）／F13 クラス・F17 頭数（レース内で全馬同じ値）／sc20 外部指数／sc9 追い切り（蓄積が少ない）。"]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\n保存: {OUT_MD}")


if __name__ == "__main__":
    main()
