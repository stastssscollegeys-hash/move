"""JRA公式サイト 馬場情報スクレイパー

クッション値・含水率を取得し、馬場バイアスを推定する。
芝とダートで「高含水率→有利な脚質」が逆転する点に注意。
"""

import logging
import time
import random
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class JRABiasScraper:
    """JRA公式サイトから馬場情報を取得し、バイアスを推定するスクレイパー。"""

    BASE_URL = "https://www.jra.go.jp/keiba/baba/"

    # 馬場状態コード → 数値（スコア計算用）
    _CONDITION_SCORE: dict[str, float] = {
        "良":  0.0,
        "稍重": 0.3,
        "重":  0.6,
        "不良": 1.0,
    }

    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            config_path = Path(__file__).parents[3] / "config" / "keiba-predictor" / "general.yaml"
        cfg = _load_yaml(str(config_path))
        sc = cfg.get("scraping", {})
        self._request_interval = float(sc.get("request_interval", 2.0))
        self._jitter_max = float(sc.get("jitter_max", 1.5))
        self._max_retries = int(sc.get("max_retries", 3))
        self._retry_wait = float(sc.get("retry_wait", 5.0))
        self._timeout = int(sc.get("timeout", 30))
        self._user_agent = sc.get(
            "user_agent",
            "Mozilla/5.0 (compatible; keiba-predictor/1.0)",
        )

        selectors_path = Path(__file__).parents[3] / "config" / "keiba-predictor" / "selectors.yaml"
        self._selectors: dict = _load_yaml(str(selectors_path)).get("jra", {}).get("track_condition", {})

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self._user_agent})

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _wait(self) -> None:
        """リクエスト間隔制御。"""
        interval = self._request_interval + random.uniform(0, self._jitter_max)
        logger.debug("待機 %.2f 秒", interval)
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

        logger.error("最大リトライ回数に達しました: %s", url)
        return None

    @staticmethod
    def _text(soup: BeautifulSoup, selector: str) -> Optional[str]:
        """セレクタでテキストを取得。見つからなければ None。"""
        el = soup.select_one(selector)
        if el is None:
            return None
        return el.get_text(strip=True) or None

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        try:
            import re
            return float(re.sub(r"[^\d.\-]", "", value))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def fetch_track_condition(self, venue: str, date: str) -> dict:
        """馬場情報を取得する。

        Parameters
        ----------
        venue:
            開催場コード（例: ``'hanshin'``, ``'tokyo'``）。
        date:
            日付文字列（例: ``'20260323'``）。

        Returns
        -------
        dict
            以下のキーを含む辞書。取得失敗項目は None。

            - ``cushion_value`` (float | None): クッション値（芝のみ）
            - ``moisture_turf`` (float | None): 芝含水率 (%)
            - ``moisture_dirt`` (float | None): ダート含水率 (%)
            - ``track_condition`` (str | None): 馬場状態（良/稍重/重/不良）
            - ``weather`` (str | None): 天候
            - ``venue`` (str): 開催場
            - ``date`` (str): 日付
        """
        url = f"{self.BASE_URL}?kaisai_date={date}&venue={venue}"
        resp = self._get(url)

        result: dict = {
            "cushion_value": None,
            "moisture_turf": None,
            "moisture_dirt": None,
            "track_condition": None,
            "weather": None,
            "venue": venue,
            "date": date,
        }

        if resp is None:
            logger.warning("馬場情報の取得に失敗しました: venue=%s, date=%s", venue, date)
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        sel = self._selectors

        result["cushion_value"] = self._safe_float(
            self._text(soup, sel.get("cushion_value", ".cushion-value"))
        )
        result["moisture_turf"] = self._safe_float(
            self._text(soup, sel.get("moisture_turf", ".moisture-turf"))
        )
        result["moisture_dirt"] = self._safe_float(
            self._text(soup, sel.get("moisture_dirt", ".moisture-dirt"))
        )
        result["track_condition"] = self._text(
            soup, sel.get("track_condition", ".track-condition")
        )
        result["weather"] = self._text(soup, sel.get("weather", ".weather"))

        return result

    def estimate_bias(self, track_data: dict, surface: str) -> dict:
        """馬場バイアスを推定する。

        芝とダートで高含水率時の有利・不利が逆転する点に注意:
        - 芝:   高含水率 → 時計がかかる → **外差し有利**
        - ダート: 高含水率 → 砂が固まり高速 → **内先行有利**（逆転現象）

        Parameters
        ----------
        track_data:
            ``fetch_track_condition`` の戻り値。
        surface:
            ``'turf'``（芝）または ``'dirt'``（ダート）。

        Returns
        -------
        dict
            - ``inner_advantage`` (float): 内枠有利度 0.0（不利） ～ 1.0（有利）
            - ``front_advantage`` (float): 先行有利度 0.0（不利） ～ 1.0（有利）
            - ``bias_label`` (str): バイアスの概要ラベル
            - ``confidence`` (float): 推定信頼度 0.0 ～ 1.0（データ欠損で低下）
        """
        surface = surface.lower()
        is_turf = surface in ("turf", "芝", "t")

        # 含水率を取得（芝 or ダートを選択）
        moisture: Optional[float] = (
            track_data.get("moisture_turf") if is_turf
            else track_data.get("moisture_dirt")
        )
        cushion: Optional[float] = track_data.get("cushion_value")
        condition_raw: Optional[str] = track_data.get("track_condition")
        condition_score = self._CONDITION_SCORE.get(condition_raw or "", 0.0)

        # データ欠損で信頼度を下げる
        available = sum([
            moisture is not None,
            cushion is not None or not is_turf,  # クッション値は芝のみ
            condition_raw is not None,
        ])
        confidence = available / 3.0

        # ------ 芝バイアス推定 ------
        if is_turf:
            # 含水率が高い（目安 >10%）または馬場が渋い → 外差し有利
            moisture_val = moisture if moisture is not None else 8.0  # 不明時は平均値
            cushion_val = cushion if cushion is not None else 9.0     # 不明時は平均値

            # 含水率補正: 高いほど外差し有利 → 内枠不利
            moisture_factor = min(moisture_val / 15.0, 1.0)
            # クッション値補正: 低いほど重い馬場 → 外差し有利
            cushion_factor = max(0.0, 1.0 - cushion_val / 12.0)
            # 馬場状態補正
            condition_factor = condition_score

            # 外差し圧力（0-1）
            outside_pressure = (moisture_factor * 0.4 + cushion_factor * 0.4 + condition_factor * 0.2)
            inner_advantage = max(0.0, 1.0 - outside_pressure)
            # 芝は差し・追い込み有利になりやすい → 先行有利度も下がる
            front_advantage = max(0.0, 0.7 - condition_score * 0.4)

            if outside_pressure >= 0.6:
                bias_label = "外差し強有利"
            elif outside_pressure >= 0.35:
                bias_label = "外差しやや有利"
            elif inner_advantage >= 0.7:
                bias_label = "内枠有利"
            else:
                bias_label = "フラット"

        # ------ ダートバイアス推定 ------
        else:
            moisture_val = moisture if moisture is not None else 5.0  # 不明時は平均値

            # ダート: 含水率が高い → 砂が締まって高速 → 内先行有利（逆転現象）
            moisture_factor = min(moisture_val / 12.0, 1.0)
            condition_factor = condition_score

            # 高含水率ほど内先行有利
            front_advantage = 0.5 + moisture_factor * 0.3 + (1.0 - condition_score) * 0.2
            front_advantage = min(front_advantage, 1.0)
            inner_advantage = 0.5 + moisture_factor * 0.25
            inner_advantage = min(inner_advantage, 1.0)

            if moisture_factor >= 0.7 or condition_score <= 0.1:
                bias_label = "内先行強有利（高速ダート）"
            elif moisture_factor >= 0.4:
                bias_label = "内先行やや有利"
            elif condition_score >= 0.6:
                bias_label = "外差しやや有利（重ダート）"
            else:
                bias_label = "フラット"

        return {
            "inner_advantage": round(inner_advantage, 3),
            "front_advantage": round(front_advantage, 3),
            "bias_label": bias_label,
            "confidence": round(confidence, 3),
        }
