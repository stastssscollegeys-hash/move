"""
repository.py — SQLite データアクセス層
DB パス: ~/.keiba/keiba.db（リポジトリ外）
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── DB パス ────────────────────────────────────────────────────────────────
DB_DIR  = Path.home() / ".keiba"
DB_PATH = DB_DIR / "keiba.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


# ── 接続ヘルパー ───────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── DB 初期化 ──────────────────────────────────────────────────────────────
def init_db() -> None:
    """schema.sql を実行してテーブルを作成する。"""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with _connect() as conn:
        conn.executescript(schema)
    print(f"[repository] DB initialized: {DB_PATH}")


# ── races ──────────────────────────────────────────────────────────────────
def save_race(race: Dict[str, Any]) -> None:
    sql = """
    INSERT OR REPLACE INTO races
        (race_id, date, venue, race_num, distance, surface,
         condition, weather, num_runners, cushion_value, moisture, week_of_meeting)
    VALUES
        (:race_id, :date, :venue, :race_num, :distance, :surface,
         :condition, :weather, :num_runners, :cushion_value, :moisture, :week_of_meeting)
    """
    with _connect() as conn:
        conn.execute(sql, race)


def get_race(race_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM races WHERE race_id = ?", (race_id,)
        ).fetchone()
    return dict(row) if row else None


def get_races_by_date(date: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM races WHERE date = ? ORDER BY venue, race_num",
            (date,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_races_by_venue(venue_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    if date:
        sql = "SELECT * FROM races WHERE venue = ? AND date = ? ORDER BY race_num"
        params = (venue_id, date)
    else:
        sql = "SELECT * FROM races WHERE venue = ? ORDER BY date, race_num"
        params = (venue_id,)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ── horses ─────────────────────────────────────────────────────────────────
def save_horse(horse: Dict[str, Any]) -> None:
    cols = [
        "horse_id", "race_id", "gate", "post", "name", "sex", "age",
        "weight_carried", "jockey", "trainer", "east_west",
        "body_weight", "weight_change", "est_popularity", "popularity_rank",
        "est_rank", "win_odds", "ten_1f", "last_3f", "cr_value",
        "dirt_share", "distance_share", "win_rate", "place_rate", "show_rate",
        "tb_position", "tb_pace", "sire_line", "bms_line", "sire_sub", "bms_sub",
    ]
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO horses ({col_list}) VALUES ({placeholders})"
    with _connect() as conn:
        conn.execute(sql, {c: horse.get(c) for c in cols})


def save_horses(horses: List[Dict[str, Any]]) -> None:
    for h in horses:
        save_horse(h)


def get_horses(race_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM horses WHERE race_id = ? ORDER BY post",
            (race_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_horse(horse_id: str, race_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM horses WHERE horse_id = ? AND race_id = ?",
            (horse_id, race_id),
        ).fetchone()
    return dict(row) if row else None


# ── past_results ───────────────────────────────────────────────────────────
def save_past_result(result: Dict[str, Any]) -> None:
    cols = [
        "horse_id", "race_id", "race_date", "venue", "distance", "surface",
        "condition", "finish", "time_seconds", "margin",
        "passing_1", "passing_2", "passing_3", "passing_4",
        "last_3f", "ten_1f", "body_weight", "weight_change",
    ]
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT INTO past_results ({col_list}) VALUES ({placeholders})"
    with _connect() as conn:
        conn.execute(sql, {c: result.get(c) for c in cols})


def save_past_results(results: List[Dict[str, Any]]) -> None:
    for r in results:
        save_past_result(r)


def get_past_results(horse_id: str, race_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM past_results
               WHERE horse_id = ? AND race_id = ?
               ORDER BY race_date DESC""",
            (horse_id, race_id),
        ).fetchall()
    return [dict(r) for r in rows]


# ── predictions ────────────────────────────────────────────────────────────
def save_prediction(pred: Dict[str, Any]) -> None:
    cols = [
        "race_id", "horse_id", "predicted_win_prob", "predicted_show_prob",
        "elimination_rule", "is_eliminated",
        "expected_value_win", "expected_value_place", "recommended",
    ]
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT INTO predictions ({col_list}) VALUES ({placeholders})"
    with _connect() as conn:
        conn.execute(sql, {c: pred.get(c) for c in cols})


def save_predictions(preds: List[Dict[str, Any]]) -> None:
    for p in preds:
        save_prediction(p)


def get_predictions(race_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE race_id = ? ORDER BY predicted_win_prob DESC",
            (race_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_recommended_predictions(race_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM predictions
               WHERE race_id = ? AND recommended = 1
               ORDER BY expected_value_win DESC""",
            (race_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── actual_results ─────────────────────────────────────────────────────────
def save_actual_result(result: Dict[str, Any]) -> None:
    cols = ["race_id", "horse_id", "finish", "time_seconds", "win_odds_final", "show_odds_final"]
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO actual_results ({col_list}) VALUES ({placeholders})"
    with _connect() as conn:
        conn.execute(sql, {c: result.get(c) for c in cols})


def save_actual_results(results: List[Dict[str, Any]]) -> None:
    for r in results:
        save_actual_result(r)


def get_actual_results(race_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM actual_results WHERE race_id = ? ORDER BY finish",
            (race_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── tracking ───────────────────────────────────────────────────────────────
def save_tracking(ticket: Dict[str, Any]) -> None:
    cols = [
        "race_id", "ticket_type", "combination",
        "odds", "expected_value", "bet_amount", "is_hit", "payout",
    ]
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT INTO tracking ({col_list}) VALUES ({placeholders})"
    with _connect() as conn:
        conn.execute(sql, {c: ticket.get(c) for c in cols})


def save_tracking_batch(tickets: List[Dict[str, Any]]) -> None:
    for t in tickets:
        save_tracking(t)


def get_tracking(race_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tracking WHERE race_id = ?",
            (race_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_tracking_by_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    sql = """
    SELECT t.*, r.date, r.venue, r.race_num
    FROM tracking t
    JOIN races r ON t.race_id = r.race_id
    WHERE r.date BETWEEN ? AND ?
    ORDER BY r.date, r.venue, r.race_num
    """
    with _connect() as conn:
        rows = conn.execute(sql, (start_date, end_date)).fetchall()
    return [dict(r) for r in rows]


def update_tracking_result(tracking_id: int, is_hit: int, payout: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tracking SET is_hit = ?, payout = ? WHERE id = ?",
            (is_hit, payout, tracking_id),
        )


# ── weight_configs ─────────────────────────────────────────────────────────
def save_weight_config(config: Dict[str, Any], backtest_hit_rate: float, backtest_roi: float) -> None:
    sql = """
    INSERT INTO weight_configs (config_json, backtest_hit_rate, backtest_roi)
    VALUES (?, ?, ?)
    """
    with _connect() as conn:
        conn.execute(sql, (json.dumps(config, ensure_ascii=False), backtest_hit_rate, backtest_roi))


def get_latest_weight_config() -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM weight_configs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["config"] = json.loads(d["config_json"])
    return d


def get_weight_config_history(limit: int = 10) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM weight_configs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["config"] = json.loads(d["config_json"])
        result.append(d)
    return result
