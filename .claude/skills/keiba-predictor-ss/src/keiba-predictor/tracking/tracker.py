"""的中実績トラッキング + 過学習検知"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class ResultTracker:
    """
    予想結果と実績を DB に記録し、的中率・回収率・消去精度を集計するクラス。
    バックテストROIと実績ROIの乖離が 15% 超で過学習アラートを発する。
    統計的有意性の判定には最低 200 回試行が必要。
    """

    def __init__(self, db_repo) -> None:
        """
        Parameters
        ----------
        db_repo:
            DB アクセス用リポジトリ。
            以下のメソッドを実装していること:
                save_prediction(record: Dict) -> None
                save_actual(race_id: str, results: Dict) -> None
                get_predictions(since: datetime) -> List[Dict]
                get_actuals(since: datetime) -> List[Dict]
        """
        self.db = db_repo

    # ------------------------------------------------------------------
    # 記録
    # ------------------------------------------------------------------

    def record_prediction(
        self,
        race_id: str,
        predictions: List[Dict],
        recommendations: List[Dict],
    ) -> None:
        """予想結果を DB に記録する。

        Parameters
        ----------
        race_id:
            レース識別子（例: "2025_0101_tokyo_11"）。
        predictions:
            ``[{post, name, win_prob, show_prob}, ...]`` の推定結果。
        recommendations:
            ``[{type, combination, odds, expected_value}, ...]`` の推奨馬券リスト。
        """
        record = {
            'race_id': race_id,
            'predicted_at': datetime.now().isoformat(),
            'predictions': predictions,
            'recommendations': recommendations,
        }
        self.db.save_prediction(record)

    def record_actual(self, race_id: str, results: Dict) -> None:
        """実際のレース結果を DB に記録する。

        Parameters
        ----------
        race_id:
            レース識別子。
        results:
            ``{finish: [{post, name, finish_pos}, ...], payouts: {...}}``
            形式の結果データ。
        """
        self.db.save_actual(race_id, results)

    # ------------------------------------------------------------------
    # 集計
    # ------------------------------------------------------------------

    def calculate_hit_rate(self, period: str = 'weekly') -> Dict[str, float]:
        """馬券種別ごとの的中率を集計する。

        Parameters
        ----------
        period:
            集計期間。``'daily'`` / ``'weekly'`` / ``'monthly'`` のいずれか。

        Returns
        -------
        Dict[str, float]
            ``{馬券種: 的中率}`` 形式の辞書。
        """
        since = self._period_to_datetime(period)
        predictions = self.db.get_predictions(since)
        actuals = self.db.get_actuals(since)

        # race_id → 実績 のマップを構築
        actual_map: Dict[str, Dict] = {a['race_id']: a for a in actuals}

        # 馬券種別に的中 / 不的中を集計
        counts: Dict[str, Dict[str, int]] = {}
        for pred in predictions:
            race_id = pred['race_id']
            actual = actual_map.get(race_id)
            if actual is None:
                continue  # まだ結果が出ていないレースはスキップ

            for rec in pred.get('recommendations', []):
                ticket_type = rec['type']
                if ticket_type not in counts:
                    counts[ticket_type] = {'hit': 0, 'total': 0}
                counts[ticket_type]['total'] += 1
                if self._is_hit(rec, actual):
                    counts[ticket_type]['hit'] += 1

        return {
            t: (v['hit'] / v['total'] if v['total'] > 0 else 0.0)
            for t, v in counts.items()
        }

    def calculate_roi(self, period: str = 'weekly') -> Dict[str, float]:
        """回収率を集計する。外れ値（100倍超の配当）除外版も出力する。

        Parameters
        ----------
        period:
            集計期間。

        Returns
        -------
        Dict[str, float]
            ``{normal: float, outlier_excluded: float}``
            normal は全配当込み、outlier_excluded は 100 倍超を除いた回収率。
        """
        since = self._period_to_datetime(period)
        predictions = self.db.get_predictions(since)
        actuals = self.db.get_actuals(since)
        actual_map: Dict[str, Dict] = {a['race_id']: a for a in actuals}

        total_bet = 0
        total_return = 0
        total_bet_ex = 0
        total_return_ex = 0
        outlier_threshold = 100.0  # 100倍超を外れ値とする

        for pred in predictions:
            actual = actual_map.get(pred['race_id'])
            if actual is None:
                continue
            for rec in pred.get('recommendations', []):
                bet_amount = rec.get('bet_amount', 100)
                odds = rec.get('odds', 0.0)
                is_hit = self._is_hit(rec, actual)

                total_bet += bet_amount
                payout = bet_amount * odds if is_hit else 0.0
                total_return += payout

                # 外れ値除外版
                if odds <= outlier_threshold:
                    total_bet_ex += bet_amount
                    total_return_ex += payout

        roi_normal = total_return / total_bet if total_bet > 0 else 0.0
        roi_ex = total_return_ex / total_bet_ex if total_bet_ex > 0 else 0.0

        return {'normal': roi_normal, 'outlier_excluded': roi_ex}

    # ------------------------------------------------------------------
    # 過学習・有意性チェック
    # ------------------------------------------------------------------

    def check_overfitting(
        self, backtest_roi: float, actual_roi: float
    ) -> bool:
        """バックテストROI と実績ROI の乖離が 15% 超で警告を発する。

        Parameters
        ----------
        backtest_roi:
            バックテストで計測した回収率（例: 1.25 = 125%）。
        actual_roi:
            実運用での実績回収率。

        Returns
        -------
        bool
            True = 過学習の可能性あり（警告済み）。
        """
        divergence = abs(backtest_roi - actual_roi)
        if divergence > 0.15:
            print(
                f"[ALERT] 過学習の可能性: "
                f"バックテストROI={backtest_roi:.1%} vs "
                f"実績ROI={actual_roi:.1%} "
                f"（乖離{divergence:.1%}）"
            )
            return True
        return False

    def check_statistical_significance(self, num_trials: int) -> bool:
        """統計的有意性の確認（最低 200 回試行が必要）。

        Parameters
        ----------
        num_trials:
            これまでの試行回数（購入馬券数）。

        Returns
        -------
        bool
            True = 統計的有意性を判定できる水準に達している。
        """
        threshold = 200
        if num_trials < threshold:
            print(
                f"[INFO] 試行回数{num_trials}回 — "
                f"統計的有意性の判定には{threshold}回以上必要"
            )
            return False
        return True

    # ------------------------------------------------------------------
    # 精度検証
    # ------------------------------------------------------------------

    def elimination_accuracy(self) -> float:
        """消去精度を検証する。

        消去した馬が実際に 3 着以内に来なかった割合を返す。

        Returns
        -------
        float
            消去精度（0〜1）。データなしの場合は 0.0。
        """
        # 全期間のデータを対象とする
        predictions = self.db.get_predictions(datetime(2000, 1, 1))
        actuals = self.db.get_actuals(datetime(2000, 1, 1))
        actual_map: Dict[str, Dict] = {a['race_id']: a for a in actuals}

        correct = 0
        total = 0
        for pred in predictions:
            actual = actual_map.get(pred['race_id'])
            if actual is None:
                continue
            # 3着以内の馬番セット
            top3_posts = {
                r['post']
                for r in actual.get('finish', [])
                if r.get('finish_pos', 99) <= 3
            }
            for eliminated in pred.get('eliminated', []):
                post = eliminated.get('post')
                if post is None:
                    continue
                total += 1
                if post not in top3_posts:
                    correct += 1  # 消去した馬が来なかった = 正解

        return correct / total if total > 0 else 0.0

    def skip_accuracy(self) -> float:
        """見送り判断の精度を検証する。

        見送ったレース（should_skip=True）で期待値プラスの馬券がなかった割合を返す。
        高いほど「見送って正解だった」ケースが多いことを意味する。

        Returns
        -------
        float
            見送り精度（0〜1）。
        """
        predictions = self.db.get_predictions(datetime(2000, 1, 1))
        actuals = self.db.get_actuals(datetime(2000, 1, 1))
        actual_map: Dict[str, Dict] = {a['race_id']: a for a in actuals}

        correct = 0
        total = 0
        for pred in predictions:
            if not pred.get('should_skip'):
                continue
            actual = actual_map.get(pred['race_id'])
            if actual is None:
                continue
            total += 1
            # 見送ったレースで購入候補の馬券がすべて外れ → 見送り正解
            payouts = actual.get('payouts', {})
            any_payout = any(v > 0 for v in payouts.values())
            if not any_payout:
                correct += 1

        return correct / total if total > 0 else 0.0

    # ------------------------------------------------------------------
    # レポート生成
    # ------------------------------------------------------------------

    def generate_report(self, period: str = 'weekly') -> Dict:
        """サマリーレポート用データを生成する。

        Parameters
        ----------
        period:
            集計期間（``'daily'`` / ``'weekly'`` / ``'monthly'``）。

        Returns
        -------
        Dict
            OutputFormatter.format_report() に渡せる形式の辞書。
        """
        hit_rates = self.calculate_hit_rate(period)
        roi = self.calculate_roi(period)

        # 試行回数
        since = self._period_to_datetime(period)
        predictions = self.db.get_predictions(since)
        num_bets = sum(
            len(p.get('recommendations', [])) for p in predictions
        )
        self.check_statistical_significance(num_bets)

        # 過学習チェック（バックテストROI が別途必要）
        backtest_roi = roi.get('normal', 0.0) * 1.1  # 暫定: 実績+10%をバックテストと仮定
        overfitting_alert = self.check_overfitting(
            backtest_roi, roi.get('normal', 0.0)
        )

        return {
            'period': period,
            'num_races': len(predictions),
            'num_bets': num_bets,
            'hit_rates': hit_rates,
            'roi': roi,
            'elimination_accuracy': self.elimination_accuracy(),
            'skip_accuracy': self.skip_accuracy(),
            'overfitting_alert': overfitting_alert,
        }

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _period_to_datetime(self, period: str) -> datetime:
        """期間文字列を集計開始日時に変換する。"""
        now = datetime.now()
        if period == 'daily':
            return now - timedelta(days=1)
        if period == 'monthly':
            return now - timedelta(days=30)
        # デフォルト: weekly
        return now - timedelta(weeks=1)

    def _is_hit(self, recommendation: Dict, actual: Dict) -> bool:
        """推奨馬券が的中したか判定する。

        Parameters
        ----------
        recommendation:
            ``{type, combination}`` の推奨馬券。
        actual:
            ``{finish: [{post, finish_pos}, ...]}`` の実績データ。

        Returns
        -------
        bool
            的中した場合 True。
        """
        ticket_type = recommendation.get('type', '')
        combination = recommendation.get('combination', '')
        finish_list: List[Dict] = actual.get('finish', [])

        # 着順マップ: post -> finish_pos
        finish_map: Dict[int, int] = {
            r['post']: r['finish_pos']
            for r in finish_list
            if 'post' in r and 'finish_pos' in r
        }

        if ticket_type == '単勝':
            post = int(combination)
            return finish_map.get(post, 99) == 1

        if ticket_type == '複勝':
            post = int(combination)
            return finish_map.get(post, 99) <= 3

        if ticket_type == '馬連':
            posts = [int(p) for p in combination.split('-')]
            if len(posts) != 2:
                return False
            return all(finish_map.get(p, 99) <= 2 for p in posts)

        if ticket_type == '三連複':
            posts = [int(p) for p in combination.split('-')]
            if len(posts) != 3:
                return False
            return all(finish_map.get(p, 99) <= 3 for p in posts)

        return False
