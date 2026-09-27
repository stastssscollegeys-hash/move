# -*- coding: utf-8 -*-
"""
pace_factor.py — sc[8] ペース補正を「距離×ペース×馬場」の実測値から出す（2026-09-27新規）
================================================================================================
これまでの実装（score_v33_*.py 内）:
    pace = {"逃げ": 8 if n_nige <= 1 else 6, "差し": 7 if n_nige <= 1 else 8, ...}
  → **逃げ馬が多い（＝ハイペースになる）と差しを加点**する設計。距離も馬場も見ていない。

2026-09-27 スプリンターズS（中山芝1200m・稍重・H）で 1着逃げ・2着先行・3着先行、
上がり最速が5着・2位が4着。うちの印は◎○△が全部「追込」だった。
ユーザー指摘:「距離が非常に関係する。短距離のハイペースは前が止まらず差しが間に合わない」

蓄積DB 2,466レースで検証した結果（pace_style_audit.py）:
  芝〜1200 H : 逃げ45.0% 先行29.3% 差し22.6% 追込 7.5%  → 前が +22.0pt 有利
  芝〜1200 H 重・不良 : 逃げ52.2% … 追込 5.3%           → 前が +26.0pt 有利
  ダ〜1200 H : 前が +33.3pt 有利
  **集計した全距離帯で、ハイペース時に前が有利。差しが有利になる枠は1つも無かった。**
  距離が短いほど差が大きい。旧実装は符号が逆だった。

本モジュールは daily_pdca/db/pace_style.json（実測68枠）を引いて sc[8] を返す。
逃げ馬の頭数は「ペースの予測」にだけ使い、有利不利の判定は実測に任せる。
"""
from __future__ import annotations
import json
from pathlib import Path

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
_P = DB / "pace_style.json"
TBL = json.loads(_P.read_text(encoding="utf-8")) if _P.exists() else {}

BASE = 7.0          # 中立点（他の因子と同じ 6〜10 のレンジに合わせる）
K = 0.09            # 3着内率1ptあたりの加点。±22pt差 → 約±2点の差になる
LO, HI = 4.0, 10.0


def dist_band(surf: str, meters: int) -> str:
    s = "芝" if str(surf).startswith("芝") else "ダ"
    m = int(meters)
    b = ("〜1200" if m <= 1200 else "1300-1400" if m <= 1400 else
         "1500-1600" if m <= 1600 else "1700-1800" if m <= 1800 else
         "1900-2000" if m <= 2000 else "2100-")
    return f"{s}{b}"


def baba_band(b: str | None) -> str:
    s = str(b or "")
    if s.startswith("良"):
        return "良"
    if s.startswith("稍"):
        return "稍重"
    if s.startswith("重") or s.startswith("不"):
        return "重・不良"
    return "全馬場"


def guess_pace(n_nige: int) -> str:
    """🚫使用禁止（2026-09-27）。逃げ馬の頭数からペースを当てようとしたが、
    蓄積DB1,231レースで的中率44.3%。**常に「M」と答えるだけの45.6%を下回る**
    （`pace_guess_audit.py`）。逃げ2頭のレースでも実際のペースは H28.1/M44.3/S27.6 と
    ほぼ三等分で、頭数はペースの情報をほとんど持っていない。
    sc[8] はペースで条件付けず、レース前に確実に分かる「距離×馬場」で引く。
    ペース別セルは事後検証用に pace_style.json に残してある。"""
    return "H" if n_nige >= 3 else ("S" if n_nige == 0 else "M")


def _cell(dist: str, baba: str, pace: str = "全ペース"):
    """実測セルを段階的にフォールバックして引く。既定はペース非条件付け"""
    for key in (f"{dist}|{pace}|{baba}", f"{dist}|{pace}|全馬場", f"{dist}|全ペース|全馬場"):
        c = TBL.get(key)
        if c and c.get("n", 0) >= 120:
            return c, key
    return None, None


def sc8(style: str, surf: str, meters: int, n_nige: int = 0, baba: str | None = None):
    """sc[8] と、その根拠の文字列を返す。
    n_nige は互換のために残しているだけで使わない（上の guess_pace を参照）"""
    dist = dist_band(surf, meters)
    bb = baba_band(baba)
    cell, key = _cell(dist, bb)
    pace = "全ペース"
    if not cell:
        return BASE, f"実測データなし（{dist}/{pace}）→ 中立"
    rates = {k: v for k, v in cell["rates"].items() if v is not None}
    if style not in rates:
        # その馬場のセルに当該脚質のサンプルが無い（逃げは頭数が少なく欠けやすい）。
        # 馬場をひとつ広げたセルで補う。中立に落とすと「逃げが不利」と誤読されるため。
        for fb in (f"{dist}|全ペース|全馬場",):
            c2 = TBL.get(fb)
            if c2 and (c2["rates"].get(style) is not None):
                r2 = {k: v for k, v in c2["rates"].items() if v is not None}
                mean2 = sum(r2.values()) / len(r2)
                sc2 = max(LO, min(HI, BASE + (r2[style] - mean2) * K))
                return round(sc2, 2), (f"{fb}・n={c2['n']}（{bb}に{style}のサンプルが無いため馬場を広げて代用）"
                                       f"：{style}の3着内率{r2[style]:.1f}%（平均{mean2:.1f}%）")
        return BASE, f"{key} に{style}のサンプルが足りない → 中立"
    mean = sum(rates.values()) / len(rates)
    sc = max(LO, min(HI, BASE + (rates[style] - mean) * K))
    return round(sc, 2), (f"{dist}/{pace}/{cell['baba']}・n={cell['n']}：{style}の3着内率"
                          f"{rates[style]:.1f}%（平均{mean:.1f}%）")


def table(surf: str, meters: int, n_nige: int, baba: str | None = None):
    """4脚質ぶんまとめて返す（score_v33 の pace dict の置き換え用）"""
    return {st: sc8(st, surf, meters, n_nige, baba)[0] for st in ("逃げ", "先行", "差し", "追込")}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("■ 2026-09-27 スプリンターズS（中山芝1200m・稍重・逃げ馬3頭想定）")
    for st in ("逃げ", "先行", "差し", "追込"):
        v, why = sc8(st, "芝", 1200, 3, "稍")
        print(f"  {st}  sc8={v:>5}  {why}")
    print("\n■ 旧実装（逃げ馬2頭以上のとき）との比較")
    old = {"逃げ": 6, "先行": 7, "差し": 8, "追込": 7}
    new = table("芝", 1200, 3, "稍")
    for st in ("逃げ", "先行", "差し", "追込"):
        print(f"  {st}  旧{old[st]:>4} → 新{new[st]:>5}  ({new[st]-old[st]:+.2f})")
    print("\n■ 距離帯ごとの新sc8（ハイペース・良馬場）")
    for surf, m in (("芝", 1200), ("芝", 1600), ("芝", 2000), ("ダ", 1200), ("ダ", 1800)):
        t = table(surf, m, 3, "良")
        print(f"  {surf}{m}m  " + "  ".join(f"{k}{v:>5.2f}" for k, v in t.items()))
