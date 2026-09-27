"""
Phase 1: JV-Link 30年分から騎手/調教師/父/母父の勝率統計テーブルを抽出
→ data/stats/ にJSON保存

出力:
  - data/stats/jockey_stats.json    {jockey_cd: {wins, runs, winrate}}
  - data/stats/trainer_stats.json   {trainer_cd: {wins, runs, winrate}}
  - data/stats/father_stats.json    {father_id: {wins, runs, winrate}}
  - data/stats/bms_stats.json       {bms_id: {wins, runs, winrate}}
  - data/stats/father_surface_stats.json  {father_id__surface: {wins, runs, winrate}}
  - data/stats/bms_surface_stats.json     {bms_id__surface: {wins, runs, winrate}}

surfaceの値: 1=芝, 2=ダート (build_features_v2.pyと同一のget_surface()ロジック)
"""
import json
import sys
import os
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
V3_DIR = os.path.join(DATA_DIR, 'jvlink_v3')
STATS_DIR = os.path.join(DATA_DIR, 'stats')

def safe_int(s, default=0):
    try: return int(s)
    except: return default

def get_surface(track_cd):
    """芝=1, ダート=2, 障害=3 (build_features_v2.pyと同一)"""
    t = safe_int(track_cd)
    if 10 <= t < 23: return 1
    elif 23 <= t < 30: return 2
    else: return 3

def main():
    os.makedirs(STATS_DIR, exist_ok=True)

    # Load races (for track_cd → surface)
    print("Loading races...", file=sys.stderr)
    races = {}
    with open(os.path.join(V3_DIR, 'races.jsonl'), encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            races[d['race_id']] = d
    print(f"  {len(races)} races", file=sys.stderr)

    # Load bloodline (for father/bms IDs)
    print("Loading bloodline...", file=sys.stderr)
    blood = {}
    with open(os.path.join(V3_DIR, 'bloodline_parsed.jsonl'), encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            blood[d['ketto_num']] = d
    print(f"  {len(blood)} bloodline records", file=sys.stderr)

    # Accumulate stats
    print("Building stats from horses...", file=sys.stderr)
    jockey = defaultdict(lambda: [0, 0])   # [wins, runs]
    trainer = defaultdict(lambda: [0, 0])
    father = defaultdict(lambda: [0, 0])
    bms = defaultdict(lambda: [0, 0])
    father_surf = defaultdict(lambda: [0, 0])  # key: (father_id, surface)
    bms_surf = defaultdict(lambda: [0, 0])

    count = 0
    with open(os.path.join(V3_DIR, 'horses.jsonl'), encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            count += 1
            if count % 500000 == 0:
                print(f"  {count}...", file=sys.stderr)

            finish = safe_int(d.get('kakutei_jyuni', '0'))
            if finish <= 0:
                continue

            rid = d.get('race_id', '')
            race = races.get(rid, {})
            surface = get_surface(race.get('track_cd', '0'))
            is_win = 1 if finish == 1 else 0

            ketto = d.get('ketto_num', '')
            bl = blood.get(ketto, {})
            father_id = bl.get('father', '')
            bms_id = bl.get('mf', '')

            jid = d.get('kisyu_cd', '')
            tid = d.get('chokyosi_cd', '')

            if jid:
                jockey[jid][0] += is_win
                jockey[jid][1] += 1
            if tid:
                trainer[tid][0] += is_win
                trainer[tid][1] += 1
            if father_id:
                father[father_id][0] += is_win
                father[father_id][1] += 1
                father_surf[(father_id, surface)][0] += is_win
                father_surf[(father_id, surface)][1] += 1
            if bms_id:
                bms[bms_id][0] += is_win
                bms[bms_id][1] += 1
                bms_surf[(bms_id, surface)][0] += is_win
                bms_surf[(bms_id, surface)][1] += 1

    print(f"  {count} entries processed", file=sys.stderr)

    # Convert to JSON-serializable format with min_n filtering
    def to_dict(stats, min_n):
        result = {}
        for key, (wins, runs) in stats.items():
            if runs >= min_n:
                result[key] = {
                    "wins": wins,
                    "runs": runs,
                    "winrate": round(wins / runs, 6)
                }
        return result

    def to_dict_tuple(stats, min_n):
        """For (id, surface) tuple keys → 'id__surface' string keys"""
        result = {}
        for (id_val, surf), (wins, runs) in stats.items():
            if runs >= min_n:
                key = f"{id_val}__{surf}"
                result[key] = {
                    "wins": wins,
                    "runs": runs,
                    "winrate": round(wins / runs, 6)
                }
        return result

    outputs = [
        ("jockey_stats.json", to_dict(jockey, 30)),
        ("trainer_stats.json", to_dict(trainer, 30)),
        ("father_stats.json", to_dict(father, 50)),
        ("bms_stats.json", to_dict(bms, 50)),
        ("father_surface_stats.json", to_dict_tuple(father_surf, 30)),
        ("bms_surface_stats.json", to_dict_tuple(bms_surf, 30)),
    ]

    for filename, data in outputs:
        path = os.path.join(STATS_DIR, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  {filename}: {len(data)} entries", file=sys.stderr)

    print("\nDone! Stats saved to data/stats/", file=sys.stderr)

if __name__ == '__main__':
    main()
