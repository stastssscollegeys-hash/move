# -*- coding: utf-8 -*-
"""
snapshot_to_odds_file.py — odds_snapshot.py の保存分から、gen_digest_sns.py / gen_kaime_v5.py の
--odds-file 形式（odds_YYYYMMDD.json）を作る（2026-09-11 新規）

形式（odds_20260830.json と同じ）: {"_comment": "...", "20260912_阪神_5": {"1": 12.3, "2": 4.5, ...}}
各レースは最新時刻のスナップショットの単勝オッズを使う。

使い方: python snapshot_to_odds_file.py --date 20260912
出力:   Desktop/競馬予想レポート/{date}/odds_{date}.json
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = Path.home() / 'Desktop' / '競馬予想レポート'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    a = ap.parse_args()
    snap_dir = BASE / 'daily_pdca' / 'db' / 'odds_snapshots' / a.date
    latest = {}
    for f in sorted(snap_dir.glob('*.json')):
        rid, hhmm = f.stem.split('_')
        if rid not in latest or hhmm > latest[rid][0]:
            latest[rid] = (hhmm, f)
    out = {"_comment": f"odds_snapshot.py の最新スナップショット（単勝）から生成。レース別の取得時刻は _fetched を参照"}
    fetched = {}
    for rid, (hhmm, f) in sorted(latest.items()):
        s = json.loads(f.read_text(encoding='utf-8'))
        win = s.get('odds', {}).get('単勝') or {}
        odds = {}
        for k, v in win.items():
            try:
                o = float(v[0])
            except (TypeError, ValueError, IndexError):
                continue
            if o > 0:
                odds[str(int(k))] = o
        if not odds:
            print(f"[WARN] {rid} 単勝オッズなし"); continue
        key = f"{a.date}_{s.get('venue')}_{int(s.get('R'))}"
        out[key] = odds
        fetched[key] = f"{s.get('fetched_at')} / 発表{(s.get('odds_meta', {}).get('単勝') or {}).get('official_datetime')}"
    out['_fetched'] = fetched
    p = BASE / a.date / f'odds_{a.date}.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"保存: {p}（{len(fetched)}レース）")


if __name__ == '__main__':
    main()
