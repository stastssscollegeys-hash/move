"""smartrc.jp スクレイパー

出馬表データ（馬情報・過去走・指標・血統等）を取得する。
HTML構造は config/keiba-predictor/selectors.yaml で管理する。
"""

import re
import time
import random
import logging
from pathlib import Path
from typing import Any, Optional

import requests
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class SmartRCScraper:
    """smartrc.jp から出馬表データを取得するスクレイパー。"""

    BASE_URL = "https://www.smartrc.jp/v3"

    def __init__(self, config_path: Optional[str] = None) -> None:
        # config/keiba-predictor/general.yaml を自動解決
        if config_path is None:
            config_path = Path(__file__).parents[3] / "config" / "keiba-predictor" / "general.yaml"
        cfg = _load_yaml(str(config_path))
        sc = cfg.get("scraping", {})
        self.config: dict[str, Any] = {
            "request_interval": float(sc.get("request_interval", 2.0)),
            "jitter_max": float(sc.get("jitter_max", 1.5)),
            "max_retries": int(sc.get("max_retries", 3)),
            "retry_wait": float(sc.get("retry_wait", 5.0)),
            "user_agent": sc.get(
                "user_agent",
                "Mozilla/5.0 (compatible; keiba-predictor/1.0)",
            ),
            "timeout": int(sc.get("timeout", 30)),
        }

        # セレクタ設定を読み込み
        selectors_path = Path(__file__).parents[3] / "config" / "keiba-predictor" / "selectors.yaml"
        self._selectors: dict = _load_yaml(str(selectors_path)).get("smartrc", {})

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.config["user_agent"]})

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _wait(self) -> None:
        """リクエスト間隔制御（設定値＋ランダムジッター）。"""
        interval = self.config["request_interval"] + random.uniform(0, self.config["jitter_max"])
        logger.debug("待機 %.2f 秒", interval)
        time.sleep(interval)

    def _get(self, url: str) -> Optional[requests.Response]:
        """GETリクエスト（リトライ付き）。

        - robots.txt 遵守: User-Agent を明示、過剰アクセスを抑制
        - verify=True を明示
        - 最大 max_retries 回リトライ
        """
        for attempt in range(1, self.config["max_retries"] + 1):
            try:
                self._wait()
                resp = self._session.get(
                    url,
                    timeout=self.config["timeout"],
                    verify=True,
                )
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                logger.debug("GET %s -> %s", url, resp.status_code)
                return resp
            except requests.HTTPError as e:
                logger.warning("HTTP エラー (試行 %d/%d): %s", attempt, self.config["max_retries"], e)
            except requests.RequestException as e:
                logger.warning("リクエストエラー (試行 %d/%d): %s", attempt, self.config["max_retries"], e)

            if attempt < self.config["max_retries"]:
                time.sleep(self.config["retry_wait"])

        logger.error("最大リトライ回数に達しました: %s", url)
        return None

    # ------------------------------------------------------------------
    # セレクタヘルパー
    # ------------------------------------------------------------------

    @staticmethod
    def _text(tag: Any, selector: str) -> Optional[str]:
        """BeautifulSoup タグから子要素のテキストを取得する。取得できなければ None。"""
        el = tag.select_one(selector)
        if el is None:
            return None
        return el.get_text(strip=True) or None

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        """文字列を float に変換。失敗時は None。"""
        if value is None:
            return None
        try:
            return float(re.sub(r"[^\d.\-]", "", value))
        except ValueError:
            return None

    @staticmethod
    def _safe_int(value: Optional[str]) -> Optional[int]:
        """文字列を int に変換。失敗時は None。"""
        if value is None:
            return None
        try:
            return int(re.sub(r"[^\d\-]", "", value))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def fetch_race_card(self, race_id: str) -> Optional[dict]:
        """出馬表データを取得する。

        Parameters
        ----------
        race_id:
            ``'20260323hanshin11'`` 形式の文字列。

        Returns
        -------
        dict or None
            ``race_info`` と ``horses`` キーを持つ辞書。取得失敗時は None。
        """
        url = f"{self.BASE_URL}/race/{race_id}"
        resp = self._get(url)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        ri_sel = self._selectors.get("race_info", {})
        hl_sel = self._selectors.get("horse_list", {})
        pr_sel = self._selectors.get("past_results", {})

        # --- レース情報 ---
        race_info: dict[str, Any] = {
            "race_id": race_id,
            "title": self._text(soup, ri_sel.get("title", "h1.race-title")),
            "venue": self._text(soup, ri_sel.get("venue", ".race-info .venue")),
            "distance": self._safe_int(
                self._text(soup, ri_sel.get("distance", ".race-info .distance"))
            ),
            "surface": self._text(soup, ri_sel.get("surface", ".race-info .surface")),
            "weather": self._text(soup, ri_sel.get("weather", ".race-info .weather")),
            "track_condition": self._text(
                soup, ri_sel.get("track_condition", ".race-info .track-condition")
            ),
            "horse_count": self._safe_int(
                self._text(soup, ri_sel.get("horse_count", ".race-info .horse-count"))
            ),
            "grade": self._text(soup, ri_sel.get("grade", ".race-info .grade")),
            "prize": self._text(soup, ri_sel.get("prize", ".race-info .prize")),
        }

        # --- 馬一覧 ---
        horses: list[dict] = []
        rows = soup.select(hl_sel.get("container", "table.race-card tbody tr"))
        for row in rows:
            horse = self._parse_horse_row(row, hl_sel)
            if horse:
                # 過去5走を取得（行内の折り畳みパネルを想定）
                horse["past_results"] = self._parse_past_results(row, pr_sel)
                horses.append(horse)

        return {"race_info": race_info, "horses": horses}

    def _parse_horse_row(self, row: Any, sel: dict) -> Optional[dict]:
        """出馬表の1行（1頭分）をパースする。"""

        def t(key: str, default: str = "") -> Optional[str]:
            return self._text(row, sel.get(key, default))

        # 馬IDを href から抽出（例: /horse/2023100001 → 2023100001）
        horse_id: Optional[str] = None
        horse_link = row.select_one(sel.get("horse_id", "td.horse-name a[href]"))
        if horse_link:
            href = horse_link.get("href", "")
            m = re.search(r"/horse/(\w+)", href)
            if m:
                horse_id = m.group(1)

        # 性齢の分解（例: "牡3" → sex="牡", age=3）
        sex_age_raw = t("sex_age")
        sex: Optional[str] = None
        age: Optional[int] = None
        if sex_age_raw:
            m2 = re.match(r"([牡牝セ騸])(\d+)", sex_age_raw)
            if m2:
                sex = m2.group(1)
                age = int(m2.group(2))

        horse: dict[str, Any] = {
            # 基本情報
            "horse_id": horse_id,
            "gate_num": self._safe_int(t("gate_num")),
            "horse_num": self._safe_int(t("horse_num")),
            "horse_name": t("horse_name"),
            "sex": sex,
            "age": age,
            "weight_carried": self._safe_float(t("weight_carried")),
            # 騎手・調教師
            "jockey": t("jockey"),
            "trainer": t("trainer"),
            # 馬体重
            "horse_weight": self._safe_int(t("horse_weight")),
            "weight_diff": self._safe_int(t("weight_diff")),
            # オッズ・人気
            "win_odds": self._safe_float(t("win_odds")),
            "popularity": self._safe_int(t("popularity")),
            # 指標
            "cr_value": self._safe_float(t("cr_value")),
            "speed_index": self._safe_float(t("speed_index")),
            "last_3f": self._safe_float(t("last_3f")),
            "ten_1f": self._safe_float(t("ten_1f")),
            "dirt_share": self._safe_float(t("dirt_share")),
            "distance_share": self._safe_float(t("distance_share")),
            # 成績率
            "win_rate": self._safe_float(t("win_rate")),
            "place_rate": self._safe_float(t("place_rate")),
            "show_rate": self._safe_float(t("show_rate")),
            # 血統
            "sire": t("sire"),
            "bms": t("bms"),
            # TB指標
            "tb_index": self._safe_float(t("tb_index")),
        }

        # 馬名が取れなければ無効行と判断
        if not horse["horse_name"] and horse_id is None:
            return None

        # 推定人気ランク（A-E）: 人気番号から変換
        pop = horse["popularity"]
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

        return horse

    def _parse_past_results(self, row: Any, sel: dict) -> list[dict]:
        """過去5走データをパースする。"""
        results: list[dict] = []
        container_sel = sel.get("container", "div.past-results table tbody tr")

        # ページ全体ではなく行内のパネルを探す
        rows = row.select(container_sel)
        # 行内に見つからなければ空リストを返す（別途 fetch が必要なサイト構造を想定）
        for pr_row in rows[:5]:

            def pt(key: str, default: str = "") -> Optional[str]:
                return self._text(pr_row, sel.get(key, default))

            entry: dict[str, Any] = {
                "date": pt("date"),
                "venue": pt("venue"),
                "surface": pt("surface"),
                "distance": self._safe_int(pt("distance")),
                "condition": pt("condition"),
                "finish": self._safe_int(pt("finish")),
                "time": pt("time"),
                "last_3f": self._safe_float(pt("last_3f")),
                "ten_1f": self._safe_float(pt("ten_1f")),
                "jockey": pt("jockey"),
                "weight_carried": self._safe_float(pt("weight_carried")),
                "horse_weight": self._safe_int(pt("horse_weight")),
                "odds": self._safe_float(pt("odds")),
                "horse_count": self._safe_int(pt("horse_count")),
            }
            results.append(entry)

        return results

    def fetch_all_races(self, venue_date: str) -> list[dict]:
        """開催全レース（最大12レース）を一括取得する。

        Parameters
        ----------
        venue_date:
            ``'20260323hanshin'`` 形式の文字列。
        """
        results: list[dict] = []
        for race_num in range(1, 13):
            race_id = f"{venue_date}{race_num:02d}"
            try:
                data = self.fetch_race_card(race_id)
                if data:
                    results.append(data)
            except Exception as e:
                logger.warning("Race %s の取得に失敗しました: %s", race_id, e)
        return results

    def parse_race_id(self, race_id_str: str) -> tuple[str, str, int]:
        """レースID文字列をパースする。

        Parameters
        ----------
        race_id_str:
            ``'20260323hanshin11'`` 形式の文字列。

        Returns
        -------
        (date, venue, race_num)
            例: ``('20260323', 'hanshin', 11)``

        Raises
        ------
        ValueError
            フォーマットが不正な場合。
        """
        m = re.match(r"^(\d{8})([a-z]+)(\d{1,2})$", race_id_str)
        if not m:
            raise ValueError(f"不正なレースID形式: {race_id_str!r}")
        date = m.group(1)
        venue = m.group(2)
        race_num = int(m.group(3))
        return date, venue, race_num
