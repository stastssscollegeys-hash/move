"""予想パイプライン - スクレイピング→特徴量→予測→消去→期待値→出力"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# パスを通す
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from scraper.smartrc_api import SmartRCAPI as SmartRCScraper
except ImportError:
    try:
        from scraper.smartrc_pw import SmartRCPlaywright as SmartRCScraper
    except ImportError:
        from scraper.smartrc import SmartRCScraper
from core.model import PredictionModel
from core.elimination import EliminationFilter
from core.expected_value import ExpectedValueCalculator
from core.difficulty import DifficultyJudge
from core.bankroll import BankrollManager
from core.formatter import OutputFormatter
from db import repository as db

logger = logging.getLogger(__name__)


def _init_engines() -> Dict[str, Any]:
    """全エンジンを初期化して返す。"""
    from engines import (
        AbilityEngine, JockeyEngine, CourseEngine,
        BloodlineEngine, BiasEngine, ConditionEngine, TrainerEngine,
    )
    cfg: Dict[str, Any] = {}
    return {
        "ability": AbilityEngine(cfg),
        "jockey": JockeyEngine(cfg),
        "course": CourseEngine(cfg),
        "bloodline": BloodlineEngine(cfg),
        "bias": BiasEngine(cfg),
        "condition": ConditionEngine(cfg),
        "trainer": TrainerEngine(cfg),
    }


def _enrich_horse(horse: Dict, race_info: Dict, engines: Dict) -> Dict:
    """馬データにエンジンスコアと消去法用フィールドを付与する。"""

    # smartrc API のデータ型を正規化（文字列→数値変換）
    for key in ("weight_diff", "horse_weight", "age", "popularity", "est_popularity"):
        val = horse.get(key)
        if val is not None and isinstance(val, str):
            stripped = val.strip()
            if stripped == "" or stripped == "   ":
                horse[key] = None
            else:
                try:
                    horse[key] = int(stripped)
                except ValueError:
                    try:
                        horse[key] = float(stripped)
                    except ValueError:
                        horse[key] = None

    # エンジンスコアを算出
    for name, engine in engines.items():
        try:
            score = engine.calculate_score(horse, race_info)
            horse[f"{name}_score"] = score
        except Exception as e:
            logger.warning("エンジン '%s' のスコア算出失敗: %s", name, e)
            horse[f"{name}_score"] = 0.0

    # 消去法用フィールドの補完
    past = horse.get("past_results") or []
    if past:
        first = past[0]
        horse.setdefault("last_finish", first.get("finish"))
        horse.setdefault("last_popularity", first.get("popularity"))
        # 前走からの休養日数（簡易推定）
        if first.get("date") and race_info.get("date"):
            try:
                from datetime import datetime
                fmt = "%Y%m%d" if len(str(first["date"])) == 8 else "%Y-%m-%d"
                last_dt = datetime.strptime(str(first["date"]), fmt)
                race_fmt = "%Y%m%d" if len(str(race_info["date"])) == 8 else "%Y-%m-%d"
                race_dt = datetime.strptime(str(race_info["date"]), race_fmt)
                horse["rest_days"] = (race_dt - last_dt).days
            except Exception:
                pass

    # 血統×コーススコア（bloodline エンジンの特徴量から取得）
    try:
        bl_features = engines["bloodline"].get_features(horse, race_info)
        horse.setdefault(
            "bloodline_course_score",
            bl_features.get("bloodline_course_score_norm", 50),
        )
    except Exception:
        pass

    # ── PDCA19: 基本情報の確定要素（リサーチ+10170頭統計） ──

    # 斤量比率: 斤量/馬体重（リサーチ: 12.5%超で複勝率-7%）
    futan = horse.get("weight_carried")
    hw = horse.get("horse_weight")
    horse["futan_bonus"] = 0
    horse["futan_penalty"] = 0
    if futan is not None and hw is not None:
        try:
            f = float(futan)
            w = int(hw)
            if w > 0:
                ratio = f / w
                if ratio >= 0.125:    # 12.5%超 → 重すぎ
                    horse["futan_penalty"] = -6
                elif ratio <= 0.11:   # 11%以下 → 軽い（有利）
                    horse["futan_bonus"] = 3
            # 絶対値でも<54kgはペナルティ（軽斤量=弱い馬の証）
            if f < 54:
                horse["futan_penalty"] = -8
        except (ValueError, TypeError):
            pass

    # 性別: 牡24.6%, 牝19.8%, セ12.0%
    # リサーチ: 牡牝差は複勝率で3.1ポイント
    sex = horse.get("sex")
    if sex == "セ" or sex == "騸":
        horse["sex_penalty"] = -5
    elif sex == "牝":
        horse["sex_penalty"] = -2
    else:
        horse["sex_penalty"] = 0

    # 馬体重: 500+kg=27.6%, <440kg=11.6%
    horse["weight_bonus"] = 0
    horse["weight_penalty"] = 0
    if hw is not None:
        try:
            w = int(hw)
            if w < 440:
                horse["weight_penalty"] = -6
            elif w >= 500:
                horse["weight_bonus"] = 3
        except (ValueError, TypeError):
            pass

    # 距離適性（リサーチ: 延長=17.9%, 同距離=23.5%, 短縮=20.5%）
    rota = horse.get("rota_type")
    if rota == "3":  # 延長
        horse["rota_penalty"] = -4
    elif rota == "1":  # 短縮（回収率は最高→穴になりやすい）
        horse["rota_penalty"] = -1
    else:
        horse["rota_penalty"] = 0

    # ── PDCA20: レース条件の確定要素（リサーチ反映） ──

    # 馬場状態×芝ダ（リサーチ: 重ダ→逃げ有利、芝稍重→荒れる）
    condition = race_info.get("condition") or race_info.get("track_condition") or ""
    surface = race_info.get("surface") or ""
    horse["ground_bonus"] = 0
    if "ダート" in surface or "dirt" in surface.lower():
        if condition in ("重", "不良"):
            # ダート重/不良: 1番人気勝率50%。先行馬有利
            pop = horse.get("est_popularity") or horse.get("popularity")
            if pop is not None:
                try:
                    if int(pop) <= 2:
                        horse["ground_bonus"] = 5  # 重ダートは人気馬有利
                except (ValueError, TypeError):
                    pass
            # 馬体重500kg+は重馬場で有利（リサーチ: 520-538kgが最高）
            hw_val = horse.get("horse_weight")
            if hw_val is not None:
                try:
                    if int(hw_val) >= 500:
                        horse["ground_bonus"] += 3
                except (ValueError, TypeError):
                    pass
    elif "芝" in surface:
        if condition in ("稍重", "重", "不良"):
            # 芝の渋い馬場は荒れやすい。パワー型有利
            horse["ground_bonus"] = -1  # 全体的にやや不確実性増

    # 天候（リサーチ: 天候自体より馬場に吸収されるが、雨天は配当変動が激しい）
    weather = race_info.get("weather") or ""
    weather_map = {"1": "晴", "2": "曇", "3": "雨", "4": "小雨", "5": "雪"}
    weather_name = weather_map.get(str(weather), weather)
    horse["weather_bonus"] = 0
    if weather_name in ("雨", "小雨", "雪"):
        # 雨天: 2番人気以下の入れ替わりが激しい → 人気馬の信頼度微減
        pop = horse.get("est_popularity") or horse.get("popularity")
        if pop is not None:
            try:
                if int(pop) >= 4:
                    horse["weather_bonus"] = 1  # 穴馬にわずかなチャンス
                elif int(pop) <= 2:
                    horse["weather_bonus"] = -1  # 人気馬はやや減
            except (ValueError, TypeError):
                pass

    # 性別×季節（リサーチ: 7-8月は牝馬の回収率が上昇）
    date_str = str(race_info.get("date", ""))
    horse["season_sex_bonus"] = 0
    if len(date_str) >= 6:
        try:
            month = int(date_str[4:6])
            sex = horse.get("sex")
            if sex == "牝" and 6 <= month <= 9:
                horse["season_sex_bonus"] = 3  # 夏は牝馬有利
            elif sex == "牝" and (month <= 3 or month >= 11):
                horse["season_sex_bonus"] = -2  # 冬は牝馬不利
        except (ValueError, TypeError):
            pass

    # 距離延長/短縮の経験値（smartrc exp_rota_*）
    horse["rota_exp_bonus"] = 0
    if rota == "1":  # 短縮
        cnt = horse.get("exp_cur_short_cnt") or 0
        wi3 = horse.get("exp_cur_short_wi3") or 0
    elif rota == "3":  # 延長
        cnt = horse.get("exp_cur_long_cnt") or 0
        wi3 = horse.get("exp_cur_long_wi3") or 0
    else:  # 同距離
        cnt = horse.get("exp_cur_same_cnt") or 0
        wi3 = horse.get("exp_cur_same_wi3") or 0
    try:
        cnt_v = int(cnt)
        wi3_v = int(wi3)
        if cnt_v >= 3 and wi3_v / cnt_v >= 0.3:
            horse["rota_exp_bonus"] = 4  # 経験豊富+好走率30%以上
        elif cnt_v >= 2 and wi3_v > 0:
            horse["rota_exp_bonus"] = 2
    except (ValueError, TypeError, ZeroDivisionError):
        pass

    # PDCA29: exp_rota_*（ローテーション経験値）の活用
    # exp_rota_*はローテーション種別（短縮/同距離/延長）での過去好走実績
    horse["rota_track_record"] = 0
    if rota == "1":  # 短縮
        wi3_n5 = horse.get("exp_rota_short_n5_wi3") or 0
        wi5_na = horse.get("exp_rota_short_na_wi5") or 0
    elif rota == "3":  # 延長
        wi3_n5 = horse.get("exp_rota_long_n5_wi3") or 0
        wi5_na = horse.get("exp_rota_long_na_wi5") or 0
    else:  # 同距離
        wi3_n5 = horse.get("exp_rota_same_n5_wi3") or 0
        wi5_na = horse.get("exp_rota_same_na_wi5") or 0
    try:
        n5 = int(wi3_n5)
        na = int(wi5_na)
        if n5 >= 2:
            horse["rota_track_record"] = 5  # 直近5走で2回以上3着以内 = 強い
        elif n5 >= 1 and na >= 3:
            horse["rota_track_record"] = 3  # 直近1回+通算3回以上
        elif na >= 2:
            horse["rota_track_record"] = 1  # 通算で実績あり
    except (ValueError, TypeError):
        pass

    # 乗り替わり検出（jcode vs jcode_before）
    horse["jockey_change_bonus"] = 0
    jcode = horse.get("jcode") if hasattr(horse, 'get') else None
    jcode_before = horse.get("jcode_before") if hasattr(horse, 'get') else None
    # smartrc の生データにjcodeがある場合
    raw = horse.get("_raw") if hasattr(horse, 'get') else None
    if raw:
        jc = raw.get("jcode")
        jcb = raw.get("jcode_before")
        if jc and jcb and jc != jcb:
            horse["jockey_change_bonus"] = 2  # 乗り替わりは微プラス（上位騎手への変更が多い）

    # ── 確定要素の追加算出 ──
    # 脚質判定（前走の通過順位から）
    if past:
        first = past[0]
        c4 = first.get("corner4")
        entry_raw = horse.get("horse_count") or race_info.get("horse_count") or 16
        try:
            c4_val = int(c4) if c4 else None
            entry_val = int(entry_raw) if entry_raw else 16
        except (ValueError, TypeError):
            c4_val = None
            entry_val = 16
        if c4_val is not None:
            if c4_val <= 2:
                horse["running_style"] = "逃げ"
            elif c4_val <= max(4, entry_val // 3):
                horse["running_style"] = "先行"
            elif c4_val <= max(8, entry_val * 2 // 3):
                horse["running_style"] = "差し"
            else:
                horse["running_style"] = "追い込み"

    # 着差評価（前走の着差から能力を補正）
    if past:
        first = past[0]
        diff = first.get("diff_time")
        finish = first.get("finish")
        if diff is not None and finish is not None:
            try:
                diff_val = int(diff) / 10  # 秒に変換
                finish_val = int(finish)
                # 1-3着で僅差（0.3秒以内）→ 実力は上位と遜色ない
                if finish_val <= 3 and diff_val <= 0.3:
                    horse["close_finish_bonus"] = 8
                # 4-5着で僅差（0.5秒以内）→ 巻き返し候補
                elif finish_val <= 5 and diff_val <= 0.5:
                    horse["close_finish_bonus"] = 5
                else:
                    horse["close_finish_bonus"] = 0
            except (ValueError, TypeError):
                horse["close_finish_bonus"] = 0
        else:
            horse["close_finish_bonus"] = 0
    else:
        horse["close_finish_bonus"] = 0

    # 通算勝率（cnt_r1/cnt_all）
    cnt_r1 = horse.get("win_rate")  # scraper で cnt_r1 を win_rate に入れている
    cnt_all = horse.get("total_races")
    if cnt_r1 is not None and cnt_all is not None:
        try:
            r1 = int(cnt_r1)
            total = int(cnt_all)
            if total > 0:
                horse["career_win_rate"] = r1 / total
            else:
                horse["career_win_rate"] = 0
        except (ValueError, TypeError):
            horse["career_win_rate"] = 0
    else:
        horse["career_win_rate"] = 0

    # ── PDCA11: 前走間隔の最適判定 ──
    if past:
        interval = past[0].get("interval")
        if interval is not None:
            try:
                iv = int(interval)
                # 中2-4週（14-28日）が理想、中1週以下は疲労、3ヶ月以上は休養明け
                if 2 <= iv <= 4:
                    horse["interval_bonus"] = 5
                elif iv == 1:
                    horse["interval_bonus"] = -3  # 連闘ペナルティ
                elif iv >= 12:
                    horse["interval_bonus"] = -5  # 長期休養明けペナルティ
                else:
                    horse["interval_bonus"] = 0
            except (ValueError, TypeError):
                horse["interval_bonus"] = 0
        else:
            horse["interval_bonus"] = 0
    else:
        horse["interval_bonus"] = 0

    # ── リサーチ反映: CR値×オッズ乖離ボーナス ──
    # CR値が高い（コース実績あり）のにオッズが高い（市場が過小評価）= 狙い目
    cr = horse.get("cr_value")
    odds = horse.get("win_odds")
    est_pop = horse.get("est_popularity")
    if cr is not None and odds is not None and est_pop is not None:
        try:
            cr_val = float(cr)
            odds_val = float(odds)
            pop_val = int(est_pop)
            # CR値が高い（5以上）のに人気薄（6番人気以下）= 過小評価
            if cr_val >= 5 and pop_val >= 6:
                horse["cr_odds_bonus"] = min(cr_val * 2, 20)  # 最大20点ボーナス
            else:
                horse["cr_odds_bonus"] = 0
        except (ValueError, TypeError):
            horse["cr_odds_bonus"] = 0
    else:
        horse["cr_odds_bonus"] = 0

    # ── リサーチ反映: TB不利好走馬の巻き返し評価 ──
    # 前走で不利なTB（超外/超差）にも関わらず好走 → 能力過小評価
    if past:
        first = past[0]
        tb_io = first.get("tb_io")  # 内外バイアス
        tb_diff = first.get("tb_diff")  # 前後バイアス
        finish = first.get("finish")
        if tb_io and tb_diff and finish:
            try:
                # TB不利（外/超外=高い値）かつ好走（3着以内）= 巻き返し候補
                tb_io_val = str(tb_io).strip()
                finish_val = int(finish)
                if finish_val <= 3 and tb_io_val in ("3", "4"):  # 外/超外
                    horse["tb_reversal_bonus"] = 10  # 巻き返しボーナス
                else:
                    horse["tb_reversal_bonus"] = 0
            except (ValueError, TypeError):
                horse["tb_reversal_bonus"] = 0
        else:
            horse["tb_reversal_bonus"] = 0
    else:
        horse["tb_reversal_bonus"] = 0

    # ── PDCA22: smartrcデータの直接活用（上がり・距離適性・馬体重安定） ──

    # 上がり3Fベスト（agari_has）: 出走馬全体での相対評価は後でやるが、
    # ここでは生値をスコア用に保持
    horse["agari_best"] = horse.get("agari_has")

    # 距離適性（distance_share）: smartrcの1-5段階
    # 5=最高適性, 1=適性低
    ds = horse.get("distance_share")
    horse["distance_fit_bonus"] = 0
    if ds is not None:
        try:
            ds_val = int(ds)
            if ds_val >= 5:
                horse["distance_fit_bonus"] = 6  # 距離ベストマッチ
            elif ds_val >= 4:
                horse["distance_fit_bonus"] = 3
            elif ds_val <= 1:
                horse["distance_fit_bonus"] = -3  # 距離不適性
        except (ValueError, TypeError):
            pass

    # 馬体重変動（weight_diff）: ±5kg以内=安定、±15kg以上=要注意
    wd = horse.get("weight_diff")
    horse["weight_stability_bonus"] = 0
    if wd is not None:
        try:
            wd_val = int(wd)
            if abs(wd_val) <= 4:
                horse["weight_stability_bonus"] = 2  # 安定
            elif abs(wd_val) >= 15:
                horse["weight_stability_bonus"] = -4  # 大幅変動
            elif abs(wd_val) >= 10:
                horse["weight_stability_bonus"] = -2  # やや不安定
        except (ValueError, TypeError):
            pass

    # ── PDCA30+32: コース別枠順スコア ──
    # リサーチ: 中山1600mは内枠有利、ローカル場は開催後半で逆転
    venue = race_info.get("venue", "")
    distance = race_info.get("distance") or 0
    gate = horse.get("gate_num") or horse.get("horse_num") or 0
    week = race_info.get("week") or 1  # 開催何週目か
    horse["gate_score"] = 0
    horse["is_local_venue"] = 0  # ローカル場フラグ
    try:
        d = int(distance)
        g = int(gate)
        w = int(week) if week else 1

        # PDCA32: ローカル場判定（小回り・馬場劣化が激しい）
        local_venues = ("小倉", "福島", "新潟", "函館", "札幌")
        is_local = any(v in str(venue) for v in local_venues)
        if is_local:
            horse["is_local_venue"] = 1

        # PDCA32: 開催前半/後半で枠順バイアスが逆転（ローカル場特有）
        is_late_week = w >= 4  # 4週目以降は後半

        if "中山" in str(venue) and 1400 <= d <= 1800:
            if g <= 4:
                horse["gate_score"] = 5
            elif g <= 8:
                horse["gate_score"] = 1
            elif g >= 13:
                horse["gate_score"] = -4
        elif "阪神" in str(venue) and d == 1600:
            if g <= 4:
                horse["gate_score"] = 2
            elif g >= 14:
                horse["gate_score"] = -2
        elif is_local:
            # ローカル場: 開催前半は内枠有利、後半は外枠有利に逆転
            if is_late_week:
                # 開催後半: 内ラチ沿いが荒れて外枠有利
                if g <= 4:
                    horse["gate_score"] = -2  # 内枠ペナルティ
                elif g >= 12:
                    horse["gate_score"] = 3   # 外枠ボーナス
            else:
                # 開催前半: 通常通り内枠有利
                if d <= 1200:
                    if g <= 4:
                        horse["gate_score"] = 4
                    elif g >= 12:
                        horse["gate_score"] = -3
                else:
                    if g <= 4:
                        horse["gate_score"] = 3
                    elif g >= 13:
                        horse["gate_score"] = -2
    except (ValueError, TypeError):
        pass

    return horse


def _build_race_data(race_info: Dict) -> Dict:
    """race_info を各モジュールが期待する race_data 形式に変換する。"""
    num_runners = race_info.get("horse_count") or 0
    grade_str = race_info.get("grade") or ""
    is_graded = any(g in grade_str for g in ("G1", "G2", "G3"))

    return {
        "race_id": race_info.get("race_id", ""),
        "date": race_info.get("date", ""),
        "venue": race_info.get("venue", ""),
        "race_num": race_info.get("race_num", ""),
        "race_name": race_info.get("title", ""),
        "surface": race_info.get("surface", ""),
        "distance": race_info.get("distance", 0),
        "condition": race_info.get("track_condition", ""),
        "weather": race_info.get("weather", ""),
        "num_runners": num_runners,
        "grade": grade_str,
        "is_graded": is_graded,
        "cushion_value": race_info.get("cushion_value", "N/A"),
    }


def run_single(race_id: str) -> Optional[Dict]:
    """1レースの予想パイプラインを実行する。

    Returns
    -------
    Dict or None
        予想結果の辞書。取得失敗時は None。
    """
    scraper = SmartRCScraper()
    model = PredictionModel()
    model.load()
    elim_filter = EliminationFilter()
    ev_calc = ExpectedValueCalculator()
    diff_judge = DifficultyJudge()
    bankroll = BankrollManager()
    formatter = OutputFormatter()
    engines = _init_engines()

    # ── 1. データ取得 ──
    print(f"[pipeline] smartrc.jp からデータを取得中... ({race_id})")
    raw = scraper.fetch_race_card(race_id)
    if raw is None:
        print(f"[ERROR] レースデータを取得できませんでした: {race_id}")
        return None

    race_info = raw["race_info"]
    horses = raw["horses"]
    race_data = _build_race_data(race_info)

    if not horses:
        print(f"[ERROR] 出走馬データが空です: {race_id}")
        return None

    print(f"[pipeline] {len(horses)}頭の出走馬を取得しました")

    # ── 2. エンジンスコア算出 ──
    for horse in horses:
        _enrich_horse(horse, race_data, engines)

    # ── 3. 難易度判定 ──
    difficulty = diff_judge.judge(race_data, horses)
    if difficulty["should_skip"]:
        print(
            f"[pipeline] 難易度{difficulty['score']} → 見送り推奨 "
            f"（{', '.join(difficulty['reasons'])}）"
        )

    # ── 4. 消去法 ──
    remaining, eliminated = elim_filter.apply(horses, race_data)
    print(f"[pipeline] 消去法: {len(eliminated)}頭消去 → {len(remaining)}頭残存")

    # ── 5. LightGBM / ルールベース予測 ──
    features_list = []
    for horse in remaining:
        features = model.build_features(horse, race_data, engines)
        features["post"] = horse.get("horse_num") or horse.get("gate_num", 0)
        features["name"] = horse.get("horse_name", "不明")
        # ルールベース用のスコアキーを追加
        features["past_performance_score"] = horse.get("ability_score", 50)
        features["jockey_score"] = horse.get("jockey_score", 50)
        features["course_fitness_score"] = horse.get("course_score", 50)
        features["bloodline_course_score_norm"] = horse.get("bloodline_score", 50)
        features["track_bias_score"] = horse.get("bias_score", 50)
        features["condition_score"] = horse.get("condition_score", 50)
        features["trainer_score"] = horse.get("trainer_score", 50)
        features["est_popularity"] = horse.get("est_popularity")
        # リサーチ反映: CR×オッズ乖離 + TB巻き返しボーナス
        # ボーナスは独立スコアキーとして加算（既存スコアを壊さない）
        cr_bonus = horse.get("cr_odds_bonus", 0)
        tb_bonus = horse.get("tb_reversal_bonus", 0)
        features["cr_tb_bonus"] = min(cr_bonus + tb_bonus, 15)
        # PDCA10: 確定要素ボーナス
        features["close_finish_bonus"] = horse.get("close_finish_bonus", 0)
        features["career_win_rate"] = horse.get("career_win_rate", 0)
        features["interval_bonus"] = horse.get("interval_bonus", 0)
        # PDCA20: 全確定要素ボーナス（リサーチ10要素反映）
        features["basic_info_bonus"] = (
            horse.get("futan_bonus", 0)
            + horse.get("futan_penalty", 0)
            + horse.get("sex_penalty", 0)
            + horse.get("weight_bonus", 0)
            + horse.get("weight_penalty", 0)
            + horse.get("rota_penalty", 0)
            + horse.get("ground_bonus", 0)
            + horse.get("weather_bonus", 0)
            + horse.get("season_sex_bonus", 0)
            + horse.get("rota_exp_bonus", 0)
            + horse.get("jockey_change_bonus", 0)
        )
        # PDCA21: 荒れ度スコアを渡す（人気ボーナス調整に使用）
        features["upset_score"] = difficulty.get("upset_score", 0)
        # PDCA22: smartrc直接活用（距離適性+馬体重安定+上がり3F）
        features["distance_fit_bonus"] = horse.get("distance_fit_bonus", 0)
        features["weight_stability_bonus"] = horse.get("weight_stability_bonus", 0)
        features["agari_best"] = horse.get("agari_best")
        # PDCA23: 脚質をfeaturesに渡す（上がり+先行の組み合わせ評価用）
        features["running_style"] = horse.get("running_style", "")
        # PDCA24: CR値の生データを渡す（荒れるレースでの重み強化用）
        cr_raw = horse.get("cr_value")
        features["cr_raw"] = float(cr_raw) if cr_raw is not None else 0.0
        # PDCA26: 昇降級フラグ（old_pr: A=大幅昇級, B=昇級, C=同クラス, D=降級）
        features["old_pr"] = horse.get("old_pr", "C")
        # PDCA29: ローテーション実績
        features["rota_track_record"] = horse.get("rota_track_record", 0)
        # PDCA30: コース別枠順スコア
        features["gate_score"] = horse.get("gate_score", 0)
        # PDCA31: レース条件をfeaturesに渡す（距離別・会場別ロジック用）
        features["race_distance"] = race_data.get("distance", 0)
        features["race_venue"] = race_data.get("venue", "")
        features["race_surface"] = race_data.get("surface", "")
        # PDCA32: ローカル場フラグ
        features["is_local_venue"] = horse.get("is_local_venue", 0)
        # PDCA33: 馬場状態をfeaturesに渡す
        features["track_condition"] = race_data.get("condition", "")
        # PDCA26: テンの生データ（相対スコアは後で計算）
        features["ten_has_best"] = horse.get("ten_has")
        features_list.append(features)

    # PDCA28: 先行争い頭数(pace_pressure)を算出
    # 逃げ馬・先行馬の頭数を数えてハイペース確率を計算
    senkou_count = 0
    nige_count = 0
    for f in features_list:
        rs = f.get('running_style', '')
        if rs == '逃げ':
            nige_count += 1
        elif rs == '先行':
            senkou_count += 1
    pace_pressure = nige_count  # 逃げ馬の頭数 = 先行争いの激しさ
    for f in features_list:
        f['pace_pressure'] = pace_pressure

    # PDCA22: 上がり3Fの相対スコア（出走馬内での順位）
    agari_vals = []
    for f in features_list:
        ab = f.get("agari_best")
        if ab is not None:
            try:
                agari_vals.append(float(ab))
            except (ValueError, TypeError):
                pass
    if agari_vals:
        agari_min = min(agari_vals)
        agari_max = max(agari_vals)
        agari_range = agari_max - agari_min if agari_max > agari_min else 1.0
        for f in features_list:
            ab = f.get("agari_best")
            if ab is not None:
                try:
                    # 上がりが速いほどスコアが高い（0-10点）
                    normalized = (agari_max - float(ab)) / agari_range
                    f["agari_rank_score"] = round(normalized * 10, 1)
                except (ValueError, TypeError):
                    f["agari_rank_score"] = 0
            else:
                f["agari_rank_score"] = 0
    else:
        for f in features_list:
            f["agari_rank_score"] = 0

    # PDCA26: テン(前半3F)の相対スコア（出走馬内での順位）
    ten_vals = []
    for f in features_list:
        tb = f.get("ten_has_best")
        if tb is not None:
            try:
                ten_vals.append(float(tb))
            except (ValueError, TypeError):
                pass
    if ten_vals:
        ten_min = min(ten_vals)
        ten_max = max(ten_vals)
        ten_range = ten_max - ten_min if ten_max > ten_min else 1.0
        for f in features_list:
            tb = f.get("ten_has_best")
            if tb is not None:
                try:
                    # テンが速いほどスコアが高い（0-10点）
                    normalized = (ten_max - float(tb)) / ten_range
                    f["ten_has_rank_score"] = round(normalized * 10, 1)
                except (ValueError, TypeError):
                    f["ten_has_rank_score"] = 0
            else:
                f["ten_has_rank_score"] = 0
    else:
        for f in features_list:
            f["ten_has_rank_score"] = 0

    predictions = model.predict(features_list)

    # ── 6. 期待値判定 + 根拠データ付与 ──
    odds_map = {h.get("horse_num"): h for h in remaining}
    for pred in predictions:
        h = odds_map.get(pred["post"])
        if h:
            pred["win_odds"] = h.get("win_odds", 0.0)
            pred["show_odds"] = h.get("show_odds") or (h.get("win_odds", 0.0) * 0.4)
            # 根拠データ
            pred["jockey"] = h.get("jockey", "")
            pred["sire"] = h.get("sire", "")
            pred["bms"] = h.get("bms", "")
            pred["age"] = h.get("age")
            pred["sex"] = h.get("sex", "")
            pred["weight_carried"] = h.get("weight_carried")
            pred["est_pop"] = h.get("est_popularity")
            pred["cr_value"] = h.get("cr_value")
            # エンジンスコア
            pred["scores"] = {
                "ability": round(h.get("ability_score", 0), 1),
                "jockey": round(h.get("jockey_score", 0), 1),
                "course": round(h.get("course_score", 0), 1),
                "bloodline": round(h.get("bloodline_score", 0), 1),
                "condition": round(h.get("condition_score", 0), 1),
                "trainer": round(h.get("trainer_score", 0), 1),
            }
            # 過去走サマリー
            past = h.get("past_results") or []
            pred["past_summary"] = []
            for p in past[:3]:
                finish = p.get("finish")
                dist = p.get("distance")
                f3 = p.get("last_3f")
                pop = p.get("popularity")
                pred["past_summary"].append({
                    "finish": finish,
                    "distance": dist,
                    "last_3f": f3,
                    "popularity": pop,
                })

    recommendations = ev_calc.get_recommendations(predictions, odds_data={})

    # ── 7. 馬場バイアス ──
    bias_info = None
    try:
        bias_features = engines["bias"].get_features(horses[0], race_data)
        bias_info = {
            "inner_advantage": bias_features.get("inner_advantage", 0),
            "front_advantage": bias_features.get("front_advantage", 0),
        }
    except Exception:
        pass

    # ── 8. 出力 ──
    # 消去馬に post / name を付与
    for h in eliminated:
        h["post"] = h.get("horse_num") or h.get("gate_num", 0)
        h["name"] = h.get("horse_name", "不明")

    output = formatter.format_prediction(
        race_data=race_data,
        eliminated=eliminated,
        remaining=remaining,
        predictions=predictions,
        recommendations=recommendations,
        difficulty=difficulty,
        bias=bias_info,
    )
    print(output)

    # ── 9. DB 保存 ──
    try:
        db.save_race({
            "race_id": race_data["race_id"],
            "date": race_data["date"],
            "venue": race_data["venue"],
            "race_num": race_data.get("race_num"),
            "distance": race_data["distance"],
            "surface": race_data["surface"],
            "condition": race_data["condition"],
            "weather": race_data.get("weather"),
            "num_runners": race_data["num_runners"],
            "cushion_value": None,
            "moisture": None,
            "week_of_meeting": None,
        })
        for pred in predictions:
            h = odds_map.get(pred["post"])
            db.save_prediction({
                "race_id": race_data["race_id"],
                "horse_id": h.get("horse_id") if h else None,
                "predicted_win_prob": pred["win_prob"],
                "predicted_show_prob": pred["show_prob"],
                "elimination_rule": None,
                "is_eliminated": 0,
                "expected_value_win": pred.get("win_odds", 0) * pred["win_prob"],
                "expected_value_place": None,
                "recommended": 1 if any(
                    r["combination"] == str(pred["post"]) for r in recommendations
                ) else 0,
            })
        for h in eliminated:
            db.save_prediction({
                "race_id": race_data["race_id"],
                "horse_id": h.get("horse_id"),
                "predicted_win_prob": 0.0,
                "predicted_show_prob": 0.0,
                "elimination_rule": h.get("elimination_rule"),
                "is_eliminated": 1,
                "expected_value_win": 0.0,
                "expected_value_place": 0.0,
                "recommended": 0,
            })
    except Exception as e:
        logger.warning("DB 保存中にエラー: %s", e)

    return {
        "race_data": race_data,
        "predictions": predictions,
        "eliminated": eliminated,
        "remaining": remaining,
        "recommendations": recommendations,
        "difficulty": difficulty,
    }


def run_venue(venue_id: str) -> List[Dict]:
    """開催全レース（最大12レース）の予想を実行する。

    Parameters
    ----------
    venue_id:
        ``'20260324hanshin'`` 形式、または ``'tokyo'`` のような短縮形。
    """
    scraper = SmartRCScraper()

    # 短縮形の場合は今日の日付を付加
    if len(venue_id) <= 10 and not venue_id[0].isdigit():
        from datetime import date
        today = date.today().strftime("%Y%m%d")
        venue_id = f"{today}{venue_id}"

    print(f"[pipeline] 開催全レース予想: {venue_id}")
    all_race_data = scraper.fetch_all_races(venue_id)

    if not all_race_data:
        print(f"[ERROR] レースデータを取得できませんでした: {venue_id}")
        return []

    results = []
    for race_data in all_race_data:
        race_id = race_data["race_info"].get("race_id", "")
        print(f"\n{'─' * 54}")
        try:
            result = run_single(race_id)
            if result:
                results.append(result)
        except Exception as e:
            print(f"[ERROR] {race_id} の予想に失敗: {e}")

    print(f"\n[pipeline] 全{len(results)}レースの予想が完了しました")
    return results
