# -*- coding: utf-8 -*-
"""web_bias.py — その日の結果（web_results.json）から トラックバイアス と 騎手の勝ち星 を出す（2026-11-08 新設）
  python web_bias.py --date 20261107   → 標準出力と {OUT}/{日付}_web_bias.md
脚質は最初のコーナー〜4角の順位から course_profile.style_of と同じ定義。倍率＝3着内率÷出走割合（1.0が標準）。"""
import argparse, collections as C, json, sys
sys.stdout.reconfigure(encoding="utf-8")
import web_live as W
from course_profile import style_of

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    R = json.load(open(W.OUT / f"{a.date}_web_results.json", encoding="utf-8")); out = []
    pr = lambda *x: (print(*x), out.append(" ".join(map(str, x))))
    st = C.defaultdict(lambda: C.defaultdict(lambda: [0, 0, 0]))   # (場,芝ダ) → 脚質 → [出走,3着内,1着]
    wk = C.defaultdict(lambda: C.defaultdict(lambda: [0, 0]))
    pace = C.defaultdict(list); jk = C.defaultdict(lambda: [0, 0, 0, 0.0]); baba = {}
    for k, r in R.items():
        if not r["rows"]: continue
        key = (r["venue"], "芝" if r["dist"].startswith("芝") else "ダ"); n = len(r["rows"]); baba[key] = r["baba"]
        lap = r.get("lap") or []
        if len(lap) >= 6: pace[key].append(round(sum(lap[:3]) - sum(lap[-3:]), 1))   # 前3F−後3F（負＝前半が速いハイペース寄り）
        for h in r["rows"]:
            s = style_of(r["corners"].get(str(h["uma"]), ""), n) or "不明"
            x = st[key][s]; x[0] += 1; x[1] += h["rank"] <= 3; x[2] += h["rank"] == 1
            g = "内(1-3)" if h["waku"] <= 3 else "中(4-6)" if h["waku"] <= 6 else "外(7-8)"
            w = wk[key][g]; w[0] += 1; w[1] += h["rank"] <= 3
            j = jk[(r["venue"], h["jockey"])]; j[0] += 1; j[1] += h["rank"] == 1; j[2] += h["rank"] <= 3
    pr(f"## {a.date} トラックバイアス（場×芝ダ・全レース合計）")
    for key in sorted(st):
        tot = sum(v[0] for v in st[key].values()); t3 = sum(v[1] for v in st[key].values())
        pr(f"■{key[0]}{key[1]}（{baba[key]}・{sum(1 for r in R.values() if r['rows'] and (r['venue'],'芝' if r['dist'].startswith('芝') else 'ダ')==key)}R） 前3F−後3F の平均 {sum(pace[key])/max(1,len(pace[key])):+.1f}秒")
        for s in ("逃げ", "先行", "差し", "追込"):
            v = st[key].get(s)
            if v and v[0]: pr(f"   {s}: 出走{v[0]} 勝{v[2]} 3着内{v[1]}（{v[1]/v[0]:.0%}／倍率{(v[1]/t3)/(v[0]/tot):.2f}）")
        pr("   枠: " + " ／ ".join(f"{g} {w[1]}/{w[0]}={w[1]/w[0]:.0%}" for g, w in sorted(wk[key].items())))
    pr("\n## 騎手の勝ち星（場別・今日2勝以上、または3着内3回以上）")
    for (v, name), j in sorted(jk.items(), key=lambda x: (-x[1][1], -x[1][2])):
        if j[1] >= 2 or j[2] >= 3: pr(f"  {v} {name}: {j[0]}鞍 {j[1]}勝 3着内{j[2]}")
    (W.OUT / f"{a.date}_web_bias.md").write_text("\n".join(out), encoding="utf-8")
main()
