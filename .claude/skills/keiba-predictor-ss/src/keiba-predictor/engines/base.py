"""分析エンジン基底クラス

全エンジンはこのクラスを継承し、
- calculate_score: 0-100 のスコアを返す
- get_features: LightGBM 用の特徴量辞書を返す
の2メソッドを実装する。
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseEngine(ABC):
    """分析エンジンの基底クラス。"""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Parameters
        ----------
        config:
            エンジン固有の設定辞書。
            各サブクラスで必要なキーを定義する。
        """
        self.config = config

    @abstractmethod
    def calculate_score(self, horse_data: dict[str, Any], race_data: dict[str, Any]) -> float:
        """馬の総合スコアを算出する。

        Parameters
        ----------
        horse_data:
            スクレイパーが返す1頭分の辞書。
        race_data:
            スクレイパーが返す ``race_info`` 辞書。

        Returns
        -------
        float
            0（最低）〜 100（最高）のスコア。
        """

    @abstractmethod
    def get_features(
        self, horse_data: dict[str, Any], race_data: dict[str, Any]
    ) -> dict[str, Any]:
        """LightGBM 用の特徴量辞書を返す。

        Parameters
        ----------
        horse_data:
            スクレイパーが返す1頭分の辞書。
        race_data:
            スクレイパーが返す ``race_info`` 辞書。

        Returns
        -------
        dict[str, Any]
            特徴量名 → 値の辞書。
            値は数値（int / float）または None（欠損）。
            文字列カテゴリは呼び出し元でエンコードする。
        """

    # ------------------------------------------------------------------
    # 共通ユーティリティ（サブクラスから使用可）
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        """値を [lo, hi] にクランプする。"""
        return max(lo, min(hi, value))

    @staticmethod
    def _safe(value: Any, default: float = 0.0) -> float:
        """None を default に変換して float で返す。"""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
