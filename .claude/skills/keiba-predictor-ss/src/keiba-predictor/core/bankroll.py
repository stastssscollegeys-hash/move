"""資金管理 - ハーフケリー + 追い上げ禁止"""
import os
import yaml
from typing import Dict, List, Optional


class BankrollManager:
    """
    ハーフケリー基準による賭け金管理クラス。
    マルチンゲール（追い上げ）は絶対禁止。
    連敗 stop_loss_streak 回で当日の賭けを停止する。
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """general.yaml から資金管理パラメータを読み込む。"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'general.yaml'
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)  # yaml.load() は禁止
        bankroll: Dict = config['bankroll']

        # 1日の予算上限（円）
        self.daily_budget: float = bankroll.get('daily_budget', 10000)
        # 総資金に対する1レースの最大賭け比率
        self.max_bet_ratio: float = bankroll.get('max_bet_ratio', 0.05)
        # ハーフケリーの係数（0.5 = ハーフケリー）
        self.kelly_fraction: float = bankroll.get('kelly_fraction', 0.5)
        # 連敗でストップする閾値
        self.stop_loss_streak: int = bankroll.get('stop_loss_streak', 3)

    # ------------------------------------------------------------------
    # ケリー基準
    # ------------------------------------------------------------------

    def calculate_kelly(self, win_prob: float, odds: float) -> float:
        """ケリー基準による最適賭け金比率を算出する。

        ケリー式: f = (p * b - q) / b
        ハーフケリー: f_half = f * kelly_fraction

        Parameters
        ----------
        win_prob:
            推定勝率（0〜1）。
        odds:
            単勝オッズ（倍）。1.0 以下の場合は 0 を返す。

        Returns
        -------
        float
            総資金に対する推奨賭け比率（0〜1）。負になる場合は 0。
        """
        if odds <= 1.0:
            return 0.0
        b = odds - 1.0          # 純利益倍率
        q = 1.0 - win_prob      # 敗率
        f = (win_prob * b - q) / b
        if f <= 0:
            return 0.0
        return f * self.kelly_fraction

    # ------------------------------------------------------------------
    # 推奨賭け金
    # ------------------------------------------------------------------

    def get_bet_amount(
        self,
        total_bankroll: float,
        win_prob: float,
        odds: float,
    ) -> int:
        """推奨賭け金を算出する（100円単位）。

        Parameters
        ----------
        total_bankroll:
            現在の総資金（円）。
        win_prob:
            推定勝率（0〜1）。
        odds:
            単勝オッズ（倍）。

        Returns
        -------
        int
            100円単位に丸めた推奨賭け金（円）。
            max_bet_ratio を超えない範囲に制限される。
        """
        kelly_ratio = self.calculate_kelly(win_prob, odds)
        if kelly_ratio <= 0:
            return 0

        # ケリー基準額
        kelly_amount = total_bankroll * kelly_ratio
        # 上限: 総資金の max_bet_ratio 以下
        max_amount = total_bankroll * self.max_bet_ratio
        # 日次予算上限も適用
        capped = min(kelly_amount, max_amount, self.daily_budget)

        # 100円単位に切り捨て
        bet = int(capped // 100) * 100
        return max(bet, 0)

    # ------------------------------------------------------------------
    # ストップロス（連敗チェック）
    # ------------------------------------------------------------------

    def check_stop_loss(self, today_results: List[bool]) -> bool:
        """連敗が stop_loss_streak 回に達したかを判定する。

        マルチンゲール（連敗後に賭け金を増やす追い上げ）は絶対禁止。
        このメソッドが True を返した場合、当日の賭けを停止すること。

        Parameters
        ----------
        today_results:
            当日の賭け結果リスト（True=的中, False=外れ）。
            最新の結果がリストの末尾にあること。

        Returns
        -------
        bool
            True = 当日の賭けを停止すべき状態。
        """
        if not today_results:
            return False

        # 末尾から連続した False の数を数える
        streak = 0
        for result in reversed(today_results):
            if not result:
                streak += 1
            else:
                break

        if streak >= self.stop_loss_streak:
            print(
                f"[STOP] {streak}連敗を検出しました。"
                f"当日の賭けを停止します（追い上げ厳禁）。"
            )
            return True
        return False

    # ------------------------------------------------------------------
    # サマリー表示
    # ------------------------------------------------------------------

    def summary(self, total_bankroll: float) -> Dict:
        """現在の設定サマリーを返す。"""
        return {
            'total_bankroll': total_bankroll,
            'daily_budget': self.daily_budget,
            'max_bet_per_race': total_bankroll * self.max_bet_ratio,
            'kelly_fraction': self.kelly_fraction,
            'stop_loss_streak': self.stop_loss_streak,
        }
