# -*- coding: utf-8 -*-
"""
rule_forward_ledger.py — 暫定ルールR1の前向き成績台帳（2026-09-11 事前登録）
============================================================================
R1: 「◎と○がどちらも1〜3番人気のレースだけ、◎○▲の馬連BOXを推定配当に反比例で買う。それ以外は見送る」
    （docs/keiba_roi100_roadmap.md §3。検証に使った385R＝〜20260906は判定に含めない）

判定基準（事前登録）:
  採用: 前向き累計の95%区間の下限が100%を超えたとき
  棄却: 前向き100レース時点で、最高配当1レース除外の回収率が80%を下回ったとき
  継続: それ以外

使い方:
  python rule_forward_ledger.py --add-week "C:\\Users\\User\\Desktop\\競馬予想レポート\\20260912"   # レース前: 買い目を登録
  python rule_forward_ledger.py --settle     # レース後: payouts.json と突き合わせて払戻を記録（fetch_payouts.py の後）
  python rule_forward_ledger.py --report     # 累計成績と判定
台帳: Desktop/競馬予想レポート/daily_pdca/db/rule_r1_ledger.json
"""
from __future__ import annotations
import argparse, glob, json, random, sys, io
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'
LEDGER = DB / 'rule_r1_ledger.json'
REGISTERED = '2026-09-11'
FIRST_ELIGIBLE_DATE = '20260907'   # これより前のレースは検証に使ったので判定に含めない


def load():
    return json.load(open(LEDGER, encoding='utf-8')) if LEDGER.exists() else []


def save(rows):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def add_week(week_dir: str):
    d = Path(week_dir)
    kaime_files = sorted(glob.glob(str(d / 'research' / 'kaime_*.json')))
    odds_files = (sorted(glob.glob(str(d / 'odds_live_*.json')))
                  or sorted(glob.glob(str(d / 'yoso_odds_*.json'))))
    if not kaime_files:
        print('[ERROR] research/kaime_*.json が見つかりません'); return

    kaime, odds = {}, {}
    for f in kaime_files:
        k = json.load(open(f, encoding='utf-8'))
        if isinstance(k, dict) and 'design' in k and 'race' in k:
            # 新形式（kaime_mixed.py 出力）を旧スキーマに合わせる
            dd = k['design']
            kaime[k['race']] = dict(
                marks=k['marks'], budget=dd.get('budget', 0),
                pattern='見送り' if dd.get('skip') else dd.get('arch', '混合型 ◎は指数・相手は人気上位'),
                bets=[{'t': b['t'], 'combo': sorted((dd['hon'], b['u'])), 'est': b.get('est')}
                      | {'amt': b['amt']} for b in dd.get('bets', [])])
        else:
            kaime.update(k)
    if odds_files:
        odds = json.load(open(odds_files[-1], encoding='utf-8'))
    else:
        # odds_YYYYMMDD.json（{"YYYYMMDD_競馬場_R": {馬番: 単勝オッズ}}）から人気を作る。
        # レースの特定と race_id は payouts.json / race_results.json（確定データ）から引く。
        pays = json.load(open(DB / 'payouts.json', encoding='utf-8'))
        res = json.load(open(DB / 'race_results.json', encoding='utf-8'))
        rid_of = {(v['date'], v['venue'], int(v['R'])): k for k, v in pays.items()}
        title_of = {(r['date'], r['競馬場'], int(r['R'])): r.get('レース名') for r in res if r.get('レース名')}
        for f in sorted(glob.glob(str(d / 'odds_*.json'))):
            raw = json.load(open(f, encoding='utf-8'))
            for key, o in raw.items():
                if not isinstance(o, dict) or key.startswith('_'):
                    continue
                day, venue, R = key.split('_')
                title = title_of.get((day, venue, int(R)))
                rid = rid_of.get((day, venue, int(R)))
                if not title or not rid:
                    continue
                race = next((nm for nm in kaime
                             if nm.replace('S', '').replace('ステークス', '') in title), None)
                if race is None or race in odds:
                    continue
                order = sorted(o.items(), key=lambda kv: kv[1])
                odds[race] = {'race_id': rid, 'source': f'前日オッズ({Path(f).name})',
                              'horses': [{'uma': int(u), 'pop': i + 1} for i, (u, _) in enumerate(order)]}
        if not odds:
            print('[ERROR] オッズファイルからレースを特定できなかった'); return
        print(f'[INFO] odds_YYYYMMDD.json から人気を復元（{len(odds)}レース）')
    rows = load()
    have = {r['race_id'] for r in rows}
    added = 0
    for race, k in kaime.items():
        o = odds.get(race)
        if not o:
            print(f'[WARN] {race}: オッズファイルに無い'); continue
        rid = o['race_id']
        if rid in have:
            print(f'[SKIP] {race}（{rid}）は登録済み'); continue
        pop = {h['uma']: h['pop'] for h in o['horses'] if h.get('uma') and h.get('pop')}
        m = k['marks']
        rows.append({
            'race_id': rid, 'race': race, 'registered_at': datetime.now().isoformat(timespec='minutes'),
            'odds_source': o.get('source', '予想'), 'marks': m,
            'hon_pop': pop.get(m['◎']), 'tai_pop': pop.get(m['○']), 'tan_pop': pop.get(m['▲']),
            'rule_ok': k['pattern'] != '見送り', 'pattern': k['pattern'], 'budget': k['budget'],
            'bets': [{'t': b['t'], 'combo': b['combo'], 'amt': b['amt'], 'odds_at_bet': b['est']} for b in k['bets']],
            'settled': False, 'payout': None,
        })
        added += 1
        print(f"[ADD] {race}（{rid}）◎{pop.get(m['◎'])}人気 ○{pop.get(m['○'])}人気 → {k['pattern']} 予算{k['budget']:,}円")
    save(rows)
    print(f'登録 {added}件 → 累計 {len(rows)}件（{LEDGER.name}）')
    print('⚠ 当日朝の実オッズで人気が変わったら、kaime を作り直してから --add-week をやり直すこと（登録済みは上書きしない）')


def settle():
    pays = json.load(open(DB / 'payouts.json', encoding='utf-8'))
    rows = load()
    n = 0
    for r in rows:
        if r['settled']:
            continue
        p = pays.get(r['race_id'])
        if not p:
            continue
        ret = 0
        for b in r['bets']:
            for x in p['payouts'].get(b['t'], []):
                if sorted(int(v) for v in x['combo'].split('-')) == sorted(b['combo']):
                    ret += b['amt'] * x['yen'] / 100
        r['payout'] = ret
        r['settled'] = True
        r['date'] = p.get('date')
        n += 1
        print(f"[SETTLE] {r['race']} {r['pattern']} 投資{r['budget']:,}円 → 払戻{int(ret):,}円")
    save(rows)
    print(f'精算 {n}件')


def report():
    rows = [r for r in load() if r['settled'] and (r.get('date') or '') >= FIRST_ELIGIBLE_DATE]
    bet = [r for r in rows if r['rule_ok'] and r['budget'] > 0]
    skip = [r for r in rows if not r['rule_ok']]
    print(f"■ R1 前向き成績（事前登録 {REGISTERED}／{FIRST_ELIGIBLE_DATE}以降のレースのみ）")
    print(f"  精算済み {len(rows)}R ／ 買った {len(bet)}R ／ 見送り {len(skip)}R")
    if not bet:
        print('  まだ判定できるデータがありません'); return
    inv = sum(r['budget'] for r in bet); ret = sum(r['payout'] for r in bet)
    by = sorted(bet, key=lambda r: -r['payout'])
    rest = by[1:]
    ex1 = sum(r['payout'] for r in rest) / sum(r['budget'] for r in rest) if rest else None
    rng = random.Random(1)
    boots = []
    for _ in range(4000):
        smp = [bet[rng.randrange(len(bet))] for _ in bet]
        si = sum(r['budget'] for r in smp)
        boots.append(sum(r['payout'] for r in smp) / si)
    boots.sort()
    lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]
    hit = sum(1 for r in bet if r['payout'] > 0) / len(bet)
    print(f"  回収率 {ret/inv*100:.1f}% ［95%区間 {lo*100:.0f}〜{hi*100:.0f}%］ ／ 上位1除外 {ex1*100:.1f}% ／ 的中率 {hit*100:.1f}%" if ex1 is not None
          else f"  回収率 {ret/inv*100:.1f}% ／ 的中率 {hit*100:.1f}%")
    if lo > 1.0:
        verdict = '【採用】95%区間の下限が100%を超えた'
    elif len(bet) >= 100 and ex1 is not None and ex1 < 0.80:
        verdict = '【棄却】100レース時点で上位1除外が80%未満'
    else:
        verdict = f'【継続】（買ったレース {len(bet)}/100 で棄却判定、下限100%超で採用）'
    print('  判定:', verdict)
    skip_ret = [r for r in skip]
    if skip_ret:
        print(f"  参考: 見送ったレースの件数 {len(skip_ret)}（見送りの妥当性は、同じ買い方を当てた場合の成績で別途確認）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--add-week')
    ap.add_argument('--settle', action='store_true')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if a.add_week:
        add_week(a.add_week)
    if a.settle:
        settle()
    if a.report or not (a.add_week or a.settle):
        report()


if __name__ == '__main__':
    main()
