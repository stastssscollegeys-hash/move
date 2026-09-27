"""
実運用予測スクリプト — 当日レースの予測出力
usage: python predict_today.py [--date YYYYMMDD]

1. features_v2.csv から指定日付のレースを抽出
2. 保存済みモデル (lgb_v17_market/ability) で予測
3. ULTIMATE v2 フィルター適用
4. 推奨ベットをテーブル出力

※ 予測対象のレースがfeatures_v2.csvに入っている必要がある
   → 新しいレースの場合は先にbuild_features_v2.pyを再実行する
"""
import sys, os, csv, json, argparse
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MODEL_DIR = os.path.join(DATA_DIR, 'models')

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
    if v is None or v == '' or v == 'None': return float('nan')
    try: return float(v)
    except: return float('nan')

def parse_payoff_field(field_str, target_uma):
    if not field_str: return 0
    for part in field_str.split('|'):
        tokens = part.split(':')
        if len(tokens) >= 2 and tokens[0] == target_uma:
            try: return int(tokens[1]) / 100.0
            except: pass
    return 0

def main():
    import lightgbm as lgb
    import numpy as np

    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, default=None,
                        help='対象日 YYYYMMDD (省略時は最新日)')
    parser.add_argument('--all-dates', action='store_true',
                        help='全日程を表示（フィルター通過分のみ）')
    parser.add_argument('--verify', action='store_true',
                        help='結果検証モード（着順付き）')
    parser.add_argument('--from-date', type=str, default=None,
                        help='検証開始日 YYYYMMDD')
    parser.add_argument('--to-date', type=str, default=None,
                        help='検証終了日 YYYYMMDD')
    args = parser.parse_args()

    # Load models (copy to temp dir to avoid Japanese path issue with LightGBM C++)
    import shutil, tempfile
    tmp_model_dir = os.path.join(tempfile.gettempdir(), 'keiba_models_predict')
    os.makedirs(tmp_model_dir, exist_ok=True)

    # v44 models (train~2024) preferred for future prediction, v17 as fallback
    model_version = 'v44'
    print("Loading models...", file=sys.stderr)
    market_models = []
    ability_models = []
    for ver in ['v44', 'v17']:
        if market_models: break
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
    print(f"  Using model: {model_version}", file=sys.stderr)

    if not market_models or not ability_models:
        print("ERROR: モデルが見つかりません", file=sys.stderr)
        return

    print(f"  Market models: {len(market_models)}, Ability models: {len(ability_models)}", file=sys.stderr)

    # Load data
    print("Loading features_v2.csv...", file=sys.stderr)
    data = []
    with open(os.path.join(DATA_DIR, 'features_v2.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            data.append(row)
    print(f"  {len(data)} rows", file=sys.stderr)

    # Load payoffs (for verification)
    payoffs = {}
    payoff_file = os.path.join(DATA_DIR, 'jvlink_v3', 'payoffs.jsonl')
    if os.path.exists(payoff_file):
        with open(payoff_file, encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                payoffs[d['race_id']] = d

    # Filter by date
    if args.date:
        target_rows = [r for r in data if r['race_id'][:8] == args.date]
    elif args.from_date or args.to_date:
        fd = args.from_date or '00000000'
        td = args.to_date or '99999999'
        target_rows = [r for r in data if fd <= r['race_id'][:8] <= td]
    elif args.all_dates:
        target_rows = [r for r in data if r['race_id'][:4] >= '2024']
    else:
        # Find latest date
        all_dates = sorted(set(r['race_id'][:8] for r in data))
        latest = all_dates[-1]
        target_rows = [r for r in data if r['race_id'][:8] == latest]
        print(f"  Latest date: {latest}", file=sys.stderr)

    if not target_rows:
        print("対象レースが見つかりません", file=sys.stderr)
        return

    print(f"  Target rows: {len(target_rows)}", file=sys.stderr)

    # Build feature arrays
    X_full = np.array([[to_float(r[c]) for c in FEATURE_COLS] for r in target_rows], dtype=np.float32)
    X_ability = np.array([[to_float(r[c]) for c in ABILITY_COLS] for r in target_rows], dtype=np.float32)

    # Predict
    pred_market = np.mean([m.predict(X_full) for m in market_models], axis=0)
    pred_ability = np.mean([m.predict(X_ability) for m in ability_models], axis=0)

    # Group by race
    race_entries = defaultdict(list)
    for j, row in enumerate(target_rows):
        o = to_float(row['odds'])
        mip = 1.0 / o if o > 0 else 0
        race_entries[row['race_id']].append({
            'row': row,
            'pred_market': float(pred_market[j]),
            'pred_ability': float(pred_ability[j]),
            'ev': float(pred_market[j]) * o,
            'div': float(pred_ability[j]) - mip,
            'odds': o,
            'umaban': row['umaban'].zfill(2),
            'ninki': int(to_float(row['ninki'])),
            'barei': int(to_float(row['barei'])),
            'distance': int(to_float(row['distance'])),
            'syusso_tosu': int(to_float(row['syusso_tosu'])),
            'venue_cd': int(to_float(row['venue_cd'])),
            'finish': int(to_float(row.get('kakutei_jyuni', '0'))),
        })

    # Apply ULTIMATE v2 filters and collect recommendations
    recommendations = []
    for rid in sorted(race_entries.keys()):
        entries = race_entries[rid]
        if len(entries) < 3: continue
        if entries[0]['distance'] < MIN_DISTANCE: continue
        if entries[0]['syusso_tosu'] < MIN_RUNNERS: continue

        # Filter candidates
        cands = [e for e in entries if e['div'] >= DIV_THRESHOLD
                  and e['odds'] < MAX_ODDS
                  and e['venue_cd'] not in EXCLUDED_VENUES
                  and e['barei'] >= MIN_AGE
                  and e['ninki'] >= MIN_NINKI]
        if not cands: continue

        best = max(cands, key=lambda e: e['ev'])
        if best['ev'] < EV_THRESHOLD: continue

        venue = VENUE_NAMES.get(best['venue_cd'], '?')
        recommendations.append({
            'race_id': rid,
            'date': rid[:8],
            'venue': venue,
            'umaban': best['umaban'],
            'ninki': best['ninki'],
            'odds': best['odds'],
            'ev': best['ev'],
            'div': best['div'],
            'distance': best['distance'],
            'age': best['barei'],
            'finish': best['finish'],
        })

    if not recommendations:
        print("\n該当レースなし（ULTIMATE v2フィルター通過ゼロ）")
        return

    # Output
    print(f"\n{'='*80}")
    print(f"ULTIMATE v2 推奨ベット — {len(recommendations)}レース")
    print(f"{'='*80}")

    if args.verify:
        # Verification mode with results
        print(f"{'日付':>10} {'会場':>4} {'R':>3} {'馬番':>4} {'人気':>4} {'Odds':>6} {'EV':>5} {'Div':>5} {'着順':>4} {'結果':>6} {'P&L':>8}")
        print("-" * 75)

        total_invest = 0; total_return = 0
        for rec in recommendations:
            rid = rec['race_id']
            race_num = rid[10:12] if len(rid) > 10 else '?'
            finish = rec['finish']

            pf = payoffs.get(rid, {})
            t_ret = rec['odds'] * 100 if finish == 1 else 0
            f_ret = parse_payoff_field(pf.get('fukusho', ''), rec['umaban']) * 100 if finish <= 3 else 0
            pnl = t_ret + f_ret - 200
            total_invest += 200
            total_return += t_ret + f_ret

            result = '○Win' if finish == 1 else ('△Top3' if finish <= 3 and finish > 0 else ('×' if finish > 0 else '?'))
            pnl_str = f"{pnl:+,.0f}円" if finish > 0 else "未確定"

            print(f"{rec['date']:>10} {rec['venue']:>4} R{race_num:>2} {rec['umaban']:>4} "
                  f"{rec['ninki']:>4} {rec['odds']:>6.1f} {rec['ev']:>5.2f} {rec['div']:>5.2f} "
                  f"{finish if finish > 0 else '-':>4} {result:>6} {pnl_str:>8}")

        if total_invest > 0:
            print("-" * 75)
            print(f"合計: 投資 {total_invest:,}円 → 回収 {total_return:,.0f}円 "
                  f"(ROI {total_return/total_invest*100:.1f}%) 損益 {total_return-total_invest:+,.0f}円")
    else:
        # Prediction mode (no results yet)
        print(f"{'日付':>10} {'会場':>4} {'R':>3} {'馬番':>4} {'人気':>4} {'Odds':>6} {'EV':>5} {'Div':>5} {'距離':>6} {'馬齢':>3}")
        print("-" * 65)
        for rec in recommendations:
            rid = rec['race_id']
            race_num = rid[10:12] if len(rid) > 10 else '?'
            print(f"{rec['date']:>10} {rec['venue']:>4} R{race_num:>2} {rec['umaban']:>4} "
                  f"{rec['ninki']:>4} {rec['odds']:>6.1f} {rec['ev']:>5.2f} {rec['div']:>5.2f} "
                  f"{rec['distance']:>5}m {rec['age']:>2}歳")

        print(f"\n推奨: 上記全レースで 単勝100円 + 複勝100円")
        print(f"ベット数: {len(recommendations)}, 総投資: {len(recommendations)*200:,}円")

if __name__ == '__main__':
    main()
