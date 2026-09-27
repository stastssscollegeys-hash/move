"""
Phase 4-1 v2: 強化版特徴量エンジニアリング
- 距離適性（同距離の過去成績）
- コース適性（同コースの過去成績）
- 馬場適性（同馬場状態の過去成績）
- 枠番別成績
- 騎手×距離の相性
- 季節・曜日

入力（読み取り専用）:
  - data/jvlink_v3/horses.jsonl, races.jsonl, bloodline_parsed.jsonl, payoffs.jsonl
出力:
  - data/features_v2.csv
"""
import json
import csv
import sys
import os
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
V3_DIR = os.path.join(DATA_DIR, 'jvlink_v3')

def safe_int(s, default=0):
    try: return int(s)
    except: return default

def safe_float(s, default=0.0):
    try: return float(s)
    except: return default

def parse_time(t):
    v = safe_int(t, 0)
    return v / 10.0 if v > 0 else None

def get_distance_category(dist):
    """距離カテゴリ: 短距離/マイル/中距離/長距離"""
    d = safe_int(dist)
    if d <= 1400: return 1  # sprint
    elif d <= 1800: return 2  # mile
    elif d <= 2200: return 3  # middle
    else: return 4  # long

def get_surface(track_cd):
    """芝=1, ダート=2, 障害=3"""
    t = safe_int(track_cd)
    if 10 <= t < 23: return 1  # turf
    elif 23 <= t < 30: return 2  # dirt
    else: return 3  # obstacle

def main():
    # Load races
    print("Loading races...", file=sys.stderr)
    races = {}
    with open(os.path.join(V3_DIR, 'races.jsonl'), encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            races[d['race_id']] = d
    print(f"  {len(races)} races", file=sys.stderr)

    # Load bloodline
    print("Loading bloodline...", file=sys.stderr)
    blood = {}
    with open(os.path.join(V3_DIR, 'bloodline_parsed.jsonl'), encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            blood[d['ketto_num']] = d
    print(f"  {len(blood)} bloodline records", file=sys.stderr)

    # Build horse history
    print("Building horse history...", file=sys.stderr)
    history = defaultdict(list)
    count = 0
    with open(os.path.join(V3_DIR, 'horses.jsonl'), encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            history[d['ketto_num']].append(d)
            count += 1
            if count % 500000 == 0:
                print(f"  {count}...", file=sys.stderr)
    for k in history:
        history[k].sort(key=lambda x: x['race_id'])
    print(f"  {count} entries, {len(history)} horses", file=sys.stderr)

    # Build stats: jockey, trainer, father, bms
    print("Building global stats...", file=sys.stderr)
    jockey_stats = defaultdict(lambda: [0, 0])
    trainer_stats = defaultdict(lambda: [0, 0])
    father_stats = defaultdict(lambda: [0, 0])
    bms_stats = defaultdict(lambda: [0, 0])
    # Father x surface, Father x distance_cat
    father_surface_stats = defaultdict(lambda: [0, 0])
    bms_surface_stats = defaultdict(lambda: [0, 0])

    for ketto, entries in history.items():
        bl = blood.get(ketto, {})
        father_id = bl.get('father', '')
        bms_id = bl.get('mf', '')

        for e in entries:
            finish = safe_int(e.get('kakutei_jyuni', '0'))
            if finish <= 0: continue
            rid = e['race_id']
            race = races.get(rid, {})

            jid = e.get('kisyu_cd', '')
            tid = e.get('chokyosi_cd', '')
            surface = get_surface(race.get('track_cd', '0'))

            if jid:
                jockey_stats[jid][1] += 1
                if finish == 1: jockey_stats[jid][0] += 1
            if tid:
                trainer_stats[tid][1] += 1
                if finish == 1: trainer_stats[tid][0] += 1
            if father_id:
                father_stats[father_id][1] += 1
                if finish == 1: father_stats[father_id][0] += 1
                father_surface_stats[(father_id, surface)][1] += 1
                if finish == 1: father_surface_stats[(father_id, surface)][0] += 1
            if bms_id:
                bms_stats[bms_id][1] += 1
                if finish == 1: bms_stats[bms_id][0] += 1
                bms_surface_stats[(bms_id, surface)][1] += 1
                if finish == 1: bms_surface_stats[(bms_id, surface)][0] += 1

    def wr(stats, key, min_n=30):
        s = stats.get(key)
        if s and s[1] >= min_n:
            return s[0] / s[1]
        return None

    print("  Stats built", file=sys.stderr)

    # Generate features
    print("Generating features v2...", file=sys.stderr)
    output_file = os.path.join(DATA_DIR, 'features_v2.csv')

    fieldnames = [
        'race_id', 'ketto_num', 'umaban',
        # Target
        'kakutei_jyuni', 'is_top3', 'is_win',
        # Horse basic
        'waku', 'sex_cd', 'barei', 'futan', 'ba_taijyu', 'zogen_sa', 'blinker',
        # Race info
        'distance', 'dist_cat', 'surface', 'grade_cd', 'tenko_cd', 'baba_cd',
        'syusso_tosu', 'prize_1', 'venue_cd', 'month', 'race_num',
        # Odds (kept for EV calculation, NOT used in training features)
        'odds', 'ninki',
        # Past performance (general)
        'num_past_races', 'avg_finish_5', 'best_finish_5',
        'win_rate_5', 'top3_rate_5',
        'avg_time_5', 'avg_l3f_5',
        'days_since_last', 'running_style', 'avg_j4c_5',
        # Past performance (distance-specific)
        'same_dist_runs', 'same_dist_winrate', 'same_dist_top3rate',
        # Past performance (surface-specific)
        'same_surface_runs', 'same_surface_winrate', 'same_surface_top3rate',
        # Past performance (baba-specific)
        'heavy_baba_runs', 'heavy_baba_top3rate',
        # Jockey/Trainer
        'jockey_winrate', 'trainer_winrate',
        # Bloodline
        'father_winrate', 'bms_winrate',
        'father_surface_wr', 'bms_surface_wr',
    ]

    row_count = 0
    with open(output_file, 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.DictWriter(csvf, fieldnames=fieldnames)
        writer.writeheader()

        for ketto, entries in history.items():
            bl = blood.get(ketto, {})
            father_id = bl.get('father', '')
            bms_id = bl.get('mf', '')

            for idx, entry in enumerate(entries):
                rid = entry['race_id']
                race = races.get(rid, {})
                finish = safe_int(entry.get('kakutei_jyuni', '0'))
                if finish <= 0: continue

                track = safe_int(race.get('track_cd', '0'))
                surface = get_surface(track)
                dist = safe_int(race.get('distance', '0'))
                dist_cat = get_distance_category(dist)
                baba = safe_int(race.get('siba_baba_cd' if surface == 1 else 'dirt_baba_cd', '0'))

                # Past races (before current)
                past = entries[:idx]
                recent = past[-5:] if len(past) >= 5 else past

                # General past stats
                finishes_past = [safe_int(r['kakutei_jyuni']) for r in recent if safe_int(r['kakutei_jyuni']) > 0]
                avg_finish = sum(finishes_past) / len(finishes_past) if finishes_past else None
                best_finish = min(finishes_past) if finishes_past else None
                win_rate = sum(1 for f in finishes_past if f == 1) / len(finishes_past) if finishes_past else 0
                top3_rate = sum(1 for f in finishes_past if f <= 3) / len(finishes_past) if finishes_past else 0

                times = [parse_time(r['time']) for r in recent if parse_time(r['time'])]
                avg_time = sum(times) / len(times) if times else None

                l3s = [safe_float(r.get('haron_l3', '0')) / 10.0 for r in recent if safe_float(r.get('haron_l3', '0')) > 0]
                avg_l3f = sum(l3s) / len(l3s) if l3s else None

                j4s = [safe_int(r.get('jyuni_4c', '0')) for r in recent if safe_int(r.get('jyuni_4c', '0')) > 0]
                avg_j4c = sum(j4s) / len(j4s) if j4s else None

                styles = [safe_int(r.get('kyakusitu_kubun', '0')) for r in recent if safe_int(r.get('kyakusitu_kubun', '0')) > 0]
                run_style = max(set(styles), key=styles.count) if styles else None

                days_since = None
                if past:
                    try:
                        last_rid = past[-1]['race_id']
                        ld = datetime(int(last_rid[0:4]), int(last_rid[4:6]), int(last_rid[6:8]))
                        cd = datetime(int(rid[0:4]), int(rid[4:6]), int(rid[6:8]))
                        days_since = (cd - ld).days
                    except: pass

                # Distance-specific past stats
                same_dist = [r for r in past if get_distance_category(races.get(r['race_id'], {}).get('distance', '0')) == dist_cat]
                sd_finishes = [safe_int(r['kakutei_jyuni']) for r in same_dist if safe_int(r['kakutei_jyuni']) > 0]
                sd_runs = len(sd_finishes)
                sd_wr = sum(1 for f in sd_finishes if f == 1) / sd_runs if sd_runs >= 3 else None
                sd_t3 = sum(1 for f in sd_finishes if f <= 3) / sd_runs if sd_runs >= 3 else None

                # Surface-specific past stats
                same_surf = [r for r in past if get_surface(races.get(r['race_id'], {}).get('track_cd', '0')) == surface]
                ss_finishes = [safe_int(r['kakutei_jyuni']) for r in same_surf if safe_int(r['kakutei_jyuni']) > 0]
                ss_runs = len(ss_finishes)
                ss_wr = sum(1 for f in ss_finishes if f == 1) / ss_runs if ss_runs >= 3 else None
                ss_t3 = sum(1 for f in ss_finishes if f <= 3) / ss_runs if ss_runs >= 3 else None

                # Heavy baba past stats (baba >= 2 = 稍重以上)
                heavy_past = [r for r in past if safe_int(races.get(r['race_id'], {}).get(
                    'siba_baba_cd' if get_surface(races.get(r['race_id'], {}).get('track_cd', '0')) == 1 else 'dirt_baba_cd', '0')) >= 2]
                hb_finishes = [safe_int(r['kakutei_jyuni']) for r in heavy_past if safe_int(r['kakutei_jyuni']) > 0]
                hb_runs = len(hb_finishes)
                hb_t3 = sum(1 for f in hb_finishes if f <= 3) / hb_runs if hb_runs >= 2 else None

                row = {
                    'race_id': rid,
                    'ketto_num': ketto,
                    'umaban': entry.get('umaban', ''),
                    'kakutei_jyuni': finish,
                    'is_top3': 1 if finish <= 3 else 0,
                    'is_win': 1 if finish == 1 else 0,
                    'waku': safe_int(entry.get('waku', '0')),
                    'sex_cd': safe_int(entry.get('sex_cd', '0')),
                    'barei': safe_int(entry.get('barei', '0')),
                    'futan': safe_float(entry.get('futan', '0')) / 10.0,
                    'ba_taijyu': safe_int(entry.get('ba_taijyu', '0')),
                    'zogen_sa': safe_int(entry.get('zogen_sa', '0')),
                    'blinker': safe_int(entry.get('blinker', '0')),
                    'distance': dist,
                    'dist_cat': dist_cat,
                    'surface': surface,
                    'grade_cd': safe_int(race.get('grade_cd', '0')) if race.get('grade_cd', '').strip() else 0,
                    'tenko_cd': safe_int(race.get('tenko_cd', '0')),
                    'baba_cd': baba,
                    'syusso_tosu': safe_int(race.get('syusso_tosu', '0')),
                    'prize_1': safe_int(race.get('prize_1', '0')),
                    'venue_cd': safe_int(race.get('venue_code', '0')),
                    'month': safe_int(rid[4:6]),
                    'race_num': safe_int(race.get('race_num', '0')),
                    'odds': safe_float(entry.get('odds', '0')) / 10.0,
                    'ninki': safe_int(entry.get('ninki', '0')),
                    'num_past_races': len(past),
                    'avg_finish_5': avg_finish,
                    'best_finish_5': best_finish,
                    'win_rate_5': win_rate,
                    'top3_rate_5': top3_rate,
                    'avg_time_5': avg_time,
                    'avg_l3f_5': avg_l3f,
                    'days_since_last': days_since,
                    'running_style': run_style,
                    'avg_j4c_5': avg_j4c,
                    'same_dist_runs': sd_runs,
                    'same_dist_winrate': sd_wr,
                    'same_dist_top3rate': sd_t3,
                    'same_surface_runs': ss_runs,
                    'same_surface_winrate': ss_wr,
                    'same_surface_top3rate': ss_t3,
                    'heavy_baba_runs': hb_runs,
                    'heavy_baba_top3rate': hb_t3,
                    'jockey_winrate': wr(jockey_stats, entry.get('kisyu_cd', '')),
                    'trainer_winrate': wr(trainer_stats, entry.get('chokyosi_cd', '')),
                    'father_winrate': wr(father_stats, father_id, 50),
                    'bms_winrate': wr(bms_stats, bms_id, 50),
                    'father_surface_wr': wr(father_surface_stats, (father_id, surface), 30),
                    'bms_surface_wr': wr(bms_surface_stats, (bms_id, surface), 30),
                }

                writer.writerow(row)
                row_count += 1
                if row_count % 500000 == 0:
                    print(f"  {row_count} rows...", file=sys.stderr)

    print(f"\nDone! {row_count} rows -> {output_file}", file=sys.stderr)
    print(f"Size: {os.path.getsize(output_file)/1024/1024:.1f} MB", file=sys.stderr)

if __name__ == '__main__':
    main()
