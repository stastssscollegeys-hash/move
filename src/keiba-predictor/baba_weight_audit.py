# -*- coding: utf-8 -*-
"""
baba_weight_audit.py — 馬場補正の上限±3点は妥当か（2026-09-27）
=================================================================
問い: 2026-09-27スプリンターズSで、1着⑯ピューロマジックに
      メンバー最大の道悪補正 +2.9 を付けていたのに印に届かなかった。
      「分析は正解に近づいていたが、補正の幅が足りずに順位が動かなかった」のか。

検証すること
  A. 現行（基礎指数 + 道悪補正±3上限）での順位
  B. 新しい sc[8]（距離×ペース×馬場の実測）を入れたらどう動くか
  C. 道悪補正の上限を ±3 / ±5 / ±8 / ±12 と広げたとき、
     1〜3着馬（⑯⑥⑤）が印（上位5頭）に入るのはどこからか
  D. その上限を採用した場合、他のレースで順位がどれだけ暴れるか（副作用）

使い方: python baba_weight_audit.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from pace_factor import table as pace_table

RES = Path.home() / "Desktop" / "競馬予想レポート" / "20260927" / "research"
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"

fix = json.loads((RES / "final_fix.json").read_text(encoding="utf-8"))
score, wet = fix["score"], fix["wet"]          # score は wet 込みの合計
post = json.loads((RES / "post_race.json").read_text(encoding="utf-8"))

# 脚質と馬名を蓄積DBから引く（レース前に持っていた情報）
rows = [r for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
        if r.get("date") == "20260927" and r.get("競馬場") == "中山" and int(r.get("R") or 0) == 11]
meta = {int(float(r["馬番"])): {"name": r["馬名"], "style": r.get("脚質") or "先行",
                               "fin": r.get("着順int")} for r in rows}
n_nige = sum(1 for v in meta.values() if v["style"] == "逃げ")

OLD_SC8 = {"逃げ": 6, "先行": 7, "差し": 8, "追込": 7}   # 逃げ馬2頭以上のときの旧実装
NEW_SC8 = pace_table("芝", 1200, n_nige, "稍")
print(f"■ 中山芝1200m・稍重・逃げ馬{n_nige}頭  sc[8] 旧→新")
for st in ("逃げ", "先行", "差し", "追込"):
    print(f"   {st}  {OLD_SC8[st]:>4} → {NEW_SC8[st]:>5.2f}  ({NEW_SC8[st]-OLD_SC8[st]:+.2f})")

horses = []
for uma, m in sorted(meta.items()):
    w = wet.get(str(uma), 0.0)
    horses.append(dict(uma=uma, name=m["name"], style=m["style"], fin=m["fin"],
                       base=round(score[str(uma)] - w, 1), wet=w,
                       d8=round(NEW_SC8[m["style"]] - OLD_SC8[m["style"]], 2)))


def ranked(key):
    return sorted(horses, key=lambda h: -key(h))


def show(title, key):
    print(f"\n■ {title}")
    print(f"{'順':>3} {'馬番':>4} {'馬名':<12}{'脚質':<5}{'合計':>7}   着順")
    for i, h in enumerate(ranked(key), 1):
        mark = ("◎○▲△△"[i-1] if i <= 5 else "  ")
        hit = f"{h['fin']}着" if h["fin"] else ""
        star = " ←1〜3着" if h["fin"] and h["fin"] <= 3 else ""
        print(f"{i:>3} {h['uma']:>4} {h['name']:<12}{h['style']:<5}{key(h):>7.1f}   {mark} {hit}{star}")
        if i == 5:
            print("   " + "-" * 44 + " 印はここまで")


show("A. 現行（基礎指数 + 道悪補正±3上限）", lambda h: h["base"] + h["wet"])
show("B. 新sc[8]を入れる（道悪補正は±3のまま）", lambda h: h["base"] + h["d8"] + h["wet"])

print("\n■ C. 道悪補正の上限を広げると 1〜3着馬は印に入るか")
print("   （wet は『道悪3着内率−良3着内率』を±3にクリップした値。"
      "元の生の差はクリップ前なので、上限を広げる＝wet を定数倍して近似する）")
print(f"{'上限':>6}{'倍率':>6} | " + "  ".join(f"{u:>4}番" for u in (16, 6, 5, 9)) + "   印5頭")
for cap, k in ((3, 1.0), (5, 5/3), (8, 8/3), (12, 12/3)):
    key = lambda h: h["base"] + h["d8"] + h["wet"] * k
    order = [h["uma"] for h in ranked(key)]
    pos = "  ".join(f"{order.index(u)+1:>4}位" for u in (16, 6, 5, 9))
    print(f"{cap:>5}点{k:>6.2f} | {pos}   {order[:5]}")

print("\n■ D. 1〜3着馬の内訳（レース前に持っていた値）")
for u in (16, 6, 5):
    h = next(x for x in horses if x["uma"] == u)
    print(f"  {u:>2}番 {h['name']:<12} {h['fin']}着  基礎{h['base']}  道悪{h['wet']:+.1f}  "
          f"新sc8{h['d8']:+.2f}  脚質{h['style']}")
print("  参考 ◎9番 " + str(next(x for x in horses if x["uma"] == 9)))
