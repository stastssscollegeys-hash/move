# -*- coding: utf-8 -*-
"""
fetch_margin_lap.py — 着差と1ハロンごとのラップを netkeiba の結果ページから取る（2026-09-27新規）
======================================================================================================
背景: 蓄積DBの「着差」が当日取得分で空のまま入っていた。着差は20因子のF03に使う項目なので、
      空だとその日のデータが不完全なまま貯まる。ラップ（200m毎）も従来は3F単位しか無かった。

取得元: race.netkeiba.com/race/result.html?race_id={race_id} （UTF-8）
  ⚠ db.netkeiba.com/race/{race_id}/ は2026-09-27時点で有料化され、結果テーブルがHTMLに無い。
  ・結果テーブルの「着差」列
  ・ラップタイム（12.0 - 10.5 - 11.1 ... の並び）とペース（前半-後半）

使い方:
  python fetch_margin_lap.py --date 20260927            # その日の全レース
  python fetch_margin_lap.py --date 20260927 --write    # 蓄積DBの着差も更新する
出力: daily_pdca/db/lap.json（レース別のラップ）＋ --write で race_results.json の着差を補完
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path
from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url, retry=3):
    for i in range(retry):
        try:
            with urlopen(Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == retry - 1:
                print(f"[WARN] {url} {e}")
                return ""
            time.sleep(2)
    return ""


def strip(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S)
    return re.sub(r"<[^>]+>", "\t", h)


def parse(html):
    """着差（馬番→着差）と ラップ を返す"""
    margin, lap, pace = {}, [], ""
    # ラップ: 「ラップタイム」ブロックの 200m/400m… の下に 12.0 12.1 … が並ぶ
    t = strip(html)
    i = t.find("ラップタイム")
    if i >= 0:
        seg = t[i:i + 1500]
        nums = re.findall(r"(?<![\d.])(\d{1,2}\.\d)(?![\d.])", seg)
        lap = nums[:18]
    m = re.search(r"ペース[:：]?\s*([HMS])", t)
    if m:
        pace = m.group(1)
    m2 = re.search(r"\((\d{2}\.\d)\s*-\s*(\d{2}\.\d)\)", t)
    if m2:
        pace += f" {m2.group(1)}-{m2.group(2)}"
    # 結果テーブル: 行ごとに 着順/枠/馬番/馬名/性齢/斤量/騎手/タイム/着差
    # 結果行: [着順, 枠, 馬番, 馬名, 性齢, 斤量, 騎手, タイム, 着差, 人気, オッズ, 上り3F]
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", td)).strip()
               for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(tds) < 9:
            continue
        ti = next((i for i, v in enumerate(tds) if re.fullmatch(r"\d:\d{2}\.\d", v)), None)
        if ti is None or ti < 3 or ti + 1 >= len(tds):
            continue
        try:
            uma = int(tds[2])
        except ValueError:
            continue
        margin[uma] = tds[ti + 1]      # 1着は空文字になる
    return margin, lap, pace


ap = argparse.ArgumentParser()
ap.add_argument("--date", required=True)
ap.add_argument("--write", action="store_true")
a = ap.parse_args()

pays = json.loads((DB / "payouts.json").read_text(encoding="utf-8"))
targets = {rid: v for rid, v in pays.items() if v.get("date") == a.date}
print(f"対象 {len(targets)} レース")

lapdb = json.loads((DB / "lap.json").read_text(encoding="utf-8")) if (DB / "lap.json").exists() else {}
allmargin = {}
for i, (rid, v) in enumerate(sorted(targets.items()), 1):
    html = get(f"https://race.netkeiba.com/race/result.html?race_id={rid}")
    if not html:
        continue
    margin, lap, pace = parse(html)
    allmargin[rid] = margin
    lapdb[rid] = dict(date=v["date"], venue=v["venue"], R=v["R"], lap=lap, pace=pace)
    print(f"  [{i}/{len(targets)}] {v['venue']}{v['R']}R 着差{len(margin)}頭 ラップ{len(lap)}本 {pace}")
    time.sleep(1.0)

(DB / "lap.json").write_text(json.dumps(lapdb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\nラップ保存: {DB / 'lap.json'}（累計{len(lapdb)}レース）")

if a.write:
    p = DB / "race_results.json"
    rows = json.loads(p.read_text(encoding="utf-8"))
    key = {(v["date"], v["venue"], int(v["R"])): rid for rid, v in targets.items()}
    n = 0
    for r in rows:
        if r.get("date") != a.date or r.get("着差"):
            continue
        rid = key.get((r["date"], r["競馬場"], int(r["R"])))
        if not rid:
            continue
        try:
            m = allmargin.get(rid, {}).get(int(float(r["馬番"])))
        except (TypeError, ValueError):
            continue
        if m:
            r["着差"] = m
            n += 1
    bak = p.with_suffix(f".json.bak_margin_{a.date}")
    if not bak.exists():
        bak.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"着差を {n} 行に補完 → race_results.json（バックアップ: {bak.name}）")
