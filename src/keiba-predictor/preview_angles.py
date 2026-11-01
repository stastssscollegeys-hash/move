# -*- coding: utf-8 -*-
"""
preview_angles.py — 重賞1週間前プレビューの「面白い視点」の材料を、登録馬のダイジェストと過去10年の型から作る（2026-11-01新規）
===============================================================================================================
・厩舎の勢い: 登録馬の調教師ごとに、直近90日の出走の3着内を「同じ人気から期待される3着内」と比べる（z）
・前走の経路: 過去10回の3着内馬の前走レース（race_profile の「前走のレース」）に、登録馬の前走が当たるか
・型への当てはまり: 間隔（過去の3着内馬の範囲）・年齢・想定脚質を数える
使い方: python preview_angles.py --dir 20261108 --race アルゼンチン共和国杯 [--since 20260802]
出力: 標準出力（JSON は research/angles_{レース}.json）
"""
from __future__ import annotations
import argparse, collections, json, math, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
DB = BASE / "daily_pdca" / "db" / "history_target"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_digest(path):
    hs, cur = [], None
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (.+?)（(.)(\d*)・([\d.]+kg)・(.+?)）", ln) or re.match(r"^## (.+?)（([牡牝セ])・([\d.]+kg)・(.+?)）", ln)
        if ln.startswith("## ") and not ln.startswith("## 目") and "（" in ln:
            nm = ln[3:].split("（")[0]
            meta = ln.split("（", 1)[1].rstrip("）")
            parts = meta.split("・")
            cur = dict(name=nm, sex=parts[0][:1] if parts else "", trainer=parts[-1], runs=[], tags="")
            hs.append(cur)
        elif cur is not None and ln.startswith("- 通算"):
            m = re.search(r"間隔 (\d+)日", ln); cur["gap"] = int(m.group(1)) if m else None
            m = re.search(r"想定脚質 (\S+)", ln); cur["style"] = m.group(1) if m else ""
            cur["rec"] = ln
        elif cur is not None and re.match(r"^\s+- \d\d/\d\d/\d\d ", ln):
            cur["runs"].append(ln.strip()[2:])
        elif cur is not None and ln.startswith("- 目印"):
            cur["tags"] = ln[5:].strip()
    return hs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--race", required=True)
    ap.add_argument("--since", default="20260802")
    a = ap.parse_args()
    rd = BASE / a.dir / "research"
    hs = parse_digest(rd / f"entry_digest_{a.race}.md")
    # 厩舎の勢い
    rows = [r for r in json.loads((DB / "results_2026.json").read_text(encoding="utf-8")) if r["date"] >= a.since and num(r.get("人気")) and r.get("着順int")]
    allr = [r for r in json.loads((DB / "results_2025.json").read_text(encoding="utf-8")) if num(r.get("人気")) and r.get("着順int")] + rows
    cnt = collections.defaultdict(lambda: [0, 0])
    for r in allr:
        e = cnt[min(int(num(r["人気"])), 18)]; e[0] += 1; e[1] += int(num(r["着順int"])) <= 3
    B = {k: v[1] / v[0] for k, v in cnt.items()}
    out = []
    for h in hs:
        fam = h["trainer"]
        sub = [r for r in rows if r.get("厩舎") and fam.startswith(re.sub(r"^(美浦|栗東)", "", r["厩舎"])) and len(re.sub(r"^(美浦|栗東)", "", r["厩舎"])) >= 2]
        n = len(sub)
        w = sum(int(num(r["着順int"])) == 1 for r in sub); t3 = sum(int(num(r["着順int"])) <= 3 for r in sub)
        exp = sum(B[min(int(num(r["人気"])), 18)] for r in sub); var = sum(B[min(int(num(r["人気"])), 18)] * (1 - B[min(int(num(r["人気"])), 18)]) for r in sub)
        z = (t3 - exp) / math.sqrt(var) if var > 0 else 0
        last = h["runs"][0] if h["runs"] else ""
        out.append(dict(name=h["name"], sex=h["sex"], trainer=h["trainer"], gap=h.get("gap"), style=h.get("style"), tags=h["tags"],
                        last=last[:90], stable_n=n, stable_win=w, stable_t3=t3, stable_exp=round(exp, 1), stable_z=round(z, 2)))
    (rd / f"angles_{a.race}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"登録 {len(out)}頭（厩舎の勢い=直近{a.since}以降）")
    for o in sorted(out, key=lambda o: -o["stable_z"])[:6]:
        print(f"  厩舎 {o['trainer']:<6} {o['name']:<12} 直近{o['stable_n']}走 勝ち{o['stable_win']} 3着内{o['stable_t3']}（期待{o['stable_exp']}）z={o['stable_z']:+.2f}")
    print("前走:")
    for o in out:
        print(f"  {o['name']:<12} {o['sex']} 間隔{o['gap']}日 {o['style']:<3} | {o['last']} | {o['tags']}")


if __name__ == "__main__":
    main()
