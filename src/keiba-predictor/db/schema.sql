-- races: レース情報
CREATE TABLE IF NOT EXISTS races (
    race_id          TEXT PRIMARY KEY,
    date             TEXT NOT NULL,
    venue            TEXT NOT NULL,
    race_num         INTEGER NOT NULL,
    distance         INTEGER NOT NULL,
    surface          TEXT NOT NULL,   -- 'turf' | 'dirt'
    condition        TEXT,            -- 良/稍重/重/不良
    weather          TEXT,
    num_runners      INTEGER,
    cushion_value    REAL,
    moisture         REAL,
    week_of_meeting  INTEGER          -- 開催週（1〜8）
);

-- horses: 出走馬情報
CREATE TABLE IF NOT EXISTS horses (
    horse_id         TEXT NOT NULL,
    race_id          TEXT NOT NULL REFERENCES races(race_id),
    gate             INTEGER,
    post             INTEGER,
    name             TEXT NOT NULL,
    sex              TEXT,
    age              INTEGER,
    weight_carried   REAL,
    jockey           TEXT,
    trainer          TEXT,
    east_west        TEXT,            -- '東' | '西'
    body_weight      INTEGER,
    weight_change    INTEGER,
    est_popularity   INTEGER,         -- 推定人気順位
    popularity_rank  INTEGER,         -- 確定人気順位
    est_rank         INTEGER,         -- 推定着順
    win_odds         REAL,
    ten_1f           REAL,            -- 前半1F速度指数
    last_3f          REAL,            -- 後半3F速度指数
    cr_value         REAL,            -- コースレート
    dirt_share       REAL,            -- ダート適性比率
    distance_share   REAL,            -- 距離適性比率
    win_rate         REAL,
    place_rate       REAL,
    show_rate        REAL,
    tb_position      TEXT,            -- トラックバイアス：位置
    tb_pace          TEXT,            -- トラックバイアス：ペース
    sire_line        TEXT,
    bms_line         TEXT,
    sire_sub         TEXT,
    bms_sub          TEXT,
    PRIMARY KEY (horse_id, race_id)
);

-- past_results: 過去5走
CREATE TABLE IF NOT EXISTS past_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    horse_id         TEXT NOT NULL,
    race_id          TEXT NOT NULL,
    race_date        TEXT NOT NULL,
    venue            TEXT,
    distance         INTEGER,
    surface          TEXT,
    condition        TEXT,
    finish           INTEGER,
    time_seconds     REAL,
    margin           REAL,
    passing_1        INTEGER,
    passing_2        INTEGER,
    passing_3        INTEGER,
    passing_4        INTEGER,
    last_3f          REAL,
    ten_1f           REAL,
    body_weight      INTEGER,
    weight_change    INTEGER,
    FOREIGN KEY (horse_id, race_id) REFERENCES horses(horse_id, race_id)
);

-- predictions: 予想結果
CREATE TABLE IF NOT EXISTS predictions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id              TEXT NOT NULL REFERENCES races(race_id),
    horse_id             TEXT NOT NULL,
    predicted_win_prob   REAL,
    predicted_show_prob  REAL,
    elimination_rule     TEXT,        -- 消去ルールID (例: 'ELIM-003')
    is_eliminated        INTEGER NOT NULL DEFAULT 0,  -- 0/1
    expected_value_win   REAL,
    expected_value_place REAL,
    recommended          INTEGER NOT NULL DEFAULT 0   -- 0/1
);

-- actual_results: 実績
CREATE TABLE IF NOT EXISTS actual_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id          TEXT NOT NULL REFERENCES races(race_id),
    horse_id         TEXT NOT NULL,
    finish           INTEGER,
    time_seconds     REAL,
    win_odds_final   REAL,
    show_odds_final  REAL
);

-- tracking: 馬券トラッキング
CREATE TABLE IF NOT EXISTS tracking (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id        TEXT NOT NULL REFERENCES races(race_id),
    ticket_type    TEXT NOT NULL,   -- '単勝' | '複勝' | '馬連' etc.
    combination    TEXT NOT NULL,   -- '3' | '3-7' etc.
    odds           REAL,
    expected_value REAL,
    bet_amount     INTEGER,
    is_hit         INTEGER,         -- 0/1/NULL(未確定)
    payout         INTEGER
);

-- weight_configs: 重み履歴
CREATE TABLE IF NOT EXISTS weight_configs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    config_json         TEXT NOT NULL,
    backtest_hit_rate   REAL,
    backtest_roi        REAL
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_races_date         ON races(date);
CREATE INDEX IF NOT EXISTS idx_horses_race_id     ON horses(race_id);
CREATE INDEX IF NOT EXISTS idx_past_results_horse ON past_results(horse_id);
CREATE INDEX IF NOT EXISTS idx_predictions_race   ON predictions(race_id);
CREATE INDEX IF NOT EXISTS idx_actual_race        ON actual_results(race_id);
CREATE INDEX IF NOT EXISTS idx_tracking_race      ON tracking(race_id);
