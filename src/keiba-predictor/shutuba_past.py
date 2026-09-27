# -*- coding: utf-8 -*-
"""
shutuba_past.py — netkeibaの馬柱（shutuba_past.html）から出走各馬の近走を構造化して取る（2026-09-25）
=====================================================================================================
重賞では手作業で作っていた「近走（会場・距離・格・着順つき）」を、どのレースでも取れるようにする部品。
平場でも sc[18]同コース実績 / sc[19]格 を出せるようにするのが目的。

⚠ 馬名は専用セル（td.Horse_Info の a）から取る。行テキスト全体だと相手馬名を拾う（2026-09-09の教訓）。

使い方:
  python shutuba_past.py --race-id 202606040611 --out form.json
  from shutuba_past import fetch_form; fetch_form("202606040611")
"""
from __future__ import annotations
import argparse, json, re, sys, io, time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HEAD = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://race.netkeiba.com/"}
GRADES = ("GI", "GII", "GIII", "G1", "G2", "G3", "L", "OP", "3勝", "2勝", "1勝", "未勝利", "新馬")


def _run(cell_text: str) -> dict | None:
    """馬柱1走分のセル（|区切り）を辞書にする。"""
    p = [x.strip() for x in cell_text.split("|") if x.strip()]
    if len(p) < 5:
        return None
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})\s*(\S+)", p[0])
    if not m:
        return None
    out = {"date": f"{m.group(1)}.{m.group(2)}.{m.group(3)}", "ven": m.group(4)}
    try:
        out["fin"] = int(p[1])
    except ValueError:
        return None
    out["race"] = p[2] if len(p) > 2 else ""
    out["grade"] = p[3] if len(p) > 3 and p[3] in GRADES else ""
    course = next((x for x in p if re.match(r"^[芝ダ障]", x)), "")
    cm = re.match(r"([芝ダ障])\D*(\d{3,4})", course)
    if cm:
        out["surf"] = {"芝": "芝", "ダ": "ダート", "障": "障害"}[cm.group(1)]
        out["dist"] = int(cm.group(2))
    field = next((x for x in p if "頭" in x and "番" in x), "")
    fm = re.search(r"(\d+)頭\s*(\d+)番\s*(\d+)人", field)
    if fm:
        out["field"], out["umaban"], out["pop"] = (int(fm.group(1)), int(fm.group(2)), int(fm.group(3)))
    ag = next((x for x in p if "(" in x and re.search(r"\(\d\d\.\d\)", x)), "")
    am = re.search(r"\((\d\d\.\d)\)", ag)
    if am:
        out["agari"] = float(am.group(1))
    mg = re.search(r"\((-?\d+\.\d)\)", p[-1])
    if mg:
        out["margin"] = float(mg.group(1))
    return out


def fetch_form(race_id: str) -> list[dict]:
    r = requests.get(f"https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}",
                     headers=HEAD, timeout=20)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    horses = []
    for row in soup.select("table.Shutuba_Table tr.HorseList"):
        info = row.select_one("td.Horse_Info")
        a = info.select_one("a") if info else None
        if not a:
            continue
        waku = row.select_one("td.Waku1, td.Waku")
        num = row.select_one("td.Waku + td, td.Umaban")
        runs = [x for x in (_run(td.get_text("|", strip=True)) for td in row.select("td.Past")) if x]
        horses.append({"name": a.get_text(strip=True),
                       "waku": (waku.get_text(strip=True) if waku else ""),
                       "uma": (num.get_text(strip=True) if num else ""),
                       "runs": runs})
    return horses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race-id", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    hs = fetch_form(a.race_id)
    print(f"{len(hs)}頭 / 近走の平均本数 {sum(len(h['runs']) for h in hs)/max(1,len(hs)):.1f}")
    for h in hs[:3]:
        print(" ", h["name"], [(r["date"], r.get("ven"), r.get("surf"), r.get("dist"), r["fin"]) for r in h["runs"][:3]])
    if a.out:
        Path(a.out).write_text(json.dumps(hs, ensure_ascii=False, indent=1), encoding="utf-8")
        print("保存:", a.out)


if __name__ == "__main__":
    main()
