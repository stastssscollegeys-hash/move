"""バックテスト - 過去データでの予測精度検証"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from db import repository as db
from core.formatter import OutputFormatter

logger = logging.getLogger(__name__)


def run(months: int = 3) -> Dict[str, Any]:
    """過去データでバックテストを実行する。

    Parameters
    ----------
    months:
        遡る月数（デフォルト3ヶ月）。

    Returns
    -------
    Dict
        バックテスト結果サマリー。
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"[backtest] 期間: {start_str} ～ {end_str}（{months}ヶ月）")

    # tracking レコードを取得
    records = db.get_tracking_by_period(start_str, end_str)
    if not records:
        print("[backtest] 対象期間のトラッキングデータがありません。")
        print("  → まず予想（--race / --all）と結果取り込み（--results）を実行してください。")
        return {}

    # 集計
    total_bet = 0
    total_payout = 0
    total_bet_ex = 0      # 外れ値除外版
    total_payout_ex = 0
    outlier_threshold = 100.0

    by_type: Dict[str, Dict[str, int]] = {}
    race_ids = set()

    for r in records:
        race_ids.add(r.get("race_id"))
        bet = r.get("bet_amount") or 100
        odds = r.get("odds") or 0.0
        is_hit = bool(r.get("is_hit"))
        payout = r.get("payout") or 0

        ticket_type = r.get("ticket_type", "不明")
        if ticket_type not in by_type:
            by_type[ticket_type] = {"hit": 0, "total": 0, "bet": 0, "payout": 0}

        by_type[ticket_type]["total"] += 1
        by_type[ticket_type]["bet"] += bet
        by_type[ticket_type]["payout"] += payout

        total_bet += bet
        total_payout += payout

        if is_hit:
            by_type[ticket_type]["hit"] += 1

        # 外れ値除外集計
        if odds <= outlier_threshold:
            total_bet_ex += bet
            total_payout_ex += payout

    # ROI
    roi = total_payout / total_bet if total_bet > 0 else 0.0
    roi_ex = total_payout_ex / total_bet_ex if total_bet_ex > 0 else 0.0

    # 消去精度
    elim_correct = 0
    elim_total = 0
    for race_id in race_ids:
        preds = db.get_predictions(race_id)
        actuals = db.get_actual_results(race_id)
        if not actuals:
            continue
        top3 = {a.get("horse_id") for a in actuals if (a.get("finish") or 99) <= 3}
        for p in preds:
            if p.get("is_eliminated"):
                elim_total += 1
                if p.get("horse_id") not in top3:
                    elim_correct += 1

    elim_accuracy = elim_correct / elim_total if elim_total > 0 else 0.0

    # 結果表示
    formatter = OutputFormatter()
    sep = "=" * 54

    print(f"\n{sep}")
    print(f"  バックテスト結果（{start_str} ～ {end_str}）")
    print(sep)
    print(f"対象レース数  : {len(race_ids)}レース")
    print(f"購入馬券数    : {len(records)}点")
    print(f"投資額合計    : {total_bet:,}円")
    print(f"回収額合計    : {total_payout:,}円")
    print(f"-" * 54)

    print("\n【馬券種別 成績】")
    for ttype, stats in by_type.items():
        hit_rate = stats["hit"] / stats["total"] if stats["total"] > 0 else 0.0
        type_roi = stats["payout"] / stats["bet"] if stats["bet"] > 0 else 0.0
        print(
            f"  {ttype:<6s}: "
            f"{stats['hit']}/{stats['total']} "
            f"的中率{hit_rate * 100:5.1f}%  "
            f"回収率{type_roi * 100:5.1f}%"
        )

    print(f"\n【総合回収率】")
    print(f"  通常       : {roi * 100:.1f}%")
    print(f"  外れ値除外 : {roi_ex * 100:.1f}%  （{outlier_threshold:.0f}倍超除外）")

    print(f"\n【消去精度】")
    print(f"  消去馬が3着以内に来なかった率: {elim_accuracy * 100:.1f}%  "
          f"（{elim_correct}/{elim_total}）")

    # 過学習チェック
    num_trials = len(records)
    if num_trials < 200:
        print(f"\n[INFO] 試行回数{num_trials}回 — 統計的有意性には200回以上必要")
    else:
        print(f"\n[INFO] 試行回数{num_trials}回 — 統計的に有意な水準です")

    # ROI が高すぎる場合の警告
    if roi > 1.5:
        print(
            f"\n[ALERT] ROI {roi * 100:.1f}% は高すぎる可能性があります。"
            "データ漏洩や過学習を確認してください。"
        )

    print(sep)

    result = {
        "period": f"{start_str} ～ {end_str}",
        "num_races": len(race_ids),
        "num_bets": len(records),
        "total_bet": total_bet,
        "total_payout": total_payout,
        "roi": roi,
        "roi_outlier_excluded": roi_ex,
        "hit_rates": {
            t: stats["hit"] / stats["total"] if stats["total"] > 0 else 0.0
            for t, stats in by_type.items()
        },
        "elimination_accuracy": elim_accuracy,
    }
    return result
