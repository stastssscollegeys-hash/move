#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
predict.py -- keiba-predictor CLI

使い方:
  python predict.py --race 202506011201        # 1レース予想
  python predict.py --all tokyo               # 開催全レース予想
  python predict.py --results 2025-06-01      # 結果取り込み
  python predict.py --report --period weekly  # サマリーレポート
  python predict.py --backtest --months 3     # バックテスト
  python predict.py --train                   # モデル再学習
"""
from __future__ import annotations

import argparse
import sys


# ── インポートヘルパー ─────────────────────────────────────────────────────
def _require(module_path: str, hint: str = ""):
    """モジュールをインポートし、失敗時に丁寧なエラーを出す。"""
    import importlib
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        pkg = module_path.split(".")[0]
        print(f"[ERROR] モジュール '{module_path}' を読み込めませんでした。")
        print(f"  原因: {e}")
        if hint:
            print(f"  ヒント: {hint}")
        else:
            print(f"  ヒント: pip install -r requirements.txt を実行してください。")
        sys.exit(1)


# ── サブコマンドハンドラ ───────────────────────────────────────────────────
def cmd_race(race_id: str) -> None:
    """1レース予想を実行する。"""
    print(f"[predict] レース予想を開始します: {race_id}")
    pipeline = _require(
        "core.pipeline",
        "src/keiba-predictor/core/pipeline.py が存在するか確認してください。",
    )
    pipeline.run_single(race_id)


def cmd_all(venue_id: str) -> None:
    """開催全レースを予想する。"""
    print(f"[predict] 開催全レース予想を開始します: {venue_id}")
    pipeline = _require(
        "core.pipeline",
        "src/keiba-predictor/core/pipeline.py が存在するか確認してください。",
    )
    pipeline.run_venue(venue_id)


def cmd_results(date: str) -> None:
    """指定日のレース結果を取り込む。"""
    print(f"[predict] 結果取り込みを開始します: {date}")
    collector = _require(
        "core.result_collector",
        "src/keiba-predictor/core/result_collector.py が存在するか確認してください。",
    )
    collector.collect(date)


def cmd_report(period: str) -> None:
    """サマリーレポートを出力する。"""
    valid = ("weekly", "monthly")
    if period not in valid:
        print(f"[ERROR] --period は {valid} のいずれかを指定してください。")
        sys.exit(1)
    print(f"[predict] サマリーレポートを生成します: {period}")
    reporter = _require(
        "tracking.reporter",
        "src/keiba-predictor/tracking/reporter.py が存在するか確認してください。",
    )
    reporter.generate(period)


def cmd_backtest(months: int) -> None:
    """過去データでバックテストを実行する。"""
    if months < 1:
        print("[ERROR] --months は 1 以上の整数を指定してください。")
        sys.exit(1)
    print(f"[predict] バックテストを開始します: 過去 {months} ヶ月")
    backtester = _require(
        "core.backtester",
        "src/keiba-predictor/core/backtester.py が存在するか確認してください。",
    )
    backtester.run(months)


def cmd_train() -> None:
    """LightGBM モデルを再学習する。"""
    print("[predict] モデル再学習を開始します")
    trainer = _require(
        "engines.trainer",
        "src/keiba-predictor/engines/trainer.py が存在するか確認してください。",
    )
    trainer.train()


# ── CLI パーサー ──────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="predict.py",
        description="keiba-predictor: smartrc.jp + LightGBM + elimination + EV-based",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python predict.py --race 202506011201
  python predict.py --all tokyo
  python predict.py --results 2025-06-01
  python predict.py --report --period weekly
  python predict.py --report --period monthly
  python predict.py --backtest --months 3
  python predict.py --train
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--race",
        metavar="RACEID",
        help="1レース予想 (例: 202506011201)",
    )
    group.add_argument(
        "--all",
        metavar="VENUEID",
        help="開催全レース予想 (例: tokyo)",
    )
    group.add_argument(
        "--results",
        metavar="DATE",
        help="結果取り込み (例: 2025-06-01)",
    )
    group.add_argument(
        "--report",
        action="store_true",
        help="サマリーレポート出力",
    )
    group.add_argument(
        "--backtest",
        action="store_true",
        help="バックテスト実行",
    )
    group.add_argument(
        "--train",
        action="store_true",
        help="モデル再学習",
    )

    parser.add_argument(
        "--period",
        choices=["weekly", "monthly"],
        default="weekly",
        help="レポート期間 (--report 時に使用, デフォルト: weekly)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        metavar="N",
        help="バックテスト期間（月数, デフォルト: 3）",
    )

    return parser


# ── エントリポイント ───────────────────────────────────────────────────────
def main() -> None:
    # DB 初期化（初回起動時のみテーブル作成）
    try:
        from db.repository import init_db
        init_db()
    except Exception as e:
        print(f"[WARN] DB 初期化をスキップしました: {e}")

    parser = build_parser()
    args = parser.parse_args()

    if args.race:
        cmd_race(args.race)
    elif args.all:
        cmd_all(args.all)
    elif args.results:
        cmd_results(args.results)
    elif args.report:
        cmd_report(args.period)
    elif args.backtest:
        cmd_backtest(args.months)
    elif args.train:
        cmd_train()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
