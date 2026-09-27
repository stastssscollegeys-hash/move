# -*- coding: utf-8 -*-
"""
oikiri_store.py — 追い切り評価を貯めて、いずれ因子化できるようにする
==========================================================================
なぜ必要か
----------
2026-09-09の一連の監査で、指数の改善余地が尽きた:

  ・既存17因子の取捨選択 → F01除去が唯一の当たり。他は全部ノイズ水準
  ・保存済みの未使用14項目を因子化 → **両関門を通る候補ゼロ**
    （平均上がり -2.6pt、近5走複勝率 -2.1pt、同距離複勝率 -2.9pt と有意に悪化。
      ML能力%が既に過去成績を織り込んでおり二重計上になるため）
  ・◎の3着内率は改善後50.4%だが、市場1番人気は60.5%。**まだ10pt負けている**

残る道は「本当に新しい情報」の因子化だが、**追い切りは1件も蓄積されていなかった**。
毎週の重賞リサーチでうましる等から取得していながら、予想に使って捨てていた。

netkeibaの追い切りページは**有料プレミアム**で無料スクレイピング不可（2026-09-09確認）。
自動全レース収集は当面できない。

→ **既に手作業で調べている重賞ぶんだけでも貯める。** 追加コストはゼロ。
   週2〜4レース×十数頭でも、3ヶ月で500〜800頭になり検証の入口に立てる。
   貯め始めない限り、永遠に検証できない。

使い方
------
  # 1レース分をまとめて記録（重賞リサーチの直後に実行する）
  python oikiri_store.py --add 20260913 中山 11 "馬名:S 別の馬:A 三頭目:B"

  # 現況（何頭貯まったか・検証可能まであとどれくらいか）
  python oikiri_store.py

  # 結果と突き合わせて、追い切り評価に予測力があるか見る（データが貯まってから）
  python oikiri_store.py --evaluate
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
STORE = DB / "oikiri.json"

# うましるのS〜E評価を点数化（SKILL.mdのsc[9]と同じ対応にする）
GRADE = {"S": 9.0, "A": 8.0, "B": 7.0, "C": 6.0, "D": 5.0, "E": 4.0}

# 検証に入れる目安。単勝でエッジを主張するには1,505ベット要るが、
# 「追い切り上位と下位で3着内率に差があるか」を見るだけなら数百頭で足りる。
TARGET_HORSES = 600


def load() -> list[dict]:
    return json.load(open(STORE, encoding="utf-8")) if STORE.exists() else []


def add(date: str, venue: str, rno: int, spec: str) -> None:
    """spec は "馬名:S 別の馬:A" の形式。空白区切り・コロンで評価を指定"""
    rows = load()
    key = {(r["date"], r["venue"], r["R"], r["馬名"]) for r in rows}
    n = 0
    for item in spec.split():
        if ":" not in item:
            print(f"  ⚠ 形式が違うので飛ばす: {item}")
            continue
        name, g = item.rsplit(":", 1)
        g = g.upper()
        if g not in GRADE:
            print(f"  ⚠ 評価が S〜E でない: {item}")
            continue
        k = (date, venue, int(rno), name)
        if k in key:
            continue
        rows.append({"date": date, "venue": venue, "R": int(rno),
                     "馬名": name, "評価": g, "点": GRADE[g]})
        n += 1
    STORE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"追加 {n}頭 → 累計 {len(rows)}頭（{STORE.name}）")


def status() -> None:
    rows = load()
    print("═══ 追い切り評価の蓄積状況 ═══\n")
    if not rows:
        print("　まだ0頭。**貯め始めない限り永遠に検証できない。**\n")
        print("　毎週の重賞リサーチでうましる等の評価を得た直後に、")
        print("　そのまま次を実行すること（追加コストはゼロ）:")
        print('     python oikiri_store.py --add 20260913 中山 11 "馬名:S 別の馬:A"')
        print(f"\n　目安 {TARGET_HORSES}頭で検証の入口。重賞2〜4R×十数頭なら約3ヶ月。")
        return
    days = sorted({r["date"] for r in rows})
    print(f"　{len(rows)}頭 / {len(days)}開催日（{days[0]}〜{days[-1]}）")
    g = defaultdict(int)
    for r in rows:
        g[r["評価"]] += 1
    print("　評価の分布: " + " ".join(f"{k}={g[k]}" for k in "SABCDE" if g[k]))
    rest = max(0, TARGET_HORSES - len(rows))
    print(f"\n　検証の入口({TARGET_HORSES}頭)まで あと {rest}頭"
          f"（重賞3R×14頭/週なら約{rest/42:.0f}週）")


def evaluate() -> None:
    """蓄積した評価と実際の着順を突き合わせる"""
    rows = load()
    if len(rows) < 100:
        print(f"まだ{len(rows)}頭。100頭を超えてから評価する（それ未満は偶然と区別できない）。")
        return
    res = json.load(open(DB / "race_results.json", encoding="utf-8"))
    idx = {}
    for r in res:
        try:
            idx[(str(r.get("date")), r.get("競馬場"), int(r.get("R")), r.get("馬名"))] = {
                "rank": int(str(r["着順"]).strip()), "pop": int(float(r["人気"])),
                "odds": float(r["単勝オッズ"])}
        except (TypeError, ValueError, KeyError):
            continue

    by = defaultdict(lambda: {"n": 0, "t3": 0, "ret": 0.0, "pop": 0})
    for r in rows:
        m = idx.get((r["date"], r["venue"], r["R"], r["馬名"]))
        if not m:
            continue
        s = by[r["評価"]]
        s["n"] += 1
        s["pop"] += m["pop"]
        if m["rank"] <= 3:
            s["t3"] += 1
        if m["rank"] == 1:
            s["ret"] += m["odds"] * 100

    print(f"═══ 追い切り評価 × 結果 ═══\n")
    print("　⚠ 評価が高い馬は人気にもなる。**平均人気を併記**して、")
    print("　　単に人気を再発見していないかを必ず確認すること\n")
    print(f"{'評価':<6}{'頭数':>6}{'3着内率':>9}{'単回収':>8}{'平均人気':>9}")
    print("─" * 40)
    for k in "SABCDE":
        s = by.get(k)
        if not s or not s["n"]:
            continue
        print(f"{k:<6}{s['n']:>6}{s['t3']/s['n']*100:>8.1f}%"
              f"{s['ret']/(s['n']*100)*100:>7.0f}%{s['pop']/s['n']:>8.1f}")
    tot = sum(s["n"] for s in by.values())
    print(f"\n　突合できた {tot}頭。同じ人気帯の中で差が出るかを見るには"
          f"あと{max(0, TARGET_HORSES-tot)}頭ほしい。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", nargs=4, metavar=("DATE", "VENUE", "R", "SPEC"))
    ap.add_argument("--evaluate", action="store_true")
    a = ap.parse_args()
    if a.add:
        add(a.add[0], a.add[1], int(a.add[2]), a.add[3])
    elif a.evaluate:
        evaluate()
    else:
        status()
