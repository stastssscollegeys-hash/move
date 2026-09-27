# -*- coding: utf-8 -*-
"""
sire_analysis.py — 自前DBによる種牡馬分析（navi-keiba相当を自分で作る）
==========================================================================
navi-keiba.com は種牡馬ごとに「距離別・コース別・馬場別」を載せているが、
**データが画像なので機械集計に使えない**（2026-09-07に実地確認）。
JBISは無料でHTMLテーブルを持つが距離別・コース別の内訳が無い。

そこで自前DBで同等の集計を作る。こちらの利点:
  ・区切り方を自分で決められる（他サイトの集計単位に縛られない）
  ・**回収率**まで出せる（多くのサイトは勝率・複勝率止まり）
  ・市場人気と突き合わせて「人気に織り込まれていない差」を測れる

🔴 最重要の注意
---------------
種牡馬別の高回収率は**ほぼ小サンプルのノイズ**である。
このスクリプトは必ず次を併記する:
  ① 出走数（少ないものは判断材料にしない）
  ② 上位1件の払戻を除いた回収率（1頭依存かどうか）
  ③ 同じ人気帯の全馬平均との差（血統固有の効果か、単に人気馬が多いだけか）

使い方
------
    python sire_analysis.py                 # 全体サマリ
    python sire_analysis.py --sire キズナ    # 1頭を詳しく（navi-keiba相当）
    python sire_analysis.py --min-runs 50   # 出走数のしきい値を変える
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"

# 等額買いの基準線（オッズ比例の上限80%ではない。ここを間違えると
# 実力ゼロの集団を「善戦している」と誤読する）
FLAT_BASELINE = 0.72


def parse_course(s: str) -> tuple[str, int]:
    """'ダート1600m' → ('ダート', 1600)。芝/ダート/障害の別と距離を分ける"""
    t = str(s or "")
    surface = "ダート" if "ダ" in t else ("障害" if "障" in t else ("芝" if "芝" in t else ""))
    digits = "".join(c for c in t if c.isdigit())
    return surface, int(digits) if digits else 0


def load() -> list[dict]:
    rows = json.load(open(DB / "race_results.json", encoding="utf-8"))
    out = []
    for r in rows:
        if not r.get("父"):
            continue
        try:
            surface, dist = parse_course(r.get("距離"))
            out.append({
                "sire": r["父"], "bms": r.get("母父", ""),
                "rank": int(str(r["着順"]).strip()),
                "odds": float(r["単勝オッズ"]), "pop": int(float(r["人気"])),
                "dist": dist, "surface": surface,
                "venue": r.get("競馬場", ""), "baba": r.get("馬場状態", ""),
                "style": r.get("脚質", ""),
            })
        except (TypeError, ValueError, KeyError):
            continue
    return out


def agg(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    wins = [r["odds"] for r in rows if r["rank"] == 1]
    ret = sum(wins) * 100
    top = max(wins) * 100 if wins else 0
    return {
        "n": n,
        "win": sum(1 for r in rows if r["rank"] == 1) / n,
        "p3": sum(1 for r in rows if r["rank"] <= 3) / n,
        "roi": ret / (n * 100),
        "roi_ex": (ret - top) / (n * 100),      # 最高配当1件を除く
        "pop": sum(r["pop"] for r in rows) / n,
    }


def dist_cat(d: int) -> str:
    if d <= 1400: return "〜1400m"
    if d <= 1800: return "1401-1800m"
    if d <= 2200: return "1801-2200m"
    return "2201m〜"


def summary(rows: list[dict], min_runs: int) -> None:
    by = defaultdict(list)
    for r in rows:
        by[r["sire"]].append(r)

    # 人気帯ごとの全体平均（比較の土台）
    pop_base = defaultdict(list)
    for r in rows:
        pop_base[min(r["pop"], 9)].append(r)
    base = {k: agg(v) for k, v in pop_base.items()}

    print(f"═══ 種牡馬別成績（自前DB {len(rows):,}頭・出走{min_runs}以上）═══\n")
    print("　単勝回収率は等額買いの基準線72%と比べる（80%ではない）")
    print("　『除外後』＝最高配当1件を除いた回収率。ここが大きく落ちるものは1頭依存\n")
    print(f"{'種牡馬':<18}{'出走':>5}{'平均人気':>8}{'勝率':>7}{'複勝率':>8}"
          f"{'単回収':>8}{'除外後':>8}{'人気補正':>9}")
    print("─" * 72)

    ranked = []
    for s, rs in by.items():
        if len(rs) < min_runs:
            continue
        a = agg(rs)
        # 同じ人気構成の馬が平均で出す回収率（＝人気で説明できるぶん）
        exp = sum(base[min(r["pop"], 9)]["roi"] for r in rs) / len(rs)
        a["edge"] = a["roi"] - exp
        a["sire"] = s
        ranked.append(a)

    for a in sorted(ranked, key=lambda x: -x["edge"]):
        print(f"{a['sire']:<18}{a['n']:>5}{a['pop']:>8.1f}{a['win']*100:>6.1f}%"
              f"{a['p3']*100:>7.1f}%{a['roi']*100:>7.0f}%{a['roi_ex']*100:>7.0f}%"
              f"{a['edge']*100:>+8.0f}pt")

    print(f"\n　人気補正 = その種牡馬の回収率 − 同じ人気構成の馬の平均回収率")
    print(f"　これがプラスでないと「血統固有の上積み」とは言えない")
    n_pos = sum(1 for a in ranked if a["edge"] > 0)
    print(f"　→ 集計{len(ranked)}頭中、人気補正がプラスは {n_pos}頭")


def detail(rows: list[dict], sire: str) -> None:
    rs = [r for r in rows if sire in r["sire"]]
    if not rs:
        print(f"該当なし: {sire}")
        return
    nm = rs[0]["sire"]
    a = agg(rs)
    print(f"═══ {nm} 産駒 — 自前DB {a['n']}走 ═══\n")
    print(f"  勝率 {a['win']*100:.1f}%  複勝率 {a['p3']*100:.1f}%  "
          f"平均人気 {a['pop']:.1f}  単勝回収率 {a['roi']*100:.0f}%"
          f"（最高配当1件を除くと {a['roi_ex']*100:.0f}%）")
    if a["n"] < 100:
        print(f"\n  ⚠ {a['n']}走は判断には少なすぎる。傾向として眺めるに留めること。")

    for label, key in (("芝ダート別", lambda r: r["surface"]),
                       ("距離別", lambda r: f'{r["surface"]}{dist_cat(r["dist"])}'),
                       ("競馬場別", lambda r: r["venue"]),
                       ("馬場状態別", lambda r: r["baba"]),
                       ("脚質別", lambda r: r["style"])):
        g = defaultdict(list)
        for r in rs:
            k = key(r)
            if k:
                g[k].append(r)
        if not g:
            continue
        print(f"\n  【{label}】")
        print(f"  {'区分':<14}{'出走':>5}{'勝率':>7}{'複勝率':>8}{'単回収':>8}{'除外後':>8}")
        print("  " + "─" * 50)
        for k, v in sorted(g.items(), key=lambda x: -len(x[1])):
            if len(v) < 5:
                continue
            b = agg(v)
            warn = "  ←少数" if len(v) < 20 else ""
            print(f"  {k:<14}{b['n']:>5}{b['win']*100:>6.1f}%{b['p3']*100:>7.1f}%"
                  f"{b['roi']*100:>7.0f}%{b['roi_ex']*100:>7.0f}%{warn}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sire", help="種牡馬名（部分一致）")
    ap.add_argument("--min-runs", type=int, default=60)
    a = ap.parse_args()
    rows = load()
    if not rows:
        print("父名が入った行がありません。先に backfill_bloodline.py --write を実行してください。")
        sys.exit(1)
    if a.sire:
        detail(rows, a.sire)
    else:
        summary(rows, a.min_runs)
