# -*- coding: utf-8 -*-
"""
pace_style_audit.py — 距離 × ペース × 馬場 で脚質の有利不利を自前測定する（2026-09-27新規）
================================================================================================
きっかけ（2026-09-27 スプリンターズS）:
  「ハイペースなら差し有利」という前提で組んだが、稍重の中山芝1200mで
  1着=逃げ・2着=先行・3着=先行。上がり最速の馬が5着、2位が4着で、上がり順位と着順が逆相関した。
  ユーザー指摘:「距離が非常に関係する。短距離のハイペースは前が止まらず差しが間に合わない」

sc[8] のペース補正は現在「逃げ馬の頭数」だけで差し/先行の有利を切り替えており、
**距離も馬場も見ていない**。その妥当性を蓄積DBで検証する。

データ: daily_pdca/db/race_results.json（結果DB。脚質・ペース・距離・馬場・着順が入っている）
出力  : daily_pdca/db/pace_style.json（距離帯×ペース×馬場 → 脚質別3着内率）
使い方: python pace_style_audit.py
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))

STYLES = ("逃げ", "先行", "差し", "追込")


def dist_band(d):
    """距離帯。芝・ダートは分けて扱う"""
    s = str(d or "")
    surf = "芝" if s.startswith("芝") else ("ダ" if s.startswith("ダ") else None)
    num = "".join(ch for ch in s if ch.isdigit())
    if not surf or not num:
        return None
    m = int(num)
    band = ("〜1200" if m <= 1200 else "1300-1400" if m <= 1400 else
            "1500-1600" if m <= 1600 else "1700-1800" if m <= 1800 else
            "1900-2000" if m <= 2000 else "2100-")
    return f"{surf}{band}"


def baba_band(b):
    s = str(b or "")
    if s.startswith("良"):
        return "良"
    if s.startswith("稍"):
        return "稍重"
    if s.startswith("重") or s.startswith("不"):
        return "重・不良"
    return None


agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for r in rows:
    d = dist_band(r.get("距離"))
    p = str(r.get("ペース") or "").strip()[:1]
    st = r.get("脚質")
    bb = baba_band(r.get("馬場状態"))
    fin = r.get("着順int")
    if not (d and p in ("H", "M", "S") and st in STYLES and fin):
        continue
    # 「全ペース×馬場別」も作る。ペースはレース前に当てられない（pace_guess_audit.py で
    # 逃げ馬頭数からの予測は44.3%＝常にMと答える45.6%より低いと判明）ので、
    # 実運用では 距離×馬場 のセルを引く。ペース別セルは事後検証用に残す。
    for key in ((d, p, "全馬場"), (d, p, bb) if bb else None,
                (d, "全ペース", "全馬場"), (d, "全ペース", bb) if bb else None):
        if key:
            e = agg[key][st]
            e[0] += 1
            e[1] += 1 if fin <= 3 else 0

out = {}
print("■ 距離帯 × ペース × 馬場 の脚質別3着内率（自前集計・n>=120の枠のみ）")
print(f"{'距離帯':<10}{'ペース':<7}{'馬場':<7}{'n':>6}" + "".join(f"{s:>9}" for s in STYLES) + "   前(逃+先)")
for (d, p, bb), by in sorted(agg.items()):
    tot = sum(e[0] for e in by.values())
    if tot < 120:
        continue
    rates = {}
    for s in STYLES:
        n, h = by[s]
        rates[s] = round(h / n * 100, 1) if n >= 20 else None
    fr = [rates[s] for s in ("逃げ", "先行") if rates[s] is not None]
    front = round(sum(fr) / len(fr), 1) if fr else None
    back = [rates[s] for s in ("差し", "追込") if rates[s] is not None]
    back = round(sum(back) / len(back), 1) if back else None
    out[f"{d}|{p}|{bb}"] = dict(dist=d, pace=p, baba=bb, n=tot,
                                rates={s: rates[s] for s in STYLES},
                                front=front, back=back,
                                front_minus_back=(round(front - back, 1) if front is not None and back is not None else None))
    cells = "".join((f"{rates[s]:>8.1f}%" if rates[s] is not None else f"{'-':>9}") for s in STYLES)
    diff = out[f"{d}|{p}|{bb}"]["front_minus_back"]
    print(f"{d:<10}{p:<7}{bb:<7}{tot:>6}{cells}   "
          + (f"{front:.1f}% vs 後{back:.1f}% → {diff:+.1f}pt" if diff is not None else ""))

(DB / "pace_style.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n保存: {DB / 'pace_style.json'}（{len(out)}枠）")

print("\n■ 要点：ハイペースのとき前が有利になる距離帯はどこか")
print(f"{'距離帯':<10}{'馬場':<8}{'H時 前-後':>12}{'S時 前-後':>12}   判定")
for d in sorted({k.split('|')[0] for k in out}):
    for bb in ("全馬場", "良", "稍重", "重・不良"):
        h = out.get(f"{d}|H|{bb}")
        s = out.get(f"{d}|S|{bb}")
        if not h or h["front_minus_back"] is None:
            continue
        sd = s["front_minus_back"] if s and s["front_minus_back"] is not None else None
        judge = "🔴ハイペースでも前が有利" if h["front_minus_back"] > 0 else "差し有利（定説どおり）"
        print(f"{d:<10}{bb:<8}{h['front_minus_back']:>+11.1f}pt"
              + (f"{sd:>+11.1f}pt" if sd is not None else f"{'-':>12}") + f"   {judge}")
