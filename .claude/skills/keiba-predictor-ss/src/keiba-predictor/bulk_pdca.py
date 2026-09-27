#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bulk_pdca.py — 過去レース一括検証（PDCA自動化）

使い方:
  python bulk_pdca.py --date 20260322                # 1日分
  python bulk_pdca.py --from 20260301 --to 20260322  # 期間指定
  python bulk_pdca.py --summary                      # DB内の全データ集計
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# パスを通す
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from scraper.smartrc_api import SmartRCAPI, _PLACE_MAP
from core.pipeline import _enrich_horse, _build_race_data, _init_engines
from core.model import PredictionModel
from core.elimination import EliminationFilter
from core.expected_value import ExpectedValueCalculator
from core.difficulty import DifficultyJudge
from db import repository as db


def get_available_dates(api: SmartRCAPI) -> List[str]:
    """smartrc.jpから取得可能な開催日一覧を返す（降順）。"""
    days = api.fetch_days()
    dates = sorted([d.get("rdate", "") for d in days if d.get("rdate")], reverse=True)
    return dates


def predict_race(
    race_data_raw: Dict,
    runners_raw: List[Dict],
    api: SmartRCAPI,
    model: PredictionModel,
    engines: Dict,
    elim_filter: EliminationFilter,
    ev_calc: ExpectedValueCalculator,
    diff_judge: DifficultyJudge,
) -> Optional[Dict]:
    """1レースの予想を実行し、結果を返す（DB保存なし）。"""
    from scraper.smartrc_api import SmartRCAPI as _API

    # _format_race / _format_runner を使ってデータ整形
    date = race_data_raw.get("rdate", "")
    race_info = api._format_race(race_data_raw, date)
    horses = [api._format_runner(r) for r in runners_raw]

    if not horses:
        return None

    race_data = _build_race_data(race_info)

    # エンジンスコア算出
    for horse in horses:
        _enrich_horse(horse, race_data, engines)

    # 難易度判定
    difficulty = diff_judge.judge(race_data, horses)

    # 消去法
    remaining, eliminated = elim_filter.apply(horses, race_data)

    if not remaining:
        return None

    # 特徴量構築 + 予測
    features_list = []
    for horse in remaining:
        features = model.build_features(horse, race_data, engines)
        features["post"] = horse.get("horse_num") or horse.get("gate_num", 0)
        features["name"] = horse.get("horse_name", "不明")
        features["past_performance_score"] = horse.get("ability_score", 50)
        features["jockey_score"] = horse.get("jockey_score", 50)
        features["course_fitness_score"] = horse.get("course_score", 50)
        features["bloodline_course_score_norm"] = horse.get("bloodline_score", 50)
        features["track_bias_score"] = horse.get("bias_score", 50)
        features["condition_score"] = horse.get("condition_score", 50)
        features["trainer_score"] = horse.get("trainer_score", 50)
        features["est_popularity"] = horse.get("est_popularity")
        cr_bonus = horse.get("cr_odds_bonus", 0)
        tb_bonus = horse.get("tb_reversal_bonus", 0)
        features["cr_tb_bonus"] = min(cr_bonus + tb_bonus, 15)
        features["close_finish_bonus"] = horse.get("close_finish_bonus", 0)
        features["career_win_rate"] = horse.get("career_win_rate", 0)
        features["interval_bonus"] = horse.get("interval_bonus", 0)
        features["basic_info_bonus"] = (
            horse.get("futan_bonus", 0) + horse.get("futan_penalty", 0)
            + horse.get("sex_penalty", 0) + horse.get("weight_bonus", 0)
            + horse.get("weight_penalty", 0) + horse.get("rota_penalty", 0)
            + horse.get("ground_bonus", 0) + horse.get("weather_bonus", 0)
            + horse.get("season_sex_bonus", 0) + horse.get("rota_exp_bonus", 0)
            + horse.get("jockey_change_bonus", 0)
        )
        features["upset_score"] = difficulty.get("upset_score", 0)
        features["distance_fit_bonus"] = horse.get("distance_fit_bonus", 0)
        features["weight_stability_bonus"] = horse.get("weight_stability_bonus", 0)
        features["agari_best"] = horse.get("agari_best")
        features["running_style"] = horse.get("running_style", "")
        cr_raw = horse.get("cr_value")
        features["cr_raw"] = float(cr_raw) if cr_raw is not None else 0.0
        features["old_pr"] = horse.get("old_pr", "C")
        features["rota_track_record"] = horse.get("rota_track_record", 0)
        features["gate_score"] = horse.get("gate_score", 0)
        features["race_distance"] = race_data.get("distance", 0)
        features["race_venue"] = race_data.get("venue", "")
        features["race_surface"] = race_data.get("surface", "")
        features["is_local_venue"] = horse.get("is_local_venue", 0)
        features["track_condition"] = race_data.get("condition", "")
        features["ten_has_best"] = horse.get("ten_has")
        features_list.append(features)

    # 先行争い(pace_pressure)
    nige_count = sum(1 for f in features_list if f.get("running_style") == "逃げ")
    for f in features_list:
        f["pace_pressure"] = nige_count

    # 上がり3F相対スコア
    agari_vals = []
    for f in features_list:
        ab = f.get("agari_best")
        if ab is not None:
            try:
                agari_vals.append(float(ab))
            except (ValueError, TypeError):
                pass
    if agari_vals:
        agari_min, agari_max = min(agari_vals), max(agari_vals)
        agari_range = agari_max - agari_min if agari_max > agari_min else 1.0
        for f in features_list:
            ab = f.get("agari_best")
            if ab is not None:
                try:
                    f["agari_rank_score"] = round((agari_max - float(ab)) / agari_range * 10, 1)
                except (ValueError, TypeError):
                    f["agari_rank_score"] = 0
            else:
                f["agari_rank_score"] = 0
    else:
        for f in features_list:
            f["agari_rank_score"] = 0

    # テン相対スコア
    ten_vals = []
    for f in features_list:
        tb = f.get("ten_has_best")
        if tb is not None:
            try:
                ten_vals.append(float(tb))
            except (ValueError, TypeError):
                pass
    if ten_vals:
        ten_min, ten_max = min(ten_vals), max(ten_vals)
        ten_range = ten_max - ten_min if ten_max > ten_min else 1.0
        for f in features_list:
            tb = f.get("ten_has_best")
            if tb is not None:
                try:
                    f["ten_has_rank_score"] = round((ten_max - float(tb)) / ten_range * 10, 1)
                except (ValueError, TypeError):
                    f["ten_has_rank_score"] = 0
            else:
                f["ten_has_rank_score"] = 0
    else:
        for f in features_list:
            f["ten_has_rank_score"] = 0

    predictions = model.predict(features_list)

    # オッズ付与
    odds_map = {h.get("horse_num"): h for h in remaining}
    for pred in predictions:
        h = odds_map.get(pred["post"])
        if h:
            pred["win_odds"] = h.get("win_odds", 0.0)
            pred["show_odds"] = h.get("show_odds") or ((h.get("win_odds") or 0.0) * 0.4)
            pred["est_pop"] = h.get("est_popularity")
            pred["horse_name"] = h.get("horse_name", "")
            pred["cr_value"] = h.get("cr_value")
            pred["jockey"] = h.get("jockey", "")
            pred["age"] = h.get("age")
            pred["sex"] = h.get("sex", "")

    # ◎ = show_prob最高の馬
    if predictions:
        predictions.sort(key=lambda x: x.get("show_prob", 0), reverse=True)
        honmei = predictions[0]
    else:
        honmei = None

    return {
        "race_info": race_info,
        "race_data": race_data,
        "predictions": predictions,
        "honmei": honmei,
        "difficulty": difficulty,
        "remaining": remaining,
        "eliminated": eliminated,
        "horses": horses,
    }


def rcode_to_netkeiba_id(rcode: str) -> str:
    """smartrc rcode → netkeiba race_id に変換する。
    smartrc: 2026032209011004 (date8 + place2 + kai2 + nichi2 + rno2)
    netkeiba: 202609011004    (year4 + place2 + kai2 + nichi2 + rno2)
    """
    return rcode[:4] + rcode[8:]


_RESULT_CACHE_PATH = _ROOT / "netkeiba_cache.json"


def _load_result_cache() -> Dict[str, Dict[str, int]]:
    """ファイルキャッシュからnetkeiba結果を読み込む。"""
    if _RESULT_CACHE_PATH.exists():
        try:
            with open(_RESULT_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_result_cache(cache: Dict[str, Dict[str, int]]) -> None:
    """netkeiba結果をファイルキャッシュに保存する。"""
    with open(_RESULT_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def get_actual_results_netkeiba(rcode: str, session: "requests.Session",
                                 cache: Optional[Dict] = None) -> Dict[int, int]:
    """netkeiba.comからレース結果（着順）を取得する。キャッシュ優先。"""
    from bs4 import BeautifulSoup

    # キャッシュにあればそれを返す
    if cache is not None and rcode in cache:
        return {int(k): v for k, v in cache[rcode].items()}

    netkeiba_id = rcode_to_netkeiba_id(rcode)
    url = f"https://race.netkeiba.com/race/result.html?race_id={netkeiba_id}"

    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        result_table = soup.find("table", class_="RaceTable01")
        if not result_table:
            return {}

        finish_map: Dict[int, int] = {}
        rows = result_table.find_all("tr")
        for row in rows[1:]:  # ヘッダーをスキップ
            cols = row.find_all("td")
            if len(cols) >= 4:
                finish_str = cols[0].get_text(strip=True)
                umaban_str = cols[2].get_text(strip=True)
                try:
                    finish = int(finish_str)
                    umaban = int(umaban_str)
                    finish_map[umaban] = finish
                except (ValueError, TypeError):
                    pass  # 取消・除外等は無視

        # キャッシュに保存
        if cache is not None and finish_map:
            cache[rcode] = {str(k): v for k, v in finish_map.items()}

        return finish_map

    except Exception:
        return {}


def run_date(date_str: str, api: SmartRCAPI, model: PredictionModel,
             engines: Dict, elim_filter: EliminationFilter,
             ev_calc: ExpectedValueCalculator, diff_judge: DifficultyJudge,
             verbose: bool = False,
             result_cache: Optional[Dict] = None) -> List[Dict]:
    """指定日の全レースを予想→結果照合して返す。"""
    import requests as req

    races = api.fetch_races(date_str)
    if not races:
        print(f"  {date_str}: レースなし")
        return []

    # netkeiba用セッション
    nk_session = req.Session()
    nk_session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    })

    results = []
    for race in races:
        rcode = race.get("rcode", "")
        rno = race.get("rno", "?")
        place = race.get("place", "")
        venue = _PLACE_MAP.get(place, place)
        name = race.get("name", "")

        # 出走馬データ取得
        runners = api.fetch_runners(rcode)
        if not runners:
            continue

        # 障害レースはスキップ
        trackkind = race.get("trackkind", "0")
        if trackkind == "2":  # 障害
            if verbose:
                print(f"  {venue}{rno}R: 障害レース → スキップ")
            continue

        # 予想
        pred_result = predict_race(
            race, runners, api, model, engines,
            elim_filter, ev_calc, diff_judge,
        )
        if pred_result is None:
            continue

        # 実績をnetkeiba.comから取得（キャッシュ優先）
        finish_map = get_actual_results_netkeiba(rcode, nk_session, cache=result_cache)

        honmei = pred_result["honmei"]
        if honmei is None:
            continue

        honmei_post = honmei["post"]
        honmei_finish = finish_map.get(honmei_post)
        is_hit = honmei_finish is not None and honmei_finish <= 3

        # 実際の1-3着を取得
        top3 = sorted(
            [(post, fin) for post, fin in finish_map.items() if fin <= 3],
            key=lambda x: x[1],
        )

        result = {
            "date": date_str,
            "venue": venue,
            "race_num": rno,
            "race_name": name,
            "rcode": rcode,
            "honmei_post": honmei_post,
            "honmei_name": honmei.get("horse_name") or honmei.get("name", ""),
            "honmei_show_prob": round(honmei.get("show_prob", 0) * 100, 1),
            "honmei_win_prob": round(honmei.get("win_prob", 0) * 100, 1),
            "honmei_est_pop": honmei.get("est_pop"),
            "honmei_odds": honmei.get("win_odds"),
            "honmei_finish": honmei_finish,
            "is_hit": is_hit,
            "top3": top3,
            "difficulty_score": pred_result["difficulty"].get("score", 0),
            "upset_score": pred_result["difficulty"].get("upset_score", 0),
            "num_runners": len(pred_result["horses"]),
            "surface": pred_result["race_data"].get("surface", ""),
            "distance": pred_result["race_data"].get("distance", 0),
            "condition": pred_result["race_data"].get("condition", ""),
            # 分析用: 2番手の情報
            "predictions_top3": [
                {
                    "post": p["post"],
                    "name": p.get("horse_name") or p.get("name", ""),
                    "show_prob": round(p.get("show_prob", 0) * 100, 1),
                    "finish": finish_map.get(p["post"]),
                }
                for p in pred_result["predictions"][:3]
            ],
        }
        results.append(result)

        # DB保存（tracking用）
        try:
            db.save_race({
                "race_id": rcode,
                "date": date_str,
                "venue": venue,
                "race_num": int(rno) if str(rno).isdigit() else 0,
                "distance": pred_result["race_data"].get("distance", 0),
                "surface": pred_result["race_data"].get("surface", ""),
                "condition": pred_result["race_data"].get("condition", ""),
                "weather": pred_result["race_data"].get("weather"),
                "num_runners": len(pred_result["horses"]),
                "cushion_value": None,
                "moisture": None,
                "week_of_meeting": None,
            })
            show_odds = honmei.get("show_odds") or (honmei.get("win_odds", 0) * 0.4)
            payout = int(100 * show_odds) if is_hit and show_odds else 0
            db.save_tracking({
                "race_id": rcode,
                "ticket_type": "複勝",
                "combination": str(honmei_post),
                "odds": show_odds or 0,
                "expected_value": honmei.get("show_prob", 0) * (show_odds or 0),
                "bet_amount": 100,
                "is_hit": int(is_hit) if honmei_finish is not None else None,
                "payout": payout,
            })
        except Exception as e:
            pass  # DB保存失敗は無視（検証に影響しない）

        if verbose:
            mark = "◯" if is_hit else "✗"
            fin_str = f"{honmei_finish}着" if honmei_finish else "不明"
            print(f"  {mark} {venue}{rno}R {honmei.get('horse_name','')} "
                  f"({honmei.get('est_pop','')}人気) → {fin_str}")

        # キャッシュヒットなら待機不要、APIアクセスした場合のみ待機
        if result_cache is None or rcode not in result_cache:
            time.sleep(3)  # netkeiba BAN防止: 最低3秒間隔

    return results


def print_summary(all_results: List[Dict]) -> None:
    """全結果のサマリーを表示する。"""
    if not all_results:
        print("結果がありません。")
        return

    total = len(all_results)
    # 着順が取得できたレースのみ
    with_finish = [r for r in all_results if r["honmei_finish"] is not None]
    hits = [r for r in with_finish if r["is_hit"]]
    misses = [r for r in with_finish if not r["is_hit"]]

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  PDCA検証結果サマリー")
    print(sep)

    dates = sorted(set(r["date"] for r in all_results))
    print(f"期間        : {dates[0]} ～ {dates[-1]}")
    print(f"開催日数    : {len(dates)}日")
    print(f"対象レース  : {total}R（着順判明: {len(with_finish)}R）")
    print(f"◎複勝的中  : {len(hits)}/{len(with_finish)} "
          f"({len(hits)/len(with_finish)*100:.1f}%)" if with_finish else "")

    # 会場別
    print(f"\n【会場別】")
    venues = sorted(set(r["venue"] for r in with_finish))
    for venue in venues:
        v_races = [r for r in with_finish if r["venue"] == venue]
        v_hits = [r for r in v_races if r["is_hit"]]
        print(f"  {venue}: {len(v_hits)}/{len(v_races)} "
              f"({len(v_hits)/len(v_races)*100:.1f}%)")

    # 荒れ度別
    print(f"\n【荒れ度別】")
    for label, lo, hi in [("堅い(0-2)", 0, 2), ("中間(3-5)", 3, 5), ("荒れ(6+)", 6, 99)]:
        group = [r for r in with_finish if lo <= r.get("upset_score", 0) <= hi]
        if group:
            g_hits = [r for r in group if r["is_hit"]]
            print(f"  {label}: {len(g_hits)}/{len(group)} "
                  f"({len(g_hits)/len(group)*100:.1f}%)")

    # 人気別
    print(f"\n【◎の推定人気別】")
    for label, lo, hi in [("1-2人気", 1, 2), ("3-5人気", 3, 5), ("6人気以下", 6, 99)]:
        group = [r for r in with_finish
                 if r.get("honmei_est_pop") is not None
                 and lo <= (int(r["honmei_est_pop"]) if r["honmei_est_pop"] else 99) <= hi]
        if group:
            g_hits = [r for r in group if r["is_hit"]]
            print(f"  {label}: {len(g_hits)}/{len(group)} "
                  f"({len(g_hits)/len(group)*100:.1f}%)")

    # 芝/ダート別
    print(f"\n【芝/ダート別】")
    for surface in ["芝", "ダート"]:
        group = [r for r in with_finish if surface in r.get("surface", "")]
        if group:
            g_hits = [r for r in group if r["is_hit"]]
            print(f"  {surface}: {len(g_hits)}/{len(group)} "
                  f"({len(g_hits)/len(group)*100:.1f}%)")

    # 距離別
    print(f"\n【距離別】")
    for label, lo, hi in [("短距離(~1400)", 0, 1400), ("マイル(1500-1800)", 1500, 1800),
                           ("中距離(1900-2200)", 1900, 2200), ("長距離(2300~)", 2300, 9999)]:
        group = [r for r in with_finish if lo <= (r.get("distance") or 0) <= hi]
        if group:
            g_hits = [r for r in group if r["is_hit"]]
            print(f"  {label}: {len(g_hits)}/{len(group)} "
                  f"({len(g_hits)/len(group)*100:.1f}%)")

    print(sep)


def print_miss_analysis(all_results: List[Dict]) -> None:
    """外れレースの詳細分析を表示する。"""
    misses = [r for r in all_results
              if r["honmei_finish"] is not None and not r["is_hit"]]
    if not misses:
        print("\n外れレースなし！")
        return

    print(f"\n{'=' * 60}")
    print(f"  外れレース分析（{len(misses)}件）")
    print(f"{'=' * 60}")

    # 外れパターンの集計
    patterns: Dict[str, int] = {
        "大敗(7着以下)": 0,
        "惜敗(4-6着)": 0,
        "荒れレース(upset6+)で外れ": 0,
        "人気薄◎(6番人気以下)で外れ": 0,
        "堅いレースで外れ(upset0-2)": 0,
    }

    for r in misses:
        fin = r["honmei_finish"]
        if fin >= 7:
            patterns["大敗(7着以下)"] += 1
        elif 4 <= fin <= 6:
            patterns["惜敗(4-6着)"] += 1

        if r.get("upset_score", 0) >= 6:
            patterns["荒れレース(upset6+)で外れ"] += 1
        elif r.get("upset_score", 0) <= 2:
            patterns["堅いレースで外れ(upset0-2)"] += 1

        pop = r.get("honmei_est_pop")
        if pop is not None and int(pop) >= 6:
            patterns["人気薄◎(6番人気以下)で外れ"] += 1

    print("\n【外れパターン集計】")
    for pattern, count in sorted(patterns.items(), key=lambda x: -x[1]):
        if count > 0:
            pct = count / len(misses) * 100
            print(f"  {pattern}: {count}件 ({pct:.0f}%)")

    # 外れの詳細（最新20件）
    print(f"\n【外れ詳細（直近20件）】")
    for r in misses[:20]:
        pop_str = f"{r.get('honmei_est_pop','')}人気" if r.get('honmei_est_pop') else ""
        print(f"  {r['date']} {r['venue']}{r['race_num']}R: "
              f"◎{r['honmei_name']}({pop_str}) → {r['honmei_finish']}着  "
              f"[荒れ度{r.get('upset_score',0)} {r['surface']}{r['distance']}m]")
        # 実際のTop3
        top3_str = ", ".join(
            f"{p}番{f}着" for p, f in r.get("top3", [])
        )
        if top3_str:
            print(f"    実際Top3: {top3_str}")


def main():
    parser = argparse.ArgumentParser(
        prog="bulk_pdca.py",
        description="過去レース一括検証（PDCA自動化）",
    )
    parser.add_argument("--date", help="検証する日付 (例: 20260322)")
    parser.add_argument("--from", dest="from_date", help="開始日 (例: 20260301)")
    parser.add_argument("--to", dest="to_date", help="終了日 (例: 20260322)")
    parser.add_argument("--summary", action="store_true", help="DB内の全データ集計")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細表示")
    args = parser.parse_args()

    # DB初期化
    db.init_db()

    api = SmartRCAPI()
    model = PredictionModel()
    model.load()
    engines = _init_engines()
    elim_filter = EliminationFilter()
    ev_calc = ExpectedValueCalculator()
    diff_judge = DifficultyJudge()

    # netkeiba結果キャッシュの読み込み
    result_cache = _load_result_cache()
    cache_size_before = len(result_cache)

    try:
        if args.date:
            # 1日分
            print(f"[bulk_pdca] {args.date} の検証を開始...")
            results = run_date(
                args.date, api, model, engines,
                elim_filter, ev_calc, diff_judge, verbose=True,
                result_cache=result_cache,
            )
            print_summary(results)
            print_miss_analysis(results)

        elif args.from_date and args.to_date:
            # 期間指定
            available = get_available_dates(api)
            target_dates = [
                d for d in available
                if args.from_date <= d <= args.to_date
            ]
            target_dates.sort()  # 古い方から

            print(f"[bulk_pdca] {args.from_date}～{args.to_date} の検証を開始")
            print(f"  対象日数: {len(target_dates)}日")
            print(f"  キャッシュ済み結果: {cache_size_before}レース")

            all_results = []
            for i, date in enumerate(target_dates):
                print(f"\n--- {date} ({i+1}/{len(target_dates)}) ---")
                results = run_date(
                    date, api, model, engines,
                    elim_filter, ev_calc, diff_judge, verbose=args.verbose,
                    result_cache=result_cache,
                )
                all_results.extend(results)

                # 日ごとの簡易集計
                with_finish = [r for r in results if r["honmei_finish"] is not None]
                hits = [r for r in with_finish if r["is_hit"]]
                print(f"  {date}: {len(hits)}/{len(with_finish)} 的中 "
                      f"(累計: {sum(1 for r in all_results if r.get('is_hit'))}"
                      f"/{sum(1 for r in all_results if r['honmei_finish'] is not None)})")

                time.sleep(0.5)  # キャッシュがあればAPIアクセス不要なのでsleep短縮

            print_summary(all_results)
            print_miss_analysis(all_results)

            # 結果をJSONで保存
            output_path = _ROOT / "pdca_results.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            print(f"\n結果を保存しました: {output_path}")

        elif args.summary:
            # DB内のtracking集計
            from core.backtester import run as backtest_run
            backtest_run(months=12)

        else:
            parser.print_help()
            sys.exit(1)

    finally:
        # キャッシュを保存（新しい結果がある場合）
        if len(result_cache) > cache_size_before:
            _save_result_cache(result_cache)
            print(f"[cache] {len(result_cache) - cache_size_before}件の新しい結果をキャッシュしました "
                  f"(合計: {len(result_cache)})")
        api.close()


if __name__ == "__main__":
    main()
