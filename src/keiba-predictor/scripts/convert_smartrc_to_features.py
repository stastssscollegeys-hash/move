"""
Phase 2: smartrcデータ → LightGBM 44特徴量に変換

smartrc APIから取得した出走馬データを、build_features_v2.pyと同じ44特徴量フォーマットに変換する。
これにより既存のLightGBMモデル（v44/v17）でそのまま予測可能。

使い方:
  python convert_smartrc_to_features.py <race_id>
  python convert_smartrc_to_features.py --date 20260412 --venue hanshin
  python convert_smartrc_to_features.py --date 20260412 --all

入力:
  - smartrc API（smartrc_api.py経由）
  - data/stats/*.json（extract_stats.pyで事前生成）

出力:
  - 標準出力にCSV（predict_today.pyにパイプ可能）
  - または --output で指定ファイルに保存
"""
import json
import sys
import os
import re
import csv
import argparse
from typing import Dict, List, Optional, Any

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(SRC_DIR, 'data')
STATS_DIR = os.path.join(DATA_DIR, 'stats')

sys.path.insert(0, os.path.join(SRC_DIR, 'scraper'))
from smartrc_api import SmartRCAPI

# ============================================================
# 統計テーブル読み込み
# ============================================================

def load_stats():
    """data/stats/ から全統計テーブル + smartrc IDマッピングを読み込む"""
    stats = {}
    files = [
        'jockey_stats.json',
        'trainer_stats.json',
        'father_stats.json',
        'bms_stats.json',
        'father_surface_stats.json',
        'bms_surface_stats.json',
        'smartrc_fcode_map.json',
        'smartrc_mfcode_map.json',
    ]
    for fname in files:
        path = os.path.join(STATS_DIR, fname)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                stats[fname.replace('.json', '')] = json.load(f)
        else:
            print(f"[WARN] {fname} not found.", file=sys.stderr)
            stats[fname.replace('.json', '')] = {}
    return stats


def get_winrate(stats_dict: dict, key: str) -> Optional[float]:
    """統計テーブルから勝率を取得。キーが存在しなければNone"""
    entry = stats_dict.get(key)
    if entry:
        return entry['winrate']
    return None


# ============================================================
# smartrc → JV-Link grade_cd マッピング
# ============================================================

def smartrc_grade_to_cd(grade: str, class_val: str) -> int:
    """
    smartrcのgrade/classフィールドからJV-Link形式のgrade_cdに変換。
    JV-Link grade_cd: A=G1, B=G2, C=G3, D=Listed, E=OP, ''=条件戦
    build_features_v2.pyではsafe_int()で数値化 → A→0, B→0, ...（文字なので0になる）

    実際のbuild_features_v2.py: grade_cd='A' → safe_int('A') → 0
    つまりJV-Linkのgrade_cdは文字列だが、safe_intで0になっている。

    しかし空文字も0になるので、実質grade_cdは常に0。
    → grade_cdは特徴量としてほぼ効いていない可能性が高い。

    念のためsmartrcのclass値で近似:
    """
    # build_features_v2.pyのロジックを忠実に再現
    # grade_cd: safe_int(race.get('grade_cd', '0')) if race.get('grade_cd', '').strip() else 0
    # JV-Linkのgrade_cdは 'A','B','C','D','E','' のいずれか
    # safe_int('A') → 0, safe_int('') → 0, safe_int('E') → 0
    # → 全部0。つまりこの特徴量は実質無効。
    return 0


def smartrc_weather_to_tenko(weather: str) -> int:
    """
    smartrcのweatherフィールド → JV-Link tenko_cd
    smartrc: '1'=晴, '2'=曇, '3'=雨, '4'=小雨, '5'=雪, '6'=小雪
    JV-Link: '1'=晴, '2'=曇, '3'=雨, '4'=小雨, '5'=雪, '6'=小雪
    → 同じ値体系
    """
    try:
        return int(weather)
    except (ValueError, TypeError):
        return 0


def smartrc_ground_to_baba(ground: str) -> int:
    """
    smartrcのground → JV-Link baba_cd
    smartrc: '0'=良, '1'=稍重, '2'=重, '3'=不良
    JV-Link: 1=良, 2=稍重, 3=重, 4=不良
    → +1のオフセット
    """
    try:
        return int(ground) + 1
    except (ValueError, TypeError):
        return 0


def smartrc_surface_to_jvlink(trackkind: str) -> int:
    """
    smartrc trackkind → JV-Link surface
    smartrc: '1'=芝, '2'=ダート
    JV-Link (build_features_v2.py get_surface): 1=芝, 2=ダート
    → 同じ
    """
    try:
        return int(trackkind)
    except (ValueError, TypeError):
        return 1


# ============================================================
# 過去走データからの特徴量計算
# ============================================================

def safe_int_val(v, default=None):
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    try:
        return int(re.sub(r'[^\d\-]', '', s))
    except (ValueError, TypeError):
        return default


def safe_float_val(v, default=None):
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    try:
        return float(re.sub(r'[^\d.\-]', '', s))
    except (ValueError, TypeError):
        return default


def compute_past_features(runner: dict, race_surface: int, race_distance: int) -> dict:
    """
    smartrcの h1_〜h5_ フィールドから過去走ベースの特徴量を計算。
    build_features_v2.pyの計算ロジックと同等。
    """
    ranks = []
    times = []
    l3fs = []
    j4cs = []
    intervals = []

    # 適性データ用
    same_dist_finishes = []
    same_surface_finishes = []
    heavy_baba_finishes = []

    dist_cat = get_dist_cat(race_distance)

    for i in range(1, 6):
        p = f"h{i}_"
        rank = safe_int_val(runner.get(f"{p}rank"))
        if rank is None or rank <= 0:
            continue

        ranks.append(rank)

        # time: stime=1151 → 115.1秒
        stime = safe_int_val(runner.get(f"{p}stime"))
        if stime and stime > 0:
            times.append(stime / 10.0)

        # last 3f: furlong3=381 → 38.1秒
        f3 = safe_int_val(runner.get(f"{p}furlong3"))
        if f3 and f3 > 0:
            l3fs.append(f3 / 10.0)

        # corner4
        c4 = safe_int_val(runner.get(f"{p}corner4"))
        if c4 and c4 > 0:
            j4cs.append(c4)

        # 同距離判定
        h_range = safe_int_val(runner.get(f"{p}range"))
        if h_range:
            h_dist_cat = get_dist_cat(h_range)
            if h_dist_cat == dist_cat:
                same_dist_finishes.append(rank)

        # 同馬場判定
        h_trackkind = safe_int_val(runner.get(f"{p}trackkind"))
        if h_trackkind is not None:
            if h_trackkind == race_surface:
                same_surface_finishes.append(rank)

        # 重馬場判定 (fr_baba: A=良, B=稍重, C=重, D=不良)
        fr_baba = (runner.get(f"{p}fr_baba") or "").strip()
        if fr_baba in ('B', 'C', 'D'):
            heavy_baba_finishes.append(rank)

    num_past = len(ranks)

    # 一般的な過去走統計
    avg_finish = sum(ranks) / len(ranks) if ranks else None
    best_finish = min(ranks) if ranks else None
    win_rate = sum(1 for r in ranks if r == 1) / len(ranks) if ranks else 0
    top3_rate = sum(1 for r in ranks if r <= 3) / len(ranks) if ranks else 0
    avg_time = sum(times) / len(times) if times else None
    avg_l3f = sum(l3fs) / len(l3fs) if l3fs else None
    avg_j4c = sum(j4cs) / len(j4cs) if j4cs else None

    # 脚質判定 (4角通過順位の平均から)
    if j4cs:
        avg_corner = sum(j4cs) / len(j4cs)
        if avg_corner <= 3:
            running_style = 1  # 逃げ/先行
        elif avg_corner <= 6:
            running_style = 2  # 差し
        else:
            running_style = 3  # 追込
    else:
        running_style = None

    # interval → days_since_last
    # smartrcのintervalフィールドは「週数」(confirmed: h1_interval=3 means 3 weeks)
    interval_val = safe_int_val(runner.get('interval'))
    days_since_last = interval_val * 7 if interval_val else None

    # 適性データ（build_features_v2.pyではmin_n=3で勝率計算）
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
        'days_since_last': days_since_last,
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


def get_dist_cat(dist: int) -> int:
    """距離カテゴリ (build_features_v2.pyと同一)"""
    if dist <= 1400: return 1
    elif dist <= 1800: return 2
    elif dist <= 2200: return 3
    else: return 4


# ============================================================
# メイン変換ロジック
# ============================================================

def convert_runner(runner_raw: dict, race_raw: dict, stats: dict) -> dict:
    """
    smartrc APIの1頭分のデータ → features_v2.csvと同じ44特徴量の辞書に変換。

    runner_raw: smartrc runners/view APIのレスポンス（生データ）
    race_raw: smartrc races/view APIのレスポンス（生データ）
    stats: load_stats()で読み込んだ統計テーブル
    """
    rcode = race_raw.get('rcode', '')

    # レース情報
    distance = safe_int_val(race_raw.get('range'), 0)
    surface = smartrc_surface_to_jvlink(race_raw.get('trackkind', '1'))
    venue_cd = safe_int_val(rcode[8:10]) if len(rcode) >= 10 else 0
    month = safe_int_val(rcode[4:6]) if len(rcode) >= 6 else 0
    race_num = safe_int_val(rcode[14:16]) if len(rcode) >= 16 else 0

    # 馬情報
    odds_raw = safe_int_val(runner_raw.get('odds_tan'))
    odds = odds_raw / 10.0 if odds_raw else None
    futan_raw = safe_int_val(runner_raw.get('futan'))
    futan = futan_raw / 10.0 if futan_raw else None

    # vary: "+02" → 2, "-04" → -4
    vary_str = str(runner_raw.get('vary', '0')).strip()
    try:
        zogen_sa = int(vary_str.replace('+', ''))
    except (ValueError, TypeError):
        zogen_sa = 0

    # 過去走ベースの特徴量
    past = compute_past_features(runner_raw, surface, distance)

    # 統計テーブルから勝率取得
    jcode = str(runner_raw.get('jcode', '')).strip()
    tcode = str(runner_raw.get('tcode', '')).strip()
    f_code_smartrc = str(runner_raw.get('f_code', '')).strip()
    mf_code_smartrc = str(runner_raw.get('mf_code', '')).strip()

    # smartrc f_code → JV-Link father ID にマッピング
    fcode_map = stats.get('smartrc_fcode_map', {})
    mfcode_map = stats.get('smartrc_mfcode_map', {})
    father_id = fcode_map.get(f_code_smartrc, '')
    bms_id = mfcode_map.get(mf_code_smartrc, '')

    jockey_wr = get_winrate(stats.get('jockey_stats', {}), jcode)
    trainer_wr = get_winrate(stats.get('trainer_stats', {}), tcode)
    father_wr = get_winrate(stats.get('father_stats', {}), father_id)
    bms_wr = get_winrate(stats.get('bms_stats', {}), bms_id)
    father_surf_wr = get_winrate(
        stats.get('father_surface_stats', {}), f"{father_id}__{surface}")
    bms_surf_wr = get_winrate(
        stats.get('bms_surface_stats', {}), f"{bms_id}__{surface}")

    # grade_cd: build_features_v2.pyでは実質常に0
    grade_cd = smartrc_grade_to_cd(
        race_raw.get('grade', ''), race_raw.get('class', ''))

    # weather → tenko_cd
    tenko_cd = smartrc_weather_to_tenko(race_raw.get('weather', ''))

    # ground → baba_cd
    baba_cd = smartrc_ground_to_baba(race_raw.get('ground', ''))

    # prize_1: smartrcにはないので0（grade_cd同様、モデルへの影響は限定的）
    prize_1 = 0

    row = {
        'race_id': rcode,
        'ketto_num': runner_raw.get('hcode', ''),
        'umaban': safe_int_val(runner_raw.get('uno'), 0),
        'horse_name': (runner_raw.get('hname') or '').strip(),
        # target columns (unknown at prediction time)
        'kakutei_jyuni': '',
        'is_top3': '',
        'is_win': '',
        # === 44 features ===
        'waku': safe_int_val(runner_raw.get('wno'), 0),
        'sex_cd': safe_int_val(runner_raw.get('sex'), 0),
        'barei': safe_int_val(runner_raw.get('age'), 0),
        'futan': futan,
        'ba_taijyu': safe_int_val(runner_raw.get('weight'), 0),
        'zogen_sa': zogen_sa,
        'blinker': safe_int_val(runner_raw.get('blinker'), 0),
        'distance': distance,
        'dist_cat': get_dist_cat(distance),
        'surface': surface,
        'grade_cd': grade_cd,
        'tenko_cd': tenko_cd,
        'baba_cd': baba_cd,
        'syusso_tosu': safe_int_val(runner_raw.get('entry'), 0),
        'prize_1': prize_1,
        'venue_cd': venue_cd,
        'month': month,
        'race_num': race_num,
        'odds': odds,
        'ninki': safe_int_val(runner_raw.get('pop_tan'), 0),
        # 過去走ベース
        **past,
        # 統計テーブルベース
        'jockey_winrate': jockey_wr,
        'trainer_winrate': trainer_wr,
        'father_winrate': father_wr,
        'bms_winrate': bms_wr,
        'father_surface_wr': father_surf_wr,
        'bms_surface_wr': bms_surf_wr,
    }

    return row


def convert_race(api: SmartRCAPI, rcode: str, race_raw: dict, stats: dict) -> List[dict]:
    """1レース分の全出走馬を変換"""
    runners_raw = api.fetch_runners(rcode)
    if not runners_raw:
        return []

    rows = []
    for runner in runners_raw:
        row = convert_runner(runner, race_raw, stats)
        rows.append(row)
    return rows


# ============================================================
# CSV出力
# ============================================================

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
]


def write_csv(rows: List[dict], output=None):
    """CSV出力（ファイルまたはstdout）"""
    if output:
        f = open(output, 'w', newline='', encoding='utf-8')
    else:
        f = sys.stdout

    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    if output:
        f.close()
        print(f"[OK] {len(rows)} rows -> {output}", file=sys.stderr)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='smartrcデータ → LightGBM 44特徴量CSV変換')
    parser.add_argument('race_id', nargs='?',
                        help='レースID (例: 20260412hanshin11 or rcode直指定)')
    parser.add_argument('--date', type=str,
                        help='対象日 YYYYMMDD')
    parser.add_argument('--venue', type=str,
                        help='会場名 (hanshin, tokyo, etc)')
    parser.add_argument('--all', action='store_true',
                        help='指定日の全レースを変換')
    parser.add_argument('--output', '-o', type=str,
                        help='出力CSVファイルパス（省略時はstdout）')
    args = parser.parse_args()

    # 統計テーブル読み込み
    print("[1/3] Loading stats...", file=sys.stderr)
    stats = load_stats()
    for name, data in stats.items():
        print(f"  {name}: {len(data)} entries", file=sys.stderr)

    # smartrc API初期化
    print("[2/3] Connecting to smartrc...", file=sys.stderr)
    api = SmartRCAPI()

    all_rows = []

    try:
        if args.race_id:
            # 単一レース指定
            card = api.fetch_race_card(args.race_id)
            if not card:
                print("[ERROR] レースが見つかりません", file=sys.stderr)
                return
            # raw dataが必要なのでrcodeから直接取得
            date, venue_code, race_num = api._parse_input(args.race_id)
            races = api.fetch_races(date)
            for r in races:
                if r.get('place') == venue_code and str(int(r.get('rno', '0'))) == str(race_num):
                    rows = convert_race(api, r['rcode'], r, stats)
                    all_rows.extend(rows)
                    rname = r.get('name', '')
                    print(f"  {r.get('rno')}R {rname}: {len(rows)}頭", file=sys.stderr)
                    break

        elif args.date:
            # 日付指定
            races = api.fetch_races(args.date)
            if not races:
                print(f"[ERROR] {args.date} のレースが見つかりません", file=sys.stderr)
                return

            # venue フィルター
            if args.venue:
                from smartrc_api import _VENUE_EN
                venue_code = _VENUE_EN.get(args.venue, args.venue)
                races = [r for r in races if r.get('place') == venue_code]

            if not args.all and not args.venue:
                print("[ERROR] --date には --venue または --all を指定してください", file=sys.stderr)
                return

            for r in races:
                rcode = r['rcode']
                rno = r.get('rno', '?')
                rname = r.get('name', '')
                rows = convert_race(api, rcode, r, stats)
                all_rows.extend(rows)
                print(f"  {rno}R {rname}: {len(rows)}頭", file=sys.stderr)

        else:
            parser.print_help()
            return

        # CSV出力
        print(f"[3/3] Writing {len(all_rows)} rows...", file=sys.stderr)
        write_csv(all_rows, args.output)

    finally:
        api.close()


if __name__ == '__main__':
    main()
