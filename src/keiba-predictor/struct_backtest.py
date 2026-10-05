# -*- coding: utf-8 -*-
"""
struct_backtest.py — flat_preview の「型ごとの買い方」を確定払戻で測る（2026-10-02）
==================================================================================
flat_preview.py は レースの型（1強／拮抗／標準）ごとに買い方を決めている（STRUCTURE）。
その対応が妥当かを、確定払戻のある全レースで測る。

  ・型の判定と買い目の組み立ては flat_preview の関数をそのまま呼ぶ（ツールと検証が同じコードを通る）
  ・◎＝単勝1番人気、相手＝単勝人気の2〜5番手（指数は使わない）
  ・金額は 推定配当に反比例 → 1点上限30%（本番と同じ allocate / cap_amount）。精算は確定払戻
  ・オッズは確定オッズ（前日オッズではない）。前日版はここから人気が入れ替わる分だけ悪くなる

読み方: どの型×買い方も控除率（単勝80%・馬連/ワイド77.5%・馬単75%）の近くに出るはず。
        100%を超える組があっても、区間が100%をまたぐ限り運用ルールにしない（SKILL §2）。
        ここで決めるのは「同じ型の中でどの買い方がいちばん損が少なく、当たりやすいか」だけ。
使い方: python struct_backtest.py [--budget 5000]
"""
from __future__ import annotations
import argparse, collections, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from payout_estimator import estimate
from kaime_select import allocate
from draw_final import cap_amount
from flat_preview import race_type, build_bets, STRUCTURE

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
STRUCTS = ["馬単流し", "BOX", "馬連流し", "単勝＋馬連流し", "ワイド流し", "単勝"]


def load():
    odds = collections.defaultdict(dict)
    for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8")):
        try:
            odds[(r["date"], r["競馬場"], int(float(r["R"])))][int(float(r["馬番"]))] = float(r["単勝オッズ"])
        except (TypeError, ValueError, KeyError):
            continue
    out = []
    for rid, rec in sorted(json.loads((DB / "payouts.json").read_text(encoding="utf-8")).items(), key=lambda kv: kv[1]["date"]):
        tan = odds.get((str(rec["date"]), rec["venue"], int(rec["R"])))
        tan = {u: o for u, o in (tan or {}).items() if o and o > 0}     # 取消馬（オッズ0）を除く
        if len(tan) < 6 or not 1.15 <= sum(1 / o for o in tan.values()) <= 1.40:
            continue
        pay = collections.defaultdict(dict)
        for t, lst in rec["payouts"].items():
            for x in lst:
                try:
                    nums = tuple(int(v) for v in str(x["combo"]).split("-"))
                except ValueError:
                    continue
                pay[t][nums if t in ("馬単", "3連単", "単勝") else tuple(sorted(nums))] = x["yen"] / 100.0
        out.append((rec["date"], tan, pay))
    return out


def play(tan, pay, structure, budget):
    order = sorted(tan, key=lambda u: tan[u])
    hon, aite = order[0], order[1:5]
    if structure == "単勝":
        return budget * pay["単勝"].get((hon,), 0.0), 1
    _, bets = build_bets(race_type(tan), hon, aite, structure)
    pts = []
    for b in bets:
        est = tan[b["combo"][0]] if b["t"] == "単勝" else estimate(b["t"], [tan[u] for u in b["combo"]])
        if est:
            pts.append(dict(t=b["t"], combo=b["combo"], est=est))
    allocate(pts, budget)
    cap_amount(pts, budget)
    ret = 0.0
    for x in pts:
        key = tuple(x["combo"]) if x["t"] in ("馬単", "単勝") else tuple(sorted(x["combo"]))
        ret += x["amt"] * pay[x["t"]].get(key, 0.0)
    return ret, len(pts)


def ci(rets, budget, n=3000, seed=1):
    rng = random.Random(seed)
    m = len(rets)
    xs = sorted(sum(rets[rng.randrange(m)] for _ in range(m)) / (m * budget) for _ in range(n))
    return xs[int(0.025 * n)], xs[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=5000)
    a = ap.parse_args()
    races = load()
    half = len(races) // 2
    print(f"■ 確定払戻つき {len(races):,}レース（{races[0][0]}〜{races[-1][0]}）　予算{a.budget:,}円/レース")
    res = collections.defaultdict(lambda: collections.defaultdict(list))      # 型 → 買い方 → [(払戻, 前半か)]
    for i, (date, tan, pay) in enumerate(races):
        rt = race_type(tan)
        for st in STRUCTS:
            ret, n = play(tan, pay, st, a.budget)
            res[rt][st].append((ret, i < half))
            res["全体"][st].append((ret, i < half))
    cur = []
    for rt in ("1強", "拮抗", "標準", "全体"):
        n = len(res[rt][STRUCTS[0]])
        print(f"\n● {rt}（{n:,}レース）" + (f"　現行の買い方: {STRUCTURE[rt]}" if rt in STRUCTURE else ""))
        print(f"  {'買い方':<8}{'回収率':>8}{'95%区間':>16}{'的中率':>8}{'前半':>8}{'後半':>8}{'最高1R除外':>10}")
        for st in STRUCTS:
            xs = res[rt][st]
            rets = [r for r, _ in xs]
            roi = sum(rets) / (n * a.budget)
            lo, hi = ci(rets, a.budget)
            h1 = [r for r, f in xs if f]
            h2 = [r for r, f in xs if not f]
            ex1 = (sum(rets) - max(rets)) / ((n - 1) * a.budget)
            mark = " ←現行" if STRUCTURE.get(rt) == st else ""
            print(f"  {st:<9}{roi*100:>7.1f}%   ［{lo*100:>5.1f}〜{hi*100:>5.1f}%］{sum(1 for r in rets if r > 0)/n*100:>7.1f}%"
                  f"{sum(h1)/(len(h1)*a.budget)*100 if h1 else 0:>7.1f}%{sum(h2)/(len(h2)*a.budget)*100 if h2 else 0:>7.1f}%{ex1*100:>9.1f}%{mark}")
        if rt in STRUCTURE:
            cur += [r for r, _ in res[rt][STRUCTURE[rt]]]
    lo, hi = ci(cur, a.budget)
    print(f"\n■ 現行の対応（型ごとに買い方を変える）全体: 回収率 {sum(cur)/(len(cur)*a.budget)*100:.1f}% ［{lo*100:.1f}〜{hi*100:.1f}%］"
          f" 的中率 {sum(1 for r in cur if r > 0)/len(cur)*100:.1f}%")


if __name__ == "__main__":
    main()
