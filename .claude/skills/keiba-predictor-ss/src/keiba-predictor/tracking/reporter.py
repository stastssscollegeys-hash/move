"""サマリーレポート生成 - 週次/月次の成績集計"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from db import repository as db
from core.formatter import OutputFormatter


def generate(period: str = "weekly") -> Dict[str, Any]:
    """サマリーレポートを生成して表示する。

    Parameters
    ----------
    period:
        ``'weekly'`` または ``'monthly'``。
    """
    now = datetime.now()
    if period == "monthly":
        start = now - timedelta(days=30)
        label = f"月次（{start.strftime('%m/%d')}～{now.strftime('%m/%d')}）"
    else:
        start = now - timedelta(weeks=1)
        label = f"週次（{start.strftime('%m/%d')}～{now.strftime('%m/%d')}）"

    start_str = start.strftime("%Y-%m-%d")
    end_str = now.strftime("%Y-%m-%d")

    # tracking データ取得
    records = db.get_tracking_by_period(start_str, end_str)

    if not records:
        print(f"[reporter] {label} のトラッキングデータがありません。")
        return {}

    # 集計
    race_ids = set()
    by_type: Dict[str, Dict[str, int]] = {}
    total_bet = 0
    total_payout = 0
    total_bet_ex = 0
    total_payout_ex = 0
    outlier_threshold = 100.0

    for r in records:
        race_ids.add(r.get("race_id"))
        bet = r.get("bet_amount") or 100
        odds = r.get("odds") or 0.0
        payout = r.get("payout") or 0
        is_hit = bool(r.get("is_hit"))
        ticket_type = r.get("ticket_type", "不明")

        if ticket_type not in by_type:
            by_type[ticket_type] = {"hit": 0, "total": 0, "bet": 0, "payout": 0}

        by_type[ticket_type]["total"] += 1
        by_type[ticket_type]["bet"] += bet
        by_type[ticket_type]["payout"] += payout
        if is_hit:
            by_type[ticket_type]["hit"] += 1

        total_bet += bet
        total_payout += payout

        if odds <= outlier_threshold:
            total_bet_ex += bet
            total_payout_ex += payout

    roi_normal = total_payout / total_bet if total_bet > 0 else 0.0
    roi_ex = total_payout_ex / total_bet_ex if total_bet_ex > 0 else 0.0

    hit_rates = {
        t: stats["hit"] / stats["total"] if stats["total"] > 0 else 0.0
        for t, stats in by_type.items()
    }

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

    # 過学習チェック（簡易: ROI が 1.5 以上なら警告）
    overfitting_alert = roi_normal > 1.5

    # レポートデータ構築
    report_data = {
        "period": label,
        "num_races": len(race_ids),
        "num_bets": len(records),
        "hit_rates": hit_rates,
        "roi": {
            "normal": roi_normal,
            "outlier_excluded": roi_ex,
        },
        "elimination_accuracy": elim_accuracy,
        "skip_accuracy": None,
        "overfitting_alert": overfitting_alert,
    }

    # フォーマットして表示
    formatter = OutputFormatter()
    output = formatter.format_report(report_data)
    print(output)

    # 馬券種別の詳細も表示
    print("\n【馬券種別 詳細】")
    for ttype, stats in by_type.items():
        type_roi = stats["payout"] / stats["bet"] if stats["bet"] > 0 else 0.0
        print(
            f"  {ttype:<6s}: "
            f"{stats['hit']}/{stats['total']}的中  "
            f"投資{stats['bet']:,}円  "
            f"回収{stats['payout']:,}円  "
            f"ROI {type_roi * 100:.1f}%"
        )

    # 統計的有意性
    num_bets = len(records)
    if num_bets < 200:
        print(f"\n[INFO] 試行{num_bets}回 — 統計的有意性には200回以上の試行が必要です")

    return report_data
