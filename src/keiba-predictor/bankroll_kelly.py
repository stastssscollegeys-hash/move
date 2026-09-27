# -*- coding: utf-8 -*-
"""
bankroll_kelly.py — 資金配分（ケリー基準）と破産確率
==========================================================================
なぜ必要か
----------
これまで「1レースの予算」の中で配分を決めてきたが、
**その予算自体がバンクロール（総資金）に対して適正かを一度も検証していなかった。**

文献調査（2026-09-06）で判明した事実:

  ・3連単/3連複に「バンクロールの1%」を張るのは **ケリーの約4倍賭け**
  ・回収率110%相当のエッジがあっても f* ≈ 0.1〜0.35%（ハーフケリーならその半分）
  ・エッジが本物(+8.75%)でも1%を張り続けると、1,000R後の資金中央値は**半減**、
    利益が出る確率は**32%**まで落ちる（モンテカルロ20,000軌道）
  ・フルケリーは**50%の確率でいつか資産が半減**する（Thorp 2006 の厳密解）
  ・**エッジがマイナスなら、賭け金をどう工夫しても破産確率は数学的に1**
    （Busseti-Ryu-Boyd 2016。最適解は「賭けない」）

🔴 現状の実測回収率69.8%でフラット1万円/レースを続けた場合:
   **約332レースで資金ゼロ。週末36Rなら約9週間。**

参考文献
--------
  Kelly (1956) Bell System Technical Journal 35(4):917-926
  Thorp (2006) "The Kelly Capital Growth Criterion" §7.3
  MacLean, Ziemba & Blazenko (1992) Management Science 38(11)
  Busseti, Ryu & Boyd (2016) "Risk-Constrained Kelly Gambling"
  Benter (1994) — 実務推奨は 1/2 または 1/3 ケリー
  Uhrín et al. (2021) arXiv:2107.08827 — 韓国2,700Rで素朴な傾斜は破産率85.2%
"""
from __future__ import annotations
import math
import sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 推奨するケリー分数。文献の実務値は 1/4〜1/2、ブラックジャックチームで 0.3〜0.7
KELLY_FRACTION = 0.25      # 保守側。エッジが未実証の段階ではこれ以上上げない
FULL_KELLY_HALVING_PROB = 0.50

# 1レースあたりの投資上限（2026-09-06ユーザー確定・目安）
# 実測69.8%のままでも約331レース＝9.2週もつ水準。
# **上限であって標準額ではない**。全レースに1万円張る意味ではなく、
# 実際の額は従来どおり期待値で決める（見送り・薄張りの判断は変えない）。
MAX_STAKE_PER_RACE = 10_000


def kelly_fraction(roi: float, odds: float) -> float:
    """
    1点あたりのケリー比率（バンクロールに対する割合）。
      f* = (回収率 - 1) / (オッズ - 1)
    roi: その買い目の期待回収率（1.10 なら +10%のエッジ）
    """
    if odds <= 1.0:
        return 0.0
    f = (roi - 1.0) / (odds - 1.0)
    return max(0.0, f)


def stake(bankroll: int, roi: float, odds: float, frac: float = KELLY_FRACTION,
          unit: int = 100) -> int:
    """実際に張る金額（100円単位）。エッジがなければ0を返す"""
    f = kelly_fraction(roi, odds) * frac
    amt = bankroll * f
    return int(amt / unit) * unit if amt >= unit else 0


def drawdown_prob(frac: float, x: float = 0.5) -> float:
    """
    ケリー分数 c で運用したとき、資産がいつか x 倍を割る確率。
      P = x^(2/c - 1)     （Thorp 2006 の厳密解）
    """
    if frac <= 0:
        return 0.0
    if frac >= 2.0:
        return 1.0
    return x ** (2.0 / frac - 1.0)


def growth_ratio(frac: float) -> float:
    """フルケリーに対する成長率の比 = 2c - c^2"""
    return 2 * frac - frac * frac


def ruin_races(bankroll: int, stake_per_race: int, roi: float) -> float | None:
    """
    期待値マイナスのまま賭け続けた場合、資金がゼロになるまでの概算レース数。
    1レースあたりの期待損失 = stake × (1 - roi)
    """
    loss = stake_per_race * (1.0 - roi)
    if loss <= 0:
        return None                      # 期待値プラスなら破産は確定しない
    return bankroll / loss


# ══════════════════════════════════════════════════════
# エッジ検証に必要なサンプル数（両側95%・検出力80%）
# ══════════════════════════════════════════════════════
# 「回収率110%ある」と統計的に言うのに必要なベット数。
# σ は1ベットあたりの回収率の標準偏差で、配当が高い券種ほど大きい。
SAMPLE_NEEDED = {
    #  券種         平均オッズ  σ     110%検出   105%検出
    "単勝":        (3.2,  1.39,   1505,   6021),
    "ワイド":      (5.0,  1.80,   2500,  10000),
    "馬連":        (12.0, 2.90,   6500,  26000),
    "3連複":       (25.0, 4.20,  13800,  55000),
    "3連単":       (36.0, 5.08,  20192,  80770),
}


def needed_bets(ticket: str, target_roi: float = 1.10) -> int | None:
    """その券種で目標回収率を統計的に主張するのに必要なベット数"""
    v = SAMPLE_NEEDED.get(ticket)
    if not v:
        return None
    return v[2] if target_roi >= 1.10 else v[3]


def weeks_to_verify(ticket: str, bets_per_weekend: int = 30,
                    target_roi: float = 1.10) -> float | None:
    n = needed_bets(ticket, target_roi)
    return None if not n else n / bets_per_weekend


def report(bankroll: int = 1_000_000, current_roi: float = 0.698) -> str:
    L = ["═══ 資金配分レポート（ケリー基準）═══", "",
         f"バンクロール {bankroll:,}円 ／ 現在の実測回収率 {current_roi*100:.1f}%", ""]

    # ① 現状の危険度
    L.append("【① いま賭け続けるとどうなるか】")
    for s in (5000, 10000, 20000, 27200):
        r = ruin_races(bankroll, s, current_roi)
        if r:
            mark = ("  ← 上限（2026-09-06確定）" if s == MAX_STAKE_PER_RACE
                    else "  ← 上限超過" if s > MAX_STAKE_PER_RACE else "")
            L.append(f"　1レース{s:,}円 → 約{r:.0f}レースで資金ゼロ"
                     f"（週末36Rなら約{r/36:.1f}週）{mark}")
    L.append("　※期待値がマイナスである限り、配分をどう工夫しても破産確率は数学的に1。")
    L.append("　　Busseti-Ryu-Boyd(2016)の定理より、この状態の最適解は『賭けない』。")
    L.append("")

    # ② エッジがあると仮定した場合の適正額
    L.append("【② 仮にエッジがあった場合の1点あたり適正額】")
    L.append(f"{'想定回収率':>10}{'オッズ':>8}{'フルKelly':>11}{'1/4Kelly':>11}{'金額(1/4)':>12}")
    L.append("─" * 54)
    for roi in (1.05, 1.10, 1.20):
        for od in (3.0, 10.0, 30.0, 100.0):
            f = kelly_fraction(roi, od)
            L.append(f"{roi*100:>9.0f}%{od:>7.0f}倍{f*100:>10.3f}%"
                     f"{f*KELLY_FRACTION*100:>10.3f}%{int(bankroll*f*KELLY_FRACTION):>11,}円")
    L.append("")
    L.append("　🔴 回収率110%でも100倍配当なら1/4ケリーで約250円。")
    L.append("　　 『バンクロールの1%』はケリーの4倍賭けで、資金中央値は半減する。")
    L.append("")

    # ③ ケリー分数の選択
    L.append("【③ ケリー分数ごとのリスク】(Thorp 2006 の厳密解)")
    L.append(f"{'分数':>8}{'成長率比':>10}{'半減確率':>10}{'1/4になる確率':>14}")
    L.append("─" * 44)
    for c in (1.00, 0.50, 0.25):
        L.append(f"{c:>8.2f}{growth_ratio(c)*100:>9.0f}%{drawdown_prob(c,0.5)*100:>9.1f}%"
                 f"{drawdown_prob(c,0.25)*100:>13.2f}%")
    L.append("　フルケリーは50%の確率でいつか半減する。実務推奨は1/4〜1/2。")
    L.append("")

    # ④ エッジ検証に必要なサンプル
    L.append("【④ 『回収率110%ある』と言うのに必要なベット数】")
    L.append(f"{'券種':<8}{'必要ベット':>11}{'週30ベットで':>14}")
    L.append("─" * 36)
    for t in SAMPLE_NEEDED:
        n = needed_bets(t)
        L.append(f"{t:<8}{n:>10,}{weeks_to_verify(t)/1:>12.0f}週")
    L.append("　🔴 3連単で110%を主張するには2万ベット必要。")
    L.append("　　 数百ベットのバックテストで出た高回収率はノイズと区別できない。")
    return "\n".join(L)


if __name__ == "__main__":
    print(report())
