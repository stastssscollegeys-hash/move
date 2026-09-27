# -*- coding: utf-8 -*-
"""
factor_candidates.py — 既に保存しているのに指数に入れていない項目を因子として試す
==========================================================================
なぜこの形なのか
----------------
2026-09-09の一連の監査で「既存17因子の取捨選択は打ち止め」と分かった
（F01除去が唯一の当たり。他は全部ノイズ水準）。

次は外部データの因子化…と考えて追い切り評価を見に行ったが、
**追い切りは1件も蓄積されていなかった**（重賞ごとにその場で調べて捨てている）。
検証データが無いので今は因子化できない。

一方 records を調べると、**毎週保存しているのに指数に入っていない項目が14個**あり、
どれも有効率100%だった。こちらは今すぐ検証できる。

特に注目:
  ・**平均上がり** … F01は「過去5走の**最速**後3F」で逆効果だった。
    「最速は極値統計でノイズ」という仮説が正しければ、**平均**なら効くはず。
    この対比がそのまま仮説検定になる。
  ・**脚質** … F01が失敗したもう一つの理由（上がりは位置取りと組でしか意味を持たない）。
  ・**中日数 / 近5走複勝率** … 古典的だが指数に入っていない。

判定の関門は前回と同じ2つ。**ブートストラップ2,000回**と**時期5分割**の両方。
片方だけ通ったものは採用しない（300帯スキャンで全滅した教訓）。

使い方
------
    python factor_candidates.py
"""
from __future__ import annotations
import random, sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import engine_backtest as B
import weight_experiment as W

CURRENT = W.norm({k: v for k, v in W.BASE.items() if k != "F01_後3F"})
ADD_W = 0.08          # 候補因子に与える重み（既存はその分だけ按分して縮める）

# 候補: (records上の名前, 0-100点への変換, 説明)
#   高いほど良い向きに揃える。向きを間違えると「効かない」ではなく「逆効果」に見える。
CANDIDATES = {
    "平均上がり":     (lambda v: max(0.0, min(100.0, (40.0 - v) / 4.0 * 100.0)),
                     "過去の平均上がり（速いほど高得点）★F01の最速版と対比"),
    "近5走複勝率%":   (lambda v: max(0.0, min(100.0, v)), "直近の安定度"),
    "近5走平均着":    (lambda v: max(0.0, min(100.0, (10.0 - v) / 9.0 * 100.0)), "直近の平均着順"),
    "同距離複勝率%":  (lambda v: max(0.0, min(100.0, v)), "この距離での実績"),
    "同距離走数":     (lambda v: max(0.0, min(100.0, v * 12.5)), "この距離の経験量"),
    "中日数":         (lambda v: 100.0 if 14 <= v <= 35 else (70.0 if v < 14 else
                       max(20.0, 100.0 - (v - 35) * 1.2)), "使い頃か（14〜35日を最良）"),
    "騎手勝率%":      (lambda v: max(0.0, min(100.0, v * 5.0)), "騎手の生の勝率"),
    "厩舎勝率%":      (lambda v: max(0.0, min(100.0, v * 5.0)), "厩舎の生の勝率"),
    "父勝率%":        (lambda v: max(0.0, min(100.0, v * 5.0)), "種牡馬の勝率（0は欠損）"),
    "DB平均着順":     (lambda v: max(0.0, min(100.0, (12.0 - v) / 11.0 * 100.0)), "蓄積DBでの平均着順"),
}
# 脚質は数値でないので別扱い（当該開催のバイアスは見ず、素の傾向だけ）
STYLE = {"逃げ": 62.0, "先行": 70.0, "差し": 52.0, "追込": 42.0, "?": 50.0}


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
            o, ml = odds.get(num), r.get("ML能力%")
            if o is None or not isinstance(ml, (int, float)):
                continue
            rows.append({"num": num, "odds": o, "ml": float(ml),
                         "f": {k: r.get(k) for k in W.BASE},
                         "extra": {k: r.get(k) for k in list(CANDIDATES) + ["脚質"]},
                         "top3": num in top3})
        if len(rows) >= 6:
            out.append({"date": date, "rows": rows})
    return sorted(out, key=lambda x: x["date"])


def score(row: dict, name: str | None) -> float:
    s = sum((row["f"].get(k) if isinstance(row["f"].get(k), (int, float)) else 50.0) * wt
            for k, wt in CURRENT.items())
    if name:
        s *= (1 - ADD_W)                     # 既存を縮めて候補ぶんの席を作る
        v = row["extra"].get(name)
        if name == "脚質":
            add = STYLE.get(str(v), 50.0)
        elif isinstance(v, (int, float)):
            add = CANDIDATES[name][0](float(v))
        else:
            add = 50.0
        s += add * ADD_W
    return s * (1 - W.ML_MIX) + row["ml"] * W.ML_MIX


def hits(races: list, name: str | None) -> list[int]:
    return [1 if max(rc["rows"], key=lambda r: score(r, name))["top3"] else 0
            for rc in races]


def main() -> None:
    races = load()
    n = len(races)
    base = hits(races, None)
    b = sum(base) / n
    k = n // 5
    bounds = [(i * k, (i + 1) * k if i < 4 else n) for i in range(5)]

    print(f"═══ 未使用フィールドを因子に足した効果（{n}レース）═══\n")
    print(f"　基準（現行・F01除去済）の ◎3着内率 = {b*100:.1f}%")
    print(f"　各候補に重み{ADD_W*100:.0f}%を与え、既存因子をその分だけ縮めて比較\n")
    print("　⚠ 11回の比較＝多重比較。**ブートストラップと時期5分割の両方**を")
    print("　　通ったものだけ採用する（改善確率の高い順に採るのは禁止）\n")
    print(f"{'候補':<14}{'3着内率':>9}{'差':>8}{'95%区間':>18}{'改善確率':>9}{'5分割':>7}  説明")
    print("─" * 96)

    keep = []
    for name in list(CANDIDATES) + ["脚質"]:
        h = hits(races, name)
        v = sum(h) / n
        d = v - b
        delta = [h[i] - base[i] for i in range(n)]
        random.seed(11)
        dif = sorted(sum(random.choices(delta, k=n)) / n for _ in range(2000))
        lo, hi = dif[50], dif[1949]
        p = sum(1 for x in dif if x > 0) / 2000
        wins = sum(1 for a, z in bounds if sum(h[a:z]) > sum(base[a:z]))
        ok = lo > 0 and wins >= 4
        if ok:
            keep.append((name, d, lo, hi, p, wins))
        desc = "走る脚質ほど高得点" if name == "脚質" else CANDIDATES[name][1]
        print(f"{name:<14}{v*100:>8.1f}%{d*100:>+7.1f}pt"
              f"{f'[{lo*100:+.1f}〜{hi*100:+.1f}]':>18}{p*100:>8.1f}%{wins:>5}/5"
              f"{'  ★' if ok else '  '}{desc}")

    print(f"\n═══ 判定 ═══\n")
    if not keep:
        print("　両方の関門を通った候補は無い。既存の保存項目からは新しい因子を作れない。")
        print("　→ **本当に新しい情報**（追い切り・厩舎コメント・当日の馬体重）を")
        print("　　 蓄積し始めるしかない。現状それらは1件も保存していない。")
    else:
        for name, d, lo, hi, p, wins in keep:
            print(f"　★ {name}: {d*100:+.1f}pt（区間[{lo*100:+.1f}〜{hi*100:+.1f}]・"
                  f"改善確率{p*100:.1f}%・5分割{wins}/5）")
        print("\n　⚠ 採用前に、重みを振り直して最適値を探すこと（今回は一律8%で試しただけ）")


if __name__ == "__main__":
    main()
