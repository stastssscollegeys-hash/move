# -*- coding: utf-8 -*-
"""
weight_experiment.py — 因子の重みを変えて印の質が上がるかを実測する
==========================================================================
なぜこの形なのか
----------------
2026-09-09の因子監査で「指数の29%が定数か逆効果」と分かったが、
**そこから素直に導いた『定数を外す』は順位を1ミリも動かさない**。

    総合指数 = 独自指数×0.55 + ML能力%×0.45
    AI印     = 総合指数の**順位**（1位◎ 2位○ 3位▲ 4-5位△）

独自指数は因子の加重和なので、**全馬に同じ値を足す定数因子は順位に影響しない**。
F15_EV(6%)とF16_乖離(2%)は完全に定数、F09_体重(6%)も96.5%が既定値70。
→ この14%を外しても印は変わらない。**見かけの整理でしかない。**

実際に順位を動かすのは、**馬ごとに値が違う因子**の重みだけ。
中でもF01_後3F(15%)は両期間とも符号が逆（1番人気で-11.8pt）なので、
ここを触ったときに印の質が上がるかを測る。

測り方
------
records に保存済みの F01〜F17 と ML能力% から独自指数を**組み直して**再ランクする。
特徴量の再計算は不要なので、重み案を何通りでも即座に試せる。
評価は **検証期（後1/3）のみ**。学習期での改善は証拠にならない。

使い方
------
    python weight_experiment.py
"""
from __future__ import annotations
import sys, io
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import engine_backtest as B

# 現行の重み（daily_pdca/config.py）
BASE = {
    "F01_後3F": .15, "F02_タイム": .10, "F03_着差": .08, "F04_騎手": .10,
    "F05_厩舎": .07, "F06_枠": .08, "F07_馬番": .04, "F08_距離": .04,
    "F09_体重": .06, "F10_斤量": .05, "F11_性別": .03, "F12_年齢": .04,
    "F13_クラス": .04, "F14_馬場": .03, "F15_EV": .06, "F16_乖離": .02,
    "F17_頭数": .01,
}
# 監査で「両期間とも正の向きに再現した」5因子
VALIDATED = ["F02_タイム", "F03_着差", "F04_騎手", "F14_馬場", "F17_頭数"]
ML_MIX = 0.45          # 総合指数に占めるMLの比率


def norm(w: dict) -> dict:
    s = sum(w.values())
    return {k: v / s for k, v in w.items()} if s else w


def variants() -> dict[str, dict]:
    v = {"① 現行": dict(BASE)}

    # 定数3つを外す（順位は変わらないはず＝対照実験）
    w = {k: x for k, x in BASE.items() if k not in ("F09_体重", "F15_EV", "F16_乖離")}
    v["② 定数3つを除去"] = norm(w)

    # F01を外す
    w = {k: x for k, x in BASE.items() if k != "F01_後3F"}
    v["③ F01を除去"] = norm(w)

    # F01の符号を反転（逆効果なら反転で改善するはず）
    v["④ F01を反転"] = dict(BASE)          # 適用側で 100-F01 にする

    # 検証済み5因子だけ
    v["⑤ 検証済み5因子のみ"] = norm({k: BASE[k] for k in VALIDATED})

    # 定数もF01も外す
    w = {k: x for k, x in BASE.items()
         if k not in ("F09_体重", "F15_EV", "F16_乖離", "F01_後3F")}
    v["⑥ 定数3つ+F01を除去"] = norm(w)
    return v


def load():
    races = B.drop_leaky(B.load_races(), verbose=False)
    out = []
    for (date, venue, rno), v in races.items():
        recs, odds, top3 = v["recs"], v["odds"], [str(x) for x in v["top3"]]
        if len(recs) < 6 or not top3:
            continue
        rows = []
        for r in recs:
            num = str(r.get("馬番"))
            o = odds.get(num)
            ml = r.get("ML能力%")
            if o is None or not isinstance(ml, (int, float)):
                continue
            rows.append({"num": num, "odds": o, "ml": float(ml),
                         "f": {k: r.get(k) for k in BASE},
                         "top3": num in top3, "win": num == top3[0]})
        if len(rows) >= 6:
            out.append({"date": date, "rows": rows})
    return sorted(out, key=lambda x: x["date"])


def score(row: dict, w: dict, flip_f01: bool) -> float:
    s = 0.0
    for k, wt in w.items():
        v = row["f"].get(k)
        if not isinstance(v, (int, float)):
            v = 50.0
        if flip_f01 and k == "F01_後3F":
            v = 100.0 - v
        s += v * wt
    return s * (1 - ML_MIX) + row["ml"] * ML_MIX


def evaluate(races: list, w: dict, flip: bool) -> dict:
    hon3 = hon1 = ret = n = 0
    for rc in races:
        rows = sorted(rc["rows"], key=lambda r: -score(r, w, flip))
        hon = rows[0]
        n += 1
        if hon["top3"]:
            hon3 += 1
        if hon["win"]:
            hon1 += 1
            ret += hon["odds"] * 100
    return {"n": n, "top3": hon3 / n if n else 0, "win": hon1 / n if n else 0,
            "roi": ret / (n * 100) if n else 0}


def main() -> None:
    races = load()
    cut = len(races) * 2 // 3
    tr, va = races[:cut], races[cut:]
    print(f"═══ 重み変更の実測（リーク除外 {len(races)}レース）═══\n")
    print(f"　学習期 {len(tr)}R（{tr[0]['date']}〜{tr[-1]['date']}） / "
          f"検証期 {len(va)}R（{va[0]['date']}〜{va[-1]['date']}）")
    print("　◎＝総合指数1位。**検証期の数字だけを見ること**\n")
    print(f"{'重み案':<20}{'◎3着内(学習)':>13}{'◎3着内(検証)':>13}"
          f"{'◎勝率(検証)':>12}{'◎単回収(検証)':>14}")
    print("─" * 74)

    base_va = None
    for name, w in variants().items():
        flip = "反転" in name
        a, b = evaluate(tr, w, flip), evaluate(va, w, flip)
        if base_va is None:
            base_va = b
        d = (b["top3"] - base_va["top3"]) * 100
        mark = "" if name.startswith("①") else f"  ({d:+.1f}pt)"
        print(f"{name:<20}{a['top3']*100:>12.1f}%{b['top3']*100:>12.1f}%"
              f"{b['win']*100:>11.1f}%{b['roi']*100:>13.0f}%{mark}")

    print("\n　参考: 市場1番人気の3着内率と比べる（これを超えなければ印に価値はない）")
    fav3 = fav1 = fret = 0
    for rc in va:
        f = min(rc["rows"], key=lambda r: r["odds"])
        if f["top3"]:
            fav3 += 1
        if f["win"]:
            fav1 += 1
            fret += f["odds"] * 100
    n = len(va)
    print(f"{'市場1番人気':<20}{'—':>12}{fav3/n*100:>12.1f}%"
          f"{fav1/n*100:>11.1f}%{fret/(n*100)*100:>13.0f}%")


if __name__ == "__main__":
    main()
