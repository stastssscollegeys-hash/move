# -*- coding: utf-8 -*-
"""
payout_est_audit.py — 配当の推定（payout_estimator）を、発売中の全組み合わせオッズと突き合わせる（2026-10-02）
==========================================================================================================
payout_estimator は「当たった組み合わせの払戻」だけで較正していた（外れた組のオッズが無かったため）。
2026-09-11 から odds_snapshot.py が**全組み合わせのオッズ**を貯めているので、同じスナップショット内の
単勝オッズから推定した倍率と、実際に付いているオッズを全組で比べられる。前日版の買い目は推定配当で金額を
決めるので、ここが偏っていると配分も「的中時の戻り」の表示も偏る。

見るもの: 推定÷実際 の中央値（1.00が理想。1より大きい＝推定が高すぎる）を、券種×人気帯で。
          馬単は「人気が上の馬→下の馬」と逆向きを分ける（推定式は向きを区別していない）。
使い方: python payout_est_audit.py [--fit]   # --fit で馬単の向き別係数を payout_coef.json に追記
"""
from __future__ import annotations
import argparse, collections, glob, json, math, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from payout_estimator import estimate, COEF, load_coef

SNAP = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "odds_snapshots"


def snapshots():
    """レースごとに、全券種がそろっている最新のスナップショットだけ使う"""
    best = {}
    for f in sorted(glob.glob(str(SNAP / "*" / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        o = d.get("odds", {})
        if all(o.get(t) for t in ("単勝", "馬連", "ワイド", "馬単", "3連複")):
            best[d["race_id"]] = d
    return list(best.values())


def band(pops):
    m = max(pops)
    return "1-3人気" if m <= 3 else "4-6人気まで" if m <= 6 else "7-10人気まで" if m <= 10 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="store_true")
    a = ap.parse_args()
    snaps = snapshots()
    days = sorted({d["race_date"] for d in snaps})
    print(f"■ 全券種のオッズがそろったスナップショット {len(snaps)}レース（{days[0]}〜{days[-1]}）")
    ratio = collections.defaultdict(list)
    fit_pts = {"fwd": [], "rev": []}
    for d in snaps:
        def f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        tan = {int(k): f(v[0]) for k, v in d["odds"]["単勝"].items() if f(v[0])}
        pop = {u: i + 1 for i, u in enumerate(sorted(tan, key=lambda u: tan[u]))}
        for t in ("馬連", "ワイド", "馬単", "3連複"):
            for k, v in d["odds"][t].items():
                nums = [int(k[i:i + 2]) for i in range(0, len(k), 2)]
                act = f(v[0])
                if not act or any(u not in tan for u in nums):
                    continue
                b = band([pop[u] for u in nums])
                if not b:
                    continue
                if t == "ワイド" and f(v[1]):
                    act = (act + f(v[1])) / 2                       # 下限と上限の中間
                est = estimate(t, [tan[u] for u in nums])
                if not est:
                    continue
                lab = t
                if t == "馬単":
                    fwd = pop[nums[0]] < pop[nums[1]]
                    lab = "馬単（人気→人気薄）" if fwd else "馬単（人気薄→人気）"
                    fit_pts["fwd" if fwd else "rev"].append((math.log(tan[nums[0]] * tan[nums[1]]), math.log(act)))
                ratio[(lab, b)].append(est / act)
    print(f"\n{'券種':<14}{'人気帯':<12}{'組数':>8}{'推定÷実際(中央値)':>16}{'25%点':>8}{'75%点':>8}")
    for (lab, b), xs in sorted(ratio.items()):
        xs.sort()
        print(f"{lab:<14}{b:<12}{len(xs):>8,}{statistics.median(xs):>14.2f}{xs[len(xs)//4]:>10.2f}{xs[len(xs)*3//4]:>8.2f}")

    # 馬単の向き別に log(実際) = a·log(単勝の積) + b を当てはめる
    print("\n■ 馬単を向き別に当てはめ直した係数")
    new = {}
    for key, lab in (("fwd", "馬単_人気順"), ("rev", "馬単_逆順")):
        pts = fit_pts[key]
        n = len(pts)
        mx, my = sum(x for x, y in pts) / n, sum(y for x, y in pts) / n
        aa = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, y in pts)
        bb = my - aa * mx
        new[lab] = {"a": round(aa, 4), "b": round(bb, 4), "n": n}
        print(f"  {lab}: a={aa:.4f} b={bb:.4f} n={n:,}")
    if a.fit:
        coef = load_coef()
        coef.update(new)
        COEF.write_text(json.dumps(coef, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  保存: {COEF}")


if __name__ == "__main__":
    main()
