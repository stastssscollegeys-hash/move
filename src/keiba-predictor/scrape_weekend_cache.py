# -*- coding: utf-8 -*-
"""
scrape_weekend_cache.py — 週末全レースの出馬表+過去走キャッシュ収集（増分保存版）

predict_and_report.py と同じ NetkeibaScaper / キャッシュ形式を使いつつ、
1レース処理するごとにディスクへ保存する（途中で切れても再実行で続きから）。

使い方:
  python scrape_weekend_cache.py --dates 20260801 20260802
  python scrape_weekend_cache.py --dates 20260913 --force   # 枠順確定後に取り直す（★日曜分は土曜に必須）

⚠ --force が必要な理由（2026-09-12に再発）:
  `fetch_shutuba` はキャッシュがあれば再取得しない。週の半ばに取った出馬表は
  **枠順確定前の仮馬番（五十音順）** なので、そのまま予想すると馬番が別の馬を指す。
  9/13の平場は24レース中22レースで馬番が実際と違っていた（例: 中山10R ◎イリフィが
  こちらのデータでは3番・実際は10番）。枠順確定後に必ず --force で取り直すこと。
"""
from __future__ import annotations
import shutil
import sys, argparse, time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR / 'scripts'))
sys.path.insert(0, str(SRC_DIR / 'scraper'))

from convert_netkeiba_to_features import rcode_to_netkeiba_id
from smartrc_api import SmartRCAPI
from netkeiba import NetkeibaScaper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', nargs='+', required=True, metavar='YYYYMMDD')
    ap.add_argument('--force', action='store_true',
                    help='キャッシュ済みでも出馬表を取り直す（枠順確定後は必須）')
    args = ap.parse_args()

    if args.force:   # 取り直す前に出馬表キャッシュを退避する
        cache_dir = SRC_DIR / '_cache' / 'netkeiba'
        src = cache_dir / 'shutuba.json'
        if src.exists():
            bak = cache_dir / f"shutuba_bak_{datetime.now():%Y%m%d_%H%M}.json"
            shutil.copy2(src, bak)
            print(f"出馬表キャッシュを退避: {bak.name}", flush=True)

    api = SmartRCAPI()
    jobs = []   # (date, rcode, race_id, rno, place)
    try:
        for d in args.dates:
            races = api.fetch_races(d)
            for r in races:
                rid = rcode_to_netkeiba_id(r['rcode'])
                jobs.append((d, r['rcode'], rid, r.get('rno','?'), r.get('place','?')))
            print(f"{d}: {len(races)}レース", flush=True)
    finally:
        api.close()

    nk = NetkeibaScaper()
    done = skipped = failed = 0
    total = len(jobs)
    try:
        for i, (d, rcode, rid, rno, place) in enumerate(jobs, 1):
            already = rid in nk._shutuba_cache
            if args.force:
                nk._shutuba_cache.pop(rid, None)   # 仮馬番のキャッシュを捨ててから取り直す
            shutuba = nk.fetch_shutuba(rid)
            if not shutuba:
                failed += 1
                print(f"[{i}/{total}] {d} {place} {rno}R: 取得失敗", flush=True)
                continue

            horses = shutuba['horses']
            fetched_past = 0
            for h in horses:
                hid = h.get('horse_id', '')
                if hid and hid not in nk._horse_cache:
                    nk.fetch_horse_past(hid, 5)
                    fetched_past += 1

            # ★増分保存（1レースごと）
            nk._save_disk_cache('shutuba.json', nk._shutuba_cache)
            nk._save_disk_cache('horse_past.json', nk._horse_cache)
            nk._save_disk_cache('horse_profile.json', nk._profile_cache)

            if already and fetched_past == 0:
                skipped += 1
                tag = 'キャッシュ済'
            else:
                done += 1
                tag = f'{len(horses)}頭(新規過去走{fetched_past})'
            print(f"[{i}/{total}] {d} {place} {rno}R {shutuba['race_info'].get('title','')}: {tag}",
                  flush=True)
    finally:
        nk.close()

    print(f"\n完了: 新規{done} / キャッシュ済{skipped} / 失敗{failed} / 全{total}レース", flush=True)


if __name__ == '__main__':
    main()
