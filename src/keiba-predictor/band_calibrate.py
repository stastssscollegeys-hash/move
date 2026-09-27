# -*- coding: utf-8 -*-
"""
band_calibrate.py — 券種横断で人気帯別の実測回収率を再生成する
==========================================================================
（旧 wide_band_calibrate.py を全券種に一般化したもの。旧版は削除済み）

なぜ必要か
----------
文献調査（2026-09-08）で「2014年の控除率改定以降の大規模な人気帯別データは
公開されていない」と判明した。この表については自前DBが最も価値ある情報源になる。

185帯を測って分かったこと:
  ・**ワイドだけが構造的に100%に届かない**（45帯中、頑健に100%超はゼロ）
  ・同じ4-6番人気でも ワイド95% ↔ **馬連122%** ↔ 3連複4-5-6は155%
  ・一貫して Favorite-Longshot Bias。**4〜7番人気の組み合わせが割安**、
    上位人気同士は過剰人気、8番人気以下同士は論外（馬単7-8人気は的中0件）

推定配当も的中確率も市場オッズ由来なので、両者から作った期待値には
「同じ配当でも人気の組み合わせで実収支が違う」という情報が入らない。
だから外からこの実測係数を掛ける必要がある。

出力: daily_pdca/db/ticket_bands.json（ev_reference が起動時に読む）

使い方
------
    python band_calibrate.py                # 測って表示するだけ
    python band_calibrate.py --write        # ticket_bands.json を更新
    python band_calibrate.py --ticket 馬連   # 1券種だけ詳しく
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path
from collections import defaultdict
from itertools import combinations, permutations

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
OUT = DB / "ticket_bands.json"

MIN_SAMPLE = 150          # これ未満の帯は信用しない
MIN_ROBUST_ROI = 0.80     # 除外後がこれ未満は本線に置かない
MAXPOP = 10               # 何番人気まで見るか

# 🔴 多重比較への歯止め（最重要）
# 300帯を検定すれば、**真のエッジが1つも無くても偶然15帯が「100%超」に見える**（300×5%）。
# 実際 MAXPOP=10 にした途端「頑健に100%超」が15帯に増えたが、その多くは
# 3連複1-9-10（的中4件・回収率313%）のような的中一桁の帯だった。
# 的中件数が少ない帯は、どれだけ回収率が高くても採用しない。
MIN_HITS = 15

# 券種ごとの「何頭の組み合わせか」「着順を区別するか」
SPEC = {
    "ワイド": {"k": 2, "ordered": False},
    "馬連":   {"k": 2, "ordered": False},
    "馬単":   {"k": 2, "ordered": True},
    "3連複":  {"k": 3, "ordered": False},
}


def measure() -> tuple[dict, int]:
    pays = json.load(open(DB / "payouts.json", encoding="utf-8"))
    rows = json.load(open(DB / "race_results.json", encoding="utf-8"))

    races: dict = defaultdict(dict)
    for r in rows:
        try:
            races[(str(r.get("date")), r.get("競馬場"), r.get("R"))][int(r["馬番"])] = \
                int(float(r["人気"]))
        except (TypeError, ValueError, KeyError):
            continue

    band: dict = {t: defaultdict(list) for t in SPEC}
    nrace = 0
    for rec in pays.values():
        m = races.get((str(rec.get("date")), rec.get("venue"), rec.get("R")))
        if not m or len(m) < 8:
            continue
        P = rec.get("payouts") or {}
        if not P.get("馬連"):
            continue
        nrace += 1
        date = str(rec.get("date"))
        pop2num = {v: k for k, v in m.items()}
        mx = max(m.values())
        lim = min(MAXPOP, mx)

        for t, sp in SPEC.items():
            paid = {}
            for w in (P.get(t) or []):
                try:
                    parts = [int(x) for x in
                             str(w["combo"]).replace("-", " ").replace(">", " ").split()]
                    paid[tuple(parts) if sp["ordered"] else tuple(sorted(parts))] = int(w["yen"])
                except (ValueError, KeyError, TypeError):
                    continue
            if not paid:
                continue
            gen = permutations if sp["ordered"] else combinations
            for pops in gen(range(1, lim + 1), sp["k"]):
                nums = [pop2num.get(p) for p in pops]
                if not all(nums):
                    continue
                key = tuple(nums) if sp["ordered"] else tuple(sorted(nums))
                band[t][pops].append((date, paid.get(key, 0)))

    out: dict = {}
    for t, d in band.items():
        rows_ = {}
        for k, v in d.items():
            n = len(v)
            if n < MIN_SAMPLE:
                continue
            # 日付だけで並べる。(date, yen) のタプル全体でソートすると
            # 同じ日の中で「外れ(0)が先・的中が後」に並び替わり、
            # 3分割の境界がずれて期間別の数字が歪む。
            v = sorted(v, key=lambda x: x[0])
            yens = [y for _, y in v]
            hits = [y for y in yens if y > 0]
            top = max(yens) if yens else 0
            # 期間3分割。全期間で良く見えても、特定の時期だけで作られた数字は使えない。
            # （例: 3連複1-3-7は全体119%だが 74% / 218% / 70% で再現しない）
            th = [yens[:n//3], yens[n//3:2*n//3], yens[2*n//3:]]
            thirds = [round(sum(x) / (len(x) * 100), 3) if x else 0.0 for x in th]
            rows_["-".join(str(x) for x in k)] = {
                "n": n,
                "hits": len(hits),
                "hit_rate": round(len(hits) / n, 4),
                "roi": round(sum(yens) / (n * 100), 4),
                "roi_ex_top": round((sum(yens) - top) / (n * 100), 4),
                "thirds": thirds,
                "median": sorted(hits)[len(hits) // 2] if hits else 0,
            }
        out[t] = rows_
    return out, nrace


def judge(v: dict) -> str:
    """3段の関門を全部通ったものだけを★にする"""
    hits = v.get("hits", round(v["hit_rate"] * v["n"]))
    if hits < MIN_HITS:
        # 的中が少ない帯は回収率がいくら高くても信用しない。
        # 300帯も検定していれば、この種の帯は偶然だけで大量に生まれる。
        return f"的中{hits}件・判定不可"
    if v["roi_ex_top"] >= 1.0:
        # 関門3: 期間3分割。1時期だけで作った数字を弾く
        n_ok = sum(1 for x in v.get("thirds", []) if x >= 1.0)
        if n_ok == 3:
            return "★頑健に100%超"
        return f"再現しない（3期中{n_ok}期のみ）"
    if v["roi_ex_top"] >= MIN_ROBUST_ROI:
        return "本線に置ける"
    if v["roi_ex_top"] >= 0.60:
        return "相手まで"
    return "買わない"


def is_robust(v: dict) -> bool:
    """的中件数・最高配当除外・期間3分割 の3関門を全て通過"""
    hits = v.get("hits", round(v["hit_rate"] * v["n"]))
    return (hits >= MIN_HITS
            and v["roi_ex_top"] >= 1.0
            and sum(1 for x in v.get("thirds", []) if x >= 1.0) == 3)


def main(write: bool, only: str | None) -> None:
    bands, nrace = measure()
    print(f"═══ 券種横断 人気帯別の実測（{nrace:,}レース・8頭立て以上）═══\n")
    print("　『除外後』＝最高配当1件を抜いた値。ここが大きく落ちる帯は万馬券1本の見せかけ。\n")

    total = {}
    for t, d in bands.items():
        if only and t != only:
            continue
        ranked = sorted(d.items(), key=lambda x: (not is_robust(x[1]), -x[1]["roi_ex_top"]))
        robust = [k for k, v in d.items() if is_robust(v)]
        total[t] = (len(d), len(robust))
        print(f"■ {t}  （測定 {len(d)}帯／頑健に100%超 {len(robust)}帯）")
        print(f"  {'人気':<10}{'件数':>7}{'的中率':>8}{'回収率':>8}{'除外後':>8}{'中央値':>10}  判定")
        print("  " + "─" * 60)
        show = ranked if only else ranked[:5]
        for k, v in show:
            print(f"  {k:<10}{v['n']:>7,}{v['hit_rate']*100:>7.1f}%{v['roi']*100:>7.0f}%"
                  f"{v['roi_ex_top']*100:>7.0f}%{v['median']:>9,}円  {judge(v)}")
        if not only and len(ranked) > 5:
            print("  …")
            k, v = ranked[-1]
            print(f"  {k:<10}{v['n']:>7,}{v['hit_rate']*100:>7.1f}%{v['roi']*100:>7.0f}%"
                  f"{v['roi_ex_top']*100:>7.0f}%{v['median']:>9,}円  {judge(v)}")
        print()

    if not only:
        print("═══ まとめ ═══\n")
        print(f"{'券種':<8}{'測定帯':>8}{'頑健に100%超':>14}")
        print("─" * 32)
        for t, (a, b) in total.items():
            print(f"{t:<8}{a:>8}{b:>14}")
        print("\n🔴 ワイドは頑健な100%超がゼロ＝**構造的に届かない**（配当が低すぎる）。")
        print("　 期待値の柱は馬連・3連複の中位人気帯に置き、ワイドは補助に回す。")
        print("　 ただし帯の高回収率は多重比較の産物でありうる。band_tracker.py で追跡すること。")

    if write:
        json.dump({"races": nrace, "tickets": bands}, open(OUT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"\n更新: {OUT}")
    else:
        print("\n※ 表示のみ。保存するには --write")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--ticket", choices=list(SPEC))
    a = ap.parse_args()
    main(a.write, a.ticket)
