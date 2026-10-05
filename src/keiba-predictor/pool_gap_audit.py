# -*- coding: utf-8 -*-
"""
pool_gap_audit.py — 券種間のオッズのずれで期待値1超を拾えるか（2026-10-02）
==========================================================================
ev_engine.py で「馬の情報から市場より正確な確率を作る」道は検証を通らなかった。
残る道の1つが **券種の間のずれ**: 単勝オッズから計算した組み合わせの的中確率（全頭λ-Harville。
prob_calib_audit で実測と合うことを確認済み）に対して、馬連・ワイド・3連複の実際のオッズが高く付いている
組み合わせだけを買う。馬の予想はせず、市場どうしの食い違いだけを使う。

odds_snapshot.py が 2026-09-12 から全組み合わせのオッズを貯めているので、初めて検証できる。
  選ぶ: レース当日9:30までに取った最新のスナップショットで、 的中確率×オッズ ≧ しきい値 の組（人気1〜6位の馬どうしに限る）
  精算: 確定払戻（パリミュチュエルなので、買った時点のオッズではなく確定の払戻で精算する）
レース数がまだ少ないので、ここで出る数字は「候補として前向きに追う価値があるか」を見るためのもの。
使い方: python pool_gap_audit.py
"""
from __future__ import annotations
import collections, glob, itertools, json, re, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from prob_core import market_probs, top3_scenarios, ticket_probs

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
SNAP = DB / "odds_snapshots"
TOPN = 6
TYPES = ("複勝", "ワイド", "馬連", "馬単", "3連複")


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pick_snapshots():
    """レースごとに「当日9:30まで」の最新。無ければ対象外（レース後のオッズで選ばないため）"""
    best = {}
    for path in glob.glob(str(SNAP / "*" / "*.json")):
        with open(path, encoding="utf-8") as fh:
            head = fh.read(2000)
        m = re.search(r'"fetched_at":\s*"([^"]+)"', head)
        d = re.search(r'"race_date":\s*"(\d{8})"', head)
        rid = Path(path).stem.split("_")[0]
        if not m or not d:
            continue
        ts, day = m.group(1), d.group(1)
        limit = f"{day[:4]}-{day[4:6]}-{day[6:]}T09:30:00"
        if ts <= limit and (rid not in best or ts > best[rid][0]):
            best[rid] = (ts, path)
    return {rid: p for rid, (ts, p) in best.items()}


def main():
    pays = json.loads((DB / "payouts.json").read_text(encoding="utf-8"))
    res = collections.defaultdict(lambda: collections.defaultdict(list))     # (券種, しきい値) → レース → [(賭け, 払戻)]
    used = 0
    for rid, path in sorted(pick_snapshots().items()):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        o = d.get("odds", {})
        if not all(o.get(t) for t in ("単勝", "馬連", "ワイド")) or rid not in pays:
            continue
        tan = {int(k): f(v[0]) for k, v in o["単勝"].items() if f(v[0])}
        if len(tan) < 8:
            continue
        used += 1
        q = market_probs(tan)
        tp = ticket_probs(top3_scenarios(q), q)
        top = sorted(tan, key=lambda u: tan[u])[:TOPN]
        pay = collections.defaultdict(dict)
        for t, lst in pays[rid]["payouts"].items():
            for x in lst:
                try:
                    nums = tuple(int(v) for v in str(x["combo"]).split("-"))
                except ValueError:
                    continue
                pay[t][nums if t == "馬単" else tuple(sorted(nums))] = x["yen"] / 100.0
        for t in TYPES:
            tbl = o.get(t) or {}
            for k, v in tbl.items():
                nums = tuple(int(k[i:i + 2]) for i in range(0, len(k), 2))
                if any(u not in top for u in nums):
                    continue
                key = nums if t == "馬単" else tuple(sorted(nums))
                odds = f(v[0])                                    # 複勝・ワイドは下限オッズ
                p = tp[t].get(key, 0.0)
                if not odds or not p:
                    continue
                ev = p * odds
                for thr in (0.0, 1.0, 1.1, 1.2, 1.4):
                    if ev >= thr:
                        res[(t, thr)][rid].append((100.0, 100.0 * pay[t].get(key, 0.0)))
    print(f"■ 対象 {used}レース（当日9:30までのスナップショットに馬連・ワイドのオッズがあるもの）")
    print(f"{'券種':<6}{'しきい値':>7}{'点数':>7}{'買ったR':>8}{'回収率':>9}{'95%区間':>18}")
    rng = np.random.default_rng(1)
    for t in TYPES:
        for thr in (0.0, 1.0, 1.1, 1.2, 1.4):
            by = res.get((t, thr))
            if not by:
                continue
            st = np.array([sum(s for s, r in v) for v in by.values()])
            rt = np.array([sum(r for s, r in v) for v in by.values()])
            idx = rng.integers(0, len(st), size=(3000, len(st)))
            x = rt[idx].sum(axis=1) / st[idx].sum(axis=1)
            lab = "（全部買う）" if thr == 0.0 else ""
            print(f"{t:<6}{thr:>7.1f}{int(st.sum()/100):>8,}{len(by):>8}{rt.sum()/st.sum()*100:>8.1f}%   ［{np.percentile(x,2.5)*100:>5.1f}〜{np.percentile(x,97.5)*100:>5.1f}%］{lab}")
        print()


if __name__ == "__main__":
    main()
