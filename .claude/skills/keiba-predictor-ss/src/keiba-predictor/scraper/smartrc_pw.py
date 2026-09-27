"""smartrc.jp スクレイパー（Playwright版）

Ext.Ajax 経由で JSON API を直接呼び出してデータを取得する。
ログイン不要。ブラウザセッション内の Ext.Ajax を使うことで認証を通過。
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_BASE = "https://www.smartrc.jp/v3/"

# 会場コード → 会場名
_PLACE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}
_PLACE_REV = {v: k for k, v in _PLACE_MAP.items()}
# 英語→コード
_VENUE_EN = {
    "sapporo": "01", "hakodate": "02", "fukushima": "03", "niigata": "04",
    "tokyo": "05", "nakayama": "06", "chukyo": "07", "kyoto": "08",
    "hanshin": "09", "kokura": "10",
}


class SmartRCPlaywright:
    """Playwright + Ext.Ajax で smartrc.jp の JSON API を取得するスクレイパー。"""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._page = None
        self._pw = None
        self._browser = None
        self._ready = False

    # ------------------------------------------------------------------
    # ブラウザ管理
    # ------------------------------------------------------------------

    def _ensure_browser(self) -> None:
        if self._ready:
            return
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        ctx = self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )
        self._page = ctx.new_page()
        self._page.goto(_BASE, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        self._ready = True

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = None
        self._browser = None
        self._pw = None
        self._ready = False

    # ------------------------------------------------------------------
    # API 呼び出し
    # ------------------------------------------------------------------

    def _api_post(self, endpoint: str, params: Dict) -> Dict:
        """Ext.Ajax.request で smartrc API を POST 呼び出しする。"""
        self._ensure_browser()
        result = self._page.evaluate('''
        ([endpoint, paramsStr]) => {
            return new Promise(function(resolve) {
                Ext.Ajax.request({
                    url: '/v3/smartrc.php/' + endpoint,
                    method: 'POST',
                    jsonData: JSON.parse(paramsStr),
                    success: function(r) { resolve(r.responseText); },
                    failure: function(r) { resolve(JSON.stringify({success:false,data:[]})); }
                });
            });
        }
        ''', [endpoint, json.dumps(params)])
        return json.loads(result)

    def fetch_days(self) -> List[Dict]:
        """開催日一覧を取得する。"""
        data = self._api_post("days/view", {"page": 1, "start": 0, "limit": 200})
        return data.get("data", [])

    def fetch_races(self, rdate: str) -> List[Dict]:
        """指定日のレース一覧を取得する。"""
        data = self._api_post("races/view", {"rdate": rdate})
        return data.get("data", [])

    def fetch_runners(self, rcode: str) -> List[Dict]:
        """出走馬データを取得する。"""
        data = self._api_post("runners/view", {"rcode": rcode})
        return data.get("data", [])

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

        print(f"[smartrc] {date} {_PLACE_MAP.get(venue_code, venue_code)} {race_num}R のデータを取得中...")

        # races API でレース一覧を取得
        races = self.fetch_races(date)
        if not races:
            print(f"[smartrc] {date} のレースが見つかりません")
            return None

        # 該当レースの rcode を特定
        target_race = None
        for r in races:
            r_place = r.get("place", "")
            r_rno = r.get("rno", "")
            if r_place == venue_code and str(int(r_rno)) == str(race_num):
                target_race = r
                break

        if target_race is None:
            # rno だけでマッチ（1会場開催の場合）
            for r in races:
                if str(int(r.get("rno", "0"))) == str(race_num):
                    target_race = r
                    break

        if target_race is None:
            print(f"[smartrc] レースが見つかりません: {race_id}")
            return None

        rcode = target_race["rcode"]
        print(f"[smartrc] rcode={rcode} ({target_race.get('name', '')})")

        # runners API で出走馬を取得
        runners_raw = self.fetch_runners(rcode)
        if not runners_raw:
            print(f"[smartrc] 出走馬データが空です（まだ公開前の可能性）")
            return None

        # 整形
        race_info = self._format_race(target_race, date)
        horses = [self._format_runner(r) for r in runners_raw]

        print(f"[smartrc] {len(horses)}頭のデータを取得しました")
        return {"race_info": race_info, "horses": horses}

    def fetch_all_races(self, venue_date: str) -> List[Dict]:
        """開催全レースを取得する。"""
        m = re.match(r"^(\d{8})([a-z]+)$", venue_date)
        if not m:
            # 日付なし → 今日を使う
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

        # 該当会場のレースだけフィルタ
        target_races = [r for r in races if r.get("place") == venue_code]
        if not target_races:
            target_races = races  # フィルタ失敗時は全レース

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
            time.sleep(1)  # サーバー負荷軽減

        return results

    # ------------------------------------------------------------------
    # 入力パース
    # ------------------------------------------------------------------

    def _parse_input(self, race_id: str) -> Tuple[str, str, int]:
        """入力文字列を (date, venue_code, race_num) に分解する。"""
        # rcode 形式 (例: 2026032209011004)
        if re.match(r"^\d{16}$", race_id):
            date = race_id[:8]
            place = race_id[8:10]
            rno = int(race_id[14:16])
            return date, place, rno

        # 英語形式 (例: 20260322hanshin11)
        m = re.match(r"^(\d{8})([a-z]+)(\d{1,2})$", race_id)
        if m:
            date = m.group(1)
            venue = m.group(2)
            race_num = int(m.group(3))
            venue_code = _VENUE_EN.get(venue, venue)
            return date, venue_code, race_num

        # 日本語形式 (例: 20260322阪神11)
        m = re.match(r"^(\d{8})(.+?)(\d{1,2})$", race_id)
        if m:
            date = m.group(1)
            venue_jp = m.group(2)
            race_num = int(m.group(3))
            venue_code = _PLACE_REV.get(venue_jp, venue_jp)
            return date, venue_code, race_num

        raise ValueError(f"不正なレースID形式: {race_id!r}")

    @staticmethod
    def parse_race_id(race_id_str: str) -> Tuple[str, str, int]:
        """互換用: (date, venue_en, race_num) を返す。"""
        m = re.match(r"^(\d{8})([a-z]+)(\d{1,2})$", race_id_str)
        if not m:
            raise ValueError(f"不正なレースID形式: {race_id_str!r}")
        return m.group(1), m.group(2), int(m.group(3))

    # ------------------------------------------------------------------
    # データ整形
    # ------------------------------------------------------------------

    def _format_race(self, r: Dict, date: str) -> Dict:
        """races API のレコードを race_info 形式に変換する。"""
        place_code = r.get("place", "")
        rno = r.get("rno", "")
        venue_name = _PLACE_MAP.get(place_code, place_code)

        # track コードから芝/ダートを判定
        track = r.get("track", "")
        trackkind = r.get("trackkind", "0")
        surface = "ダート" if trackkind == "1" else "芝"

        # 馬場状態
        ground = r.get("ground") or ""
        ground_map = {"0": "良", "1": "稍重", "2": "重", "3": "不良"}
        condition = ground_map.get(ground, ground)

        return {
            "race_id": r.get("rcode", ""),
            "date": date,
            "venue": venue_name,
            "race_num": int(rno) if rno else 0,
            "title": r.get("name", ""),
            "surface": surface,
            "distance": _safe_int(r.get("range")),
            "track_condition": condition,
            "weather": r.get("weather") or "",
            "horse_count": _safe_int(r.get("entry")),
            "grade": r.get("grade", ""),
        }

    def _format_runner(self, r: Dict) -> Dict:
        """runners API のレコードを馬データ形式に変換する。"""
        # 性別コード → 文字
        sex_map = {"1": "牡", "2": "牝", "3": "セ"}
        sex = sex_map.get(r.get("sex"), r.get("sex"))

        # 斤量（10倍値 "570" → 57.0）
        futan_raw = r.get("futan")
        futan = int(futan_raw) / 10 if futan_raw and futan_raw.strip() else None

        # オッズ（10倍値 "2793" → 279.3）
        odds_tan = _safe_int(r.get("odds_tan"))
        win_odds = odds_tan / 10 if odds_tan else None

        # 複勝オッズ
        odds_fuku = _safe_int(r.get("odds_fuku"))
        show_odds = odds_fuku / 10 if odds_fuku else None

        horse: Dict[str, Any] = {
            "horse_id": r.get("hcode"),
            "gate_num": _safe_int(r.get("wno")),     # 枠番
            "horse_num": _safe_int(r.get("uno")),     # 馬番
            "horse_name": (r.get("hname") or "").strip(),
            "sex": sex,
            "age": _safe_int(r.get("age")),
            "weight_carried": futan,
            "jockey": (r.get("jname8") or "").strip(),
            "trainer": (r.get("tname8") or "").strip(),
            "tozai": r.get("tozai"),
            "horse_weight": _safe_int(r.get("weight")),
            "weight_diff": _safe_int(r.get("vary")),
            "win_odds": win_odds,
            "show_odds": show_odds,
            "popularity": _safe_int(r.get("pop_tan")),
            "est_popularity": _safe_int(r.get("est_pop")),
            # CR / TB / 指標
            "cr_value": _safe_float(r.get("cr_value")),
            "ten_has": _safe_float_10(r.get("ten_has")),          # テンハロン（10倍値）
            "ten_has_rank": r.get("ten_has_rank", "").strip(),
            "agari_has": _safe_float_10(r.get("agari_has")),      # 上がりハロン（10倍値）
            "agari_has_rank": r.get("agari_has_rank", "").strip(),
            "ten1f_best": _safe_float_10(r.get("ten1f_best")),    # テン1F最速
            # 血統
            "sire": (r.get("f_name") or "").strip(),
            "sire_line_l": r.get("f_llcode"),
            "sire_line_s": r.get("f_slcode"),
            "sire_line_c": r.get("f_clcode"),
            "sire_country": r.get("f_country"),
            "bms": (r.get("mf_name") or "").strip(),
            "bms_line_l": r.get("mf_llcode"),
            "bms_line_s": r.get("mf_slcode"),
            "bms_line_c": r.get("mf_clcode"),
            # 適性シェア
            "dirt_share": _safe_int(r.get("f_dirt_share")),
            "distance_share": _safe_int(r.get("f_1400_share")),
            # 成績
            "win_rate": _safe_int(r.get("cnt_r1")),
            "place_rate": _safe_int(r.get("cnt_r12")),
            "show_rate": _safe_int(r.get("cnt_r123")),
            "total_races": _safe_int(r.get("cnt_all")),
            # ローテ・経験値
            "rota_type": r.get("rota_type"),
            "rota_eval": (r.get("rota_eval") or "").strip(),
            "old_pr": (r.get("old_pr") or "").strip(),
            # 経験値データ
            "exp_cur_course_cnt": _safe_int(r.get("exp_cur_course_cnt")),
            "exp_cur_course_wi3": _safe_int(r.get("exp_cur_course_wi3")),
        }

        # 人気ランク
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

        # 過去5走
        horse["past_results"] = self._extract_past_results(r)

        return horse

    def _extract_past_results(self, r: Dict) -> List[Dict]:
        """h1_〜h5_ プレフィックスの過去走データを抽出する。"""
        results = []
        for i in range(1, 6):
            p = f"h{i}_"
            rank = r.get(f"{p}rank")
            if rank is None:
                continue  # データなし
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


# ── ヘルパー ──

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
    """10倍整数値を実数に変換する（例: "362" → 36.2）。"""
    n = _safe_int(v)
    if n is None:
        return None
    return n / 10


def _format_time(v) -> Optional[str]:
    """タイム値（10倍整数）を "M:SS.S" 形式に変換する。"""
    n = _safe_int(v)
    if n is None:
        return None
    seconds = n / 10
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    if minutes > 0:
        return f"{minutes}:{secs:04.1f}"
    return f"{secs:.1f}"
