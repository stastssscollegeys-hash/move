# -*- coding: utf-8 -*-
"""
roi_type_tracker.py — 型別（S/H/D）の実測を蓄積し、設計値と突き合わせる
======================================================================
年間120%は「目標」であって、達成は蓄積で近づける。
そのために毎週、型ごとに次を記録して設計値とのズレを見る。

    型別の 的中率 × 的中時回収率 = 寄与ROI

設計値（SKILL.md v6.3）
    S 的中率重視型  的中68% × 195% = 133%
    H 高配当型      的中26% × 460% = 120%

実測が設計値から離れたら、SPEC（race_type_v63.py）の数値と
型判定のしきい値を見直す。**推測ではなく実測で更新する**のが要点。

使い方
------
  python roi_type_tracker.py --add 20260906 S "阪神11R セントウルS" 5000 4370
  python roi_type_tracker.py --report
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
LEDGER = DB / "roi_by_type.json"

SPEC = {"S": {"name": "S 的中率重視型", "hit": 0.68, "ret": 1.95},
        "H": {"name": "H 高配当型",     "hit": 0.26, "ret": 4.60}}
TARGET = 1.20   # 年間目標


def _load() -> list:
    if LEDGER.exists():
        return json.load(open(LEDGER, encoding="utf-8"))
    return []


def add(date: str, rtype: str, race: str, invest: int, payout: int, note: str = "") -> None:
    rows = _load()
    rows.append({"date": date, "type": rtype, "race": race,
                 "invest": int(invest), "payout": int(payout),
                 "roi": round(payout / invest * 100, 1) if invest else 0.0,
                 "hit": payout > 0, "note": note})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"追加: {date} [{rtype}] {race} {invest:,}→{payout:,}円 ({payout/invest*100:.0f}%)")


def report() -> None:
    rows = _load()
    if not rows:
        print("まだ1件も記録がありません。--add で追加してください。")
        return
    by = defaultdict(list)
    for r in rows:
        by[r["type"]].append(r)

    print(f"═══ 型別 実測 vs 設計値（全{len(rows)}レース）═══\n")
    print(f"{'型':<16}{'R数':>5}{'投資':>10}{'払戻':>10}{'的中率':>8}{'的中時回収':>11}{'寄与ROI':>9}")
    print("─" * 72)
    tot_i = tot_p = 0
    for t in ["S", "H", "D"]:
        rs = by.get(t)
        if not rs:
            continue
        i = sum(x["invest"] for x in rs); p = sum(x["payout"] for x in rs)
        tot_i += i; tot_p += p
        hits = [x for x in rs if x["hit"]]
        hr = len(hits) / len(rs)
        hi = sum(x["invest"] for x in hits)
        hret = (sum(x["payout"] for x in hits) / hi) if hi else 0
        nm = SPEC.get(t, {}).get("name", t)
        print(f"{nm:<16}{len(rs):>5}{i:>10,}{p:>10,}{hr*100:>7.1f}%{hret*100:>10.0f}%{p/i*100 if i else 0:>8.0f}%")
    print("─" * 72)
    if tot_i:
        print(f"{'合計':<16}{len(rows):>5}{tot_i:>10,}{tot_p:>10,}{'':>8}{'':>11}{tot_p/tot_i*100:>8.0f}%")

    print(f"\n═══ 設計値とのズレ ═══\n")
    print(f"{'型':<16}{'的中率 実測/設計':>22}{'的中時回収 実測/設計':>24}{'判定':<20}")
    print("─" * 84)
    for t in ["S", "H"]:
        rs = by.get(t)
        if not rs:
            print(f"{SPEC[t]['name']:<16}{'—（未記録）':>22}"); continue
        hits = [x for x in rs if x["hit"]]
        hr = len(hits) / len(rs)
        hi = sum(x["invest"] for x in hits)
        hret = (sum(x["payout"] for x in hits) / hi) if hi else 0
        s = SPEC[t]
        judge = "サンプル不足" if len(rs) < 20 else (
            "設計どおり" if abs(hr * hret - s["hit"] * s["ret"]) < 0.25 else "要見直し")
        print(f"{s['name']:<16}{hr*100:>10.1f}% / {s['hit']*100:>5.0f}%"
              f"{hret*100:>14.0f}% / {s['ret']*100:>5.0f}%  {judge:<20}")
    print("\n※20レース未満は判定しない（偶然と区別できないため）")

    if tot_i:
        cur = tot_p / tot_i
        print(f"\n═══ 年間目標120%までの距離 ═══\n")
        print(f"  現状 {cur*100:.0f}%  →  目標 {TARGET*100:.0f}%")
        print(f"  必要な改善: あと {(TARGET/cur-1)*100:.0f}% 分の上積み" if cur > 0 else "  （まず的中を作る）")
        print(f"\n  達成の組み合わせ（的中率 × 的中時回収率 = 120%）")
        for hr in [0.68, 0.50, 0.40, 0.30, 0.26]:
            print(f"    的中率{hr*100:>4.0f}% なら 的中時回収 {TARGET/hr*100:>4.0f}% が必要")

    _significance(rows, tot_i, tot_p)


# ══════════════════════════════════════════════════════
# 統計的有意性 — 「今週150%だった」を実力の証拠にしないための歯止め
# ══════════════════════════════════════════════════════
# 両側95%・検出力80%で「回収率110%ある」と言うのに必要なベット数。
# 配当が高い券種ほど1ベットあたりの分散が大きく、必要数が跳ね上がる。
NEEDED_110 = {"単勝": 1505, "ワイド": 2500, "馬連": 6500, "3連複": 13800, "3連単": 20192}


def _significance(rows: list, tot_i: int, tot_p: int) -> None:
    n = len(rows)
    print(f"\n═══ この数字はまだ信用してよいか（統計的有意性）═══\n")
    if not n or not tot_i:
        print("  記録なし。")
        return

    # レース単位のROIの標準偏差から95%信頼区間を出す
    rois = [x["payout"] / x["invest"] for x in rows if x["invest"]]
    m = sum(rois) / len(rois)
    var = sum((x - m) ** 2 for x in rois) / (len(rois) - 1) if len(rois) > 1 else 0.0
    se = (var / len(rois)) ** 0.5
    lo, hi = (m - 1.96 * se) * 100, (m + 1.96 * se) * 100
    print(f"  実測 {m*100:.1f}%   95%信頼区間 [{lo:.0f}% 〜 {hi:.0f}%]（{n}レース）")
    if lo <= 100 <= hi:
        print("  🔴 区間が100%をまたいでいる ＝ **プラスともマイナスとも言えない**。")
        print("     この段階の高回収率を『実力がついた』根拠に使わない。台帳に貯めるだけにする。")
    elif hi < 100:
        print("  ⚠ 区間が100%を下回りきっている ＝ 統計的に負けが確定している水準。")
        print("     Busseti-Ryu-Boyd(2016)より、この状態の最適賭け金は0。まず賭け金を落とす。")
    else:
        print("  ✅ 区間が100%を上回りきっている ＝ エッジが統計的に確認できた。")

    print(f"\n  券種別・エッジ実証までの残りベット数（110%を主張する場合）")
    print(f"  {'券種':<8}{'必要':>9}{'現在':>8}{'残り':>9}{'週30なら'}")
    print("  " + "─" * 46)
    for k, need in NEEDED_110.items():
        rest = max(0, need - n)
        print(f"  {k:<8}{need:>9,}{n:>8,}{rest:>9,}{rest/30:>9.0f}週")
    print("\n  🔴 3連単の実証には約2万ベット＝実質不可能。**検証は単勝・ワイドで行う。**")
    print("     3連単・3連複は『実証できない券種』と割り切り、主軸に据えない。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", nargs="+", metavar=("DATE TYPE RACE INVEST PAYOUT"))
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.add:
        d, t, *rest = a.add
        race = " ".join(rest[:-2]); inv, pay = rest[-2], rest[-1]
        add(d, t, race, int(inv), int(pay))
    else:
        report()
