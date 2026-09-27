# -*- coding: utf-8 -*-
"""
fetch_pedigree_netkeiba.py — 残りの父・母父をnetkeibaから埋める（2026-09-25）
=============================================================================
手元のデータ（smartrc_runners.json / JV-Linkの血統ファイル）で90.7%まで埋めた残り、
3,085行・1,791頭ぶんをnetkeibaの血統ページから取る。

手順:
  ① 馬名→horse_id（＝血統登録番号）: まず出馬表キャッシュから引く（1,269頭ぶん）。
     足りない馬は、その馬が走ったレースの結果ページ（db.netkeiba）を開いてリンクからIDを拾う
  ② 血統ページ db.netkeiba.com/horse/ped/{id}/ の blood_table から
     父（rowspan16の1つ目）と母父（rowspan8の3つ目）を取る
  ③ race_results.json の空欄だけ埋める（既存値は上書きしない）

途中で止めても再開できる（取得済みは _cache/pedigree_netkeiba.json に貯める）。
使い方: python fetch_pedigree_netkeiba.py [--limit 300] [--sleep 1.0]
"""
from __future__ import annotations
import argparse, json, re, shutil, sys, io, time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bs4 import BeautifulSoup
from fetch_payouts import session, get, race_ids_for, VENUE

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
RESULTS = DB / "race_results.json"
CACHE = HERE / "_cache" / "pedigree_netkeiba.json"
IDMAP = HERE / "_cache" / "name_to_horseid.json"


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def parse_ped(html: str) -> tuple[str, str] | None:
    soup = BeautifulSoup(html, "html.parser")
    t = soup.select_one("table.blood_table")
    if not t:
        return None
    cells = []
    for td in t.select("td"):
        a = td.select_one("a")
        cells.append((int(td.get("rowspan") or 1), (a.get_text(strip=True) if a else td.get_text(" ", strip=True))))
    g1 = [c[1] for c in cells if c[0] == 16]
    g2 = [c[1] for c in cells if c[0] == 8]
    if not g1:
        return None
    return g1[0], (g2[2] if len(g2) > 2 else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="この頭数だけ取得して終わる（試すとき用）")
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()

    db = json.loads(RESULTS.read_text(encoding="utf-8"))
    need_rows = [r for r in db if not r.get("父") and r.get("馬名")]
    need = {r["馬名"] for r in need_rows}
    print(f"父が無い: {len(need_rows):,}行 / {len(need):,}頭")

    # ① 馬名→ID
    name2id = load(IDMAP, {})
    sh = load(HERE / "_cache" / "netkeiba" / "shutuba.json", {})
    for v in sh.values():
        for h in v.get("horses", []):
            if h.get("horse_name") and h.get("horse_id"):
                name2id.setdefault(h["horse_name"], h["horse_id"])
    unknown = need - set(name2id)
    print(f"IDが分かる: {len(need & set(name2id)):,}頭 ／ 不明: {len(unknown):,}頭")

    s = session()
    if unknown:
        races = defaultdict(set)
        for r in need_rows:
            if r["馬名"] in unknown:
                races[r["date"]].add((r["競馬場"], int(float(r["R"]))))
        print(f"IDを拾うために開くレース: {sum(len(v) for v in races.values()):,}（{len(races)}日）")
        for di, (date, keys) in enumerate(sorted(races.items()), 1):
            ids = race_ids_for(s, date)
            by_key = {(VENUE.get(rid[4:6], "?"), int(rid[10:12])): rid for rid in ids}
            for ven, rno in sorted(keys):
                rid = by_key.get((ven, rno))
                if not rid:
                    continue
                html = get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
                if not html:
                    continue
                for aa in BeautifulSoup(html, "html.parser").select('a[href*="/horse/"]'):
                    m = re.search(r"/horse/(\d{8,12})", aa.get("href", ""))
                    nm = aa.get_text(strip=True)
                    if m and nm:
                        name2id.setdefault(nm, m.group(1))
                time.sleep(a.sleep)
            IDMAP.write_text(json.dumps(name2id, ensure_ascii=False), encoding="utf-8")
            print(f"  [{di}/{len(races)}] {date} ID {len(name2id):,}件", flush=True)

    # ② 血統ページ
    ped = load(CACHE, {})
    todo = [n for n in sorted(need) if n in name2id and name2id[n] not in ped]
    if a.limit:
        todo = todo[:a.limit]
    print(f"血統を取りに行く: {len(todo):,}頭（取得済み {len(ped):,}頭）")
    ok = ng = 0
    for i, nm in enumerate(todo, 1):
        hid = name2id[nm]
        html = get(s, f"https://db.netkeiba.com/horse/ped/{hid}/", "euc-jp")
        p = parse_ped(html) if html else None
        if p:
            ped[hid] = {"name": nm, "father": p[0], "mf": p[1]}
            ok += 1
        else:
            ng += 1
        if i % 25 == 0 or i == len(todo):
            CACHE.write_text(json.dumps(ped, ensure_ascii=False), encoding="utf-8")
            print(f"  [{i}/{len(todo)}] 取得{ok} 失敗{ng}", flush=True)
        time.sleep(a.sleep)
    CACHE.write_text(json.dumps(ped, ensure_ascii=False), encoding="utf-8")

    # ③ 書き込み
    by_name = {v["name"]: v for v in ped.values()}
    filled = 0
    for r in db:
        if r.get("父") or not r.get("馬名"):
            continue
        p = by_name.get(r["馬名"])
        if not p:
            continue
        r["父"] = p["father"]
        if p["mf"] and not r.get("母父"):
            r["母父"] = p["mf"]
        filled += 1
    bak = RESULTS.with_suffix(f".json.bak_ped2_{time.strftime('%Y%m%d_%H%M')}")
    shutil.copy2(RESULTS, bak)
    RESULTS.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
    rest = sum(1 for r in db if not r.get("父"))
    print(f"\n完了: {filled:,}行を補完 ／ 父なしの残り {rest:,}行（{rest/len(db)*100:.1f}%）")
    print("バックアップ:", bak.name)


if __name__ == "__main__":
    main()
