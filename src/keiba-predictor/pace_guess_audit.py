# -*- coding: utf-8 -*-
"""
pace_guess_audit.py — sc[8] の入口「逃げ馬の頭数からペースを当てる」は当たるのか（2026-09-27）
==============================================================================================
pace_factor.guess_pace(n_nige) は n_nige>=3 で H、0 で S、それ以外 M と決め打っている。
しかし 2026-09-27スプリンターズSは登録上の逃げ馬2頭（→Mと判定）で、実際は H（33.6-35.6）だった。
入口を外すと、その先の実測セルがどれだけ正確でも意味がない。蓄積DBで的中率を測る。

使い方: python pace_guess_audit.py
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))

# レース単位に畳む
races = collections.defaultdict(list)
for r in rows:
    k = (r.get("date"), r.get("競馬場"), r.get("R"))
    if all(k):
        races[k].append(r)

pairs, by_field = [], collections.defaultdict(list)
for k, rs in races.items():
    pace = str(rs[0].get("ペース") or "").strip()[:1]
    if pace not in ("H", "M", "S"):
        continue
    n_nige = sum(1 for r in rs if r.get("脚質") == "逃げ")
    guess = "H" if n_nige >= 3 else ("S" if n_nige == 0 else "M")
    pairs.append((guess, pace, n_nige, len(rs)))
    by_field[len(rs)].append((guess, pace))

print(f"■ 対象 {len(pairs)} レース")
cm = collections.Counter((g, a) for g, a, _, _ in pairs)
print(f"\n{'予測\\実際':<10}" + "".join(f"{a:>8}" for a in "HMS") + f"{'計':>8}{'的中':>8}")
for g in "HMS":
    tot = sum(cm[(g, a)] for a in "HMS")
    acc = cm[(g, g)] / tot * 100 if tot else 0
    print(f"{g:<10}" + "".join(f"{cm[(g,a)]:>8}" for a in "HMS") + f"{tot:>8}{acc:>7.1f}%")
hit = sum(cm[(x, x)] for x in "HMS")
print(f"{'全体的中':<10}{'':>24}{len(pairs):>8}{hit/len(pairs)*100:>7.1f}%")

base = collections.Counter(a for _, a, _, _ in pairs)
top = base.most_common(1)[0]
print(f"\n基準線：常に「{top[0]}」と答えるだけで {top[1]/len(pairs)*100:.1f}%（{top[1]}/{len(pairs)}）")
print(f"実際の分布 " + " / ".join(f"{a}{base[a]/len(pairs)*100:.1f}%" for a in "HMS"))

print("\n■ 逃げ馬の頭数ごとに、実際のペースはどうだったか")
print(f"{'逃げ頭数':>8}{'n':>7}" + "".join(f"{a:>9}" for a in "HMS"))
byn = collections.defaultdict(collections.Counter)
for g, a, n, _ in pairs:
    byn[min(n, 5)][a] += 1
for n in sorted(byn):
    c = byn[n]
    t = sum(c.values())
    lbl = f"{n}頭" + ("以上" if n == 5 else "")
    print(f"{lbl:>8}{t:>7}" + "".join(f"{c[a]/t*100:>8.1f}%" for a in "HMS"))

print("\n■ もし n_nige を使わず『常にそのコースの最頻ペース』にしたら")
bycourse = collections.defaultdict(collections.Counter)
for k, rs in races.items():
    pace = str(rs[0].get("ペース") or "").strip()[:1]
    d = str(rs[0].get("距離") or "")
    if pace in ("H", "M", "S") and d:
        bycourse[d][pace] += 1
ok = n = 0
for k, rs in races.items():
    pace = str(rs[0].get("ペース") or "").strip()[:1]
    d = str(rs[0].get("距離") or "")
    if pace in ("H", "M", "S") and d and sum(bycourse[d].values()) >= 20:
        n += 1
        ok += 1 if bycourse[d].most_common(1)[0][0] == pace else 0
print(f"   距離別の最頻ペースで答える：{ok/n*100:.1f}%（{ok}/{n}）")
