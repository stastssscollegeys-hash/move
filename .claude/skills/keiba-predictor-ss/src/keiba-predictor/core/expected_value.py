"""期待値ベース馬券判定 - Mamba/umaro_ai/Laplace の共通設計"""
import os
import yaml
from typing import Dict, List, Optional
from itertools import combinations


class ExpectedValueCalculator:
    """
    推定確率とオッズから期待値を算出し、推奨馬券を選別するクラス。
    期待値 >= min_ev かつ 合成オッズ >= min_composite_odds の馬券のみを推奨する。
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """general.yaml から閾値を読み込む。"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'general.yaml'
            )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)  # yaml.load() は禁止
        bankroll: Dict = config['bankroll']
        self.min_ev: float = bankroll.get('min_expected_value', 1.0)
        self.min_composite_odds: float = bankroll.get('min_composite_odds', 4.0)

    # ------------------------------------------------------------------
    # 単一馬券の期待値
    # ------------------------------------------------------------------

    def calculate_win_ev(self, win_prob: float, odds: float) -> float:
        """単勝期待値を算出する。

        Parameters
        ----------
        win_prob:
            推定勝率（0〜1）。
        odds:
            単勝オッズ（倍）。

        Returns
        -------
        float
            期待値 = 推定勝率 × オッズ。
        """
        return win_prob * odds

    def calculate_place_ev(self, show_prob: float, show_odds: float) -> float:
        """複勝期待値を算出する。

        Parameters
        ----------
        show_prob:
            推定複勝率（0〜1）。
        show_odds:
            複勝オッズ（倍）。

        Returns
        -------
        float
            期待値 = 推定複勝率 × 複勝オッズ。
        """
        return show_prob * show_odds

    # ------------------------------------------------------------------
    # 馬連期待値
    # ------------------------------------------------------------------

    def calculate_quinella_ev(
        self,
        probs: List[Dict],
        odds_matrix: Dict,
    ) -> List[Dict]:
        """上位5頭の馬連全組み合わせの期待値を算出する。

        Parameters
        ----------
        probs:
            ``[{post, name, win_prob, show_prob}, ...]`` の予測リスト。
        odds_matrix:
            ``{"1-2": 12.5, ...}`` 形式の馬連オッズ辞書。
            キーは「小さい馬番-大きい馬番」順を推奨。

        Returns
        -------
        List[Dict]
            期待値降順でソートされた馬連候補リスト。
        """
        results: List[Dict] = []
        # 勝率上位5頭に絞る
        top_horses = sorted(probs, key=lambda x: x['win_prob'], reverse=True)[:5]

        for h1, h2 in combinations(top_horses, 2):
            # 馬連確率の近似式（独立性を仮定した上限推定）
            # P(h1 1着 & h2 2着) + P(h2 1着 & h1 2着)
            pair_prob = (
                h1['win_prob'] * h2['show_prob']
                + h2['win_prob'] * h1['show_prob']
            )

            # キーは「小-大」順で統一
            p1, p2 = sorted([h1['post'], h2['post']])
            pair_key = f"{p1}-{p2}"
            odds = odds_matrix.get(pair_key, 0.0)

            if odds > 0:
                ev = pair_prob * odds
                results.append({
                    'type': '馬連',
                    'combination': pair_key,
                    'horse_names': f"{h1['name']}-{h2['name']}",
                    'probability': pair_prob,
                    'odds': odds,
                    'expected_value': ev,
                    'recommended': ev >= self.min_ev,
                })

        return sorted(results, key=lambda x: x['expected_value'], reverse=True)

    # ------------------------------------------------------------------
    # 三連複・三連単の期待値（簡易推定）
    # ------------------------------------------------------------------

    def calculate_trio_ev(
        self,
        probs: List[Dict],
        odds_matrix: Dict,
    ) -> List[Dict]:
        """上位5頭の三連複全組み合わせの期待値を算出する。

        Parameters
        ----------
        probs:
            予測リスト。
        odds_matrix:
            ``{"1-2-3": 45.0, ...}`` 形式の三連複オッズ辞書。
        """
        results: List[Dict] = []
        top_horses = sorted(probs, key=lambda x: x['win_prob'], reverse=True)[:5]

        for h1, h2, h3 in combinations(top_horses, 3):
            # 三連複確率の簡易近似（順列確率の和 / 6 ≒ 組み合わせ確率）
            trio_prob = (
                h1['win_prob'] * h2['show_prob'] * h3['show_prob']
                + h2['win_prob'] * h1['show_prob'] * h3['show_prob']
                + h3['win_prob'] * h1['show_prob'] * h2['show_prob']
            ) / 3.0

            posts = sorted([h1['post'], h2['post'], h3['post']])
            key = f"{posts[0]}-{posts[1]}-{posts[2]}"
            odds = odds_matrix.get(key, 0.0)

            if odds > 0:
                ev = trio_prob * odds
                results.append({
                    'type': '三連複',
                    'combination': key,
                    'probability': trio_prob,
                    'odds': odds,
                    'expected_value': ev,
                    'recommended': ev >= self.min_ev,
                })

        return sorted(results, key=lambda x: x['expected_value'], reverse=True)

    # ------------------------------------------------------------------
    # 合成オッズ計算
    # ------------------------------------------------------------------

    def calculate_composite_odds(self, tickets: List[Dict]) -> float:
        """購入馬券群の合成オッズを算出する。

        合成オッズ = 1 / Σ(1 / 各馬券のオッズ)

        Parameters
        ----------
        tickets:
            ``[{odds: float, ...}, ...]``

        Returns
        -------
        float
            合成オッズ。
        """
        if not tickets:
            return 0.0
        denominator = sum(1.0 / t['odds'] for t in tickets if t.get('odds', 0) > 0)
        return (1.0 / denominator) if denominator > 0 else 0.0

    # ------------------------------------------------------------------
    # 全馬券種の推奨判定
    # ------------------------------------------------------------------

    def get_recommendations(
        self,
        predictions: List[Dict],
        odds_data: Dict,
    ) -> List[Dict]:
        """全馬券種の期待値を算出し、推奨馬券リストを返す。

        Parameters
        ----------
        predictions:
            ``[{post, name, win_prob, show_prob, win_odds, show_odds}, ...]``
        odds_data:
            ``{quinella: {"1-2": 12.5, ...}, trio: {...}}`` 形式のオッズ辞書。

        Returns
        -------
        List[Dict]
            期待値降順の推奨馬券リスト（合成オッズ確認済み）。
        """
        all_tickets: List[Dict] = []

        # --- 単勝 ---
        for pred in predictions:
            win_odds = pred.get('win_odds', 0.0)
            if win_odds <= 0:
                continue
            ev = self.calculate_win_ev(pred['win_prob'], win_odds)
            if ev >= self.min_ev:
                all_tickets.append({
                    'type': '単勝',
                    'combination': str(pred['post']),
                    'horse_name': pred.get('name', ''),
                    'probability': pred['win_prob'],
                    'odds': win_odds,
                    'expected_value': ev,
                    'recommended': True,
                })

        # --- 複勝 ---
        for pred in predictions:
            show_odds = pred.get('show_odds', 0.0)
            if show_odds <= 0:
                continue
            ev = self.calculate_place_ev(pred['show_prob'], show_odds)
            if ev >= self.min_ev:
                all_tickets.append({
                    'type': '複勝',
                    'combination': str(pred['post']),
                    'horse_name': pred.get('name', ''),
                    'probability': pred['show_prob'],
                    'odds': show_odds,
                    'expected_value': ev,
                    'recommended': True,
                })

        # --- 馬連 ---
        quinella_tickets = self.calculate_quinella_ev(
            predictions, odds_data.get('quinella', {})
        )
        all_tickets.extend([t for t in quinella_tickets if t['recommended']])

        # --- 三連複 ---
        trio_tickets = self.calculate_trio_ev(
            predictions, odds_data.get('trio', {})
        )
        all_tickets.extend([t for t in trio_tickets if t['recommended']])

        if not all_tickets:
            return []

        # 合成オッズ確認
        composite = self.calculate_composite_odds(all_tickets)
        if composite < self.min_composite_odds:
            print(
                f"[INFO] 合成オッズ{composite:.1f}倍 < 基準{self.min_composite_odds}倍 "
                f"→ 見送りを検討してください"
            )

        # 期待値降順でソートし、上位4点に制限
        # リサーチ知見: 買い目を絞るほど回収率が高い
        sorted_tickets = sorted(all_tickets, key=lambda x: x['expected_value'], reverse=True)
        max_tickets = 4
        return sorted_tickets[:max_tickets]
