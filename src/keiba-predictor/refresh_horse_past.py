# -*- coding: utf-8 -*-
"""
refresh_horse_past.py — 出走馬の過去走キャッシュを「日付つき」で取り直す（2026-09-11 新規）
==========================================================================================
背景（docs/keiba_roi100_roadmap.md §6-1）:
  `_cache/netkeiba/horse_past.json` は一度取った馬を二度と取り直さない。9/4 に scraper が日付を
  返すよう直したが、それ以前に取った古い形式（日付なし）がキャッシュの約9割に残っており、
  中日数が0になる・直近走が抜けていても分からない。9/12-13 の records でも約75%の馬が中日数0だった。

やること:
  指定レース（shutuba.json に入っている出走馬）のうち、キャッシュに無い馬・日付の無い馬だけを取り直す。
  実行前に horse_past.json をバックアップする。書き込むのは horse_past.json だけ。

使い方:
  python refresh_horse_past.py --race-ids 202609040311
  python refresh_horse_past.py --race-ids 202606040411 202609040411 --all   # 日付があっても全頭取り直す
その後: python collect_weekend_bigdata.py --dates YYYYMMDD ...
"""
from __future__ import annotations
import argparse, json, shutil, sys, io
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from scraper.netkeiba import NetkeibaScaper

CACHE = Path(__file__).resolve().parent / '_cache' / 'netkeiba'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--race-ids', nargs='+', required=True)
    ap.add_argument('--all', action='store_true', help='日付がある馬も取り直す')
    a = ap.parse_args()

    shutuba = json.load(open(CACHE / 'shutuba.json', encoding='utf-8'))
    bak = CACHE / f"horse_past_bak_{datetime.now():%Y%m%d_%H%M}.json"
    shutil.copy2(CACHE / 'horse_past.json', bak)
    print(f'バックアップ: {bak.name}')

    nk = NetkeibaScaper()
    cache = nk._horse_cache
    todo = []
    for rid in a.race_ids:
        race = shutuba.get(rid)
        if not race:
            print(f'[WARN] {rid} は shutuba.json に無い（先に出馬表を取り直す）'); continue
        for h in race['horses']:
            hid = h.get('horse_id')
            if not hid:
                continue
            past = cache.get(hid)
            if a.all or past is None or not any(p.get('date') for p in past):
                todo.append((rid, hid, h.get('horse_name', '')))
    print(f'取り直し対象 {len(todo)}頭')
    for i, (rid, hid, nm) in enumerate(todo, 1):
        before = cache.pop(hid, None)
        res = nk.fetch_horse_past(hid, max_races=99)
        if not res and before:          # 取得失敗時は元に戻す（空で上書きしない）
            cache[hid] = before
            print(f'  [{i}/{len(todo)}] {nm}: 取得失敗 → 元のまま'); continue
        last = next((p.get('date') for p in res if p.get('date')), None)
        print(f"  [{i}/{len(todo)}] {nm}: {len(before or [])}走(日付{'あり' if before and any(p.get('date') for p in before) else 'なし'}) → {len(res)}走 直近{last}")
    nk._save_disk_cache('horse_past.json', cache)
    print('保存: horse_past.json')


if __name__ == '__main__':
    main()
