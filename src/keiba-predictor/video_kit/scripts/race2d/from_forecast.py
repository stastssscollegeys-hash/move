# -*- coding: utf-8 -*-
"""展開予想図（これから走るレース）の race2d JSON を作る（2026-11-19）
脚質＝予想 AI（src/keiba-predictor/core/pipeline.py「脚質判定（前走の通過順位から）」）と同じ決め方：
  前走の4コーナーの順位が 2番手以内＝逃げ／頭数の1/3（最低4）以内＝先行／2/3（最低8）以内＝差し／それより後ろ＝追い込み
馬番が要るので、枠順の発表のあと（レースの2日前の午後）に動かす。

使い方:
  python from_forecast.py smartrc <race_id 16桁> <出力.json> [--jvlink <JV-Linkのフォルダ>] [--pred <predictions.json>] [--ana <馬番>]
      出走馬と前走は smartrc から取る（競馬予想の一式の scraper/smartrc_api.py・場所は KVC_PREDICTOR_DIR）
  python from_forecast.py race2d <race2d.json> <出力.json> [--jvlink ...]
      終わったレースの JSON の脚質（style）で組む（道具の確認用）
--jvlink を付けると、同じ競馬場・芝ダ・距離の過去のレースのラップの中央値を使う（無ければ200mごと12.0秒）
--pred（予想の JSON）の honmei を「軸」、--ana の馬番を「穴」として札を付ける
"""
import json, sys, argparse, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from course_key import course_key   # 2026-11-20 内回り・外回り・直線をトラックコードで分ける

STYLE = {1: "逃げ", 2: "先行", 3: "差し", 4: "追い込み"}
VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}


def style_from_c4(c4, n):
    """pipeline.py と同じ決め方（1逃げ 2先行 3差し 4追い込み）"""
    try:
        c4, n = int(c4), int(n or 16)
    except (TypeError, ValueError):
        return None
    if c4 <= 0: return None
    if c4 <= 2: return 1
    if c4 <= max(4, n // 3): return 2
    if c4 <= max(8, n * 2 // 3): return 3
    return 4


def median_laps(jv, venue_code, surface, D):
    tk = "1" if surface == "芝" else "2"
    rows = []
    with open(Path(jv) / "races.jsonl", encoding="utf-8") as f:
        for l in f:
            if f'"venue_code": "{venue_code}"' not in l or f'"distance": "{D}"' not in l: continue
            r = json.loads(l)
            if r["year"] < "2022" or not r["track_cd"].startswith(tk): continue
            lp = [int(x) for x in r["lap_times"].split(",") if x.strip() and int(x) > 0]
            if lp: rows.append(lp)
    n = max((len(x) for x in rows), default=0)
    rows = [x for x in rows if len(x) == n]
    if not rows: return None, 0
    return [round(statistics.median(c) / 10, 1) for c in zip(*rows)], len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["smartrc", "race2d"]); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--jvlink"); ap.add_argument("--pred"); ap.add_argument("--ana", type=int, action="append", default=[])
    ap.add_argument("--jiku", type=int, action="append", default=[])
    a = ap.parse_args()
    if a.kind == "race2d":
        base = json.loads(Path(a.src).read_text(encoding="utf-8"))
        race = dict(base["race"]); rid = base.get("race_id", "")
        horses = [dict(umaban=h["umaban"], waku=h["waku"], name=h["name"], style=h.get("style")) for h in base["horses"]]
        venue_code = rid[8:10] if len(rid) == 16 else "05"
    else:
        rid = a.src
        import os   # 予想ツールの場所（既定の場所以外なら環境変数 KVC_PREDICTOR_DIR）
        sys.path.insert(0, os.environ.get("KVC_PREDICTOR_DIR") or str(Path(__file__).resolve().parents[6] / "src" / "keiba-predictor"))
        try:
            from scraper.smartrc_api import SmartRCAPI
        except ImportError:
            sys.exit("smartrc の道具（scraper/smartrc_api.py）が見つかりません。競馬予想の一式（keiba-yosou）のフォルダを環境変数 KVC_PREDICTOR_DIR に入れてください（例：export KVC_PREDICTOR_DIR=~/keiba-yosou）")
        api = SmartRCAPI()
        info = next((r for r in api.fetch_races(rid[:8]) if r.get("rcode") == rid), None)
        runners = api.fetch_runners(rid)
        api.save_cache()
        if not info or not runners:
            sys.exit("出走馬がまだ出ていません。枠順の発表のあと（レースの2日前の午後）に動かしてください")
        venue_code = rid[8:10]
        surface = "芝" if str(info.get("track", "1")).startswith("1") else "ダート"
        race = dict(name=(info.get("name") or "").strip() or f"{int(rid[-2:])}R", date=f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}",
                    venue=VENUE.get(venue_code, venue_code), surface=surface, distance=int(info["range"]), track_cd=str(info.get("track") or ""))
        horses = []
        for r in runners:
            f = api._format_runner(r)
            past = api._extract_past_results(r)
            st = style_from_c4(past[0].get("corner4"), past[0].get("horse_count")) if past else None
            horses.append(dict(umaban=int(f.get("umaban") or 0), waku=int(f.get("waku") or 0), name=(f.get("horse_name") or f.get("name") or "").strip(), style=st))
    race["course"] = course_key(race["venue"], race.get("track_cd")) if race.get("track_cd") else f"{race['venue']}_{race['surface']}"   # 2026-11-20 内回り・外回り
    laps, nref = (median_laps(a.jvlink, venue_code, race["surface"], race["distance"]) if a.jvlink else (None, 0))
    if not laps:
        n = -(-race["distance"] // 200); laps = [12.0] * n
    race["laps"] = laps; race["runners"] = len(horses)
    jiku = set(a.jiku)
    if a.pred:
        pr = json.loads(Path(a.pred).read_text(encoding="utf-8"))["races"].get(rid, {})
        hon = next((p["horse_name"] for p in pr.get("picks", []) if p.get("mark") == "honmei"), None)
        jiku |= {h["umaban"] for h in horses if h["name"] == hon}
    for h in horses:
        h["mark"] = "軸" if h["umaban"] in jiku else ("穴" if h["umaban"] in a.ana else None)
    nige = sum(1 for h in horses if h["style"] == 1)
    unknown = [h["umaban"] for h in horses if not h["style"]]
    out = dict(source=a.kind, mode="forecast", race_id=rid, race=race, horses=sorted(horses, key=lambda h: h["umaban"]),
               forecast=dict(nige=nige, pace="速くなりそう" if nige >= 2 else ("落ち着きそう" if nige == 0 else "平均くらい"),
                             laps_from=f"過去{nref}レースのラップの中央値" if nref else "仮のラップ（200mごと12.0秒）", unknown_style=unknown))
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {a.out}  {race['name']} {race['venue']}{race['surface']}{race['distance']}m {len(horses)}頭  逃げ{nige}頭→ペース{out['forecast']['pace']}"
          f"  ラップ＝{out['forecast']['laps_from']}" + (f"  脚質の分からない馬 {unknown}（差しとして並べる）" if unknown else ""))


if __name__ == "__main__":
    main()
