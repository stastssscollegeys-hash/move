# -*- coding: utf-8 -*-
"""
load_leakfree.py — 検証側で「本物のレース前records（結果リーク除外済み）＋
leak-free backfill版」をまとめて読み込むための新規ローダー。

engine_backtest.py は一切変更しない（読み取り専用でimportし、その load_races() /
drop_leaky() をそのまま再利用して genuine 側を作る）。backfill_leakfree.py が
Desktop/競馬予想レポート/backfill_leakfree/{date}/leakfree_records_{date}.json に
保存したレコードを追加でマージし、engine_backtest.load_races() と同じ形式
（(date, venue, R) -> {'recs','odds','top3','pay'}）に 'origin' キーを足して返す。

使い方:
  from load_leakfree import load_races_leakfree
  races = load_races_leakfree()
  races[key]['origin']  # 'genuine' | 'leakfree'
"""
from __future__ import annotations
import collections, datetime, json, sys
from pathlib import Path

PROD_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROD_ROOT))

import engine_backtest as EB   # 読み取り専用import。書き込みは一切行わない。

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
DB = BASE / 'daily_pdca' / 'db'
LEAKFREE_DIR = BASE / 'backfill_leakfree'


def _load_payouts_and_results():
    payouts = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    res_by = collections.defaultdict(list)
    for r in res:
        res_by[(r['date'], r['競馬場'], int(r['R']))].append(r)
    return payouts, res_by


def _match_with_payouts(pre_by_key: dict, payouts: dict, res_by: dict) -> dict:
    """engine_backtest.load_races() 後半と同じマッチングロジック（複製・読み取り専用）。
    pre_by_key: (date,venue,R) -> list[recs]"""
    out = {}
    for rid, v in payouts.items():
        key = (v['date'], v['venue'], v['R'])
        recs = pre_by_key.get(key)
        rows = res_by.get(key)
        if not recs or not rows or len(recs) < 8:
            continue
        odds, fin = {}, []
        for r in rows:
            try:
                num = str(int(float(r['馬番'])))
                o = float(r['単勝オッズ'])
            except (TypeError, ValueError):
                continue
            odds[num] = o
            if r.get('着順int'):
                fin.append((num, r['着順int']))
        if len(fin) < 3:
            continue
        fin.sort(key=lambda x: x[1])
        top3 = [fin[0][0], fin[1][0], fin[2][0]]
        if not all(str(r.get('馬番')) in odds for r in recs):
            continue
        out[key] = {'recs': recs, 'odds': odds, 'top3': top3, 'pay': v['payouts']}
    return out


def _load_leakfree_pre() -> tuple[dict, dict]:
    """backfill_leakfree/*/leakfree_records_*.json を読み込み、
    (date,venue,R) -> recs のdictと、そのprovenance情報を返す。"""
    pre = collections.defaultdict(list)
    prov = {}
    if not LEAKFREE_DIR.exists():
        return pre, prov
    for f in sorted(LEAKFREE_DIR.glob('*/leakfree_records_*.json')):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        recs_in = d.get('records', [])
        if not recs_in:
            continue
        by_key_this_file = collections.defaultdict(list)
        for r in recs_in:
            key = (r['date'], r['競馬場'], int(r['R']))
            by_key_this_file[key].append(r)
        for key, recs in by_key_this_file.items():
            pre[key] = recs   # 1レース=1ファイルのはずなので上書きでよい
            prov[key] = d.get('provenance', {})
    return pre, prov


def load_races_leakfree(include_leakfree: bool = True) -> dict:
    """genuine（結果リーク除外済みの本物レース前records）+ leakfree backfill版を
    engine_backtest.load_races() と同じ形式で返す。各レースに 'origin' を付与する。
    同じ(date,venue,R)が両方にある場合は genuine を優先する。"""
    payouts, res_by = _load_payouts_and_results()

    # ---- genuine 側: engine_backtest.load_races() + drop_leaky() をそのまま利用 ----
    genuine_races = EB.load_races()
    genuine_races = EB.drop_leaky(genuine_races, verbose=False)
    for v in genuine_races.values():
        v['origin'] = 'genuine'

    if not include_leakfree:
        return genuine_races

    # ---- leakfree 側 ----
    leakfree_pre, _prov = _load_leakfree_pre()
    leakfree_races = _match_with_payouts(leakfree_pre, payouts, res_by)
    for v in leakfree_races.values():
        v['origin'] = 'leakfree'

    merged = dict(leakfree_races)
    merged.update(genuine_races)   # genuine優先（同キーがあれば上書き）
    return merged


def summarize(races: dict) -> None:
    by_origin = collections.Counter(v['origin'] for v in races.values())
    by_date_origin = collections.defaultdict(lambda: collections.Counter())
    for (d, _v, _r), v in races.items():
        by_date_origin[d][v['origin']] += 1
    print(f"合計 {len(races)}レース  {dict(by_origin)}")
    for d in sorted(by_date_origin):
        print(f"  {d}: {dict(by_date_origin[d])}")


if __name__ == '__main__':
    races = load_races_leakfree()
    summarize(races)
