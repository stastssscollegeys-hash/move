# -*- coding: utf-8 -*-
"""
backfill_leakfree.py — 結果リークなし「レース前時点の予想（records）」バックフィル 本番スクリプト
================================================================================
過去レースについて、当時（レース前日）に得られたはずの情報だけを使って印・総合指数を
再構築する。研究フェーズ（Desktop/競馬予想レポート/20260912/research/backfill_study/
leakfree_reconstruct.py, predict_leakfree.py）の設計をそのまま本番化したもの。

【絶対厳守】
  - 本番のキャッシュ・DB・スクリプトは一切変更しない。書き込み先は以下のみ:
      * このファイル自身の新規キャッシュ: src/keiba-predictor/_cache/leakfree/
      * 出力: Desktop/競馬予想レポート/backfill_leakfree/
  - 本番の collect_weekend_bigdata.py / convert_netkeiba_to_features.py は
    「読み取り専用」でimportして関数・重みだけ再利用する（実行時に書き込みは一切しない）。
  - scraper/netkeiba.py の NetkeibaScaper は絶対に使わない
    （5走キャップ・日付フィルタなし＝リーク／かつ _cache/netkeiba/*.json に書き込む＝本番汚染）。

リーク対策（研究レポート section 4 のとおり）:
  1. 出馬表: db.netkeiba.com/race/{race_id}/ の「結果ページ」から
     着順・タイム・着差・通過・上がり3F・単勝オッズ・人気の列を一切読まず、
     枠/馬番/馬名/性齢/斤量/騎手/調教師/馬体重のみ再構成する。
  2. 過去走: db.netkeiba.com/horse/result/{id}/ から全戦績を取得し、
     date < レース日 でローカルフィルタしてから直近5走を使う（5走キャップ前にフィルタ）。
  3. 累積DB照合: race_results.json は date < レース日 の行だけを使う。
  4. 統計/血統/MLモデル: 本番の data/stats/*.json・bloodline_parsed.jsonl・
     lgb_v44_*.txt をそのまま読み取り専用で使う（2026-04-11固定・対象レースより後の情報なし
     と確認済み）。2026-04-18/19（学習期間の境界）は対象から除外する。
  5. オッズ由来 F15/F16 は本番の前日パスと同じ中立値(50.0)固定。

使い方:
  python backfill_leakfree.py --dates 20260607 20260613
  python backfill_leakfree.py --all-missing
  python backfill_leakfree.py --validate 20260801 20260808 20260822 20260906
"""
from __future__ import annotations
import argparse, collections, datetime, io, json, re, sys, time, traceback
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import numpy as np
import lightgbm as lgb

PROD_ROOT = Path(__file__).resolve().parent
SCRIPT_DIR = PROD_ROOT / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROD_ROOT))
PDCA_DIR = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca'
sys.path.insert(0, str(PDCA_DIR))

# 読み取り専用import: 本番の特徴量計算・因子計算・重みをそのまま再利用する。
# （collect_weekend_bigdata / convert_netkeiba_to_features は import 時に副作用なし。
#   main()はガードされており実行されない。ネットワークアクセスやキャッシュ書き込みは
#   関数を明示的に呼んだ時だけ発生し、本スクリプトはその関数を一切呼ばない）
from convert_netkeiba_to_features import (
    load_stats, load_bloodline, load_name_to_id_maps, convert_shutuba_horse,
)
import collect_weekend_bigdata as PROD   # calc_dokuji_forecast, VENUE_NAMES, SEX_NAMES, ABILITY_COLS 等

VERSION = 'backfill_leakfree.py v1.0 (2026-09-11)'

OUT_ROOT = Path.home() / 'Desktop' / '競馬予想レポート' / 'backfill_leakfree'
OUT_ROOT.mkdir(parents=True, exist_ok=True)
PROGRESS_LOG = OUT_ROOT / 'progress.log'
VALIDATION_REPORT = OUT_ROOT / 'validation_report.md'

CACHE = PROD_ROOT / '_cache' / 'leakfree'
CACHE_HTML = CACHE / 'html'
CACHE_ENTRIES = CACHE / 'entries'
CACHE_HIST = CACHE / 'horse_hist'
for d in (CACHE, CACHE_HTML, CACHE_ENTRIES, CACHE_HIST):
    d.mkdir(parents=True, exist_ok=True)

DB_DIR = PDCA_DIR / 'db'
RACE_RESULTS_PATH = DB_DIR / 'race_results.json'
PAYOUTS_PATH = DB_DIR / 'payouts.json'

MODEL_DIR = PROD_ROOT / 'data' / 'models'

VENUE_NAMES = PROD.VENUE_NAMES
SEX_NAMES = PROD.SEX_NAMES
ABILITY_COLS = PROD.ABILITY_COLS
calc_dokuji_forecast = PROD.calc_dokuji_forecast
_RS_MAP = PROD._RS_MAP

# 学習期間の境界であいまいなため除外（研究レポート section 5）
EXCLUDED_DATES = {'20260418', '20260419'}

_BASE = "https://db.netkeiba.com"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.9",
    "Referer": "https://www.netkeiba.com/",
})

_last_request_ts = [0.0]
MIN_INTERVAL = 1.2   # 秒。1リクエストごとに1秒以上あける（安全マージンを見て1.2秒）


def log(msg: str):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(PROGRESS_LOG, 'a', encoding='utf-8') as f:
        f.write(line + "\n")


def _throttled_get(url: str) -> str:
    wait = MIN_INTERVAL - (time.time() - _last_request_ts[0])
    if wait > 0:
        time.sleep(wait)
    last_err = None
    for attempt in range(3):
        try:
            resp = SESSION.get(url, timeout=20)
            _last_request_ts[0] = time.time()
            resp.encoding = resp.apparent_encoding or 'euc-jp'
            if resp.status_code != 200:
                last_err = f"status {resp.status_code}"
                time.sleep(2 * (attempt + 1))
                continue
            return resp.text
        except Exception as e:
            last_err = str(e)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after retries: {url} ({last_err})")


def _cached_get(url: str, cache_path: Path) -> str:
    if cache_path.exists():
        return cache_path.read_text(encoding='utf-8', errors='ignore')
    text = _throttled_get(url)
    cache_path.write_text(text, encoding='utf-8')
    return text


# ============================================================
# 1. race_id 列挙
# ============================================================
def fetch_race_ids_for_date(date_str: str) -> list[str]:
    """db.netkeiba/race/list/{date}/ にはNAR(地方)・海外レースのidも混ざるため、
    venue_cd が VENUE_NAMES(1-10, JRA10場) に含まれるものだけに絞る。"""
    key = CACHE_HTML / f'dblist_{date_str}.html'
    html = _cached_get(f"{_BASE}/race/list/{date_str}/", key)
    ids = []
    for m in re.finditer(r"/race/(\d{12})", html):
        rid = m.group(1)
        if rid in ids:
            continue
        try:
            venue_cd = int(rid[4:6])
        except ValueError:
            continue
        if venue_cd not in VENUE_NAMES:
            continue
        ids.append(rid)
    return ids


def _safe_int(v):
    if not v:
        return None
    try:
        return int(re.sub(r"[^\d\-]", "", v))
    except Exception:
        return None


def _safe_float(v):
    if not v:
        return None
    try:
        return float(re.sub(r"[^\d.\-]", "", v))
    except Exception:
        return None


# ============================================================
# 2. 出走情報（結果非依存）
# ============================================================
def fetch_entry_leakfree(race_id: str) -> dict:
    """結果ページから『着順・タイム・着差・通過・上がり3F・単勝オッズ・人気』を
    一切読まずに出走情報（構造情報）だけを再構成する。キャッシュ済みなら再利用。"""
    cpath = CACHE_ENTRIES / f'{race_id}.json'
    if cpath.exists():
        return json.loads(cpath.read_text(encoding='utf-8'))

    html = _cached_get(f"{_BASE}/race/{race_id}/", CACHE_HTML / f'race_{race_id}.html')
    soup = BeautifulSoup(html, 'html.parser')

    title_el = soup.select_one("title")
    title = title_el.get_text(strip=True).split("｜")[0] if title_el else ""
    info_el = soup.select_one(".racedata, .data_intro")
    info_text = info_el.get_text(" ", strip=True) if info_el else ""
    dist_m = re.search(r"(\d{3,4})m", info_text)
    distance = int(dist_m.group(1)) if dist_m else 0
    surface = "ダート" if ("ダ" in info_text and "芝" not in info_text) else "芝"
    grade = ""
    for g in ["G1", "G2", "G3", "(L)"]:
        if g in title:
            grade = g.strip("()")
            break
    venue_cd = int(race_id[4:6])

    table = soup.select_one("table.race_table_01")
    horses = []
    if table:
        header_cells = table.select("tr")[0].select("th, td")
        headers = [c.get_text(strip=True) for c in header_cells]

        def idx_of(name):
            try:
                return headers.index(name)
            except ValueError:
                return None

        i_waku = idx_of("枠番") if idx_of("枠番") is not None else idx_of("枠")
        i_umaban = idx_of("馬番")
        i_horse = idx_of("馬名")
        i_sexage = idx_of("性齢")
        i_futan = idx_of("斤量")
        i_jockey = idx_of("騎手")
        i_weight = idx_of("馬体重")
        i_trainer = idx_of("調教師") if idx_of("調教師") is not None else idx_of("厩舎")

        rows = table.select("tr")[1:]
        for row in rows:
            cells = row.select("td")
            if not cells:
                continue

            def cell_text(i):
                return cells[i].get_text(strip=True) if (i is not None and i < len(cells)) else ""

            horse_name_cell = cells[i_horse] if (i_horse is not None and i_horse < len(cells)) else None
            horse_link = horse_name_cell.select_one('a[href*="/horse/"]') if horse_name_cell else None
            horse_name = horse_link.get_text(strip=True) if horse_link else cell_text(i_horse)
            horse_id = ""
            if horse_link:
                mm = re.search(r"/horse/(\w+)", horse_link.get('href', ''))
                if mm:
                    horse_id = mm.group(1)

            jockey_cell = cells[i_jockey] if (i_jockey is not None and i_jockey < len(cells)) else None
            jockey_link = jockey_cell.select_one('a[href*="/jockey/"]') if jockey_cell else None
            jockey_id = ""
            if jockey_link:
                mm = re.search(r"/jockey/(?:result/recent/)?(\w+)", jockey_link.get('href', ''))
                if mm:
                    jockey_id = mm.group(1)

            trainer_cell = cells[i_trainer] if (i_trainer is not None and i_trainer < len(cells)) else None
            trainer_link = trainer_cell.select_one('a[href*="/trainer/"]') if trainer_cell else None
            trainer_id = ""
            if trainer_link:
                mm = re.search(r"/trainer/(?:result/recent/)?(\w+)", trainer_link.get('href', ''))
                if mm:
                    trainer_id = mm.group(1)

            sex_age = cell_text(i_sexage)
            sex_map = {"牡": 1, "牝": 2, "セ": 3}
            sex_cd = sex_map.get(sex_age[:1], 0) if sex_age else 0
            age_m = re.search(r"(\d+)", sex_age) if sex_age else None
            age = int(age_m.group(1)) if age_m else 0

            weight_text = cell_text(i_weight)
            horse_weight = 0
            w_m = re.match(r"(\d+)\(([+\-]?\d+)\)", weight_text)
            if w_m:
                horse_weight = int(w_m.group(1))

            if not horse_name and not horse_id:
                continue

            horses.append({
                "waku": _safe_int(cell_text(i_waku)),
                "umaban": _safe_int(cell_text(i_umaban)),
                "horse_name": horse_name,
                "horse_id": horse_id,
                "sex_cd": sex_cd,
                "age": age,
                "futan": _safe_float(cell_text(i_futan)),
                "jockey_id": jockey_id,
                "trainer_id": trainer_id,
                "horse_weight": horse_weight,
                "weight_diff": 0,
            })

    race_info = {
        "race_id": race_id,
        "distance": distance,
        "surface": surface,
        "condition": "",   # 前日予測と同じ扱い（本番のnetkeibaモードも前日は未確定）
        "weather": "",
        "venue_cd": venue_cd,
        "horse_count": len(horses),
        "prize_1": 0,
        "grade": grade,
        "title": title,
    }
    out = {"race_info": race_info, "horses": horses}
    cpath.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out


# ============================================================
# 3. 馬の全戦績（日付フィルタはローカルで別途行う）
# ============================================================
def fetch_horse_full_history(horse_id: str) -> list[dict]:
    cpath = CACHE_HIST / f'{horse_id}.json'
    if cpath.exists():
        return json.loads(cpath.read_text(encoding='utf-8'))

    html = _cached_get(f"{_BASE}/horse/result/{horse_id}/", CACHE_HTML / f'horse_{horse_id}.html')
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.select_one("table.db_h_race_results")
    results = []
    if table:
        header_row = table.select_one("tr")
        col_map = {}
        if header_row:
            for i, th in enumerate(header_row.select("th, td")):
                text = th.get_text(strip=True)
                if text == "着順": col_map["rank"] = i
                elif text == "距離": col_map["distance"] = i
                elif text == "馬場": col_map["baba"] = i
                elif text == "タイム": col_map["time"] = i
                elif text == "頭数": col_map["tosu"] = i
                elif text == "日付": col_map["date"] = i
                elif text == "上り": col_map["l3f"] = i
                elif text == "通過": col_map["passing"] = i

        rank_idx = col_map.get("rank", 11)
        dist_idx = col_map.get("distance", 14)
        baba_idx = col_map.get("baba", 16)
        time_idx = col_map.get("time", 18)
        tosu_idx = col_map.get("tosu", 6)
        date_idx = col_map.get("date", 0)
        l3f_idx = col_map.get("l3f")
        passing_idx = col_map.get("passing")

        for row in table.select("tr")[1:]:
            cells = row.select("td")
            if len(cells) < 15:
                continue
            try:
                rank = _safe_int(cells[rank_idx].get_text(strip=True))
                if rank is None or rank <= 0:
                    continue
                dist_text = cells[dist_idx].get_text(strip=True)
                surface_char = dist_text[0] if dist_text else ""
                dist_val = _safe_int(re.sub(r"[^\d]", "", dist_text))
                trackkind = 1 if surface_char == "芝" else 2
                baba_text = cells[baba_idx].get_text(strip=True) if len(cells) > baba_idx else ""
                baba_map = {"良": "A", "稍": "B", "重": "C", "不": "D"}
                fr_baba = baba_map.get(baba_text[:1], "A") if baba_text else "A"
                time_text = cells[time_idx].get_text(strip=True) if len(cells) > time_idx else ""
                stime = None
                tm = re.match(r"(\d+):(\d+\.\d+)", time_text)
                if tm:
                    stime = float(tm.group(1)) * 60 + float(tm.group(2))
                l3f = _safe_float(cells[l3f_idx].get_text(strip=True)) if (l3f_idx is not None and len(cells) > l3f_idx) else None
                corner4 = None
                if passing_idx is not None and len(cells) > passing_idx:
                    passing = cells[passing_idx].get_text(strip=True)
                    corners = passing.split("-")
                    corner4 = _safe_int(corners[-1]) if corners else None
                horse_count = _safe_int(cells[tosu_idx].get_text(strip=True))
                date_str = cells[date_idx].get_text(strip=True) if len(cells) > date_idx else ""
                results.append({
                    "rank": rank, "distance": dist_val, "trackkind": trackkind,
                    "fr_baba": fr_baba, "last_3f": l3f, "stime": stime, "corner4": corner4,
                    "horse_count": horse_count, "date": date_str,
                })
            except Exception:
                continue

    cpath.write_text(json.dumps(results, ensure_ascii=False), encoding='utf-8')
    return results


def filter_before(results: list[dict], race_date_yyyymmdd: str) -> list[dict]:
    """race_date より前の日付の行だけを残し、新しい順に並べ替える（=真の過去走のみ）。"""
    base = datetime.datetime.strptime(race_date_yyyymmdd, "%Y%m%d").date()
    out = []
    for r in results:
        s = (r.get("date") or "").strip()
        d0 = None
        for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
            try:
                d0 = datetime.datetime.strptime(s, fmt).date()
                break
            except ValueError:
                continue
        if d0 and d0 < base:
            out.append(r)
    return sorted(out, key=lambda r: r.get("date", ""), reverse=True)


# ============================================================
# 4. 累積DB照合（date < race_date のみ）
# ============================================================
_CUM_DB_CACHE = {}


def load_cumulative_db_by_name() -> dict:
    if '_by_name' in _CUM_DB_CACHE:
        return _CUM_DB_CACHE['_by_name']
    if not RACE_RESULTS_PATH.exists():
        _CUM_DB_CACHE['_by_name'] = {}
        return {}
    with open(RACE_RESULTS_PATH, encoding='utf-8') as f:
        db = json.load(f)
    by_name = collections.defaultdict(list)
    for e in db:
        nm = e.get('馬名', '')
        if nm:
            by_name[nm].append(e)
    _CUM_DB_CACHE['_by_name'] = by_name
    log(f"[累積DB] {len(db)}レコード / {len(by_name)}頭（読み取り専用）")
    return by_name


def lookup_past_db_leakfree(horse_name: str, by_name: dict, race_date: str) -> dict:
    """本番 lookup_past_db と同じ計算だが、date < race_date の行だけを使う
    （本番はここに日付フィルタが無いのが結果リーク経路#5）。"""
    records = by_name.get(horse_name, [])
    records = [r for r in records if (r.get('date') or '') and r['date'] < race_date]
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
# 5. 1日分の再構築
# ============================================================
def build_day(date_str: str, stats, bloodline, name_father_map, name_bms_map,
              ability_models, db_by_name) -> dict | None:
    log(f"[{date_str}] race_id一覧取得")
    race_ids = fetch_race_ids_for_date(date_str)
    if not race_ids:
        log(f"[{date_str}] レースが見つからない -> スキップ")
        return None
    log(f"[{date_str}] {len(race_ids)}レース")

    all_records = []
    race_summaries = []

    for race_id in sorted(race_ids):
        try:
            entry = fetch_entry_leakfree(race_id)
        except Exception as e:
            log(f"  [WARN] {race_id} 出走情報取得失敗: {e}")
            continue
        ri = dict(entry['race_info'])
        ri['month'] = int(date_str[4:6])
        ri['date'] = date_str
        # 2026-09-11 照合で判明した2経路を塞ぐ:
        #  - 結果ページは着順に並んでいるので馬番順に並べ直す（総合指数が同点の時に着順の良い馬が上に来ないように）
        #  - 馬体重は当日発表の値なので使わない（本番の前日パスと同じく未確定扱い。ML入力 ba_taijyu と F09 に効いていた）
        horses = sorted(({**h, 'horse_weight': 0, 'weight_diff': 0} for h in entry['horses']),
                        key=lambda h: h.get('umaban') or 99)
        n = len(horses)
        if n == 0:
            continue
        venue = VENUE_NAMES.get(ri.get('venue_cd', 0), '?')
        rno = int(race_id[10:12])

        rows, metas = [], []
        for h in horses:
            hid = h.get('horse_id', '')
            past = []
            if hid:
                try:
                    hist = fetch_horse_full_history(hid)
                    past = filter_before(hist, date_str)[:5]
                except Exception as e:
                    log(f"  [WARN] horse {hid} 過去走取得失敗: {e}")
                    past = []
            try:
                row = convert_shutuba_horse(
                    h, ri, past, stats, bloodline,
                    name_father_map=name_father_map, name_bms_map=name_bms_map,
                    nk_scraper=None,   # 血統フォールバックなし（結果非依存・本番キャッシュ非汚染を優先）
                )
            except Exception as e:
                log(f"  [WARN] convert失敗 {h.get('horse_name')}: {e}")
                row = {}
            rows.append(row)
            metas.append((h, past))

        X = np.array(
            [[float(rows[i].get(c)) if rows[i].get(c) is not None else float('nan') for c in ABILITY_COLS]
             for i in range(len(rows))],
            dtype=np.float32,
        )
        pred = np.mean([m.predict(X) for m in ability_models], axis=0)

        kins = [h.get('futan') for h, _ in metas]
        kins = [k for k in kins if isinstance(k, (int, float)) and k and k > 0]
        kin_avg = sum(kins) / len(kins) if kins else 55.5

        recs = []
        for i, (h, past) in enumerate(metas):
            row = rows[i]
            ml_pct = float(pred[i]) * 100.0
            dokuji, factors = calc_dokuji_forecast(h, past, ri, row, n, venue, kin_avg)
            db_info = lookup_past_db_leakfree(h.get('horse_name', ''), db_by_name, date_str)

            ml_scaled = min(100.0, ml_pct * (100.0 / 40.0))
            total = round(dokuji * 0.55 + ml_scaled * 0.45, 1)

            def fv(key):
                v = row.get(key)
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    return 0.0
                return 0.0 if v != v else v

            rec = {
                'date': date_str, '競馬場': venue, 'R': rno,
                'レース名': ri.get('title', ''),
                '距離': f"{'芝' if '芝' in str(ri.get('surface', '')) else 'ダ'}{ri.get('distance', '')}m",
                'グレード': ri.get('grade', ''),
                '頭数': n,
                '枠': h.get('waku') or '', '馬番': h.get('umaban', ''),
                '馬名': h.get('horse_name', ''),
                '性齢': f"{SEX_NAMES.get(h.get('sex_cd', 0), '?')}{h.get('age', '')}",
                '斤量': h.get('futan', ''),
                '騎手勝率%': round(fv('jockey_winrate') * 100, 1),
                '厩舎勝率%': round(fv('trainer_winrate') * 100, 1),
                '父勝率%':   round(fv('father_winrate') * 100, 1),
                '母父勝率%': round(fv('bms_winrate') * 100, 1),
                '父':   row.get('father_name', '') or '',
                '母父': row.get('bms_name', '') or '',
                '脚質': _RS_MAP.get(int(fv('running_style')), '?'),
                '近5走平均着': round(fv('avg_finish_5'), 1),
                '近5走複勝率%': round(fv('top3_rate_5') * 100, 0),
                '平均上がり': round(fv('avg_l3f_5'), 1),
                '中日数': int(fv('days_since_last')),
                '同距離走数': int(fv('same_dist_runs')),
                '同距離複勝率%': round(fv('same_dist_top3rate') * 100, 0),
                'ML能力%': round(ml_pct, 1),
                '独自指数': dokuji,
                '総合指数': total,
                **factors,
                **db_info,
            }
            recs.append(rec)

        recs.sort(key=lambda x: -x['総合指数'])
        MARKS = {1: '◎', 2: '○', 3: '▲', 4: '△', 5: '△'}
        for i, r in enumerate(recs):
            r['AI印'] = MARKS.get(i + 1, '')
            r['AI予測順位'] = i + 1
        all_records.extend(recs)

        top3 = recs[:3]
        race_summaries.append({
            'date': date_str, '競馬場': venue, 'R': rno,
            'レース名': ri.get('title', ''), '距離': recs[0]['距離'] if recs else '',
            'グレード': ri.get('grade', ''), '頭数': n,
            '本命': f"{top3[0]['馬番']}番{top3[0]['馬名']}" if top3 else '',
            '本命総合': top3[0]['総合指数'] if top3 else 0,
            '対抗': f"{top3[1]['馬番']}番{top3[1]['馬名']}" if len(top3) > 1 else '',
            '単穴': f"{top3[2]['馬番']}番{top3[2]['馬名']}" if len(top3) > 2 else '',
            '上位差': round(top3[0]['総合指数'] - top3[1]['総合指数'], 1) if len(top3) > 1 else 0,
        })

    hon_hits = sum(1 for s in race_summaries)  # placeholder, 実際の的中率は後段で算出
    log(f"[{date_str}] 完了: {len(race_summaries)}レース / {len(all_records)}頭")
    return {'records': all_records, 'summaries': race_summaries}


def save_day(date_str: str, data: dict):
    out_dir = OUT_ROOT / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'leakfree_records_{date_str}.json'
    cutoff = (datetime.datetime.strptime(date_str, '%Y%m%d') - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    payload = {
        'records': data['records'],
        'summaries': data['summaries'],
        'provenance': {
            'created_at': datetime.datetime.now().isoformat(timespec='seconds'),
            'cutoff_date': cutoff,   # レース日の前日＝この日までの情報のみ使用
            'race_date': date_str,
            'script': VERSION,
            'source': 'db.netkeiba.com (結果非依存再構成) + 本番stats/bloodline/lgb_v44(2026-04-11固定)',
            'leak_free': True,
        },
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=None), encoding='utf-8')
    log(f"[{date_str}] 保存 -> {out_path} ({len(data['records'])}頭 / {len(data['summaries'])}レース)")
    return out_path


_UNFILTERED_DB = {}


def load_cumulative_db_by_name_unfiltered():
    if '_by_name' in _UNFILTERED_DB:
        return _UNFILTERED_DB['_by_name']
    with open(RACE_RESULTS_PATH, encoding='utf-8') as f:
        db = json.load(f)
    by_key = collections.defaultdict(list)
    for e in db:
        key = (e.get('date'), e.get('競馬場'), int(e.get('R', 0)))
        by_key[key].append(e)
    _UNFILTERED_DB['_by_name'] = by_key
    return by_key


def compute_hon_top3_rate(records: list[dict]) -> tuple[int, int]:
    """指定レコード群（1日分）について ◎の3着内率(該当数,3着内数) を返す。
    着順は race_results.json（実測・日付フィルタ不要=事後評価用）から引く。"""
    by_key = load_cumulative_db_by_name_unfiltered()
    by_race = collections.defaultdict(list)
    for r in records:
        by_race[(r['date'], r['競馬場'], r['R'])].append(r)
    total, hit = 0, 0
    for key, recs in by_race.items():
        hon = [r for r in recs if r.get('AI印') == '◎']
        if not hon:
            continue
        results = by_key.get(key, [])
        if not results:
            continue
        result_by_umaban = {}
        for e in results:
            try:
                num = str(int(float(e.get('馬番', -1))))
            except (TypeError, ValueError):
                continue
            ci = e.get('着順int')
            if ci:
                result_by_umaban[num] = ci
        top3_nums = {n for n, c in result_by_umaban.items() if c <= 3}
        if not top3_nums:
            continue
        total += 1
        honban = str(hon[0].get('馬番'))
        if honban in top3_nums:
            hit += 1
    return total, hit


def compute_hon_vs_favorite_match(records: list[dict]) -> tuple[int, int]:
    """◎(AI予測順位1位)が実際の単勝1番人気と一致した割合(一致数, 対象数)を返す。
    事後評価専用（race_results.jsonの確定人気を参照するだけで、予測パスには人気を渡さない）。"""
    by_key = load_cumulative_db_by_name_unfiltered()
    by_race = collections.defaultdict(list)
    for r in records:
        by_race[(r['date'], r['競馬場'], r['R'])].append(r)
    total, match = 0, 0
    for key, recs in by_race.items():
        hon = [r for r in recs if r.get('AI印') == '◎']
        if not hon:
            continue
        results = by_key.get(key, [])
        fav_num = None
        for e in results:
            try:
                ninki = int(float(e.get('人気', -1)))
            except (TypeError, ValueError):
                continue
            if ninki == 1:
                try:
                    fav_num = str(int(float(e.get('馬番', -1))))
                except (TypeError, ValueError):
                    fav_num = None
                break
        if fav_num is None:
            continue
        total += 1
        if str(hon[0].get('馬番')) == fav_num:
            match += 1
    return match, total


# ============================================================
# 6. 既存クリーン日・欠落日の判定（--all-missing）
# ============================================================
def genuine_clean_dates() -> set[str]:
    """本物のレース前records（backfill産の結果リークを除く）がある日付集合。
    engine_backtest.py の drop_leaky と全く同じ判定基準を使う:
    ファイル単位で mtime > 収録レースの「最終日」なら丸ごと backfilled 扱い
    （週末バッチは土日2日分を月曜早朝等にまとめて保存するため、日付単位ではなく
    ファイル単位の「最終収録日」で見る必要がある。日付単位で見ると土曜日分まで
    誤って「汚染」と判定してしまうバグがあったため2026-09-11に修正）。"""
    base = Path.home() / 'Desktop' / '競馬予想レポート'
    clean = set()
    for f in base.glob('**/週末ビッグデータ_*_records.json'):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        recs = d.get('records', [])
        if not recs:
            continue
        dates_in_file = sorted(set(r['date'] for r in recs))
        last_race = max(dates_in_file)
        last_race_d = datetime.date(int(last_race[:4]), int(last_race[4:6]), int(last_race[6:8]))
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).date()
        backfilled = mtime > last_race_d
        if not backfilled:
            clean.update(dates_in_file)
    return clean


def already_backfilled_dates() -> set[str]:
    done = set()
    for f in OUT_ROOT.glob('*/leakfree_records_*.json'):
        m = re.search(r'leakfree_records_(\d{8})\.json', f.name)
        if m:
            done.add(m.group(1))
    return done


def all_missing_dates() -> list[str]:
    payouts = json.loads(PAYOUTS_PATH.read_text(encoding='utf-8'))
    all_dates = sorted(set(v['date'] for v in payouts.values()))
    clean = genuine_clean_dates()
    done = already_backfilled_dates()
    missing = [d for d in all_dates
               if d not in clean and d not in done and d not in EXCLUDED_DATES]
    return missing


# ============================================================
# 7. 検証モード
# ============================================================
def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3 or len(a) != len(b):
        return None
    from scipy.stats import spearmanr
    try:
        rho, _ = spearmanr(a, b)
        if rho != rho:
            return None
        return float(rho)
    except Exception:
        return None


def load_genuine_records_for_date(date_str: str) -> list[dict]:
    """指定日の本物レース前recordsを返す。判定は genuine_clean_dates() と同じ
    ファイル単位の「mtime <= 最終収録日」基準（日付単位ではない。理由は
    genuine_clean_dates() のdocstring参照）。"""
    base = Path.home() / 'Desktop' / '競馬予想レポート'
    out = []
    for f in base.glob('**/週末ビッグデータ_*_records.json'):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        all_recs = d.get('records', [])
        recs = [r for r in all_recs if r.get('date') == date_str]
        if not recs:
            continue
        dates_in_file = sorted(set(r['date'] for r in all_recs))
        last_race = max(dates_in_file)
        last_race_d = datetime.date(int(last_race[:4]), int(last_race[4:6]), int(last_race[6:8]))
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).date()
        if mtime <= last_race_d:
            out.extend(recs)
    return out


VALIDATION_RESULTS_JSON = OUT_ROOT / 'validation_results.json'


def _load_validation_results() -> dict:
    if VALIDATION_RESULTS_JSON.exists():
        try:
            return json.loads(VALIDATION_RESULTS_JSON.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def _write_validation_report(results: dict):
    lines = []
    lines.append(f"# leak-free backfill 照合レポート")
    lines.append(f"")
    lines.append(f"更新: {datetime.datetime.now().isoformat(timespec='seconds')}  script: {VERSION}")
    lines.append(f"")
    lines.append(f"| 日付 | 本物レース数 | 再構築レース数 | Spearman平均 | Spearman中央値 |"
                 f" ◎3着内(本物) | ◎3着内(再構築) | ◎vs1番人気一致率(再構築) |")
    lines.append(f"|---|---|---|---|---|---|---|---|")
    for date_str in sorted(results):
        row = results[date_str]
        lines.append(f"| {date_str} | {row['g_races']} | {row['r_races']} | {row['rho_mean']:.3f} |"
                     f" {row['rho_med']:.3f} | {row['g_rate']} | {row['r_rate']} | {row['match_rate']} |")
    lines.append("")
    lines.append("注: 「◎3着内(再構築)」が「◎3着内(本物)」より **5ポイント以上高い** 場合は"
                 "リークを疑い、原因を特定するまで大量実行しない（指示どおり）。")
    VALIDATION_REPORT.write_text("\n".join(lines), encoding='utf-8')
    log(f"検証レポート保存 -> {VALIDATION_REPORT} ({len(results)}日分)")


def run_validate(dates: list[str], stats, bloodline, name_father_map, name_bms_map,
                  ability_models, db_by_name):
    """1日ずつ結果をJSONに追記保存するため、途中でプロセスが落ちても
    それまでに完了した日の結果は失われない（メモリ逼迫時の再実行に対応）。"""
    results = _load_validation_results()

    for date_str in dates:
        log(f"[VALIDATE {date_str}] 再構築開始")
        genuine = load_genuine_records_for_date(date_str)
        if not genuine:
            log(f"[VALIDATE {date_str}] 本物のrecordsが無い -> スキップ")
            continue
        data = build_day(date_str, stats, bloodline, name_father_map, name_bms_map,
                          ability_models, db_by_name)
        if not data:
            continue
        save_day(date_str, data)   # 検証対象日も同じ形式で保存しておく(load_leakfreeはgenuine優先なので無害)

        rebuilt = data['records']

        # レースごとにSpearman順位相関
        g_by_race = collections.defaultdict(list)
        for r in genuine:
            g_by_race[(r['date'], r['競馬場'], r['R'])].append(r)
        r_by_race = collections.defaultdict(list)
        for r in rebuilt:
            r_by_race[(r['date'], r['競馬場'], r['R'])].append(r)

        rhos = []
        for key, grecs in g_by_race.items():
            rrecs = r_by_race.get(key)
            if not rrecs:
                continue
            g_by_num = {str(r['馬番']): r['AI予測順位'] for r in grecs}
            r_by_num = {str(r['馬番']): r['AI予測順位'] for r in rrecs}
            common = sorted(set(g_by_num) & set(r_by_num), key=lambda x: int(x))
            if len(common) < 3:
                continue
            ga = [g_by_num[n] for n in common]
            rb = [r_by_num[n] for n in common]
            rho = spearman(ga, rb)
            if rho is not None:
                rhos.append(rho)

        g_total, g_hit = compute_hon_top3_rate(genuine)
        r_total, r_hit = compute_hon_top3_rate(rebuilt)
        # ◎(AI予測順位1位) と 市場1番人気(実際の単勝人気1位)の一致率
        # ※前日予測なのでオッズは使わない。ここは事後評価用に確定人気(race_results.json)を参照するだけで
        #   予測パス自体には人気を一切渡していない（F15/F16は常に中立50固定のまま）。
        fav_match_g, fav_total_g = compute_hon_vs_favorite_match(genuine)
        fav_match_r, fav_total_r = compute_hon_vs_favorite_match(rebuilt)

        rho_mean = sum(rhos) / len(rhos) if rhos else 0.0
        rho_med = sorted(rhos)[len(rhos) // 2] if rhos else 0.0
        g_rate = f"{g_hit}/{g_total} ({100*g_hit/g_total:.1f}%)" if g_total else "n/a"
        r_rate = f"{r_hit}/{r_total} ({100*r_hit/r_total:.1f}%)" if r_total else "n/a"
        g_fav = f"{fav_match_g}/{fav_total_g} ({100*fav_match_g/fav_total_g:.1f}%)" if fav_total_g else "n/a"
        r_fav = f"{fav_match_r}/{fav_total_r} ({100*fav_match_r/fav_total_r:.1f}%)" if fav_total_r else "n/a"
        match_rate = f"本物{g_fav} / 再構築{r_fav}"

        results[date_str] = {
            'g_races': len(g_by_race), 'r_races': len(r_by_race),
            'rho_mean': rho_mean, 'rho_med': rho_med,
            'g_rate': g_rate, 'r_rate': r_rate, 'match_rate': match_rate,
            'g_total': g_total, 'g_hit': g_hit, 'r_total': r_total, 'r_hit': r_hit,
        }
        VALIDATION_RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        _write_validation_report(results)
        log(f"[VALIDATE {date_str}] Spearman平均={rho_mean:.3f} ◎3着内 本物={g_rate} 再構築={r_rate}")

    _write_validation_report(results)


# ============================================================
# main
# ============================================================
def load_common():
    log("統計・血統・MLモデルロード（読み取り専用）")
    stats = load_stats()
    bloodline = load_bloodline()
    name_father_map, name_bms_map = load_name_to_id_maps()
    ability_models = [
        lgb.Booster(model_file=str(MODEL_DIR / f'lgb_v44_ability_{i}.txt'))
        for i in range(3)
    ]
    db_by_name = load_cumulative_db_by_name()
    return stats, bloodline, name_father_map, name_bms_map, ability_models, db_by_name


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dates', nargs='+', metavar='YYYYMMDD')
    g.add_argument('--all-missing', action='store_true')
    g.add_argument('--validate', nargs='+', metavar='YYYYMMDD')
    args = ap.parse_args()

    stats, bloodline, name_father_map, name_bms_map, ability_models, db_by_name = load_common()

    if args.validate:
        run_validate(args.validate, stats, bloodline, name_father_map, name_bms_map,
                     ability_models, db_by_name)
        return

    if args.all_missing:
        dates = all_missing_dates()
        log(f"--all-missing: {len(dates)}日分を対象にする: {dates}")
    else:
        dates = [d for d in args.dates if d not in EXCLUDED_DATES]
        skipped = [d for d in args.dates if d in EXCLUDED_DATES]
        if skipped:
            log(f"[SKIP] 学習期間境界のため除外: {skipped}")

    day_stats = []
    for date_str in dates:
        try:
            data = build_day(date_str, stats, bloodline, name_father_map, name_bms_map,
                              ability_models, db_by_name)
        except Exception as e:
            log(f"[ERROR] {date_str} 失敗: {e}\n{traceback.format_exc()}")
            continue
        if not data or not data['records']:
            log(f"[{date_str}] レコードなし -> 保存スキップ")
            continue
        save_day(date_str, data)
        total, hit = compute_hon_top3_rate(data['records'])
        rate = (hit / total * 100) if total else 0.0
        flag = "  ⚠️ 60%超" if rate > 60 else ""
        log(f"[{date_str}] ◎3着内率 = {hit}/{total} ({rate:.1f}%){flag}")
        day_stats.append((date_str, total, hit, rate))

    log(f"完了: {len(day_stats)}日分")
    for date_str, total, hit, rate in day_stats:
        flag = " ⚠️" if rate > 60 else ""
        log(f"  {date_str}: ◎3着内 {hit}/{total} ({rate:.1f}%){flag}")


if __name__ == '__main__':
    main()
