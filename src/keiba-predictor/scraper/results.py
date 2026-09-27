"""レース結果スクレイパー

確定後のレース結果（着順・タイム・確定オッズ等）を取得する。
"""

import logging
import re
import time
import random
from pathlib import Path
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class ResultsScraper:
    """レース結果を取得するスクレイパー。"""

    BASE_URL = "https://www.smartrc.jp/v3"

    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            config_path = (
                Path(__file__).parents[3] / "config" / "keiba-predictor" / "general.yaml"
            )
        cfg = _load_yaml(str(config_path))
        sc = cfg.get("scraping", {})
        self._request_interval = float(sc.get("request_interval", 2.0))
        self._jitter_max = float(sc.get("jitter_max", 1.5))
        self._max_retries = int(sc.get("max_retries", 3))
        self._retry_wait = float(sc.get("retry_wait", 5.0))
        self._timeout = int(sc.get("timeout", 30))
        self._user_agent = sc.get(
            "user_agent", "Mozilla/5.0 (compatible; keiba-predictor/1.0)"
        )
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self._user_agent})

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _wait(self) -> None:
        """リクエスト間隔制御。"""
        interval = self._request_interval + random.uniform(0, self._jitter_max)
        time.sleep(interval)

    def _get(self, url: str) -> Optional[requests.Response]:
        """GETリクエスト（リトライ付き）。"""
        for attempt in range(1, self._max_retries + 1):
            try:
                self._wait()
                resp = self._session.get(url, timeout=self._timeout, verify=True)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp
            except requests.HTTPError as e:
                logger.warning("HTTP エラー (試行 %d/%d): %s", attempt, self._max_retries, e)
            except requests.RequestException as e:
                logger.warning("リクエストエラー (試行 %d/%d): %s", attempt, self._max_retries, e)
            if attempt < self._max_retries:
                time.sleep(self._retry_wait)
        logger.error("最大リトライ: %s", url)
        return None

    @staticmethod
    def _text(tag: object, selector: str) -> Optional[str]:
        el = tag.select_one(selector)  # type: ignore[union-attr]
        if el is None:
            return None
        return el.get_text(strip=True) or None

    @staticmethod
    def _safe_float(v: Optional[str]) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(re.sub(r"[^\d.\-]", "", v))
        except ValueError:
            return None

    @staticmethod
    def _safe_int(v: Optional[str]) -> Optional[int]:
        if v is None:
            return None
        try:
            return int(re.sub(r"[^\d\-]", "", v))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def fetch_results(self, race_id: str) -> list[dict]:
        """レース結果を取得する。

        Parameters
        ----------
        race_id:
            ``'20260323hanshin11'`` 形式。

        Returns
        -------
        list[dict]
            各馬の結果リスト。以下のキーを含む:

            - ``horse_id`` (str | None)
            - ``horse_name`` (str | None)
            - ``horse_num`` (int | None)
            - ``finish`` (int | None): 着順
            - ``time`` (str | None): タイム（例: ``'1:32.5'``）
            - ``last_3f`` (float | None): 上がり3F
            - ``win_odds_final`` (float | None): 確定単勝オッズ
            - ``show_odds_final`` (float | None): 確定複勝オッズ
            - ``jockey`` (str | None)
            - ``horse_weight`` (int | None)
            - ``weight_diff`` (int | None)
        """
        url = f"{self.BASE_URL}/result/{race_id}"
        resp = self._get(url)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []

        # 結果テーブルの各行をパース（セレクタはプレースホルダー）
        rows = soup.select("table.race-result tbody tr")
        for row in rows:
            t = lambda sel: self._text(row, sel)

            # 馬IDを href から抽出
            horse_id: Optional[str] = None
            link = row.select_one("td.horse-name a[href]")
            if link:
                m = re.search(r"/horse/(\w+)", link.get("href", ""))
                if m:
                    horse_id = m.group(1)

            entry: dict = {
                "horse_id": horse_id,
                "horse_name": t("td.horse-name"),
                "horse_num": self._safe_int(t("td.horse-num")),
                "finish": self._safe_int(t("td.finish")),
                "time": t("td.race-time"),
                "last_3f": self._safe_float(t("td.last-3f")),
                "win_odds_final": self._safe_float(t("td.win-odds")),
                "show_odds_final": self._safe_float(t("td.show-odds")),
                "jockey": t("td.jockey"),
                "horse_weight": self._safe_int(t("td.horse-weight")),
                "weight_diff": self._safe_int(t("td.weight-diff")),
            }

            # 着順が取れない行はヘッダ等の可能性があるためスキップ
            if entry["finish"] is None and entry["horse_name"] is None:
                continue

            results.append(entry)

        logger.info("race_id=%s: %d 頭分の結果を取得しました", race_id, len(results))
        return results

    def fetch_daily_results(self, date: str) -> dict[str, list[dict]]:
        """日次結果を一括取得する。

        Parameters
        ----------
        date:
            日付文字列（例: ``'20260323'``）。

        Returns
        -------
        dict[str, list[dict]]
            ``{race_id: [結果リスト]}`` の形式。
            取得できなかったレースはキーが存在しない。
        """
        # 当日の開催場一覧ページから race_id を収集する想定
        # HTML 構造が不明なため、まず開催一覧URLを試みる
        index_url = f"{self.BASE_URL}/results/{date}"
        resp = self._get(index_url)

        race_ids: list[str] = []
        if resp is not None:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 各レースリンクの href から race_id を収集（セレクタはプレースホルダー）
            for link in soup.select("a.race-link[href]"):
                href = link.get("href", "")
                m = re.search(r"/race/(\w+)", href)
                if m:
                    race_ids.append(m.group(1))

        if not race_ids:
            logger.warning("date=%s: レースIDが見つかりませんでした", date)

        daily: dict[str, list[dict]] = {}
        for race_id in race_ids:
            try:
                res = self.fetch_results(race_id)
                if res:
                    daily[race_id] = res
            except Exception as e:
                logger.warning("race_id=%s の結果取得に失敗: %s", race_id, e)

        logger.info("date=%s: %d レース分の結果を取得しました", date, len(daily))
        return daily
