# -*- coding: utf-8 -*-
"""
payout_estimator.py — 券種別の配当推定器（v6.3 型別ROI設計の土台）
================================================================
なぜ必要か
----------
v6.3では「本線に置く点の推定配当が何倍か」で型と券種を決める。
　S 的中率重視型 → 8〜15倍帯を本線
　H 高配当型     → 20〜50倍帯を本線
つまり **買う前に配当を推定できないと型設計が回らない**。

方法
----
確定払戻 payouts.json（1,044レース×7券種）と
累積DB race_results.json（各馬の単勝オッズ）を突き合わせ、
「的中した組み合わせの単勝オッズの積」→「実際の配当」を対数回帰で較正する。

    log(配当) = a * log(オッズの積) + b

Harville近似より単純だが、**実データで直接較正している**ぶん素性が明快。
係数は calibrate() で再計算でき、開催が増えるほど精度が上がる（蓄積して育てる設計）。

使い方
------
    python payout_estimator.py --calibrate      # 係数を再計算して保存
    python payout_estimator.py --show           # 現在の係数と誤差を表示

    from payout_estimator import estimate
    estimate("3連複", [9.9, 3.2, 5.1])   # -> 推定倍率
"""
from __future__ import annotations
import argparse, json, math, sys, io
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
PAYOUTS = DB / "payouts.json"
RESULTS = DB / "race_results.json"
COEF = Path(__file__).resolve().parent / "payout_coef.json"

# 券種ごとの必要頭数
NHORSE = {"単勝": 1, "複勝": 1, "馬連": 2, "ワイド": 2, "馬単": 2, "3連複": 3, "3連単": 3}

DEFAULT = {  # 較正前のフォールバック（2026-09-06の実測5点から粗く推定）
    "馬連":   {"a": 1.05, "b": -0.55, "n": 0},
    "ワイド": {"a": 0.90, "b": -1.15, "n": 0},
    "馬単":   {"a": 1.10, "b": -0.10, "n": 0},
    "3連複": {"a": 1.32, "b": -3.97, "n": 0},
    "3連単": {"a": 1.45, "b": -3.30, "n": 0},
}


def load_coef() -> dict:
    if COEF.exists():
        return json.load(open(COEF, encoding="utf-8"))
    return DEFAULT


def estimate(ticket: str, odds: list[float]) -> float | None:
    """単勝オッズのリストから配当倍率を推定する"""
    c = load_coef().get(ticket)
    if not c or not odds or any(o is None or o <= 0 for o in odds):
        return None
    if len(odds) != NHORSE.get(ticket, len(odds)):
        return None
    prod = 1.0
    for o in odds:
        prod *= o
    try:
        return math.exp(c["a"] * math.log(prod) + c["b"])
    except ValueError:
        return None


def _build_odds_index() -> dict:
    """(date, 競馬場, R) -> {馬番: 単勝オッズ}"""
    rows = json.load(open(RESULTS, encoding="utf-8"))
    idx = defaultdict(dict)
    for r in rows:
        try:
            num = int(r.get("馬番"))
            o = float(r.get("単勝オッズ"))
        except (TypeError, ValueError):
            continue
        if o <= 0:
            continue
        idx[(str(r.get("date")), r.get("競馬場"), r.get("R"))][num] = o
    return idx


def calibrate(verbose: bool = True) -> dict:
    """payouts.json × race_results.json で係数を再計算"""
    pays = json.load(open(PAYOUTS, encoding="utf-8"))
    oidx = _build_odds_index()
    # payouts.json は race_id -> {date, venue, R, payouts:{券種:[{combo,yen,pop}]}}
    samples = defaultdict(list)
    matched = skipped = 0
    for rid, rec in pays.items():
        key = (str(rec.get("date")), rec.get("venue"), rec.get("R"))
        omap = oidx.get(key)
        if not omap:
            skipped += 1
            continue
        matched += 1
        for tk, lst in (rec.get("payouts") or {}).items():
            n = NHORSE.get(tk)
            if not n or n < 2:
                continue
            for item in lst:
                combo, yen = item.get("combo"), item.get("yen")
                if not combo or not yen or yen <= 0:
                    continue
                try:
                    nums = [int(x) for x in str(combo).split("-")]
                except ValueError:
                    continue
                if len(nums) != n:
                    continue
                od = [omap.get(x) for x in nums]
                if any(o is None for o in od):
                    continue
                prod = 1.0
                for o in od:
                    prod *= o
                if prod <= 0:
                    continue
                samples[tk].append((math.log(prod), math.log(yen / 100.0)))

    coef = {}
    for tk, pts in samples.items():
        if len(pts) < 50:
            continue
        n = len(pts)
        sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
        sxx = sum(p[0] * p[0] for p in pts); sxy = sum(p[0] * p[1] for p in pts)
        den = n * sxx - sx * sx
        if abs(den) < 1e-9:
            continue
        a = (n * sxy - sx * sy) / den
        b = (sy - a * sx) / n
        # 中央値の相対誤差
        errs = sorted(abs(math.exp(a * x + b) / math.exp(y) - 1.0) for x, y in pts)
        coef[tk] = {"a": round(a, 4), "b": round(b, 4), "n": n,
                    "median_err": round(errs[len(errs) // 2], 3)}

    if coef:
        json.dump(coef, open(COEF, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if verbose:
        print(f"較正: 突合できたレース {matched:,} / スキップ {skipped:,}")
        print(f"{'券種':<8}{'サンプル':>9}{'a':>8}{'b':>9}{'中央値誤差':>10}")
        print("-" * 46)
        for tk in ["馬連", "ワイド", "馬単", "3連複", "3連単"]:
            c = coef.get(tk)
            if c:
                print(f"{tk:<8}{c['n']:>9,}{c['a']:>8.3f}{c['b']:>9.3f}{c['median_err']*100:>9.0f}%")
            else:
                print(f"{tk:<8}{'—':>9}  （サンプル不足・DEFAULTを使用）")
    return coef


def _show():
    c = load_coef()
    src = "payout_coef.json（実データ較正済み）" if COEF.exists() else "DEFAULT（未較正）"
    print(f"係数の出所: {src}\n")
    print(f"{'券種':<8}{'a':>8}{'b':>9}{'サンプル':>9}{'中央値誤差':>10}")
    print("-" * 46)
    for tk in ["馬連", "ワイド", "馬単", "3連複", "3連単"]:
        x = c.get(tk)
        if x:
            e = f"{x.get('median_err', 0)*100:.0f}%" if x.get("median_err") else "—"
            print(f"{tk:<8}{x['a']:>8.3f}{x['b']:>9.3f}{x.get('n',0):>9,}{e:>10}")
    print("\n参考: 推定値の例")
    for tk, od in [("ワイド", [3.2, 5.1]), ("馬連", [3.2, 5.1]), ("馬単", [3.2, 5.1]),
                   ("3連複", [9.9, 3.2, 5.1]), ("3連複", [8.5, 15.4, 2.5])]:
        v = estimate(tk, od)
        print(f"  {tk:<6} オッズ{od} → 推定 {v:.1f}倍" if v else f"  {tk}: 推定不可")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if a.calibrate:
        calibrate()
    else:
        _show()
