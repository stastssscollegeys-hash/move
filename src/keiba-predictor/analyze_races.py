"""
フローラS・マイラーズC 詳細予測分析スクリプト（EV閾値なし）
"""
import sys, os, json
import numpy as np
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
SCRAPER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scraper')
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, SCRAPER_DIR)

from convert_smartrc_to_features import load_stats, convert_race, FIELDNAMES
from smartrc_api import SmartRCAPI

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'models')

ABILITY_COLS = [
    'waku', 'sex_cd', 'barei', 'futan', 'ba_taijyu', 'zogen_sa', 'blinker',
    'distance', 'dist_cat', 'surface', 'grade_cd', 'tenko_cd', 'baba_cd',
    'syusso_tosu', 'prize_1', 'venue_cd', 'month', 'race_num',
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
FEATURE_COLS = ABILITY_COLS + ['odds', 'ninki']

VENUE_NAMES = {1:'札幌',2:'函館',3:'福島',4:'新潟',5:'東京',
               6:'中山',7:'中京',8:'京都',9:'阪神',10:'小倉'}


def to_float(v):
    if v is None or v == '' or v == 'None':
        return float('nan')
    try:
        return float(v)
    except:
        return float('nan')


def load_models():
    import lightgbm as lgb
    ability_models, market_models = [], []
    for i in range(3):
        ap = os.path.join(MODEL_DIR, f'lgb_v44_ability_{i}.txt')
        mp = os.path.join(MODEL_DIR, f'lgb_v44_market_{i}.txt')
        if os.path.exists(ap):
            ability_models.append(lgb.Booster(model_file=ap))
        if os.path.exists(mp):
            market_models.append(lgb.Booster(model_file=mp))
    print(f"モデル: ability×{len(ability_models)} market×{len(market_models)}", file=sys.stderr)
    return ability_models, market_models


def analyze_race(api, rcode, race_info, stats, ability_models, market_models):
    rows = convert_race(api, rcode, race_info, stats)
    if not rows:
        print(f"  データ取得失敗: {rcode}", file=sys.stderr)
        return

    X_ability = np.array(
        [[to_float(r.get(c)) for c in ABILITY_COLS] for r in rows],
        dtype=np.float32,
    )
    X_full = np.array(
        [[to_float(r.get(c)) for c in FEATURE_COLS] for r in rows],
        dtype=np.float32,
    )
    pred_ability = np.mean([m.predict(X_ability) for m in ability_models], axis=0)
    pred_market = np.mean([m.predict(X_full) for m in market_models], axis=0)

    entries = []
    for j, row in enumerate(rows):
        o = to_float(row.get('odds'))
        ev = float(pred_market[j]) * o if o > 0 and o == o else 0
        entries.append({
            'umaban': str(row.get('umaban', '')).zfill(2),
            'horse_name': row.get('horse_name', ''),
            'pred_ability': float(pred_ability[j]),
            'pred_market': float(pred_market[j]),
            'ev': ev,
            'odds': o if o == o else 0,
            'ninki': int(to_float(row.get('ninki', 0))) if not (to_float(row.get('ninki', 0)) != to_float(row.get('ninki', 0))) else 0,
        })

    # ability順でソート
    entries.sort(key=lambda e: e['pred_ability'], reverse=True)
    total_ability = sum(e['pred_ability'] for e in entries)

    return entries, total_ability


def main():
    print("モデルロード中...", file=sys.stderr)
    ability_models, market_models = load_models()
    stats = load_stats()
    print("統計データロード完了", file=sys.stderr)

    api = SmartRCAPI()

    # 分析対象レース
    target_races = [
        ('2026042605020211', {'place': '05', 'rno': '11', 'name': 'フローラステークス',
                               'range': '2000', 'trackkind': '1', 'ground': '1', 'weather': '1',
                               'track': '23', 'grade': 'B', 'venue_cd': 5}),
        ('2026042608030211', {'place': '08', 'rno': '11', 'name': '読売マイラーズカップ',
                               'range': '1600', 'trackkind': '1', 'ground': '1', 'weather': '1',
                               'track': '11', 'grade': 'B', 'venue_cd': 8}),
    ]

    results = {}
    for rcode, race_info in target_races:
        race_info['rcode'] = rcode
        venue_name = '東京' if race_info['place'] == '05' else '京都'
        print(f"\n{venue_name} 11R {race_info['name']} を分析中...", file=sys.stderr)
        result = analyze_race(api, rcode, race_info, stats, ability_models, market_models)
        if result:
            results[rcode] = (race_info, result[0], result[1])

    api.close()

    # 結果出力
    MARK_MAP = {0: '◎', 1: '○', 2: '▲', 3: '△', 4: '△'}

    for rcode, (race_info, entries, total_ability) in results.items():
        venue_name = '東京' if race_info['place'] == '05' else '京都'
        print(f"\n{'='*60}")
        print(f"【{venue_name} 11R {race_info['name']} 芝{race_info['range']}m】")
        print(f"{'='*60}")
        print(f"{'順':>3} {'馬番':>4} {'馬名':<18} {'能力%':>6} {'市場%':>6} {'EV':>6} {'人気':>4} {'オッズ':>6}")
        print('-' * 65)
        for i, e in enumerate(entries):
            mark = MARK_MAP.get(i, '  ')
            ability_pct = e['pred_ability'] / total_ability * 100
            market_pct = e['pred_market'] * 100
            print(f"{mark:>3} {e['umaban']:>4}番 {e['horse_name']:<18} {ability_pct:>5.1f}% {market_pct:>5.1f}% {e['ev']:>5.2f}x {e['ninki']:>4}人 {e['odds']:>5.1f}倍")

        print()
        # 上位5頭の詳細
        print("【推奨印】")
        for i, e in enumerate(entries[:5]):
            mark = MARK_MAP.get(i, '△')
            ability_pct = e['pred_ability'] / total_ability * 100
            print(f"  {mark} {int(e['umaban'])}番 {e['horse_name']} (能力{ability_pct:.1f}% / {e['ninki']}人気{e['odds']}倍)")

        # 買い目提案
        top = entries[:3]
        print(f"\n【買い目案】")
        print(f"  単勝: {int(top[0]['umaban'])}番")
        print(f"  ワイド: {int(top[0]['umaban'])}-{int(top[1]['umaban'])} / {int(top[0]['umaban'])}-{int(top[2]['umaban'])}")
        print(f"  馬連: {int(top[0]['umaban'])}-{int(top[1]['umaban'])} / {int(top[0]['umaban'])}-{int(top[2]['umaban'])}")


if __name__ == '__main__':
    main()
