# -*- coding: utf-8 -*-
"""
backfill_results_fields.py — 累積DBの旧形式行に欠けている項目を補完する（2026-09-25）
====================================================================================
なぜ必要か:
  累積DB（race_results.json）の前半 16,837行（2026-01-04〜05-10・1,194レース）は項目の少ない旧形式で、
  **レース名・斤量・馬体重・馬場状態・天候・性齢・騎手・厩舎が丸ごと無い**。
  そのため PDCA 100ラウンド（pdca_rounds.py）で「父」「騎手」「クラス」別の仮説が
  「前半0頭」で判定不能になり、検証できる仮説が64件に減っていた。

やること:
  netkeibaのレース結果ページ（db.netkeiba.com/race/{race_id}/）から、その行に足りない項目だけを埋める。
  ⚠ **結果DBの補完であって、レース前の予想データ（records）は触らない**。
     records を後から作るのは結果リークになるため禁止（engine_backtest.drop_leaky）。
  ⚠ 既に値がある項目は上書きしない。馬番＋馬名で照合し、合わない行はスキップして報告する。

使い方:
  python backfill_results_fields.py --limit-days 3      # まず3日分だけ試す
  python backfill_results_fields.py                     # 全部
"""
from __future__ import annotations
import argparse, json, re, shutil, sys, io, time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bs4 import BeautifulSoup
from fetch_payouts import session, get, race_ids_for, VENUE

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
STORE = DB / "race_results.json"
FIELDS = ("レース名", "性齢", "斤量_kg", "騎手", "厩舎", "馬体重", "馬場状態", "天候", "距離")


def parse_race(html: str) -> tuple[dict, dict]:
    """(レース共通情報, {馬番: 行情報}) を返す。"""
    soup = BeautifulSoup(html, "html.parser")
    head = {}
    h1 = soup.select_one("div.data_intro h1, div.data_intro dl dt h1")
    if h1:
        head["レース名"] = h1.get_text(strip=True)
    intro = soup.select_one("div.data_intro")
    txt = intro.get_text(" ", strip=True) if intro else ""
    m = re.search(r"(芝|ダート|ダ|障)\s*[左右内外\s]*(\d{3,4})m", txt)
    if m:
        surf = {"ダ": "ダート", "ダート": "ダート", "芝": "芝", "障": "障害"}[m.group(1)]
        head["距離"] = f"{surf}{m.group(2)}m"
    m = re.search(r"天候\s*:\s*(\S+?)\s", txt)
    if m:
        head["天候"] = m.group(1)
    m = re.search(r"(?:芝|ダート)\s*:\s*(良|稍重|重|不良)", txt)
    if m:
        head["馬場状態"] = m.group(1)
    rows = {}
    table = soup.select_one("table.race_table_01")
    if not table:
        return head, rows
    trs = table.select("tr")
    # 列の位置は決め打ちにしない（タイム指数など隠し列があり、ずれると馬体重に通過順が入る）
    hdr = [th.get_text(strip=True) for th in trs[0].select("th")]
    col = {}
    for i, h in enumerate(hdr):
        for key, label in (("馬番", "馬番"), ("馬名", "馬名"), ("性齢", "性齢"), ("斤量_kg", "斤量"),
                           ("騎手", "騎手"), ("馬体重", "馬体重"), ("厩舎", "調教師")):
            if h == label and key not in col:
                col[key] = i
    if "馬番" not in col:
        return head, rows
    for tr in trs[1:]:
        td = [x.get_text(strip=True) for x in tr.select("td")]
        if len(td) <= max(col.values()):
            continue
        try:
            uma = int(td[col["馬番"]])
        except ValueError:
            continue
        rec = {}
        for key, i in col.items():
            if key == "馬番":
                continue
            v = td[i]
            if key == "斤量_kg":
                try:
                    v = float(v)
                except ValueError:
                    v = None
            if key == "厩舎":
                v = re.sub(r"^\[[東西地外]\]", "", v)
            rec[key] = v
        rows[uma] = rec
    return head, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-days", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()
    db = json.loads(STORE.read_text(encoding="utf-8"))
    need = defaultdict(list)
    for r in db:
        if not r.get("騎手"):
            need[(r["date"], r["競馬場"], int(float(r["R"])))].append(r)
    dates = sorted({k[0] for k in need})
    if a.limit_days:
        dates = dates[:a.limit_days]
    print(f"補完対象: {sum(len(v) for k, v in need.items() if k[0] in dates):,}行 / "
          f"{len([k for k in need if k[0] in dates]):,}レース / {len(dates)}日")
    bak = STORE.with_suffix(f".json.bak_backfill_{time.strftime('%Y%m%d_%H%M')}")
    shutil.copy2(STORE, bak)
    print("バックアップ:", bak.name)

    s = session()
    filled = races_done = skipped = 0
    for di, date in enumerate(dates, 1):
        ids = race_ids_for(s, date)
        by_key = {}
        for rid in ids:
            by_key[(VENUE.get(rid[4:6], "?"), int(rid[10:12]))] = rid
        for (d, ven, rno), rows in sorted((k, v) for k, v in need.items() if k[0] == date):
            rid = by_key.get((ven, rno))
            if not rid:
                skipped += len(rows); continue
            html = get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
            if not html:
                skipped += len(rows); continue
            head, parsed = parse_race(html)
            for r in rows:
                p = parsed.get(int(float(r["馬番"])))
                if not p or (r.get("馬名") and p["馬名"] and r["馬名"] != p["馬名"]):
                    skipped += 1
                    continue
                for k, v in list(head.items()) + list(p.items()):
                    if k in FIELDS and v and not r.get(k):
                        r[k] = v
                        filled += 1
            races_done += 1
            time.sleep(a.sleep)
        STORE.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
        print(f"[{di}/{len(dates)}] {date} 完了（累計 {races_done}レース・{filled:,}項目補完・不一致{skipped}）", flush=True)
    print(f"\n完了: {races_done}レース / {filled:,}項目を補完 / 照合できず{skipped}行 → {STORE.name}")


if __name__ == "__main__":
    main()
