# -*- coding: utf-8 -*-
"""
factor_audit_v2.py — 17因子が本当に効いているかを実測する
==========================================================================
なぜ必要か
----------
2026年9月の2週間で、買い方の探索（人気帯・血統）は**すべてhold-outで棄却**された。
共通の敗因は「市場が既に織り込んだ情報を、市場由来の特徴量で探していた」こと。
下流をいくら磨いても、指数そのものが市場を上回らない限り71%は動かない。

そこで最上流に戻り、**17因子の配点に根拠があるのか**を測る。

判明済みの欠陥（2026-09-09）
  ・**F15 EV(6%) と F16 人気乖離(2%) は前日時点で定数50にハードコードされている**
    （collect_weekend_bigdata.py: f15 = 50.0 / f16 = 50.0）
    → 指数の**8%が何の情報も運ばず**、点数の幅を圧縮して有効な因子を薄めているだけ
  ・しかも人気乖離は当日オッズで値が入るときは**逆効果**（2026-08-30実測。
    モデルが妙味と見た馬ほど回収率が低い）

🔴 この監査の要点：**市場人気で条件付けて測る**
--------------------------------------------------------------
単に「F01が高い馬は勝ちやすい」を見ても意味がない。それは
「強い馬は人気になる」を再発見しているだけで、市場を上回る情報ではない。
**同じ人気帯の中で差がつくか**を見る。ここで差が出ない因子は、
どれだけ勝率と相関していても指数に置く価値がない。

さらに **時期を分けて**測る（前2/3で見えたものが後1/3で再現するか）。
帯スキャンではこれを怠って in-sample の数字に飛びつき、hold-outで全滅した。

使い方
------
    python factor_audit_v2.py              # 全因子
    python factor_audit_v2.py --factor F01_後3F
"""
from __future__ import annotations
import argparse, sys, io
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import engine_backtest as B

FACTORS = ["F01_後3F", "F02_タイム", "F03_着差", "F04_騎手", "F05_厩舎",
           "F06_枠", "F07_馬番", "F08_距離", "F09_体重", "F10_斤量",
           "F11_性別", "F12_年齢", "F13_クラス", "F14_馬場",
           "F15_EV", "F16_乖離", "F17_頭数"]

# 前日予想の重み（daily_pdca/config.py）。監査結果と突き合わせる
WEIGHTS = {
    "F01_後3F": .15, "F02_タイム": .10, "F04_騎手": .10, "F03_着差": .08,
    "F06_枠": .08, "F05_厩舎": .07, "F09_体重": .06, "F15_EV": .06,
    "F10_斤量": .05, "F07_馬番": .04, "F08_距離": .04, "F12_年齢": .04,
    "F13_クラス": .04, "F11_性別": .03, "F14_馬場": .03,
    "F16_乖離": .02, "F17_頭数": .01,
}


def load() -> list[dict]:
    """リーク除外後の全出走馬を、着順・人気つきで平たく並べる"""
    races = B.drop_leaky(B.load_races(), verbose=False)
    out = []
    for (date, venue, rno), v in races.items():
        recs, odds, top3 = v["recs"], v["odds"], set(str(x) for x in v["top3"])
        # そのレースの人気順位を単勝オッズから作る
        valid = [(r, odds.get(str(r.get("馬番")))) for r in recs]
        valid = [(r, o) for r, o in valid if o]
        if len(valid) < 6:
            continue
        ranked = sorted(valid, key=lambda x: x[1])
        for pop, (r, o) in enumerate(ranked, 1):
            num = str(r.get("馬番"))
            out.append({
                "date": date, "pop": pop, "odds": o,
                "top3": num in top3,
                "win": top3 and list(v["top3"])[0] == num,
                "f": {k: r.get(k) for k in FACTORS},
            })
    return out


def _split(rows: list[dict]) -> tuple[list, list]:
    """時期で前2/3・後1/3に分ける（後ろが検証用）"""
    rows = sorted(rows, key=lambda x: x["date"])
    cut = len(rows) * 2 // 3
    return rows[:cut], rows[cut:]


def discrimination(rows: list[dict], key: str) -> dict:
    """
    その因子の判別力を測る。
      raw   : 全体で上位20% vs 下位20% の3着内率の差（人気の再発見を含む）
      cond  : **同じ人気帯の中で**上位半分 vs 下位半分 の3着内率の差 ← これが本命
    """
    vals = [r["f"].get(key) for r in rows]
    vals = [v for v in vals if isinstance(v, (int, float))]
    if len(vals) < 200:
        return {"n": len(vals), "const": True}
    lo, hi = sorted(vals)[len(vals)//5], sorted(vals)[len(vals)*4//5]
    if hi - lo < 1e-9:
        return {"n": len(vals), "const": True}      # 定数＝情報ゼロ

    top = [r for r in rows if isinstance(r["f"].get(key), (int, float))
           and r["f"][key] >= hi]
    bot = [r for r in rows if isinstance(r["f"].get(key), (int, float))
           and r["f"][key] <= lo]
    raw = (sum(r["top3"] for r in top)/len(top) -
           sum(r["top3"] for r in bot)/len(bot)) if top and bot else 0.0

    # ── 人気帯で条件付け ──
    by_pop = defaultdict(list)
    for r in rows:
        v = r["f"].get(key)
        if isinstance(v, (int, float)):
            by_pop[min(r["pop"], 9)].append(r)
    diffs, wts = [], []
    for p, rs in by_pop.items():
        if len(rs) < 100:
            continue
        rs = sorted(rs, key=lambda x: x["f"][key])
        h = rs[len(rs)//2:]
        l = rs[:len(rs)//2]
        if not h or not l:
            continue
        diffs.append(sum(x["top3"] for x in h)/len(h) - sum(x["top3"] for x in l)/len(l))
        wts.append(len(rs))
    cond = sum(d*w for d, w in zip(diffs, wts))/sum(wts) if wts else 0.0
    return {"n": len(vals), "const": False, "raw": raw, "cond": cond,
            "spread": hi - lo}


def main(only: str | None) -> None:
    rows = load()
    tr, va = _split(rows)
    print(f"═══ 因子監査 v2（リーク除外後 {len(rows):,}頭 / "
          f"学習期 {len(tr):,} ・ 検証期 {len(va):,}）═══\n")
    print("　raw  = 全体で上位20% vs 下位20% の3着内率の差")
    print("　      （※これは『強い馬は人気になる』の再発見を含むので、単体では意味がない）")
    print("　cond = **同じ人気帯の中で**上位半分 vs 下位半分 の差 ← 市場を上回る情報はここにしか無い")
    print("　両方の期間で cond が同じ向きに出ない因子は、指数に置く価値がない\n")

    print(f"{'因子':<12}{'重み':>6}{'raw':>8}{'cond学習':>10}{'cond検証':>10}  判定")
    print("─" * 62)

    rank = []
    for k in FACTORS:
        if only and k != only:
            continue
        a, b = discrimination(tr, k), discrimination(va, k)
        w = WEIGHTS.get(k, 0)
        if a.get("const") or b.get("const"):
            print(f"{k:<12}{w*100:>5.0f}%{'—':>8}{'—':>10}{'—':>10}  "
                  f"🔴 **定数＝情報ゼロ**（重みの{w*100:.0f}%が死んでいる）")
            rank.append((k, w, 0.0, "dead"))
            continue
        ca, cb = a["cond"], b["cond"]
        pos = ca > 0.005 and cb > 0.005
        neg = ca < -0.005 and cb < -0.005
        same = pos or neg
        if neg:
            # 両期間とも負＝「その因子で高得点の馬ほど、同じ人気の中で走らない」。
            # 情報はあるが**符号が逆**なので、加点に使うと指数を悪くする。
            jd = "🔴 **逆効果（符号が逆）**"
        elif pos and abs(cb) >= 0.02:
            jd = "✅ 再現・有効"
        elif pos:
            jd = "△ 再現するが小さい"
        elif ca * cb < 0:
            jd = "❌ 向きが反転＝使えない"
        else:
            jd = "— ほぼ無情報"
        print(f"{k:<12}{w*100:>5.0f}%{a['raw']*100:>7.1f}pt{ca*100:>9.1f}pt"
              f"{cb*100:>9.1f}pt  {jd}")
        rank.append((k, w, cb if same else 0.0, jd))

    if only:
        return

    print("\n═══ 重みの再配分案 ═══\n")
    print("　検証期でも同じ向きに出た因子の cond に比例して配分し直す。")
    print("　（無情報・反転した因子はゼロにする）\n")
    live = [(k, w, c) for k, w, c, j in rank if c > 0]
    tot = sum(c for _, _, c in live)
    if not tot:
        print("　🔴 検証期で再現する因子が1つも無い。指数そのものを作り直す必要がある。")
        return
    print(f"{'因子':<12}{'現行':>8}{'提案':>8}{'増減':>8}")
    print("─" * 38)
    for k, w, c in sorted(live, key=lambda x: -x[2]):
        new = c / tot
        print(f"{k:<12}{w*100:>7.0f}%{new*100:>7.0f}%{(new-w)*100:>+7.0f}pt")
    dead = [k for k, w, c, j in rank if c <= 0 and w > 0]
    if dead:
        lost = sum(w for k, w, c, j in rank if c <= 0)
        print(f"\n　ゼロにする因子: {', '.join(dead)}")
        print(f"　→ 現行はここに **{lost*100:.0f}%** の重みを割いている")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", choices=FACTORS)
    main(ap.parse_args().factor)
