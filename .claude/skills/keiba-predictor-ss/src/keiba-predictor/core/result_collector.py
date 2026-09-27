"""レース結果取り込み - 実績データの収集と DB 保存"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scraper.smartrc import SmartRCScraper
from db import repository as db

logger = logging.getLogger(__name__)


def collect(date: str) -> None:
    """指定日のレース結果を取り込む。

    Parameters
    ----------
    date:
        ``'2026-03-24'`` または ``'20260324'`` 形式の日付文字列。
    """
    # 日付を正規化（ハイフンなし8桁に統一）
    normalized = date.replace("-", "")
    if not re.match(r"^\d{8}$", normalized):
        print(f"[ERROR] 不正な日付形式です: {date}（例: 2026-03-24）")
        return

    print(f"[result_collector] {normalized} の結果を取り込み中...")

    # DB に保存済みの予想レースを取得
    display_date = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:8]}"
    predicted_races = db.get_races_by_date(display_date)

    if not predicted_races:
        # ハイフンなし形式でも検索
        predicted_races = db.get_races_by_date(normalized)

    if not predicted_races:
        print(f"[INFO] {display_date} の予想データがDBにありません。"
              "先に予想を実行してください。")
        return

    scraper = SmartRCScraper()
    collected = 0

    for race in predicted_races:
        race_id = race["race_id"]
        print(f"  {race.get('venue', '')} {race.get('race_num', '')}R: ", end="")

        result = _fetch_result(scraper, race_id)
        if result is None:
            print("結果未取得（レース未実施または取得失敗）")
            continue

        # DB に保存
        try:
            for entry in result:
                db.save_actual_result({
                    "race_id": race_id,
                    "horse_id": entry.get("horse_id"),
                    "finish": entry.get("finish"),
                    "time_seconds": entry.get("time_seconds"),
                    "win_odds_final": entry.get("win_odds_final"),
                    "show_odds_final": entry.get("show_odds_final"),
                })

            # 予測との照合
            _evaluate_predictions(race_id, result)
            collected += 1
            print(f"OK（{len(result)}頭）")
        except Exception as e:
            print(f"DB保存エラー: {e}")
            logger.warning("結果保存失敗 %s: %s", race_id, e)

    print(f"\n[result_collector] {collected}/{len(predicted_races)} レースの結果を取り込みました")


def _fetch_result(scraper: SmartRCScraper, race_id: str) -> Optional[List[Dict]]:
    """レース結果ページをスクレイピングする。

    結果ページの URL パターンは出馬表と同じ構造を想定し、
    着順・タイム・確定オッズを抽出する。
    取得できない場合は None を返す。
    """
    try:
        raw = scraper.fetch_race_card(race_id)
        if raw is None:
            return None

        horses = raw.get("horses", [])
        if not horses:
            return None

        results = []
        for h in horses:
            past = h.get("past_results") or []
            # 最新走が今回のレース結果の可能性がある
            # （結果反映後のページでは着順が入る）
            finish = h.get("finish")
            if finish is None and past:
                finish = past[0].get("finish")

            results.append({
                "horse_id": h.get("horse_id"),
                "horse_name": h.get("horse_name"),
                "finish": finish,
                "time_seconds": _parse_time(h.get("time") or (past[0].get("time") if past else None)),
                "win_odds_final": h.get("win_odds"),
                "show_odds_final": None,
            })

        # 着順でソート（着順なしは末尾）
        results.sort(key=lambda x: x.get("finish") or 999)
        return results if any(r.get("finish") for r in results) else None

    except Exception as e:
        logger.warning("結果取得失敗 %s: %s", race_id, e)
        return None


def _parse_time(time_str: Optional[str]) -> Optional[float]:
    """タイム文字列を秒数に変換する。"""
    if not time_str:
        return None
    try:
        # "1:34.5" → 94.5
        if ":" in time_str:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        return float(time_str)
    except (ValueError, IndexError):
        return None


def _evaluate_predictions(race_id: str, results: List[Dict]) -> None:
    """予測と実績を照合し、tracking テーブルを更新する。"""
    try:
        tracking_records = db.get_tracking(race_id)
        if not tracking_records:
            return

        # 着順マップ: horse_id -> finish
        finish_map: Dict = {}
        for r in results:
            hid = r.get("horse_id")
            if hid and r.get("finish"):
                finish_map[hid] = r["finish"]

        # 馬番 -> 着順マップ（tracking は馬番ベースの combination を持つ）
        post_finish: Dict[int, int] = {}
        predictions = db.get_predictions(race_id)
        for pred in predictions:
            hid = pred.get("horse_id")
            if hid and hid in finish_map:
                # horse テーブルから post を逆引き
                horse = db.get_horse(hid, race_id)
                if horse:
                    post_finish[horse.get("post", 0)] = finish_map[hid]

        for record in tracking_records:
            tid = record.get("id")
            if tid is None:
                continue
            combination = record.get("combination", "")
            ticket_type = record.get("ticket_type", "")
            odds = record.get("odds", 0.0)

            is_hit = _check_hit(ticket_type, combination, post_finish)
            payout = int(record.get("bet_amount", 100) * odds) if is_hit else 0

            db.update_tracking_result(tid, int(is_hit), payout)

    except Exception as e:
        logger.warning("照合処理エラー %s: %s", race_id, e)


def _check_hit(ticket_type: str, combination: str, post_finish: Dict[int, int]) -> bool:
    """馬券が的中したか判定する。"""
    try:
        if ticket_type == "単勝":
            post = int(combination)
            return post_finish.get(post, 99) == 1

        if ticket_type == "複勝":
            post = int(combination)
            return post_finish.get(post, 99) <= 3

        if ticket_type == "馬連":
            posts = [int(p) for p in combination.split("-")]
            return len(posts) == 2 and all(post_finish.get(p, 99) <= 2 for p in posts)

        if ticket_type == "三連複":
            posts = [int(p) for p in combination.split("-")]
            return len(posts) == 3 and all(post_finish.get(p, 99) <= 3 for p in posts)

    except (ValueError, TypeError):
        pass
    return False
