"""
smartrc/netkeibaデータから予測 — ULTIMATE v2フィルター適用

smartrc APIまたはnetkeiba出馬表でデータ取得 → 44特徴量変換 → LightGBMで予測

使い方:
  python predict_smartrc.py 20260412hanshin11        # 単一レース（smartrc）
  python predict_smartrc.py --date 20260412 --all    # 指定日全レース（smartrc）
  python predict_smartrc.py --date 20260412 --all --netkeiba  # netkeiba出馬表（前日予測用）

前日予測（--netkeiba）:
  - odds/ninkiが未確定のため、abilityモデルのみで予測
  - EVフィルターの代わりにability確率でランキング
  - 距離・頭数等の基本フィルターは同じ

依存:
  - data/stats/*.json (extract_stats.py + build_smartrc_id_map.py で事前生成)
  - data/models/lgb_v44_*.txt (学習済みモデル)
  - data/jvlink_v3/bloodline_parsed.jsonl (netkeiba使用時)
"""
import sys
import os
import csv
import io
import argparse
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(SRC_DIR, 'data')
MODEL_DIR = os.path.join(DATA_DIR, 'models')

sys.path.insert(0, SCRIPT_DIR)
from convert_smartrc_to_features import (
    load_stats as load_stats_smartrc, convert_race, FIELDNAMES,
)
from convert_netkeiba_to_features import (
    load_stats as load_stats_nk, load_bloodline, load_name_to_id_maps,
    convert_shutuba_horse, rcode_to_netkeiba_id, rcode_to_month,
)

sys.path.insert(0, os.path.join(SRC_DIR, 'scraper'))
from smartrc_api import SmartRCAPI, _VENUE_EN
from netkeiba import NetkeibaScaper

VENUE_NAMES = {1:'札幌',2:'函館',3:'福島',4:'新潟',5:'東京',
               6:'中山',7:'中京',8:'京都',9:'阪神',10:'小倉'}

# ULTIMATE v2 フィルター定数
EV_THRESHOLD = 1.35
DIV_THRESHOLD = 0.10
MIN_DISTANCE = 1800
MIN_RUNNERS = 10
MAX_ODDS = 100
EXCLUDED_VENUES = {3}  # 福島
MIN_AGE = 3
MIN_NINKI = 5

FEATURE_COLS = [
    'waku', 'sex_cd', 'barei', 'futan', 'ba_taijyu', 'zogen_sa', 'blinker',
    'distance', 'dist_cat', 'surface', 'grade_cd', 'tenko_cd', 'baba_cd',
    'syusso_tosu', 'prize_1', 'venue_cd', 'month', 'race_num',
    'odds', 'ninki',
    'num_past_races', 'avg_finish_5', 'best_finish_5',
    'win_rate_5', 'top3_rate_5',
    'avg_time_5', 'avg_l3f_5',
    'days_since_last', 'running_style', 'avg_j4c_5',
    'same_dist_runs', 'same_dist_winrate', 'same_dist_top3rate',
    'same_surface_runs', 'same_surface_winrate', 'same_surface_top3rate',
    'heavy_baba_runs', 'heavy_baba_top3rate',
    'jockey_winrate', 'trainer_winrate',
    'father_winrate', 'bms_winrate',
    'father_surface_wr', 'bms_surface_wr',
]
ABILITY_COLS = [c for c in FEATURE_COLS if c not in ('odds', 'ninki')]


def to_float(v):
    if v is None or v == '' or v == 'None':
        return float('nan')
    try:
        return float(v)
    except (ValueError, TypeError):
        return float('nan')


def main():
    import lightgbm as lgb
    import numpy as np

    parser = argparse.ArgumentParser(description='smartrc/netkeibaから予測')
    parser.add_argument('race_id', nargs='?',
                        help='レースID (例: 20260412hanshin11)')
    parser.add_argument('--date', type=str,
                        help='対象日 YYYYMMDD')
    parser.add_argument('--venue', type=str,
                        help='会場名 (hanshin等)')
    parser.add_argument('--all', action='store_true',
                        help='指定日の全レースを予測')
    parser.add_argument('--netkeiba', action='store_true',
                        help='netkeiba出馬表から取得（前日予測用）')
    parser.add_argument('--no-filter', action='store_true',
                        help='距離/頭数フィルターなしで全レース予想を出力')
    args = parser.parse_args()

    # ---- Load models ----
    import shutil, tempfile
    tmp_model_dir = os.path.join(tempfile.gettempdir(), 'keiba_models_predict')
    os.makedirs(tmp_model_dir, exist_ok=True)

    print("Loading models...", file=sys.stderr)
    market_models = []
    ability_models = []
    model_version = None
    for ver in ['v44', 'v17']:
        if market_models:
            break
        for i in range(3):
            src = os.path.join(MODEL_DIR, f'lgb_{ver}_market_{i}.txt')
            if os.path.exists(src):
                dst = os.path.join(tmp_model_dir, f'lgb_{ver}_market_{i}.txt')
                shutil.copy2(src, dst)
                market_models.append(lgb.Booster(model_file=dst))
        if market_models:
            model_version = ver
            for i in range(3):
                src = os.path.join(MODEL_DIR, f'lgb_{ver}_ability_{i}.txt')
                if os.path.exists(src):
                    dst = os.path.join(tmp_model_dir, f'lgb_{ver}_ability_{i}.txt')
                    shutil.copy2(src, dst)
                    ability_models.append(lgb.Booster(model_file=dst))

    if not market_models or not ability_models:
        print("ERROR: モデルが見つかりません", file=sys.stderr)
        return
    print(f"  Model: {model_version} (M:{len(market_models)} A:{len(ability_models)})", file=sys.stderr)

    # ---- Load stats ----
    print("Loading stats...", file=sys.stderr)
    use_netkeiba = args.netkeiba
    if use_netkeiba:
        stats = load_stats_nk()
        bloodline = load_bloodline()
        name_father_map, name_bms_map = load_name_to_id_maps()
        print(f"  Bloodline: {len(bloodline)} horses, NameMaps: F={len(name_father_map)} B={len(name_bms_map)}", file=sys.stderr)
    else:
        stats = load_stats_smartrc()
        bloodline = {}
        name_father_map, name_bms_map = {}, {}

    # ---- Fetch & convert data ----
    all_rows = []
    api = SmartRCAPI()

    try:
        if use_netkeiba:
            # netkeiba出馬表モード（前日予測用）
            print("Fetching from netkeiba...", file=sys.stderr)
            nk = NetkeibaScaper()

            if not args.date:
                print("[ERROR] --netkeiba には --date が必要", file=sys.stderr)
                return

            races = api.fetch_races(args.date)
            if not races:
                print(f"[ERROR] {args.date} のレースなし", file=sys.stderr)
                return

            if args.venue:
                venue_code = _VENUE_EN.get(args.venue, args.venue)
                races = [r for r in races if r.get('place') == venue_code]

            for r in races:
                rcode = r['rcode']
                nk_id = rcode_to_netkeiba_id(rcode)
                month = rcode_to_month(rcode)
                shutuba = nk.fetch_shutuba(nk_id)
                if not shutuba:
                    print(f"  {r.get('rno','?')}R: データなし", file=sys.stderr)
                    continue

                race_info = shutuba['race_info']
                race_info['month'] = month
                horses = shutuba['horses']
                print(f"  {r.get('rno','?')}R {race_info.get('title','')}: {len(horses)}頭",
                      file=sys.stderr, end="", flush=True)

                for h in horses:
                    hid = h.get('horse_id', '')
                    past = nk.fetch_horse_past(hid, 5) if hid else []
                    row = convert_shutuba_horse(
                        h, race_info, past, stats, bloodline,
                        name_father_map=name_father_map,
                        name_bms_map=name_bms_map,
                        nk_scraper=nk,
                    )
                    # race_idをsmartrc rcodeに統一（フィルターで使うため）
                    row['race_id'] = rcode
                    all_rows.append(row)

                print(f" OK", file=sys.stderr)

            nk.close()
        else:
            # smartrcモード（当日予測用）
            print("Fetching from smartrc...", file=sys.stderr)

            if args.race_id:
                date, venue_code, race_num = api._parse_input(args.race_id)
                races = api.fetch_races(date)
                for r in races:
                    if r.get('place') == venue_code and str(int(r.get('rno', '0'))) == str(race_num):
                        rows = convert_race(api, r['rcode'], r, stats)
                        all_rows.extend(rows)
                        print(f"  {r.get('rno')}R {r.get('name','')}: {len(rows)}頭", file=sys.stderr)
                        break

            elif args.date:
                races = api.fetch_races(args.date)
                if not races:
                    print(f"[ERROR] {args.date} のレースなし", file=sys.stderr)
                    return

                if args.venue:
                    venue_code = _VENUE_EN.get(args.venue, args.venue)
                    races = [r for r in races if r.get('place') == venue_code]

                if not args.all and not args.venue:
                    print("[ERROR] --date には --venue or --all を指定", file=sys.stderr)
                    return

                for r in races:
                    rows = convert_race(api, r['rcode'], r, stats)
                    all_rows.extend(rows)
                    print(f"  {r.get('rno','?')}R {r.get('name','')}: {len(rows)}頭", file=sys.stderr)

            else:
                parser.print_help()
                return

    finally:
        api.close()

    if not all_rows:
        print("データが取得できませんでした", file=sys.stderr)
        return

    print(f"  Total: {len(all_rows)} horses", file=sys.stderr)

    # ---- Predict ----
    X_ability = np.array(
        [[to_float(r.get(c)) for c in ABILITY_COLS] for r in all_rows],
        dtype=np.float32
    )
    pred_ability = np.mean([m.predict(X_ability) for m in ability_models], axis=0)

    if use_netkeiba:
        # 前日予測: abilityモデルのみ（odds/ninkiなし）
        pred_market = np.zeros_like(pred_ability)
    else:
        X_full = np.array(
            [[to_float(r.get(c)) for c in FEATURE_COLS] for r in all_rows],
            dtype=np.float32
        )
        pred_market = np.mean([m.predict(X_full) for m in market_models], axis=0)

    # ---- Group by race ----
    race_entries = defaultdict(list)
    for j, row in enumerate(all_rows):
        o = to_float(row.get('odds'))
        mip = 1.0 / o if o > 0 else 0
        race_entries[row['race_id']].append({
            'row': row,
            'pred_market': float(pred_market[j]),
            'pred_ability': float(pred_ability[j]),
            'ev': float(pred_market[j]) * o if not np.isnan(o) and o > 0 else 0,
            'div': float(pred_ability[j]) - mip if not np.isnan(o) and o > 0 else float(pred_ability[j]),
            'odds': o if not np.isnan(o) else 0,
            'umaban': str(row.get('umaban', '')).zfill(2),
            'horse_name': row.get('horse_name', ''),
            'ninki': int(to_float(row.get('ninki', 0))) if not np.isnan(to_float(row.get('ninki', 0))) else 0,
            'barei': int(to_float(row.get('barei', 0))),
            'distance': int(to_float(row.get('distance', 0))),
            'syusso_tosu': int(to_float(row.get('syusso_tosu', 0))),
            'venue_cd': int(to_float(row.get('venue_cd', 0))),
        })

    # ---- Apply filters ----
    recommendations = []

    no_filter = args.no_filter

    if use_netkeiba:
        # 前日予測モード: abilityスコアでランキング
        for rid in sorted(race_entries.keys()):
            entries = race_entries[rid]
            if len(entries) < 3:
                continue

            if not no_filter:
                if entries[0]['distance'] < MIN_DISTANCE:
                    continue
                if entries[0]['syusso_tosu'] < MIN_RUNNERS:
                    continue
                if entries[0]['venue_cd'] in EXCLUDED_VENUES:
                    continue

            # ability確率でソート → 上位を推奨
            sorted_entries = sorted(entries, key=lambda e: e['pred_ability'], reverse=True)
            best = sorted_entries[0]

            venue = VENUE_NAMES.get(best['venue_cd'], '?')
            rno = rid[14:16] if len(rid) >= 16 else '?'
            recommendations.append({
                'race_id': rid,
                'date': rid[:8],
                'venue': venue,
                'race_num': rno,
                'umaban': best['umaban'],
                'horse_name': best['horse_name'],
                'ninki': best['ninki'],
                'odds': best['odds'],
                'ev': 0,
                'div': best['pred_ability'],
                'distance': best['distance'],
                'age': best['barei'],
                'ability': best['pred_ability'],
                # Top3 candidates for display
                'top3': [(e['umaban'], e['horse_name'], e['pred_ability']) for e in sorted_entries[:3]],
            })
    else:
        # 当日予測モード: ULTIMATE v2フィルター
        for rid in sorted(race_entries.keys()):
            entries = race_entries[rid]
            if len(entries) < 3:
                continue
            if entries[0]['distance'] < MIN_DISTANCE:
                continue
            if entries[0]['syusso_tosu'] < MIN_RUNNERS:
                continue

            cands = [e for e in entries
                     if e['div'] >= DIV_THRESHOLD
                     and e['odds'] < MAX_ODDS
                     and e['venue_cd'] not in EXCLUDED_VENUES
                     and e['barei'] >= MIN_AGE
                     and e['ninki'] >= MIN_NINKI]
            if not cands:
                continue

            best = max(cands, key=lambda e: e['ev'])
            if best['ev'] < EV_THRESHOLD:
                continue

            venue = VENUE_NAMES.get(best['venue_cd'], '?')
            rno = rid[14:16] if len(rid) >= 16 else '?'
            recommendations.append({
                'race_id': rid,
                'date': rid[:8],
                'venue': venue,
                'race_num': rno,
                'umaban': best['umaban'],
                'horse_name': best['horse_name'],
                'ninki': best['ninki'],
                'odds': best['odds'],
                'ev': best['ev'],
                'div': best['div'],
                'distance': best['distance'],
                'age': best['barei'],
            })

    # ---- Output ----
    if use_netkeiba:
        print(f"\n{'='*80}")
        print(f"前日予測（abilityモデル） — netkeiba出馬表")
        print(f"{'='*80}")

        if not recommendations:
            print("\n該当レースなし（距離/頭数フィルター通過ゼロ）")
            print(f"\n[参考] 全{len(race_entries)}レースの分析結果:")
            for rid in sorted(race_entries.keys()):
                entries = race_entries[rid]
                venue = VENUE_NAMES.get(entries[0]['venue_cd'], '?')
                rno = rid[14:16] if len(rid) >= 16 else '?'
                dist = entries[0]['distance']
                n = entries[0]['syusso_tosu']
                best_ab = max(e['pred_ability'] for e in entries)
                reason = []
                if dist < MIN_DISTANCE: reason.append(f"距離{dist}m<{MIN_DISTANCE}")
                if n < MIN_RUNNERS: reason.append(f"頭数{n}<{MIN_RUNNERS}")
                if entries[0]['venue_cd'] in EXCLUDED_VENUES: reason.append("除外会場")
                if best_ab < 0.10: reason.append(f"Ab{best_ab:.3f}<0.10")
                skip = ', '.join(reason) if reason else 'フィルター不適合'
                print(f"  {venue} {rno}R {dist}m {n}頭 BestAb={best_ab:.3f} → {skip}")
            return

        # Sort by ability score
        recommendations.sort(key=lambda r: r.get('ability', 0), reverse=True)

        print(f"\n{'会場':>4} {'R':>3} {'距離':>6} {'推奨':>12}  {'Ab%':>6}  Top3候補")
        print("-" * 80)
        for rec in recommendations:
            name1 = rec['horse_name'][:8] if rec['horse_name'] else '?'
            top3_str = ""
            if 'top3' in rec:
                parts = []
                for ub, nm, ab in rec['top3']:
                    parts.append(f"{ub}{nm[:6]}({ab:.1%})")
                top3_str = " > ".join(parts)

            print(f"{rec['venue']:>4} R{rec['race_num']:>2} {rec['distance']:>5}m "
                  f"{rec['umaban']:>2} {name1:>8}  {rec.get('ability',0):>5.1%}  {top3_str}")

        print(f"\n対象: {len(recommendations)}レース")
        print(f"※ 前日予測のため、当日のオッズで最終判断してください")
        print(f"※ 当日はオッズ込みで --netkeiba なしで再実行を推奨")
    else:
        print(f"\n{'='*80}")
        print(f"ULTIMATE v2 推奨ベット — smartrcリアルタイム予測")
        print(f"{'='*80}")

        if not recommendations:
            print("\n該当レースなし（ULTIMATE v2フィルター通過ゼロ）")

            print(f"\n[参考] 全{len(race_entries)}レースの分析結果:")
            for rid in sorted(race_entries.keys()):
                entries = race_entries[rid]
                venue = VENUE_NAMES.get(entries[0]['venue_cd'], '?')
                rno = rid[14:16] if len(rid) >= 16 else '?'
                dist = entries[0]['distance']
                n = entries[0]['syusso_tosu']
                best_ev = max(e['ev'] for e in entries)
                reason = []
                if dist < MIN_DISTANCE: reason.append(f"距離{dist}m<{MIN_DISTANCE}")
                if n < MIN_RUNNERS: reason.append(f"頭数{n}<{MIN_RUNNERS}")
                if best_ev < EV_THRESHOLD: reason.append(f"EV{best_ev:.2f}<{EV_THRESHOLD}")
                if entries[0]['venue_cd'] in EXCLUDED_VENUES: reason.append("除外会場")
                skip = ', '.join(reason) if reason else 'フィルター条件不適合'
                print(f"  {venue} {rno}R {dist}m {n}頭 BestEV={best_ev:.2f} → {skip}")
            return

        print(f"\n{'日付':>10} {'会場':>4} {'R':>3} {'馬番':>4} {'馬名':>10} {'人気':>4} {'Odds':>6} {'EV':>5} {'Div':>5} {'距離':>6}")
        print("-" * 75)
        for rec in recommendations:
            name_display = rec['horse_name'][:8] if rec['horse_name'] else '?'
            print(f"{rec['date']:>10} {rec['venue']:>4} R{rec['race_num']:>2} "
                  f"{rec['umaban']:>4} {name_display:>10} "
                  f"{rec['ninki']:>4} {rec['odds']:>6.1f} {rec['ev']:>5.2f} {rec['div']:>5.2f} "
                  f"{rec['distance']:>5}m")

        print(f"\n推奨: 上記全レースで 単勝100円 + 複勝100円")
        print(f"ベット数: {len(recommendations)}, 総投資: {len(recommendations)*200:,}円")


if __name__ == '__main__':
    main()
