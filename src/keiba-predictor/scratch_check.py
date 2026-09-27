# -*- coding: utf-8 -*-
"""
scratch_check.py — 当日朝の出走取消チェック（2026-09-12 新設）
================================================================
背景: 9/12チャレンジCで▲⑬グランヴィノスが出走取消だったのに、買い目3点のうち2点（8,000円中3,200円）が
      その馬を含んだまま公開されていた。予想・買い目・SNS生成のどこにも取消の判定が無かった。

判定: その時刻の単勝オッズに馬番が無い＝取消・除外とみなす（netkeibaのオッズAPIは取消馬を返さない）。
      先に `python odds_snapshot.py --date YYYYMMDD` で当日の実オッズを取っておくこと。

使い方:
  python scratch_check.py --date 20260913
  python scratch_check.py --date 20260913 --marks チャレンジC=9,11,13   # 印の馬が取消かどうかも判定する
終了コード: 取消が1頭でもあれば 1（買い目を組み直す合図）、無ければ 0
"""
from __future__ import annotations
import argparse, json, sys, io, collections
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = Path.home() / 'Desktop' / '競馬予想レポート'


def latest_snapshots(date: str) -> dict:
    d = BASE / 'daily_pdca' / 'db' / 'odds_snapshots' / date
    out = {}
    for f in sorted(d.glob('*.json')):
        rid, hhmm = f.stem.split('_')
        if rid not in out or hhmm > out[rid][0]:
            out[rid] = (hhmm, f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--records', help='週末ビッグデータ_*_records.json（省略時は自動検出）')
    ap.add_argument('--marks', nargs='*', default=[], help='レース名=馬番,馬番,... 形式で印の馬を渡すと取消判定する')
    a = ap.parse_args()

    if a.records:
        rec_path = Path(a.records)
    else:
        cands = sorted((BASE / a.date[:8]).glob('週末ビッグデータ_*_records.json')) if (BASE / a.date).exists() else []
        if not cands:
            cands = sorted(BASE.glob(f'*/週末ビッグデータ_{a.date}-*_records.json'))
        if not cands:
            print(f'[ERROR] {a.date} の records が見つかりません'); return 2
        rec_path = cands[0]
    recs = [r for r in json.loads(rec_path.read_text(encoding='utf-8'))['records'] if r['date'] == a.date]
    if not recs:
        print(f'[ERROR] {rec_path.name} に {a.date} のレコードがありません'); return 2
    by_race = collections.defaultdict(dict)
    for r in recs:
        by_race[(r['競馬場'], int(r['R']))][int(r['馬番'])] = r['馬名']

    snaps = latest_snapshots(a.date)
    if not snaps:
        print(f'[ERROR] {a.date} のオッズスナップショットがありません。先に odds_snapshot.py を実行すること'); return 2

    scratched = {}
    for rid, (hhmm, f) in sorted(snaps.items()):
        s = json.loads(f.read_text(encoding='utf-8'))
        key = (s.get('venue'), int(s.get('R')))
        entry = by_race.get(key)
        if not entry:
            continue
        live = {int(k) for k in (s.get('odds', {}).get('単勝') or {})}
        if not live:
            print(f'  [SKIP] {key[0]}{key[1]}R 単勝オッズが空（発売前）')
            continue
        gone = sorted(set(entry) - live)
        if gone:
            scratched[key] = [(u, entry[u]) for u in gone]
            print(f'🔴 {key[0]}{key[1]}R 取消・除外 {len(gone)}頭（{hhmm}時点）: ' + ' '.join(f'{u}番{entry[u]}' for u in gone))
    if not scratched:
        print(f'{a.date}: 取消なし（{len(snaps)}レース確認）')
    for m in a.marks:
        try:
            name, nums = m.split('=')
            nums = [int(x) for x in nums.split(',')]
        except ValueError:
            print(f'[WARN] --marks の書式が違います: {m}'); continue
        hit = [(k, u, nm) for k, v in scratched.items() for u, nm in v if u in nums]
        print(f'  印チェック {name}: ' + ('🔴 ' + ' '.join(f'{k[0]}{k[1]}R {u}番{nm}が取消' for k, u, nm in hit) if hit else '印の馬に取消なし'))
    return 1 if scratched else 0


if __name__ == '__main__':
    sys.exit(main())
