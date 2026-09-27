"""smartrc.jp スクレイパー（API直接版）

Playwright / Chromium 不要。requests のみで JSON API を取得する。
Renderデプロイ・携帯からのアクセスに対応。
キャッシュ機能: 一度取得したデータはローカルに保存しBAN対策。
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_BASE = "https://www.smartrc.jp/v3/"
_API = "https://www.smartrc.jp/v3/smartrc.php/"
_SSO = "https://www.smartrc.jp/sso_agent/sso/spget"

# 会場コード
_PLACE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}
_PLACE_REV = {v: k for k, v in _PLACE_MAP.items()}
_VENUE_EN = {
    "sapporo": "01", "hakodate": "02", "fukushima": "03", "niigata": "04",
    "tokyo": "05", "nakayama": "06", "chukyo": "07", "kyoto": "08",
    "hanshin": "09", "kokura": "10",
}


_CACHE_DIR = Path(__file__).resolve().parent.parent / "_cache"


class SmartRCAPI:
    """requests のみで smartrc.jp API を取得するスクレイパー。
    キャッシュ機能付き: 同じリクエストを2度送らない。"""

    # レート制限: 最低2秒間隔
    _MIN_INTERVAL = 2.0

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "Referer": _BASE,
            "Origin": "https://www.smartrc.jp",
            "X-Requested-With": "XMLHttpRequest",
        })
        self._initialized = False
        self._last_request_time = 0.0
        # キャッシュ初期化
        _CACHE_DIR.mkdir(exist_ok=True)
        self._races_cache: Dict[str, List[Dict]] = {}
        self._runners_cache: Dict[str, List[Dict]] = {}
        self._load_cache()

    # ------------------------------------------------------------------
    # キャッシュ管理
    # ------------------------------------------------------------------

    def _load_cache(self) -> None:
        """ローカルキャッシュを読み込む。"""
        races_path = _CACHE_DIR / "smartrc_races.json"
        runners_path = _CACHE_DIR / "smartrc_runners.json"
        if races_path.exists():
            try:
                self._races_cache = json.loads(races_path.read_text(encoding="utf-8"))
            except Exception:
                self._races_cache = {}
        if runners_path.exists():
            try:
                self._runners_cache = json.loads(runners_path.read_text(encoding="utf-8"))
            except Exception:
                self._runners_cache = {}

    def save_cache(self) -> None:
        """キャッシュをファイルに保存する。close()時に自動呼び出し。"""
        _CACHE_DIR.mkdir(exist_ok=True)
        races_path = _CACHE_DIR / "smartrc_races.json"
        runners_path = _CACHE_DIR / "smartrc_runners.json"
        races_path.write_text(json.dumps(self._races_cache, ensure_ascii=False), encoding="utf-8")
        runners_path.write_text(json.dumps(self._runners_cache, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # セッション・API
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """最低間隔を守る。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._MIN_INTERVAL:
            time.sleep(self._MIN_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _ensure_session(self) -> None:
        """セッションを初期化する（初回のみ）。"""
        if self._initialized:
            return
        try:
            self._session.get(_BASE, timeout=15)
            self._session.post(_SSO, timeout=15)
            self._initialized = True
        except Exception as e:
            logger.warning("セッション初期化失敗: %s", e)

    def _api_post(self, endpoint: str, params: Dict) -> Dict:
        """smartrc API を POST で呼び出す（レートリミット付き）。"""
        self._ensure_session()
        self._rate_limit()
        try:
            resp = self._session.post(
                f"{_API}{endpoint}",
                json=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("API呼び出し失敗 %s: %s", endpoint, e)
            return {"success": False, "data": []}

    # ------------------------------------------------------------------
    # API メソッド
    # ------------------------------------------------------------------

    def fetch_days(self) -> List[Dict]:
        """開催日一覧を取得する。"""
        data = self._api_post("days/view", {"page": 1, "start": 0, "limit": 200})
        return data.get("data", [])

    def fetch_races(self, rdate: str) -> List[Dict]:
        """指定日のレース一覧を取得する（キャッシュ優先）。"""
        if rdate in self._races_cache:
            return self._races_cache[rdate]
        data = self._api_post("races/view", {"rdate": rdate})
        result = data.get("data", [])
        if result:
            self._races_cache[rdate] = result
        return result

    def fetch_runners(self, rcode: str) -> List[Dict]:
        """出走馬データを取得する（キャッシュ優先）。"""
        if rcode in self._runners_cache:
            return self._runners_cache[rcode]
        data = self._api_post("runners/view", {"rcode": rcode})
        result = data.get("data", [])
        if result:
            self._runners_cache[rcode] = result
        return result

    # ------------------------------------------------------------------
    # 公開メソッド（pipeline.py 互換）
    # ------------------------------------------------------------------

    def fetch_race_card(self, race_id: str) -> Optional[Dict]:
        """出馬表データを取得する。

        Parameters
        ----------
        race_id:
            '20260322hanshin11' 形式 または rcode 直指定。
        """
        date, venue_code, race_num = self._parse_input(race_id)
        venue_name = _PLACE_MAP.get(venue_code, venue_code)

        print(f"[smartrc] {date} {venue_name} {race_num}R のデータを取得中...")

        races = self.fetch_races(date)
        if not races:
            print(f"[smartrc] {date} のレースが見つかりません")
            return None

        # 該当レースの rcode を特定
        target_race = None
        for r in races:
            if r.get("place") == venue_code and str(int(r.get("rno", "0"))) == str(race_num):
                target_race = r
                break
        if target_race is None:
            for r in races:
                if str(int(r.get("rno", "0"))) == str(race_num):
                    target_race = r
                    break
        if target_race is None:
            print(f"[smartrc] レースが見つかりません: {race_id}")
            return None

        rcode = target_race["rcode"]
        print(f"[smartrc] rcode={rcode} ({target_race.get('name', '')})")

        runners_raw = self.fetch_runners(rcode)
        if not runners_raw:
            print("[smartrc] 出走馬データが空です（まだ公開前の可能性）")
            return None

        race_info = self._format_race(target_race, date)
        horses = [self._format_runner(r) for r in runners_raw]

        print(f"[smartrc] {len(horses)}頭のデータを取得しました")
        return {"race_info": race_info, "horses": horses}

    def fetch_all_races(self, venue_date: str) -> List[Dict]:
        """開催全レースを取得する。"""
        m = re.match(r"^(\d{8})([a-z]+)$", venue_date)
        if not m:
            from datetime import date as dt_date
            today = dt_date.today().strftime("%Y%m%d")
            venue_date = today + venue_date
            m = re.match(r"^(\d{8})([a-z]+)$", venue_date)
            if not m:
                print(f"[ERROR] 不正な形式: {venue_date}")
                return []

        date = m.group(1)
        venue = m.group(2)
        venue_code = _VENUE_EN.get(venue, venue)

        races = self.fetch_races(date)
        if not races:
            print(f"[smartrc] {date} のレースが見つかりません")
            return []

        target_races = [r for r in races if r.get("place") == venue_code]
        if not target_races:
            target_races = races

        results = []
        for race in target_races:
            rcode = race["rcode"]
            rno = race.get("rno", "?")
            name = race.get("name", "")
            print(f"  {rno}R {name}: ", end="", flush=True)

            runners_raw = self.fetch_runners(rcode)
            if not runners_raw:
                print("データなし")
                continue

            race_info = self._format_race(race, date)
            horses = [self._format_runner(r) for r in runners_raw]
            results.append({"race_info": race_info, "horses": horses})
            print(f"{len(horses)}頭")
            time.sleep(1)

        return results

    def close(self) -> None:
        """セッションを閉じてキャッシュを保存する。"""
        self.save_cache()
        self._session.close()

    # ------------------------------------------------------------------
    # 入力パース
    # ------------------------------------------------------------------

    def _parse_input(self, race_id: str) -> Tuple[str, str, int]:
        if re.match(r"^\d{16}$", race_id):
            return race_id[:8], race_id[8:10], int(race_id[14:16])
        m = re.match(r"^(\d{8})([a-z]+)(\d{1,2})$", race_id)
        if m:
            return m.group(1), _VENUE_EN.get(m.group(2), m.group(2)), int(m.group(3))
        m = re.match(r"^(\d{8})(.+?)(\d{1,2})$", race_id)
        if m:
            return m.group(1), _PLACE_REV.get(m.group(2), m.group(2)), int(m.group(3))
        raise ValueError(f"不正なレースID形式: {race_id!r}")

    @staticmethod
    def parse_race_id(race_id_str: str) -> Tuple[str, str, int]:
        m = re.match(r"^(\d{8})([a-z]+)(\d{1,2})$", race_id_str)
        if not m:
            raise ValueError(f"不正なレースID形式: {race_id_str!r}")
        return m.group(1), m.group(2), int(m.group(3))

    # ------------------------------------------------------------------
    # データ整形（smartrc_pw.py と同一ロジック）
    # ------------------------------------------------------------------

    def _format_race(self, r: Dict, date: str) -> Dict:
        place_code = r.get("place", "")
        rno = r.get("rno", "")
        trackkind = r.get("trackkind", "0")
        surface = "ダート" if trackkind == "1" else "芝"
        ground = r.get("ground") or ""
        ground_map = {"0": "良", "1": "稍重", "2": "重", "3": "不良"}
        return {
            "race_id": r.get("rcode", ""),
            "date": date,
            "venue": _PLACE_MAP.get(place_code, place_code),
            "race_num": int(rno) if rno else 0,
            "title": r.get("name", ""),
            "surface": surface,
            "distance": _safe_int(r.get("range")),
            "track_condition": ground_map.get(ground, ground),
            "weather": r.get("weather") or "",
            "horse_count": _safe_int(r.get("entry")),
            "grade": r.get("grade", ""),
            "week": _safe_int(r.get("week")),  # PDCA32: 開催何週目か
        }

    def _format_runner(self, r: Dict) -> Dict:
        sex_map = {"1": "牡", "2": "牝", "3": "セ"}
        sex = sex_map.get(r.get("sex"), r.get("sex"))
        futan_raw = r.get("futan")
        futan = int(futan_raw) / 10 if futan_raw and str(futan_raw).strip() else None
        odds_tan = _safe_int(r.get("odds_tan"))
        win_odds = odds_tan / 10 if odds_tan else None
        odds_fuku = _safe_int(r.get("odds_fuku"))
        show_odds = odds_fuku / 10 if odds_fuku else None

        horse: Dict[str, Any] = {
            "horse_id": r.get("hcode"),
            "gate_num": _safe_int(r.get("wno")),
            "horse_num": _safe_int(r.get("uno")),
            "horse_name": (r.get("hname") or "").strip(),
            "sex": sex,
            "age": _safe_int(r.get("age")),
            "weight_carried": futan,
            "jockey": (r.get("jname8") or "").strip(),
            "trainer": (r.get("tname8") or "").strip(),
            "tozai": r.get("tozai"),  # 東西所属 1=東(美浦), 2=西(栗東)
            "horse_weight": _safe_int(r.get("weight")),
            "weight_diff": _safe_int(r.get("vary")),
            "win_odds": win_odds,
            "show_odds": show_odds,
            "popularity": _safe_int(r.get("pop_tan")),
            "est_popularity": _safe_int(r.get("est_pop")),
            "cr_value": _safe_float(r.get("cr_value")),
            "ten_has": _safe_float_10(r.get("ten_has")),
            "ten_has_rank": (r.get("ten_has_rank") or "").strip(),
            "agari_has": _safe_float_10(r.get("agari_has")),
            "agari_has_rank": (r.get("agari_has_rank") or "").strip(),
            "ten1f_best": _safe_float_10(r.get("ten1f_best")),
            "sire": (r.get("f_name") or "").strip(),
            "sire_line_l": r.get("f_llcode"),
            "sire_line_s": r.get("f_slcode"),
            "sire_line_c": r.get("f_clcode"),
            "sire_country": r.get("f_country"),
            "bms": (r.get("mf_name") or "").strip(),
            "bms_line_l": r.get("mf_llcode"),
            "bms_line_s": r.get("mf_slcode"),
            "bms_line_c": r.get("mf_clcode"),
            "dirt_share": _safe_int(r.get("f_dirt_share")),
            "distance_share": _safe_int(r.get("f_1400_share")),
            "win_rate": _safe_int(r.get("cnt_r1")),
            "place_rate": _safe_int(r.get("cnt_r12")),
            "show_rate": _safe_int(r.get("cnt_r123")),
            "total_races": _safe_int(r.get("cnt_all")),
            "rota_type": r.get("rota_type"),
            "rota_eval": (r.get("rota_eval") or "").strip(),
            "old_pr": (r.get("old_pr") or "").strip(),
            "exp_cur_course_cnt": _safe_int(r.get("exp_cur_course_cnt")),
            "exp_cur_course_wi3": _safe_int(r.get("exp_cur_course_wi3")),
            # PDCA20: 距離延長/短縮/同距離の経験値
            "exp_cur_short_cnt": _safe_int(r.get("exp_cur_short_cnt")),
            "exp_cur_short_wi3": _safe_int(r.get("exp_cur_short_wi3")),
            "exp_cur_long_cnt": _safe_int(r.get("exp_cur_long_cnt")),
            "exp_cur_long_wi3": _safe_int(r.get("exp_cur_long_wi3")),
            "exp_cur_same_cnt": _safe_int(r.get("exp_cur_same_cnt")),
            "exp_cur_same_wi3": _safe_int(r.get("exp_cur_same_wi3")),
            # 乗り替わり検出用
            "jcode": r.get("jcode"),
            "jcode_before": r.get("jcode_before"),
            # ブリンカー
            "blinker": r.get("blinker"),
        }

        pop = horse["popularity"] or horse["est_popularity"]
        if pop is not None:
            if pop <= 2:
                horse["popularity_rank"] = "A"
            elif pop <= 4:
                horse["popularity_rank"] = "B"
            elif pop <= 7:
                horse["popularity_rank"] = "C"
            elif pop <= 10:
                horse["popularity_rank"] = "D"
            else:
                horse["popularity_rank"] = "E"
        else:
            horse["popularity_rank"] = None

        horse["past_results"] = self._extract_past_results(r)
        return horse

    def _extract_past_results(self, r: Dict) -> List[Dict]:
        results = []
        for i in range(1, 6):
            p = f"h{i}_"
            rank = r.get(f"{p}rank")
            if rank is None:
                continue
            results.append({
                "finish": _safe_int(rank),
                "distance": _safe_int(r.get(f"{p}range")),
                "last_3f": _safe_float_10(r.get(f"{p}furlong3")),
                "time": _format_time(r.get(f"{p}stime")),
                "popularity": _safe_int(r.get(f"{p}pop")),
                "grade": (r.get(f"{p}grade") or "").strip(),
                "condition": (r.get(f"{p}cond") or "").strip(),
                "horse_count": _safe_int(r.get(f"{p}kscode")),
                "corner1": r.get(f"{p}corner1"),
                "corner2": r.get(f"{p}corner2"),
                "corner3": r.get(f"{p}corner3"),
                "corner4": r.get(f"{p}corner4"),
                "diff_time": _safe_float_10(r.get(f"{p}difftime")),
                "interval": _safe_int(r.get(f"{p}interval")),
                "weight": _safe_int(r.get(f"{p}weight")),
                "tb_io": r.get(f"{p}tb_io"),
                "tb_diff": r.get(f"{p}tb_diff"),
                "ten_1f": _safe_float_10(r.get(f"{p}ten1f")),
                "rcode": r.get(f"{p}rcode"),
                "name": (r.get(f"{p}name") or "").strip(),
            })
        return results


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(re.sub(r"[^\d\-]", "", s))
    except (ValueError, TypeError):
        return None


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(re.sub(r"[^\d.\-]", "", s))
    except (ValueError, TypeError):
        return None


def _safe_float_10(v) -> Optional[float]:
    n = _safe_int(v)
    if n is None:
        return None
    return n / 10


def _format_time(v) -> Optional[str]:
    n = _safe_int(v)
    if n is None:
        return None
    seconds = n / 10
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    if minutes > 0:
        return f"{minutes}:{secs:04.1f}"
    return f"{secs:.1f}"
