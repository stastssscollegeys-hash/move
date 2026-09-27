"""netkeiba.com スクレイパー — 出馬表 + 過去レース結果取得

race_id: YYYYCCDDNNRR (12桁)
  YYYY=年, CC=競馬場(01-10), DD=開催日(01-), NN=開催回(01-), RR=レース番号(01-12)

競馬場コード: 01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉

出馬表取得（前日可能）:
  - race.netkeiba.com/race/shutuba.html?race_id=YYYYPPKKNNRR
  - 木曜夜以降に週末レースの出馬表が公開される
  - オッズはJSONエンドポイントから取得可能
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE = "https://db.netkeiba.com"
_RACE_BASE = "https://race.netkeiba.com"

_VENUE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
}


class NetkeibaScaper:
    """netkeiba.com から出馬表・過去レース結果を取得するスクレイパー。"""

    _CACHE_DIR = Path(__file__).resolve().parent.parent / "_cache" / "netkeiba"

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
            "Referer": "https://www.netkeiba.com/",
        })
        # ディスク永続化キャッシュ
        self._CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._horse_cache: Dict[str, List[Dict]] = self._load_disk_cache("horse_past.json")
        self._profile_cache: Dict[str, Dict] = self._load_disk_cache("horse_profile.json")
        self._shutuba_cache: Dict[str, Dict] = self._load_disk_cache("shutuba.json")

    def _load_disk_cache(self, filename: str) -> Dict:
        path = self._CACHE_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_disk_cache(self, filename: str, data: Dict) -> None:
        path = self._CACHE_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # ==================================================================
    # 出馬表取得（前日予測用）
    # ==================================================================

    def fetch_shutuba(self, race_id: str) -> Optional[Dict]:
        """出馬表ページ(shutuba.html)を取得してパースする。前日から取得可能。

        Parameters
        ----------
        race_id: 12桁のレースID (例: 202609020611)

        Returns
        -------
        {"race_info": {...}, "horses": [...]} or None
        """
        if race_id in self._shutuba_cache:
            return self._shutuba_cache[race_id]

        url = f"{_RACE_BASE}/race/shutuba.html?race_id={race_id}"
        time.sleep(2)

        try:
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning("shutuba %s: status %d", race_id, resp.status_code)
                return None
            resp.encoding = resp.apparent_encoding or "euc-jp"
        except Exception as e:
            logger.warning("shutuba %s: %s", race_id, e)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        race_info = self._parse_shutuba_race_info(soup, race_id)
        if not race_info:
            return None

        horses = self._parse_shutuba_table(soup)
        if not horses:
            return None

        result = {"race_info": race_info, "horses": horses}
        self._shutuba_cache[race_id] = result
        return result

    def _parse_shutuba_race_info(self, soup: BeautifulSoup, race_id: str) -> Optional[Dict]:
        """出馬表ページからレース情報を抽出する。"""
        try:
            rd1 = soup.select_one(".RaceData01")
            rd2 = soup.select_one(".RaceData02")
            rd1_text = rd1.get_text(" ", strip=True) if rd1 else ""
            rd2_text = rd2.get_text(" ", strip=True) if rd2 else ""

            # 距離
            dist_m = re.search(r"(\d{3,4})m", rd1_text)
            distance = int(dist_m.group(1)) if dist_m else 0

            # 芝/ダート
            surface = "ダート" if "ダ" in rd1_text else "芝"

            # 馬場状態（当日のみ、前日はなし）
            condition = ""
            for cond in ["不良", "重", "稍重", "良"]:
                if cond in rd1_text:
                    condition = cond
                    break

            # 天候
            weather = ""
            for w in ["晴", "曇", "雨", "小雨", "雪", "小雪"]:
                if w in rd1_text:
                    weather = w
                    break

            # 開催情報（回・場・日目）
            kai_m = re.search(r"(\d+)回\s*(\S+?)\s*(\d+)日目", rd2_text)
            venue_name = kai_m.group(2) if kai_m else ""

            # 頭数
            tosu_m = re.search(r"(\d+)頭", rd2_text)
            horse_count = int(tosu_m.group(1)) if tosu_m else 0

            # 賞金（万円）
            prize_m = re.search(r"本賞金[:：]([0-9,]+)", rd2_text)
            prize_1 = 0
            if prize_m:
                prizes = prize_m.group(1).split(",")
                if prizes:
                    try:
                        prize_1 = int(prizes[0])  # 1着賞金（万円）
                    except ValueError:
                        pass

            # グレード
            grade = ""
            title_el = soup.select_one("title")
            title_text = title_el.get_text(strip=True) if title_el else ""
            for g in ["(G1)", "(G2)", "(G3)", "(L)"]:
                if g in title_text:
                    grade = g.strip("()")
                    break

            # venue_cd from race_id
            venue_cd = int(race_id[4:6]) if len(race_id) >= 6 else 0

            return {
                "race_id": race_id,
                "distance": distance,
                "surface": surface,
                "condition": condition,
                "weather": weather,
                "venue_name": venue_name,
                "venue_cd": venue_cd,
                "horse_count": horse_count,
                "prize_1": prize_1,
                "grade": grade,
                "title": title_text.split("出馬表")[0].strip() if "出馬表" in title_text else "",
            }
        except Exception as e:
            logger.warning("shutuba race_info parse error: %s", e)
            return None

    def _parse_shutuba_table(self, soup: BeautifulSoup) -> List[Dict]:
        """出馬表テーブルから馬情報を抽出する。"""
        horses = []
        table = soup.select_one("table.Shutuba_Table")
        if not table:
            return horses

        rows = table.select("tr.HorseList")
        for idx, row in enumerate(rows):
            cells = row.select("td")
            if len(cells) < 8:
                continue
            try:
                # 枠番・馬番（JS描画のためtextが空の場合は行インデックスで補完）
                waku = _safe_int(cells[0].get_text(strip=True))
                umaban = _safe_int(cells[1].get_text(strip=True)) or (idx + 1)

                # 馬名・horse_id
                horse_cell = cells[3]
                horse_link = horse_cell.select_one('a[href*="/horse/"]')
                horse_name = horse_link.get_text(strip=True) if horse_link else ""
                horse_id = ""
                if horse_link:
                    m = re.search(r"/horse/(\w+)", horse_link.get("href", ""))
                    if m:
                        horse_id = m.group(1)

                # 性齢
                sex_age = cells[4].get_text(strip=True)
                sex_cd = 0
                age = 0
                if sex_age:
                    sex_map = {"牡": 1, "牝": 2, "セ": 3}
                    sex_cd = sex_map.get(sex_age[0], 0)
                    age_m = re.search(r"(\d+)", sex_age)
                    age = int(age_m.group(1)) if age_m else 0

                # 斤量
                futan = _safe_float(cells[5].get_text(strip=True))

                # 騎手ID
                jockey_cell = cells[6]
                jockey_link = jockey_cell.select_one('a[href*="jockey"]')
                jockey_id = ""
                if jockey_link:
                    m = re.search(r"/jockey/(?:result/recent/)?(\w+)", jockey_link.get("href", ""))
                    if m:
                        jockey_id = m.group(1)

                # 調教師ID
                trainer_cell = cells[7]
                trainer_link = trainer_cell.select_one('a[href*="trainer"]')
                trainer_id = ""
                if trainer_link:
                    m = re.search(r"/trainer/(?:result/recent/)?(\w+)", trainer_link.get("href", ""))
                    if m:
                        trainer_id = m.group(1)

                # 馬体重（当日のみ）
                weight_text = cells[8].get_text(strip=True) if len(cells) > 8 else ""
                horse_weight = 0
                weight_diff = 0
                w_m = re.match(r"(\d+)\(([+\-]?\d+)\)", weight_text)
                if w_m:
                    horse_weight = int(w_m.group(1))
                    weight_diff = int(w_m.group(2))

                horses.append({
                    "waku": waku,
                    "umaban": umaban,
                    "horse_name": horse_name,
                    "horse_id": horse_id,  # = ketto_num
                    "sex_cd": sex_cd,
                    "age": age,
                    "futan": futan,
                    "jockey_id": jockey_id,
                    "trainer_id": trainer_id,
                    "horse_weight": horse_weight,
                    "weight_diff": weight_diff,
                })
            except Exception:
                continue
        return horses

    def fetch_horse_past(self, horse_id: str, max_races: int = 5) -> List[Dict]:
        """馬の過去走データを取得する（キャッシュ付き）。

        Parameters
        ----------
        horse_id: 馬ID (ketto_num形式, 例: 2023107265)
        max_races: 取得する最大レース数
        """
        if horse_id in self._horse_cache:
            return self._horse_cache[horse_id][:max_races]

        # /horse/result/ID/ が戦績ページ（/horse/ID/ はプロフィールのみ）
        url = f"{_BASE}/horse/result/{horse_id}/"
        time.sleep(2)

        try:
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                return []
            resp.encoding = resp.apparent_encoding or "euc-jp"
        except Exception:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = self._parse_horse_results(soup)
        self._horse_cache[horse_id] = results
        return results[:max_races]

    def _parse_horse_results(self, soup: BeautifulSoup) -> List[Dict]:
        """馬の戦績テーブルをパースする。

        /horse/result/ID/ ページの db_h_race_results テーブル。
        カラム構造（33列）:
          [0]日付 [1]開催 [2]天気 [3]R [4]レース名 [5]映像 [6]頭数
          [7]枠番 [8]馬番 [9]オッズ [10]人気 [11]着順 [12]騎手 [13]斤量
          [14]距離 [15]水分量 [16]馬場 [17]馬場指数 [18]タイム [19]着差
          ... [24]上がり指数
        ※ヘッダーの順序はnetkeiba側の仕様変更で変わる可能性あり
        """
        results = []
        table = soup.select_one("table.db_h_race_results")
        if not table:
            return results

        # ヘッダーからカラムインデックスを動的に特定
        header_row = table.select_one("tr")
        col_map = {}
        if header_row:
            for i, th in enumerate(header_row.select("th, td")):
                text = th.get_text(strip=True)
                if text == "着順":
                    col_map["rank"] = i
                elif text == "距離":
                    col_map["distance"] = i
                elif text == "馬場":
                    col_map["baba"] = i
                elif text == "タイム":
                    col_map["time"] = i
                elif text == "頭数":
                    col_map["tosu"] = i
                # ↓ 2026-09-04 追加。監査で「取得できるのに保持していない」と判明した列
                elif text == "日付":
                    col_map["date"] = i
                elif text == "人気":
                    col_map["ninki"] = i
                elif text == "オッズ":
                    col_map["odds"] = i
                elif text == "着差":
                    col_map["margin"] = i
                elif text == "レース名":
                    col_map["race_name"] = i
                elif text == "枠番":
                    col_map["waku"] = i

        # フォールバック: 固定インデックス
        rank_idx = col_map.get("rank", 11)
        dist_idx = col_map.get("distance", 14)
        baba_idx = col_map.get("baba", 16)
        time_idx = col_map.get("time", 18)
        tosu_idx = col_map.get("tosu", 6)
        date_idx = col_map.get("date", 0)
        ninki_idx = col_map.get("ninki", 10)
        odds_idx = col_map.get("odds", 9)
        margin_idx = col_map.get("margin", 19)
        rname_idx = col_map.get("race_name", 4)
        waku_idx = col_map.get("waku", 7)

        rows = table.select("tr")
        for row in rows[1:]:  # skip header
            cells = row.select("td")
            if len(cells) < 15:
                continue
            try:
                rank = _safe_int(cells[rank_idx].get_text(strip=True))
                if rank is None or rank <= 0:
                    continue

                # 距離 (例: "芝1400", "ダ1200")
                dist_text = cells[dist_idx].get_text(strip=True)
                surface_char = dist_text[0] if dist_text else ""
                dist_val = _safe_int(re.sub(r"[^\d]", "", dist_text))
                trackkind = 1 if surface_char == "芝" else 2

                # 馬場状態
                baba_text = cells[baba_idx].get_text(strip=True) if len(cells) > baba_idx else ""
                baba_map = {"良": "A", "稍": "B", "重": "C", "不": "D"}
                fr_baba = baba_map.get(baba_text[:1], "A") if baba_text else "A"

                # タイム (M:SS.S形式)
                time_text = cells[time_idx].get_text(strip=True) if len(cells) > time_idx else ""
                stime = None
                tm = re.match(r"(\d+):(\d+\.\d+)", time_text)
                if tm:
                    stime = float(tm.group(1)) * 60 + float(tm.group(2))

                # 上り3F: ヘッダー「上り」（「上がり指数」ではない）
                l3f = None
                for ci, th in enumerate(header_row.select("th, td") if header_row else []):
                    th_text = th.get_text(strip=True)
                    if th_text == "上り":
                        if len(cells) > ci:
                            l3f = _safe_float(cells[ci].get_text(strip=True))
                        break

                # 通過順: ヘッダー「通過」
                corner4 = None
                for ci, th in enumerate(header_row.select("th, td") if header_row else []):
                    if th.get_text(strip=True) == "通過":
                        if len(cells) > ci:
                            passing = cells[ci].get_text(strip=True)
                            corners = passing.split("-")
                            corner4 = _safe_int(corners[-1]) if corners else None
                        break

                horse_count = _safe_int(cells[tosu_idx].get_text(strip=True))

                def cell(i):
                    return cells[i].get_text(strip=True) if len(cells) > i else ""

                results.append({
                    "rank": rank,
                    "distance": dist_val,
                    "trackkind": trackkind,
                    "fr_baba": fr_baba,
                    "last_3f": l3f,
                    "stime": stime,
                    "corner4": corner4,
                    "horse_count": horse_count,
                    # ── 2026-09-04 追加 ──
                    # date は中日数(days_since_last)の算出に必須。
                    # 従来は日付を保持しておらず、この因子が7,235頭すべて0だった。
                    "date": cell(date_idx),                    # 'YYYY/MM/DD'
                    "ninki": _safe_int(cell(ninki_idx)),
                    "odds": _safe_float(cell(odds_idx)),
                    "margin": cell(margin_idx),
                    "race_name": cell(rname_idx),
                    "waku": _safe_int(cell(waku_idx)),
                })
            except Exception:
                continue
        return results

    def fetch_horse_profile(self, horse_id: str) -> Dict:
        """馬のプロフィールページから父・母父の名前とnetkeiba horse_idを取得する。

        db.netkeiba.com/horse/{horse_id}/ ページ:
        - db_prof_table: 基本情報（生年月日・調教師等）
        - blood_table: 血統表（5×4の血統ツリー）

        血統表の構造:
          列0: 馬本人（1セル）
          列1: 父・母（2セル）
          列2: 父父・父母・母父・母母（4セル）
          列3: 更に祖先（8セル）
          列4: 更に祖先（16セル）

        → 父は列1の1番目セル、母父は列2の3番目セル

        Returns
        -------
        dict with keys:
          father_name: str  (父の名前)
          father_nk_id: str (父のnetkeiba horse_id、例: "2009110034")
          bms_name: str     (母父の名前)
          bms_nk_id: str    (母父のnetkeiba horse_id)
        """
        if horse_id in self._profile_cache:
            return self._profile_cache[horse_id]

        # blood_tableは /horse/ped/{id}/ (血統ページ) にしかない
        url = f"{_BASE}/horse/ped/{horse_id}/"
        time.sleep(2)

        try:
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning("fetch_horse_profile %s: status %d", horse_id, resp.status_code)
                return {}
            resp.encoding = resp.apparent_encoding or "euc-jp"
        except Exception as e:
            logger.warning("fetch_horse_profile %s: %s", horse_id, e)
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        result = {}

        # 血統テーブル（blood_table）から父・母父を取得
        # 5代血統表のrowspan:
        #   16 → 父/母（generation 0）
        #    8 → 父父/父母/母父/母母（generation 1）
        #    4 → generation 2
        blood_table = soup.select_one("table.blood_table")
        if blood_table:
            gen0_cells = []  # rowspan=16: 父, 母
            gen1_cells = []  # rowspan=8: 父父, 父母, 母父, 母母

            for td in blood_table.select("td"):
                rs_int = int(td.get("rowspan", "1") or "1")

                link = td.select_one('a[href*="/horse/"]')
                if not link:
                    continue

                name = link.get_text(strip=True)
                href = link.get("href", "")
                m = re.search(r"/horse/(?:ped/)?(\w+)/?$", href)
                nk_id = m.group(1) if m else ""

                if rs_int >= 16:
                    gen0_cells.append((name, nk_id))
                elif rs_int >= 8:
                    gen1_cells.append((name, nk_id))

            # 父: gen0_cells[0]
            if gen0_cells:
                result["father_name"] = gen0_cells[0][0]
                result["father_nk_id"] = gen0_cells[0][1]

            # 母父: gen1_cells[2] (父父=0, 父母=1, 母父=2, 母母=3)
            if len(gen1_cells) >= 3:
                result["bms_name"] = gen1_cells[2][0]
                result["bms_nk_id"] = gen1_cells[2][1]

        self._profile_cache[horse_id] = result
        return result

    def fetch_horse_blood(self, horse_id: str) -> Dict:
        """馬の血統情報（父・母父ID）を取得する。

        db.netkeiba.com/horse/{horse_id}/ ページの血統リンクから取得。
        fetch_horse_profile() の旧API互換ラッパー。
        """
        return self.fetch_horse_profile(horse_id)

    # ==================================================================
    # 過去レース結果取得（既存機能）
    # ==================================================================

    def fetch_race_result(self, race_id: str) -> Optional[Dict]:
        """レース結果ページを取得してパースする。

        Parameters
        ----------
        race_id: 12桁のレースID (例: 202506010101)
        """
        url = f"{_BASE}/race/{race_id}/"
        time.sleep(2)  # サーバー負荷軽減

        try:
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning("netkeiba %s: status %d", race_id, resp.status_code)
                return None
            resp.encoding = resp.apparent_encoding or "euc-jp"
        except Exception as e:
            logger.warning("netkeiba %s: %s", race_id, e)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # レース情報
        race_info = self._parse_race_info(soup, race_id)
        if not race_info:
            return None

        # 結果テーブル
        results = self._parse_results_table(soup)

        return {"race_info": race_info, "results": results}

    def _parse_race_info(self, soup: BeautifulSoup, race_id: str) -> Optional[Dict]:
        """レース情報をパースする。"""
        try:
            title_el = soup.select_one("title")
            title = title_el.get_text(strip=True).split("｜")[0] if title_el else ""

            info_el = soup.select_one(".racedata, .data_intro")
            info_text = info_el.get_text(" ", strip=True) if info_el else ""

            dist_match = re.search(r"(\d{3,4})m", info_text)
            distance = int(dist_match.group(1)) if dist_match else None
            surface = "ダート" if "ダ" in info_text and "芝" not in info_text else "芝"
            condition = "良"
            for cond in ["不良", "重", "稍重", "良"]:
                if cond in info_text:
                    condition = cond
                    break

            return {"race_id": race_id, "title": title, "distance": distance,
                    "surface": surface, "condition": condition}
        except Exception as e:
            logger.warning("race_info parse error: %s", e)
            return None

    def _parse_results_table(self, soup: BeautifulSoup) -> List[Dict]:
        """結果テーブル（25列）をパースする。"""
        results = []
        table = soup.select_one("table.race_table_01")
        if not table:
            return results

        rows = table.select("tr")
        for row in rows:
            cells = row.select("td")
            if len(cells) < 15:
                continue
            try:
                # netkeiba列構造(25列):
                # [0]着順 [1]枠 [2]馬番 [3]馬名 [4]性齢 [5]斤量 [6]騎手
                # [7]タイム [8]着差 [14]通過 [15]上がり3F [16]オッズ [17]人気
                # [18]馬体重
                result = {
                    "finish": _safe_int(cells[0].get_text(strip=True)),
                    "gate_num": _safe_int(cells[1].get_text(strip=True)),
                    "horse_num": _safe_int(cells[2].get_text(strip=True)),
                    "horse_name": cells[3].get_text(strip=True),
                    "sex_age": cells[4].get_text(strip=True),
                    "weight_carried": _safe_float(cells[5].get_text(strip=True)),
                    "jockey": cells[6].get_text(strip=True),
                    "time": cells[7].get_text(strip=True),
                    "margin": cells[8].get_text(strip=True),
                    "passing": cells[14].get_text(strip=True) if len(cells) > 14 else "",
                    "last_3f": _safe_float(cells[15].get_text(strip=True)) if len(cells) > 15 else None,
                    "odds": _safe_float(cells[16].get_text(strip=True)) if len(cells) > 16 else None,
                    "popularity": _safe_int(cells[17].get_text(strip=True)) if len(cells) > 17 else None,
                    "horse_weight": cells[18].get_text(strip=True) if len(cells) > 18 else "",
                }
                horse_link = cells[3].select_one("a[href]")
                if horse_link:
                    m = re.search(r"/horse/(\w+)", horse_link.get("href", ""))
                    if m:
                        result["horse_id"] = m.group(1)
                results.append(result)
            except Exception:
                continue
        return results

    def fetch_race_ids_for_date(self, year: int, month: int, day: int) -> List[str]:
        """指定日のレースID一覧を取得する。"""
        url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={year:04d}{month:02d}{day:02d}"
        time.sleep(2)

        try:
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                return []
            resp.encoding = "utf-8"
        except Exception:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        race_ids = []
        for link in soup.select("a[href*='/race/']"):
            href = link.get("href", "")
            m = re.search(r"/race/(\d{12})", href)
            if m:
                rid = m.group(1)
                if rid not in race_ids:
                    race_ids.append(rid)

        return race_ids

    def close(self) -> None:
        """セッションを閉じてキャッシュをディスクに保存する。"""
        self._save_disk_cache("horse_past.json", self._horse_cache)
        self._save_disk_cache("horse_profile.json", self._profile_cache)
        self._save_disk_cache("shutuba.json", self._shutuba_cache)
        self._session.close()


def _safe_int(v) -> Optional[int]:
    if not v:
        return None
    try:
        return int(re.sub(r"[^\d\-]", "", v))
    except (ValueError, TypeError):
        return None


def _safe_float(v) -> Optional[float]:
    if not v:
        return None
    try:
        return float(re.sub(r"[^\d.\-]", "", v))
    except (ValueError, TypeError):
        return None
