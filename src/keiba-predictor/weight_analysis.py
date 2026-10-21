# -*- coding: utf-8 -*-
"""
weight_analysis.py — 馬体重（体重そのもの・増減）がどう効くかを10年分で測る（2026-10-14）
==========================================================================================
指標（horse_profile.py と同じ）: 比 = 3着内の実数 ÷ 人気×頭数帯から期待される3着内（1.00＝人気どおり）／単回 = 単勝100円ずつの回収率（全馬平均 72.7%）
前半（〜2022）と後半（2023〜）を並べ、同じ向きのものだけ「安定」。
見るもの:
  A 体重の帯 × 芝ダ ／ × 距離帯 ／ × 性別
  B 増減の帯 × 芝ダ ／ × 間隔（休み明けか） ／ × 年齢（2〜3歳は成長期）
  C 「その馬が3着内に来たときの体重（平均）」との差
  D 同じレースの中での体重の順位（一番軽い〜一番重い）
出力: docs/keiba_weight_analysis.md ／ 競馬予想レポート/20261014_馬体重の分析.md
使い方: python weight_analysis.py   （約2分）
"""
from __future__ import annotations
import collections, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import horse_profile as HP

OUT = Path(__file__).resolve().parents[2] / "docs" / "keiba_weight_analysis.md"
SPLIT = "20230101"


def wband(w):
    for hi, lab in ((420, "〜419kg"), (440, "420〜439kg"), (460, "440〜459kg"), (480, "460〜479kg"), (500, "480〜499kg"), (520, "500〜519kg"), (540, "520〜539kg")):
        if w < hi:
            return lab
    return "540kg〜"


def dband(d):
    return ("−12kg以下" if d <= -12 else "−10〜−6kg" if d <= -6 else "−4〜−2kg" if d <= -2 else "±0" if d == 0 else
            "+2〜+4kg" if d <= 4 else "+6〜+10kg" if d <= 10 else "+12kg以上")


DORD = ["−12kg以下", "−10〜−6kg", "−4〜−2kg", "±0", "+2〜+4kg", "+6〜+10kg", "+12kg以上"]
WORD = ["〜419kg", "420〜439kg", "440〜459kg", "460〜479kg", "480〜499kg", "500〜519kg", "520〜539kg", "540kg〜"]


class Acc:
    def __init__(self):
        self.d = collections.defaultdict(lambda: [[0, 0, 0.0, 0.0], [0, 0, 0.0, 0.0]])

    def add(self, key, r):
        a = self.d[key][0 if r["date"] < SPLIT else 1]
        a[0] += 1; a[1] += r["f"] <= 3; a[2] += r["exp3"]; a[3] += r["odds"] * 100 if r["f"] == 1 else 0

    def row(self, key):
        a, b = self.d.get(key, ([0, 0, 0, 0], [0, 0, 0, 0]))
        n, t3, e, p = a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3]
        if n == 0 or e == 0:
            return None
        z = (t3 - e) / math.sqrt(e * (1 - min(0.99, e / n)))
        ra = a[1] / a[2] if a[2] else float("nan")
        rb = b[1] / b[2] if b[2] else float("nan")
        st = "◎" if (a[0] >= 300 and b[0] >= 300 and (ra - 1) * (rb - 1) > 0 and abs(z) >= 3) else ""
        return n, t3 / e, ra, rb, p / n, z, st


def table(title, acc, groups, cats, note=""):
    L = [f"\n### {title}\n", note] if note else [f"\n### {title}\n"]
    L.append("| " + " | ".join(["区分"] + cats) + " |")
    L.append("|---" * (len(cats) + 1) + "|")
    for g in groups:
        cells = []
        for c in cats:
            x = acc.row((g, c))
            cells.append("－" if not x or x[0] < 200 else f"{x[1]:.2f}{x[6]}<br>{x[4]:.0f}%<br>n={x[0]:,}")
        L.append("| " + " | ".join([g] + cells) + " |")
    return L


def main():
    runs = HP.load()
    cards, by = HP.horse_cards(runs)          # gap・prev を付ける
    A = Acc()
    for hid, rs in by.items():
        top3_w = []
        for r in rs:
            bw, bwd = r["bw"], r["bwd"]
            sa = r["sexage"]
            sex = {"牡": "牡", "牝": "牝", "セ": "セン"}.get(sa[:1], "?")
            age = int(sa[1:]) if sa[1:].isdigit() else None
            agec = "2〜3歳" if age and age <= 3 else "4歳以上" if age else "?"
            if bw:
                wb = wband(bw)
                A.add(("全体", wb), r)
                A.add((f"{r['surf']}", wb), r)
                A.add((f"{r['surf']}{r['band']}", wb), r)
                A.add((f"性別:{sex}", wb), r)
            if bwd is not None and r["prev"]:
                db_ = dband(bwd)
                gp = r["gap"] or 0
                gapc = "休み明け(13週〜)" if gp >= 91 else "6〜12週" if gp >= 42 else "中5週以内"
                A.add(("増減:全体", db_), r)
                A.add((f"増減:{r['surf']}", db_), r)
                A.add((f"増減:{gapc}", db_), r)
                A.add((f"増減:{agec}", db_), r)
                A.add((f"増減:{'牝' if sex == '牝' else '牡・セン'}", db_), r)
                if bw and top3_w:
                    diff = bw - sum(top3_w) / len(top3_w)
                    c = ("−16kg以下" if diff <= -16 else "−14〜−8kg" if diff <= -8 else "−6〜+6kg" if diff <= 6 else "+8〜+14kg" if diff <= 14 else "+16kg以上")
                    A.add(("好走時との差", c), r)
                    A.add((f"好走時との差:{r['surf']}", c), r)
            if bw and r["f"] <= 3:
                top3_w.append(bw)
    # D レース内の体重順位
    races = collections.defaultdict(list)
    for r in runs:
        if r["bw"]:
            races[(r["date"], r["venue"], r["n"], r["surf"], r["m"])].append(r)
    for k, hs in races.items():
        if len(hs) < 8:
            continue
        srt = sorted(hs, key=lambda r: r["bw"])
        for i, r in enumerate(srt):
            pos = "一番軽い" if i == 0 else "軽い方(下位1/3)" if i < len(srt) / 3 else "一番重い" if i == len(srt) - 1 else "重い方(上位1/3)" if i >= len(srt) * 2 / 3 else "中くらい"
            A.add((f"順位:{r['surf']}", pos), r)
            A.add((f"順位:{r['surf']}{r['band']}", pos), r)
    L = [f"# 馬体重はどう効くか（{runs[0]['date']}〜{runs[-1]['date']}・{len(runs):,}走）\n",
         "各セル: **比**（3着内の実数÷人気からの期待。1.00＝人気どおり）／単勝回収率（全馬平均72.7%）／走数。"
         "◎＝前半（〜2022）と後半（2023〜）で同じ向き かつ |z|≧3（偶然ではなさそう）。200走未満は－。",
         "比が1未満＝**人気ほど走らない（市場が買いかぶっている）**、1超＝人気以上に走る。単勝回収率が72.7%より大きく低い区分は「人気で買うと損」。\n",
         "## A. 体重そのもの"]
    L += table("芝ダ・距離帯 × 体重の帯", A, ["全体", "芝", "ダ", "芝〜1300", "芝1400〜1600", "芝1700〜2200", "芝2300〜", "ダ〜1300", "ダ1400〜1600", "ダ1700〜2200"], WORD)
    L += table("性別 × 体重の帯", A, ["性別:牡", "性別:牝", "性別:セン"], WORD)
    L.append("\n## B. 体重の増減（前走との差）")
    L += table("増減 × 芝ダ・間隔・年齢・性別", A, ["増減:全体", "増減:芝", "増減:ダ", "増減:中5週以内", "増減:6〜12週", "増減:休み明け(13週〜)",
                                           "増減:2〜3歳", "増減:4歳以上", "増減:牝", "増減:牡・セン"], DORD)
    L.append("\n## C. その馬が3着内に来たときの体重（平均）との差")
    L += table("好走時の体重との差", A, ["好走時との差", "好走時との差:芝", "好走時との差:ダ"], ["−16kg以下", "−14〜−8kg", "−6〜+6kg", "+8〜+14kg", "+16kg以上"])
    L.append("\n## D. 同じレースの中での体重の順位（8頭以上）")
    L += table("レース内の順位", A, ["順位:芝", "順位:ダ", "順位:ダ〜1300", "順位:ダ1400〜1600", "順位:ダ1700〜2200", "順位:芝〜1300", "順位:芝1700〜2200"],
               ["一番軽い", "軽い方(下位1/3)", "中くらい", "重い方(上位1/3)", "一番重い"])
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n保存: {OUT}")


if __name__ == "__main__":
    main()
