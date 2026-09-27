# -*- coding: utf-8 -*-
"""
collect_weekend_bigdata.py — 週末全レース ビッグデータ集約（メガリサーチ）

3系統の全ファクターを1頭ごとに統合し、独自指数を綿密に計算する:
  A. LightGBM v44 ML能力%（43特徴量アンサンブル）
  B. 17ファクター独自指数 F01-F17（daily_pdca方式・前日予測版）
     - F04騎手/F05厩舎はティア表ではなくML統計の実勝率から換算（データ主導）
  C. 累積DB照合（9,259戦の実測独自指数: 平均・最高・最高F01・平均着順）

使い方:
  python collect_weekend_bigdata.py --dates 20260801 20260802

前提: predict_and_report.py --date YYYYMMDD --netkeiba を先に実行して
      _cache/netkeiba/{shutuba,horse_past}.json にデータが蓄積されていること

出力:
  Desktop/競馬予想レポート/{最初の日付}/週末ビッグデータ_{日付範囲}_独自指数.xlsx
"""
from __future__ import annotations
import sys, json, argparse, datetime
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SRC_DIR   = Path(__file__).resolve().parent
SCRIPT_DIR = SRC_DIR / 'scripts'
CACHE_DIR = SRC_DIR / '_cache' / 'netkeiba'
MODEL_DIR = SRC_DIR / 'data' / 'models'
PDCA_DIR  = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca'
DB_PATH   = PDCA_DIR / 'db' / 'race_results.json'
OUT_ROOT  = Path.home() / 'Desktop' / '競馬予想レポート'

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SRC_DIR / 'scraper'))
sys.path.insert(0, str(PDCA_DIR))

import numpy as np
import lightgbm as lgb

from convert_netkeiba_to_features import (
    load_stats, load_bloodline, load_name_to_id_maps,
    convert_shutuba_horse, rcode_to_netkeiba_id, rcode_to_month,
)
from smartrc_api import SmartRCAPI
from netkeiba import NetkeibaScaper   # 血統フォールバック用（2026-09-04）
import os
# 2026-09-04 の修正（中日数の実装・血統フォールバック有効化）を無効化して
# 修正前の挙動を再現するスイッチ。効果測定用。
NO_FIX = os.environ.get('KEIBA_NO_FIX') == '1'

# daily_pdca の重み・枠バイアス・馬場適性表（独自指数の正本）
from config import WEIGHTS, GATE_BIAS, SURFACE_SC

VENUE_NAMES = {1:'札幌',2:'函館',3:'福島',4:'新潟',5:'東京',
               6:'中山',7:'中京',8:'京都',9:'阪神',10:'小倉'}
SEX_NAMES = {1:'牡', 2:'牝', 3:'セ'}

FEATURE_COLS = [
    'waku','sex_cd','barei','futan','ba_taijyu','zogen_sa','blinker',
    'distance','dist_cat','surface','grade_cd','tenko_cd','baba_cd',
    'syusso_tosu','prize_1','venue_cd','month','race_num',
    'odds','ninki',
    'num_past_races','avg_finish_5','best_finish_5',
    'win_rate_5','top3_rate_5',
    'avg_time_5','avg_l3f_5',
    'days_since_last','running_style','avg_j4c_5',
    'same_dist_runs','same_dist_winrate','same_dist_top3rate',
    'same_surface_runs','same_surface_winrate','same_surface_top3rate',
    'heavy_baba_runs','heavy_baba_top3rate',
    'jockey_winrate','trainer_winrate',
    'father_winrate','bms_winrate',
    'father_surface_wr','bms_surface_wr',
]
ABILITY_COLS = [c for c in FEATURE_COLS if c not in ('odds','ninki')]

_RS_MAP = {1:'逃げ', 2:'先行', 3:'差し', 4:'追込'}


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


def fv(row, key):
    v = to_float(row.get(key, 0))
    return 0.0 if (v != v) else v


# ============================================================
# 17ファクター独自指数（前日予測版・キャッシュ形式適応）
# ============================================================
def calc_dokuji_forecast(horse: dict, past: list, race_info: dict,
                          row: dict, n: int, venue: str,
                          field_kinryo_avg: float) -> tuple[float, dict]:
    """
    F01-F17を計算して(独自指数, 因子dict)を返す。
    daily_pdca/predict_shutuba.py の calc_forecast_score を
    netkeibaキャッシュ形式（rank/distance/trackkind/last_3f/stime）に適応。
    F04/F05はティア表ではなくML統計の実勝率から換算する。
    """
    dist_m  = race_info.get('distance', 0) or 0
    surface_raw = race_info.get('surface', '')
    surface = '芝' if '芝' in str(surface_raw) else 'ダート'
    track_now = 1 if surface == '芝' else 2
    grade   = race_info.get('grade', '') or ''
    rname   = race_info.get('title', '') or ''

    # F01 後3F能力（過去5走の最速後3F。33.0秒=100点, 36.0秒=0点）
    valid_f3 = [p['last_3f'] for p in past if p.get('last_3f')]
    if valid_f3:
        best_f3 = min(valid_f3)
        f01 = min(100.0, max(0.0, (36.0 - best_f3) / 3.0 * 100.0))
    else:
        f01 = 50.0

    # F02 タイム指数（同距離±200mの最速タイムを距離基準と比較）
    same_dist = [p for p in past
                 if p.get('distance') and abs(p['distance'] - dist_m) <= 200
                 and p.get('stime')]
    if same_dist and dist_m > 0:
        best_ts = min(p['stime'] for p in same_dist)
        base = dist_m / 1000.0 * 61.0
        f02 = min(100.0, max(0.0, (base + 3 - best_ts) / 3.0 * 100.0))
    else:
        f02 = 50.0

    # F03 着差スコア（着差データがないため着順から近似 + 勝利補正）
    recent_ranks = [p['rank'] for p in past[:3] if p.get('rank')]
    if recent_ranks:
        # 1着=0.0 / 2着=0.3 / 3着=0.6 / 以降0.5刻み で着差を近似
        def rank_to_diff(r):
            if r <= 1: return 0.0
            if r == 2: return 0.3
            if r == 3: return 0.6
            return min(5.0, 0.6 + (r - 3) * 0.5)
        avg_diff = sum(rank_to_diff(r) for r in recent_ranks) / len(recent_ranks)
        f03 = max(0.0, 100.0 - avg_diff * 15.0)
    else:
        f03 = 50.0
    wins = sum(1 for p in past if p.get('rank') == 1)
    if wins > 0:
        f03 = min(100.0, f03 + wins * 5.0)

    # F04 騎手（ML統計の実勝率から換算: 勝率10%=78点, 17.8%=100点）
    jk_wr = fv(row, 'jockey_winrate')
    f04 = min(100.0, 50.0 + jk_wr * 280.0) if jk_wr > 0 else 50.0

    # F05 厩舎（同上）
    tr_wr = fv(row, 'trainer_winrate')
    f05 = min(100.0, 50.0 + tr_wr * 280.0) if tr_wr > 0 else 50.0

    # F06 枠順バイアス（会場別）
    waku = horse.get('waku') or 0
    try:
        f06 = float(GATE_BIAS.get(venue, {}).get(int(waku), 65)) if waku else 65.0
    except Exception:
        f06 = 65.0

    # F07 馬番内外
    # 🔴 2026-09-11: 枠順発表前の umaban は「登録順の仮番号」で実際の馬番と無関係。
    #   それで内外を採点すると最大30点（総合指数で約0.8点）の偽の差がつき、
    #   上位差0.8のローズS(2026-09-13)では◎○の並びに効く大きさだった。
    #   枠（waku）が未確定の間は内外比率を中央(0.5)に固定して全馬同点にする。
    banum = int(horse.get('umaban') or 8)
    inner = 1.0 - (banum - 1) / max(n - 1, 1) if waku else 0.5
    if venue == '東京':   f07 = 55.0 + inner * 25.0
    elif venue == '京都': f07 = 60.0 + inner * 35.0
    elif venue == '中山': f07 = 60.0 + inner * 30.0
    elif venue == '阪神': f07 = 58.0 + inner * 28.0
    else:                  f07 = 60.0 + inner * 15.0
    f07 = min(100.0, max(0.0, f07))

    # F08 距離適性（カテゴリ基準×過去同距離の複勝率で補正）
    if dist_m <= 1200:   f08 = 72.0
    elif dist_m <= 1600: f08 = 75.0
    elif dist_m <= 2000: f08 = 78.0
    elif dist_m <= 2400: f08 = 74.0
    else:                f08 = 70.0
    if same_dist:
        good = sum(1 for p in same_dist if p.get('rank') and p['rank'] <= 3)
        ratio = good / len(same_dist)
        f08 = f08 * 0.6 + ratio * 100.0 * 0.4

    # F09 馬体重変化（前日段階は不明が多い→不明時は中立70点）
    hw = horse.get('horse_weight') or 0
    wc = horse.get('weight_diff') or 0
    if not hw:
        f09 = 70.0
    elif abs(wc) <= 4:  f09 = 92.0
    elif abs(wc) <= 8:  f09 = 77.0
    elif abs(wc) <= 14: f09 = 60.0
    else:               f09 = 40.0

    # F10 斤量（フィールド平均比）
    kin = to_float(horse.get('futan'))
    if kin == kin and kin > 0:
        f10 = min(100.0, max(0.0, 65.0 + (field_kinryo_avg - kin) * 4.0))
    else:
        f10 = 60.0

    # F11 性別
    sex = horse.get('sex_cd', 0)
    f11 = {1: 60.0, 2: 62.0, 3: 58.0}.get(sex, 60.0)

    # F12 年齢
    age = horse.get('age', 0)
    f12 = {2: 80, 3: 88, 4: 98, 5: 95, 6: 85, 7: 75}.get(age, 68.0)

    # F13 クラス
    if 'G1' in grade or 'GI' == grade:   f13 = 90.0
    elif 'G2' in grade: f13 = 83.0
    elif 'G3' in grade: f13 = 77.0
    elif grade in ('L', 'OP') or 'オープン' in rname: f13 = 72.0
    elif '3勝' in rname: f13 = 65.0
    elif '2勝' in rname: f13 = 60.0
    elif '1勝' in rname: f13 = 55.0
    else: f13 = 50.0

    # F14 馬場適性（会場×馬場の基準×過去同馬場の複勝率で補正）
    f14 = float(SURFACE_SC.get((surface, venue), 70))
    same_surf = [p for p in past if p.get('trackkind') == track_now]
    if same_surf:
        good = sum(1 for p in same_surf if p.get('rank') and p['rank'] <= 3)
        f14 = f14 * 0.7 + (good / len(same_surf)) * 100.0 * 0.3

    # F15 EV / F16 人気乖離（前日はオッズ未確定→中立50点）
    f15 = 50.0
    f16 = 50.0

    # F17 頭数影響
    f17 = max(40.0, 100.0 - (n - 8) * 3.0)

    dokuji = (
        f01*WEIGHTS['後3F能力']   + f02*WEIGHTS['タイム指数'] +
        f03*WEIGHTS['着差スコア'] + f04*WEIGHTS['騎手']       +
        f05*WEIGHTS['厩舎']       + f06*WEIGHTS['枠バイアス'] +
        f07*WEIGHTS['馬番内外']   + f08*WEIGHTS['距離適性']   +
        f09*WEIGHTS['馬体重変化'] + f10*WEIGHTS['斤量']       +
        f11*WEIGHTS['性別']       + f12*WEIGHTS['年齢']       +
        f13*WEIGHTS['クラス']     + f14*WEIGHTS['馬場適性']   +
        f15*WEIGHTS['EV']         + f16*WEIGHTS['人気乖離']   +
        f17*WEIGHTS['頭数影響']
    )
    dokuji = round(min(100.0, max(0.0, dokuji)), 1)
    factors = {
        'F01_後3F': round(f01,1), 'F02_タイム': round(f02,1),
        'F03_着差': round(f03,1), 'F04_騎手': round(f04,1),
        'F05_厩舎': round(f05,1), 'F06_枠': round(f06,1),
        'F07_馬番': round(f07,1), 'F08_距離': round(f08,1),
        'F09_体重': round(f09,1), 'F10_斤量': round(f10,1),
        'F11_性別': round(f11,1), 'F12_年齢': round(f12,1),
        'F13_クラス': round(f13,1), 'F14_馬場': round(f14,1),
        'F15_EV': round(f15,1), 'F16_乖離': round(f16,1),
        'F17_頭数': round(f17,1),
    }
    return dokuji, factors


# ============================================================
# 累積DB照合
# ============================================================
def load_cumulative_db():
    if not DB_PATH.exists():
        print(f"[WARN] 累積DBなし: {DB_PATH}", file=sys.stderr)
        return {}
    with open(DB_PATH, encoding='utf-8') as f:
        db = json.load(f)
    by_name = defaultdict(list)
    for e in db:
        nm = e.get('馬名', '')
        if nm:
            by_name[nm].append(e)
    print(f"[累積DB] {len(db)}レコード / {len(by_name)}頭", file=sys.stderr)
    return by_name


def lookup_past_db(horse_name: str, by_name: dict) -> dict:
    records = by_name.get(horse_name, [])
    if not records:
        return {}
    records = sorted(records, key=lambda x: x.get('date', ''), reverse=True)
    scores = [r.get('独自指数', 0) for r in records]
    chakus = [r.get('着順int', 99) for r in records if r.get('着順int', 99) < 99]
    return {
        'DB出走数':   len(records),
        'DB平均指数': round(sum(scores) / len(scores), 1),
        'DB最高指数': round(max(scores), 1),
        'DB最高F01':  round(max(r.get('F01_後3F', 0) for r in records), 1),
        'DB平均着順': round(sum(chakus) / len(chakus), 1) if chakus else 0.0,
        'DB直近印':   records[0].get('AI印', ''),
        'DB直近着順': records[0].get('着順', ''),
    }


# ============================================================
# メイン
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', nargs='+', required=True, metavar='YYYYMMDD')
    args = ap.parse_args()

    # ── race_id → 日付マッピング（smartrc開催情報から）──────────
    print('[1/5] 開催レースID取得...', file=sys.stderr)
    api = SmartRCAPI()
    rid_date = {}   # netkeiba race_id -> (date, rcode)
    try:
        for d in args.dates:
            races = api.fetch_races(d)
            for r in races:
                rid = rcode_to_netkeiba_id(r['rcode'])
                rid_date[rid] = (d, r['rcode'])
            print(f"  {d}: {len(races)}レース", file=sys.stderr)
    finally:
        api.close()

    # ── キャッシュ読込 ────────────────────────────────────────
    print('[2/5] キャッシュ読込...', file=sys.stderr)
    with open(CACHE_DIR / 'shutuba.json', encoding='utf-8') as f:
        shutuba_cache = json.load(f)
    with open(CACHE_DIR / 'horse_past.json', encoding='utf-8') as f:
        past_cache = json.load(f)

    target_rids = [rid for rid in rid_date if rid in shutuba_cache]
    missing = [rid for rid in rid_date if rid not in shutuba_cache]
    print(f"  対象: {len(target_rids)}レース（キャッシュ済み）/ 未取得 {len(missing)}レース",
          file=sys.stderr)

    # ── モデル・統計ロード ────────────────────────────────────
    print('[3/5] MLモデル・統計・累積DBロード...', file=sys.stderr)
    ability_models = [
        lgb.Booster(model_file=str(MODEL_DIR / f'lgb_v44_ability_{i}.txt'))
        for i in range(3)
    ]
    stats = load_stats()
    bloodline = load_bloodline()
    name_father_map, name_bms_map = load_name_to_id_maps()
    db_by_name = load_cumulative_db()
    # 血統DB未登録の若い馬をプロフィール経由で救済するためのスクレイパー
    # （horse_profile.json にキャッシュされるので2回目以降は高速）
    nk = NetkeibaScaper()
    print(f'  父名マップ {len(name_father_map):,}件 / 母父名マップ {len(name_bms_map):,}件',
          file=sys.stderr)

    # ── 全レース・全馬 スコア計算 ─────────────────────────────
    print('[4/5] 全馬スコア計算...', file=sys.stderr)
    all_records = []
    race_summaries = []

    for rid in sorted(target_rids):
        date_str, rcode = rid_date[rid]
        data = shutuba_cache[rid]
        ri = dict(data['race_info'])
        ri['month'] = rcode_to_month(rcode)
        ri['date'] = date_str          # 中日数の算出に使う（2026-09-04）
        horses = data['horses']
        n = len(horses)
        if n == 0:
            continue
        venue = VENUE_NAMES.get(ri.get('venue_cd', 0), ri.get('venue_name', '?'))
        rno = int(rid[10:12])

        # ML特徴量行の構築
        rows, metas = [], []
        for h in horses:
            hid = h.get('horse_id', '')
            past = past_cache.get(hid, [])
            # A/B用スイッチ（2026-09-04）。KEIBA_NO_FIX=1 で修正前の挙動を再現する
            #   date を落とす → 中日数が None になる（従来の状態）
            #   nk_scraper を渡さない → 血統フォールバックが効かない（従来の状態）
            if NO_FIX:
                past = [{k: v for k, v in p.items() if k != 'date'} for p in past]
            try:
                # nk_scraper を渡すと、血統DB未登録の若い馬について
                # netkeibaプロフィールから父名を引き→名前マップでIDを解決する
                # フォールバックが働く。従来これを渡しておらず、
                # 父勝率%が60.8%の馬で0（レースの48.1%は全頭0）になっていた。
                row = convert_shutuba_horse(
                    h, ri, past, stats, bloodline,
                    name_father_map=name_father_map, name_bms_map=name_bms_map,
                    nk_scraper=(None if NO_FIX else nk),
                )
            except Exception:
                row = {}
            rows.append(row)
            metas.append((h, past))

        X = np.array(
            [[to_float(r.get(c)) for c in ABILITY_COLS] for r in rows],
            dtype=np.float32,
        )
        pred = np.mean([m.predict(X) for m in ability_models], axis=0)

        # 斤量フィールド平均
        kins = [to_float(h.get('futan')) for h, _ in metas]
        kins = [k for k in kins if k == k and k > 0]
        kin_avg = sum(kins) / len(kins) if kins else 55.5

        recs = []
        for i, (h, past) in enumerate(metas):
            row = rows[i]
            ml_pct = float(pred[i]) * 100.0
            dokuji, factors = calc_dokuji_forecast(
                h, past, ri, row, n, venue, kin_avg)
            db_info = lookup_past_db(h.get('horse_name',''), db_by_name)

            # 総合指数 = 独自指数55% + ML能力%45%（0-100スケール合成）
            ml_scaled = min(100.0, ml_pct * (100.0 / 40.0))  # 40%≒上限級
            total = round(dokuji * 0.55 + ml_scaled * 0.45, 1)

            rec = {
                'date': date_str, '競馬場': venue, 'R': rno,
                'レース名': ri.get('title',''), '距離': f"{'芝' if '芝' in str(ri.get('surface','')) else 'ダ'}{ri.get('distance','')}m",
                'グレード': ri.get('grade',''),
                '頭数': n,
                '枠': h.get('waku') or '', '馬番': h.get('umaban',''),
                '馬名': h.get('horse_name',''),
                '性齢': f"{SEX_NAMES.get(h.get('sex_cd',0),'?')}{h.get('age','')}",
                '斤量': h.get('futan',''),
                '騎手勝率%': round(fv(row,'jockey_winrate')*100,1),
                '厩舎勝率%': round(fv(row,'trainer_winrate')*100,1),
                '父勝率%':   round(fv(row,'father_winrate')*100,1),
                '母父勝率%': round(fv(row,'bms_winrate')*100,1),
                # 2026-09-07追加: 種牡馬名そのもの。勝率だけでは
                # 「どの種牡馬が効いたか」を後から検証できないため。
                # 勝率0.0は「弱い」ではなく「データ無し」を意味するので、
                # 分析時は必ず名前の有無で欠損を判定すること。
                '父':   row.get('father_name','') or '',
                '母父': row.get('bms_name','') or '',
                '脚質': _RS_MAP.get(int(fv(row,'running_style')), '?'),
                '近5走平均着': round(fv(row,'avg_finish_5'),1),
                '近5走複勝率%': round(fv(row,'top3_rate_5')*100,0),
                '平均上がり': round(fv(row,'avg_l3f_5'),1),
                '中日数': int(fv(row,'days_since_last')),
                '同距離走数': int(fv(row,'same_dist_runs')),
                '同距離複勝率%': round(fv(row,'same_dist_top3rate')*100,0),
                'ML能力%': round(ml_pct,1),
                '独自指数': dokuji,
                '総合指数': total,
                **factors,
                **db_info,
            }
            recs.append(rec)

        # レース内ランク & AI印（総合指数順）
        recs.sort(key=lambda x: -x['総合指数'])
        MARKS = {1:'◎',2:'○',3:'▲',4:'△',5:'△'}
        for i, r in enumerate(recs):
            r['AI印'] = MARKS.get(i+1, '')
            r['AI予測順位'] = i+1
        all_records.extend(recs)

        top3 = recs[:3]
        race_summaries.append({
            'date': date_str, '競馬場': venue, 'R': rno,
            'レース名': ri.get('title',''), '距離': recs[0]['距離'],
            'グレード': ri.get('grade',''), '頭数': n,
            '本命': f"{top3[0]['馬番']}番{top3[0]['馬名']}",
            '本命総合': top3[0]['総合指数'],
            '対抗': f"{top3[1]['馬番']}番{top3[1]['馬名']}" if len(top3)>1 else '',
            '単穴': f"{top3[2]['馬番']}番{top3[2]['馬名']}" if len(top3)>2 else '',
            '上位差': round(top3[0]['総合指数'] - top3[1]['総合指数'],1) if len(top3)>1 else 0,
        })

    print(f"  完了: {len(race_summaries)}レース / {len(all_records)}頭", file=sys.stderr)

    # ── Excel出力 ─────────────────────────────────────────────
    print('[5/5] Excel出力...', file=sys.stderr)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    HEAD_FILL = PatternFill('solid', fgColor='1F4E5F')
    HEAD_FONT = Font(color='FFFFFF', bold=True, size=9)
    MARK_FILL = PatternFill('solid', fgColor='FFF2CC')

    def write_sheet(ws, headers, rows_data, widths=None, highlight_col=None):
        ws.append(headers)
        for c in range(1, len(headers)+1):
            cell = ws.cell(row=1, column=c)
            cell.fill = HEAD_FILL
            cell.font = HEAD_FONT
            cell.alignment = Alignment(horizontal='center')
        for rd in rows_data:
            ws.append(rd)
        if widths:
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = 'A2'

    # シート1: 全馬データ（フラット）
    ws1 = wb.active
    ws1.title = '全馬ビッグデータ'
    cols1 = ['date','競馬場','R','レース名','距離','グレード','頭数',
             'AI印','AI予測順位','枠','馬番','馬名','性齢','斤量',
             '総合指数','独自指数','ML能力%',
             'F01_後3F','F02_タイム','F03_着差','F04_騎手','F05_厩舎',
             'F06_枠','F07_馬番','F08_距離','F09_体重','F10_斤量',
             'F11_性別','F12_年齢','F13_クラス','F14_馬場','F15_EV',
             'F16_乖離','F17_頭数',
             '騎手勝率%','厩舎勝率%','父勝率%','母父勝率%','父','母父',
             '脚質','近5走平均着','近5走複勝率%','平均上がり','中日数',
             '同距離走数','同距離複勝率%',
             'DB出走数','DB平均指数','DB最高指数','DB最高F01','DB平均着順',
             'DB直近印','DB直近着順']
    sorted_recs = sorted(all_records, key=lambda x: (x['date'], x['競馬場'], x['R'], x['AI予測順位']))
    write_sheet(ws1, cols1,
                [[r.get(c,'') for c in cols1] for r in sorted_recs],
                widths=[9,6,4,16,9,6,5,5,5,4,5,16,6,6,8,8,8]+[7]*17+[8,8,8,8,6,8,8,8,7,7,9,7,9,9,9,9,7,8])
    # AI印行をハイライト
    for ri_, r in enumerate(sorted_recs, 2):
        if r.get('AI印') == '◎':
            for c in range(1, len(cols1)+1):
                ws1.cell(row=ri_, column=c).fill = MARK_FILL

    # シート2: レース別サマリー
    ws2 = wb.create_sheet('レース別サマリー')
    cols2 = ['date','競馬場','R','レース名','距離','グレード','頭数',
             '本命','本命総合','対抗','単穴','上位差']
    write_sheet(ws2, cols2,
                [[s.get(c,'') for c in cols2]
                 for s in sorted(race_summaries, key=lambda x:(x['date'],x['競馬場'],x['R']))],
                widths=[9,6,4,18,9,6,5,22,9,22,22,7])

    # シート3: 高指数注目馬（総合指数75以上 or DB最高指数78以上）
    ws3 = wb.create_sheet('高指数注目馬')
    hot = [r for r in all_records
           if r['総合指数'] >= 75 or r.get('DB最高指数', 0) >= 78]
    hot.sort(key=lambda x: -x['総合指数'])
    cols3 = ['date','競馬場','R','レース名','距離','AI印','馬番','馬名',
             '総合指数','独自指数','ML能力%','DB最高指数','DB平均着順',
             '騎手勝率%','近5走複勝率%','脚質']
    write_sheet(ws3, cols3, [[r.get(c,'') for c in cols3] for r in hot],
                widths=[9,6,4,16,9,5,5,16,8,8,8,9,9,9,10,6])

    # シート4: 穴候補（独自指数72+ × 近5走平均着順4着以下 = 人気盲点）
    ws4 = wb.create_sheet('穴候補')
    ana = [r for r in all_records
           if r['独自指数'] >= 68 and r.get('近5走平均着', 0) >= 4.0
           and r.get('DB最高指数', 0) >= 70]
    ana.sort(key=lambda x: -x['独自指数'])
    write_sheet(ws4, cols3, [[r.get(c,'') for c in cols3] for r in ana],
                widths=[9,6,4,16,9,5,5,16,8,8,8,9,9,9,10,6])

    # シート5: 日別・会場別サマリー
    ws5 = wb.create_sheet('日別会場別')
    agg = defaultdict(lambda: {'races':0,'horses':0})
    for s in race_summaries:
        k = (s['date'], s['競馬場'])
        agg[k]['races'] += 1
        agg[k]['horses'] += s['頭数']
    write_sheet(ws5, ['date','競馬場','レース数','頭数'],
                [[d, v, agg[(d,v)]['races'], agg[(d,v)]['horses']]
                 for (d,v) in sorted(agg)],
                widths=[10,8,8,8])

    first = min(args.dates)
    last  = max(args.dates)
    out_dir = OUT_ROOT / first
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"週末ビッグデータ_{first}-{last[4:]}_独自指数.xlsx"
    wb.save(out)

    # 後段レポート用の生データJSONダンプ
    json_out = out_dir / f"週末ビッグデータ_{first}-{last[4:]}_records.json"
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump({'records': all_records, 'summaries': race_summaries},
                  f, ensure_ascii=False)

    # ── コンソールサマリー ────────────────────────────────────
    print(f"\n{'='*90}")
    print(f"週末ビッグデータ集約 完了: {len(race_summaries)}レース / {len(all_records)}頭")
    print(f"{'='*90}")
    for d in args.dates:
        day_races = [s for s in race_summaries if s['date'] == d]
        venues = sorted(set(s['競馬場'] for s in day_races))
        print(f"\n■ {d}: {len(day_races)}レース（{'/'.join(venues)}）")
        graded = [s for s in day_races if s['グレード']]
        for s in graded:
            print(f"  [{s['グレード']}] {s['競馬場']}{s['R']}R {s['レース名']}: "
                  f"◎{s['本命']}({s['本命総合']}) ○{s['対抗']} ▲{s['単穴']}")

    print(f"\n=== 総合指数 TOP15（全レース横断） ===")
    top15 = sorted(all_records, key=lambda x: -x['総合指数'])[:15]
    for r in top15:
        print(f"  {r['date'][4:6]}/{r['date'][6:]} {r['競馬場']}{r['R']:>2}R "
              f"{r['AI印']}{r['馬番']:>2}番 {r['馬名']:<14} "
              f"総合{r['総合指数']:>5.1f} 独自{r['独自指数']:>5.1f} ML{r['ML能力%']:>5.1f}% "
              f"DB最高{r.get('DB最高指数','—')}")

    print(f"\n=== 穴候補（高指数×近走凡走=人気盲点） ===")
    for r in ana[:10]:
        print(f"  {r['date'][4:6]}/{r['date'][6:]} {r['競馬場']}{r['R']:>2}R "
              f"{r['馬番']:>2}番 {r['馬名']:<14} "
              f"独自{r['独自指数']:>5.1f} 近5走平均{r['近5走平均着']}着 "
              f"DB最高{r.get('DB最高指数','—')}")

    if missing:
        print(f"\n[注意] キャッシュ未取得 {len(missing)}レース（スクレイプ完了後に再実行で反映）")

    print(f"\n[保存] {out}")


if __name__ == '__main__':
    main()
