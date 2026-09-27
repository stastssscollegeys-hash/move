"""netkeiba.com スクレイパー — 過去レース結果取得

race_id: YYYYCCDDNNRR (12桁)
  YYYY=年, CC=競馬場(01-10), DD=開催日(01-), NN=開催回(01-), RR=レース番号(01-12)

競馬場コード: 01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE = "https://db.netkeiba.com"


class NetkeibaScaper:
    """netkeiba.com から過去レース結果を取得するスクレイパー。"""

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
