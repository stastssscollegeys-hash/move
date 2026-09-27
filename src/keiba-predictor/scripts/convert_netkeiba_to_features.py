"""
netkeibaの出馬表データ → LightGBM 44特徴量に変換

前日予測用: netkeiba出馬表 + 馬の過去走ページ → 44特徴量
smartrcが当日しかデータを返さない問題を解決。

使い方:
  python convert_netkeiba_to_features.py --date 20260412
  python convert_netkeiba_to_features.py --race-id 202609020611

入力:
  - netkeiba出馬表 (shutuba.html)
  - netkeiba馬ページ (過去走)
  - data/stats/*.json（extract_stats.pyで事前生成）
  - data/jvlink_v3/bloodline_parsed.jsonl（父/母父ID解決）

出力:
  - CSV（predict_smartrc.pyのload部分と互換）
"""
import json
import sys
import os
import re
import csv
import argparse
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(SRC_DIR, 'data')
STATS_DIR = os.path.join(DATA_DIR, 'stats')

sys.path.insert(0, os.path.join(SRC_DIR, 'scraper'))
from netkeiba import NetkeibaScaper
from smartrc_api import SmartRCAPI


# ============================================================
# 統計テーブル・血統データ
# ============================================================

def load_stats():
    """統計テーブルを読み込む"""
    stats = {}
    files = [
        'jockey_stats.json', 'trainer_stats.json',
        'father_stats.json', 'bms_stats.json',
        'father_surface_stats.json', 'bms_surface_stats.json',
    ]
    for fname in files:
        path = os.path.join(STATS_DIR, fname)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                stats[fname.replace('.json', '')] = json.load(f)
        else:
            stats[fname.replace('.json', '')] = {}
    return stats


def load_bloodline():
    """JV-Link bloodlineを読み込む（horse_id→father/bms ID）"""
    blood_path = os.path.join(DATA_DIR, 'jvlink_v3', 'bloodline_parsed.jsonl')
    blood = {}
    if os.path.exists(blood_path):
        with open(blood_path, encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                blood[d['ketto_num']] = d
    return blood


def load_name_to_id_maps():
    """父名・母父名 → JV-Link IDマップを読み込む（2023年以降生まれ馬向けフォールバック用）"""
    father_map_path = os.path.join(STATS_DIR, 'name_to_father_id.json')
    bms_map_path = os.path.join(STATS_DIR, 'name_to_bms_id.json')
    father_map = {}
    bms_map = {}
    if os.path.exists(father_map_path):
        with open(father_map_path, encoding='utf-8') as f:
            father_map = json.load(f)
    if os.path.exists(bms_map_path):
        with open(bms_map_path, encoding='utf-8') as f:
            bms_map = json.load(f)
    return father_map, bms_map


def get_winrate(stats_dict: dict, key: str) -> Optional[float]:
    entry = stats_dict.get(key)
    return entry['winrate'] if entry else None


# ============================================================
# 特徴量計算
# ============================================================

def get_dist_cat(dist: int) -> int:
    if dist <= 1400: return 1
    elif dist <= 1800: return 2
    elif dist <= 2200: return 3
    else: return 4


def grade_to_cd(grade: str) -> int:
    # build_features_v2.pyでは常に0（safe_int('A')=0）
    return 0


def weather_to_tenko(weather: str) -> int:
    wmap = {"晴": 1, "曇": 2, "雨": 3, "小雨": 4, "雪": 5, "小雪": 6}
    return wmap.get(weather, 0)


def condition_to_baba(condition: str) -> int:
    cmap = {"良": 1, "稍重": 2, "重": 3, "不良": 4}
    return cmap.get(condition, 0)


def surface_to_code(surface: str) -> int:
    return 2 if "ダ" in surface else 1


def _days_since_last(past_results: List[Dict], race_date: str = None):
    """前走からの中日数を算出する（2026-09-04 実装）。

    従来ここは `'days_since_last': None` のハードコードで「後で対応」のまま放置されており、
    監査の結果 records 7,235頭すべてで0＝**因子が完全に死んでいた**。
    過去走キャッシュに日付が無かったのが原因だが、netkeibaの戦績ページは日付を返すため
    scraper 側に 'date' を追加して取得できるようにした。

    race_date: 'YYYYMMDD'。省略時は今日を基準にする。
    """
    import datetime as _dt
    d0 = None
    for pr in past_results:
        s = (pr.get('date') or '').strip()
        if not s:
            continue
        for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%Y%m%d'):
            try:
                d0 = _dt.datetime.strptime(s, fmt).date()
                break
            except ValueError:
                continue
        if d0:
            break
    if not d0:
        return None
    if race_date:
        try:
            base = _dt.datetime.strptime(str(race_date)[:8], '%Y%m%d').date()
        except ValueError:
            base = _dt.date.today()
    else:
        base = _dt.date.today()
    n = (base - d0).days
    return n if 0 < n < 3000 else None


def compute_past_features(past_results: List[Dict], race_surface: int, race_distance: int,
                          race_date: str = None) -> dict:
    """netkeiba馬ページの過去走から特徴量計算"""
    ranks = []
    times = []
    l3fs = []
    j4cs = []
    same_dist_finishes = []
    same_surface_finishes = []
    heavy_baba_finishes = []
    dist_cat = get_dist_cat(race_distance)

    for pr in past_results[:5]:
        rank = pr.get('rank')
        if not rank or rank <= 0:
            continue
        ranks.append(rank)

        if pr.get('stime') and pr['stime'] > 0:
            times.append(pr['stime'])
        if pr.get('last_3f') and pr['last_3f'] > 0:
            l3fs.append(pr['last_3f'])
        if pr.get('corner4') and pr['corner4'] > 0:
            j4cs.append(pr['corner4'])

        # 同距離
        h_dist = pr.get('distance', 0)
        if h_dist and get_dist_cat(h_dist) == dist_cat:
            same_dist_finishes.append(rank)
        # 同馬場
        h_tk = pr.get('trackkind', 0)
        if h_tk == race_surface:
            same_surface_finishes.append(rank)
        # 重馬場
        if pr.get('fr_baba', 'A') in ('B', 'C', 'D'):
            heavy_baba_finishes.append(rank)

    num_past = len(ranks)
    avg_finish = sum(ranks) / len(ranks) if ranks else None
    best_finish = min(ranks) if ranks else None
    win_rate = sum(1 for r in ranks if r == 1) / len(ranks) if ranks else 0
    top3_rate = sum(1 for r in ranks if r <= 3) / len(ranks) if ranks else 0
    avg_time = sum(times) / len(times) if times else None
    avg_l3f = sum(l3fs) / len(l3fs) if l3fs else None
    avg_j4c = sum(j4cs) / len(j4cs) if j4cs else None

    if j4cs:
        avg_corner = sum(j4cs) / len(j4cs)
        running_style = 1 if avg_corner <= 3 else (2 if avg_corner <= 6 else 3)
    else:
        running_style = None

    sd_runs = len(same_dist_finishes)
    sd_wr = sum(1 for f in same_dist_finishes if f == 1) / sd_runs if sd_runs >= 3 else None
    sd_t3 = sum(1 for f in same_dist_finishes if f <= 3) / sd_runs if sd_runs >= 3 else None
    ss_runs = len(same_surface_finishes)
    ss_wr = sum(1 for f in same_surface_finishes if f == 1) / ss_runs if ss_runs >= 3 else None
    ss_t3 = sum(1 for f in same_surface_finishes if f <= 3) / ss_runs if ss_runs >= 3 else None
    hb_runs = len(heavy_baba_finishes)
    hb_t3 = sum(1 for f in heavy_baba_finishes if f <= 3) / hb_runs if hb_runs >= 2 else None

    return {
        'num_past_races': num_past,
        'avg_finish_5': avg_finish,
        'best_finish_5': best_finish,
        'win_rate_5': win_rate,
        'top3_rate_5': top3_rate,
        'avg_time_5': avg_time,
        'avg_l3f_5': avg_l3f,
        'days_since_last': _days_since_last(past_results, race_date),  # 2026-09-04 実装
        'running_style': running_style,
        'avg_j4c_5': avg_j4c,
        'same_dist_runs': sd_runs,
        'same_dist_winrate': sd_wr,
        'same_dist_top3rate': sd_t3,
        'same_surface_runs': ss_runs,
        'same_surface_winrate': ss_wr,
        'same_surface_top3rate': ss_t3,
        'heavy_baba_runs': hb_runs,
        'heavy_baba_top3rate': hb_t3,
    }


# ============================================================
# メイン変換
# ============================================================

def convert_shutuba_horse(horse: dict, race_info: dict,
                          past_results: List[Dict],
                          stats: dict, bloodline: dict,
                          name_father_map: dict = None,
                          name_bms_map: dict = None,
                          nk_scraper=None) -> dict:
    """netkeiba出馬表の1頭→44特徴量

    Parameters
    ----------
    name_father_map: 父名→JV-Link IDマップ（2023年以降生まれ向けフォールバック）
    name_bms_map:    母父名→JV-Link IDマップ（同上）
    nk_scraper:      NetkeibaScaper インスタンス（プロフィール取得用）
    """
    distance = race_info.get('distance', 0)
    surface = surface_to_code(race_info.get('surface', '芝'))
    venue_cd = race_info.get('venue_cd', 0)
    race_id = race_info.get('race_id', '')
    month = int(race_id[0:4]) if len(race_id) >= 4 else 0  # Will fix below
    race_num = int(race_id[10:12]) if len(race_id) >= 12 else 0

    # month from rcode context (race_id doesn't directly encode month)
    # We'll pass it separately
    month = race_info.get('month', 0)

    # 過去走ベース特徴量
    past = compute_past_features(past_results, surface, distance,
                                 race_date=race_info.get('date'))

    # 血統→統計テーブル
    horse_id = horse.get('horse_id', '')
    bl = bloodline.get(horse_id, {})
    father_id = bl.get('father', '')
    bms_id = bl.get('mf', '')

    # 2026-09-07追加: 父名・母父名そのものを保持する。
    #   従来は名前→IDに変換した直後に名前を捨てていたため、蓄積DBに種牡馬名が
    #   1件も残っておらず、**自前データでの血統分析が原理的に不可能**だった。
    #   （navi-keiba のような「種牡馬別×距離別×コース別」を自前で作れなかった原因）
    #   IDは統計テーブルの引き当て用、名前は蓄積・分析用として両方残す。
    father_name = bl.get('father_name', '')
    bms_name_v = bl.get('mf_name', '')

    # bloodlineに存在しない場合（2023年以降生まれ等）: neteika profileから名前取得→名前マップで解決
    if (not father_id or not bms_id or not father_name or not bms_name_v) \
            and horse_id and nk_scraper is not None:
        profile = nk_scraper.fetch_horse_profile(horse_id)
        if profile:
            fname = profile.get('father_name', '')
            bms_name = profile.get('bms_name', '')
            if fname:
                father_name = father_name or fname
                if not father_id and name_father_map:
                    father_id = name_father_map.get(fname, '')
            if bms_name:
                bms_name_v = bms_name_v or bms_name
                if not bms_id and name_bms_map:
                    bms_id = name_bms_map.get(bms_name, '')

    jockey_wr = get_winrate(stats.get('jockey_stats', {}), horse['jockey_id'])
    trainer_wr = get_winrate(stats.get('trainer_stats', {}), horse['trainer_id'])
    father_wr = get_winrate(stats.get('father_stats', {}), father_id)
    bms_wr = get_winrate(stats.get('bms_stats', {}), bms_id)
    father_surf_wr = get_winrate(
        stats.get('father_surface_stats', {}), f"{father_id}__{surface}")
    bms_surf_wr = get_winrate(
        stats.get('bms_surface_stats', {}), f"{bms_id}__{surface}")

    return {
        'race_id': race_id,
        'ketto_num': horse_id,
        'umaban': horse.get('umaban', 0),
        'horse_name': horse.get('horse_name', ''),
        'kakutei_jyuni': '',
        'is_top3': '',
        'is_win': '',
        'waku': horse.get('waku', 0),
        'sex_cd': horse.get('sex_cd', 0),
        'barei': horse.get('age', 0),
        'futan': horse.get('futan'),
        'ba_taijyu': horse.get('horse_weight', 0) or None,
        'zogen_sa': horse.get('weight_diff', 0) or 0,
        'blinker': 0,  # netkeiba出馬表にはブリンカー情報なし
        'distance': distance,
        'dist_cat': get_dist_cat(distance),
        'surface': surface,
        'grade_cd': grade_to_cd(race_info.get('grade', '')),
        'tenko_cd': weather_to_tenko(race_info.get('weather', '')),
        'baba_cd': condition_to_baba(race_info.get('condition', '')),
        'syusso_tosu': race_info.get('horse_count', 0),
        'prize_1': race_info.get('prize_1', 0),
        'venue_cd': venue_cd,
        'month': month,
        'race_num': race_num,
        'odds': None,   # 前日時点では未確定
        'ninki': None,   # 前日時点では未確定
        **past,
        'jockey_winrate': jockey_wr,
        'trainer_winrate': trainer_wr,
        'father_winrate': father_wr,
        'bms_winrate': bms_wr,
        'father_surface_wr': father_surf_wr,
        'bms_surface_wr': bms_surf_wr,
        # 種牡馬名そのもの（2026-09-07追加・分析用）。
        # これが無いと「どの種牡馬が効いたか」を後から一切検証できない。
        'father_name': father_name,
        'bms_name': bms_name_v,
    }


FIELDNAMES = [
    'race_id', 'ketto_num', 'umaban', 'horse_name',
    'kakutei_jyuni', 'is_top3', 'is_win',
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
    'father_name', 'bms_name',        # 2026-09-07追加（自前の種牡馬別分析用）
]


# ============================================================
# smartrc rcode → netkeiba race_id 変換
# ============================================================

def rcode_to_netkeiba_id(rcode: str) -> str:
    """smartrc rcode (16桁) → netkeiba race_id (12桁)"""
    year = rcode[0:4]
    place = rcode[8:10]
    kai = rcode[10:12]
    nichi = rcode[12:14]
    race = rcode[14:16]
    return f'{year}{place}{kai}{nichi}{race}'


def rcode_to_month(rcode: str) -> int:
    """rcodeから月を取得"""
    return int(rcode[4:6]) if len(rcode) >= 6 else 0


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='netkeiba出馬表 → LightGBM 44特徴量CSV変換（前日予測用）')
    parser.add_argument('--date', type=str,
                        help='対象日 YYYYMMDD')
    parser.add_argument('--race-id', type=str,
                        help='netkeiba race_id (12桁)')
    parser.add_argument('--output', '-o', type=str,
                        help='出力CSVファイルパス')
    args = parser.parse_args()

    # Load stats & bloodline
    print("[1/4] Loading stats...", file=sys.stderr)
    stats = load_stats()
    for name, data in stats.items():
        print(f"  {name}: {len(data)} entries", file=sys.stderr)

    print("[2/4] Loading bloodline...", file=sys.stderr)
    bloodline = load_bloodline()
    print(f"  {len(bloodline)} horses", file=sys.stderr)
    name_father_map, name_bms_map = load_name_to_id_maps()
    print(f"  name_to_father_id: {len(name_father_map)} entries", file=sys.stderr)
    print(f"  name_to_bms_id:    {len(name_bms_map)} entries", file=sys.stderr)

    # Get race list from smartrc (for rcode → netkeiba_id mapping)
    print("[3/4] Getting race list...", file=sys.stderr)
    smartrc = SmartRCAPI()
    nk = NetkeibaScaper()

    all_rows = []

    try:
        if args.race_id:
            # 単一レース
            race_ids = [args.race_id]
            months = [int(args.date[4:6]) if args.date else 0]
        elif args.date:
            # smartrcからレース一覧を取得 → netkeiba IDに変換
            races = smartrc.fetch_races(args.date)
            if not races:
                print(f"[ERROR] {args.date} のレースが見つかりません", file=sys.stderr)
                return
            race_ids = [rcode_to_netkeiba_id(r['rcode']) for r in races]
            months = [rcode_to_month(r['rcode']) for r in races]
            print(f"  {len(race_ids)} races found", file=sys.stderr)
        else:
            parser.print_help()
            return

        # Fetch shutuba & past results for each race
        print("[4/4] Fetching shutuba & past results...", file=sys.stderr)
        for idx, nk_id in enumerate(race_ids):
            month = months[idx] if idx < len(months) else 0
            shutuba = nk.fetch_shutuba(nk_id)
            if not shutuba:
                print(f"  {nk_id}: データなし", file=sys.stderr)
                continue

            race_info = shutuba['race_info']
            race_info['month'] = month
            horses = shutuba['horses']
            title = race_info.get('title', '')
            print(f"  {nk_id} {title}: {len(horses)}頭", file=sys.stderr, end="")

            # 各馬の過去走を取得
            for h in horses:
                hid = h.get('horse_id', '')
                if hid:
                    past = nk.fetch_horse_past(hid, max_races=5)
                else:
                    past = []

                row = convert_shutuba_horse(
                    h, race_info, past, stats, bloodline,
                    name_father_map=name_father_map,
                    name_bms_map=name_bms_map,
                    nk_scraper=nk,
                )
                all_rows.append(row)

            print(f" -> {len(horses)} converted", file=sys.stderr)

        # Output
        if not all_rows:
            print("データが取得できませんでした", file=sys.stderr)
            return

        if args.output:
            f = open(args.output, 'w', newline='', encoding='utf-8')
        else:
            f = sys.stdout

        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

        if args.output:
            f.close()
            print(f"\n[OK] {len(all_rows)} rows -> {args.output}", file=sys.stderr)
        else:
            print(f"\n[OK] {len(all_rows)} rows", file=sys.stderr)

    finally:
        smartrc.close()
        nk.close()


if __name__ == '__main__':
    main()
