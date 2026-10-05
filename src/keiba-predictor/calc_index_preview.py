# -*- coding: utf-8 -*-
"""
calc_index_preview.py — 枠順確定前に独自指数を算出する（2026-09-30新規）
==========================================================================
通常の指数は collect_weekend_bigdata.py が netkeiba の出馬表キャッシュから計算するが、
枠順確定前は出馬表が取れない（netkeibaのページがJS描画で中身を返さない）。
一方で **calc_dokuji_forecast の式そのものは枠順が無くても動く設計** になっている:
    F06枠バイアス → 65点固定 ／ F07馬番内外 → 内外比0.5で全馬同じ
    F09馬体重    → 70点固定 ／ F15EV・F16人気乖離 → 50点固定
つまりこの5因子（重み計29%）は**全馬同点**になるので、**順位には影響しない**。
残り71%ぶんを蓄積DBの過去走から計算すれば、枠順前でも順位づけができる。

本スクリプトは calc_dokuji_forecast と同じ式・同じ重み（daily_pdca/config.py）を使い、
過去走を蓄積DB（race_results.json）から供給する。

使い方: python calc_index_preview.py <入力JSON>
入力JSON: {"races":[{"name","venue","surface","distance","grade","horses":[{"name","kin","age","sex"}]}]}
          枠順確定後は各馬に "waku","umaban" を足すと F06・F07 も本番と同じ式で入る（2026-10-02）。
          "prev_rank","prev_index" を足すと出力にそのまま引き継ぐ（枠順前との比較用）。
出力: 同ディレクトリに index_ranking.json（指数順の一覧＋因子内訳）
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DAILY = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca"
sys.path.insert(0, str(DAILY))
from config import WEIGHTS, GATE_BIAS, SURFACE_SC          # 本番と同じ設定を読む
sys.path.insert(0, str(Path(__file__).resolve().parent))
from index_factors import time_index, waku_score

DB = DAILY / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))


def sec(t):
    """'1:26.3' → 86.3 秒"""
    s = str(t or "")
    if ":" in s:
        m, r = s.split(":", 1)
        try:
            return int(m) * 60 + float(r)
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def meters(d):
    s = str(d or "")
    n = "".join(c for c in s if c.isdigit())
    return int(n) if n else None


def is_turf(d):
    return str(d or "").startswith("芝")


# ── 過去走を馬ごとに整形（本番の past と同じ形に寄せる）──────────────
past_of = collections.defaultdict(list)
for r in rows:
    nm = r.get("馬名")
    if not nm:
        continue
    past_of[nm].append({
        "date": r.get("date"), "rank": r.get("着順int"),
        "distance": meters(r.get("距離")), "trackkind": 1 if is_turf(r.get("距離")) else 2,
        "last_3f": r.get("後3F"), "stime": sec(r.get("タイム")),
        "fr_baba": "A" if str(r.get("馬場状態") or "良")[:1] == "良" else "B",
    })
for v in past_of.values():
    v.sort(key=lambda p: p["date"] or "", reverse=True)     # 本番同様 past[0] が直近

# ── 騎手・厩舎の勝率（本番は ML統計。ここは蓄積DBの実勝率で代用）──────
def winrate(field):
    agg = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        k, f = r.get(field), r.get("着順int")
        if k and f:
            agg[k][0] += 1
            agg[k][1] += 1 if f == 1 else 0
    return {k: v[1] / v[0] for k, v in agg.items() if v[0] >= 30}


JK, TR = winrate("騎手"), winrate("厩舎")


def lookup_rate(table, name):
    """DBの表記ゆれ（姓のみ等）に対応して引く"""
    if not name:
        return 0.0
    if name in table:
        return table[name]
    for k in table:
        if k and (k in name or name.startswith(k[:2])) and len(k) >= 2:
            return table[k]
    return 0.0


def score(h, race, kin_avg, n):
    dist, venue = race["distance"], race["venue"]
    surface = race["surface"]
    track_now = 1 if surface == "芝" else 2
    past = past_of.get(h["name"], [])
    F = {}

    f3 = [p["last_3f"] for p in past if p.get("last_3f")]
    F["F01_後3F"] = min(100.0, max(0.0, (36.0 - min(f3)) / 3.0 * 100.0)) if f3 else 50.0

    same_dist = [p for p in past if p.get("distance") and abs(p["distance"] - dist) <= 200 and p.get("stime")]
    # 2026-10-02: 本番（collect_weekend_bigdata）と同じ実測ベースのタイム指数に統一（index_factors.time_index）
    F["F02_タイム"] = time_index(past, track_now)

    rk = [p["rank"] for p in past[:3] if p.get("rank")]
    if rk:
        def d(r):
            return 0.0 if r <= 1 else 0.3 if r == 2 else 0.6 if r == 3 else min(5.0, 0.6 + (r - 3) * 0.5)
        F["F03_着差"] = max(0.0, 100.0 - sum(d(r) for r in rk) / len(rk) * 15.0)
    else:
        F["F03_着差"] = 50.0
    wins = sum(1 for p in past if p.get("rank") == 1)
    if wins:
        F["F03_着差"] = min(100.0, F["F03_着差"] + wins * 5.0)

    jw = lookup_rate(JK, h.get("jockey"))
    F["F04_騎手"] = min(100.0, 50.0 + jw * 280.0) if jw > 0 else 50.0
    tw = lookup_rate(TR, h.get("trainer"))
    F["F05_厩舎"] = min(100.0, 50.0 + tw * 280.0) if tw > 0 else 50.0

    # 枠順が無い段階は本番コードと同じ扱い（全馬同点なので順位に効かない）。
    # 入力に waku / umaban があれば（枠順確定後）、本番(collect_weekend_bigdata)と同じ式で採点する。
    waku, banum = h.get("waku"), h.get("umaban")
    F["F06_枠"] = waku_score(venue, waku) if waku else 65.0
    inner = 1.0 - (int(banum) - 1) / max(n - 1, 1) if (waku and banum) else 0.5
    F["F07_馬番"] = {"東京": 55.0 + inner * 25.0, "京都": 60.0 + inner * 35.0,
                     "中山": 60.0 + inner * 30.0, "阪神": 58.0 + inner * 28.0}.get(venue, 60.0 + inner * 15.0)

    f08 = 72.0 if dist <= 1200 else 75.0 if dist <= 1600 else 78.0 if dist <= 2000 else 74.0 if dist <= 2400 else 70.0
    if same_dist:
        good = sum(1 for p in same_dist if p.get("rank") and p["rank"] <= 3)
        f08 = f08 * 0.6 + good / len(same_dist) * 100.0 * 0.4
    F["F08_距離"] = f08

    F["F09_体重"] = 70.0                                   # 当日発表
    kin = h.get("kin")
    F["F10_斤量"] = min(100.0, max(0.0, 65.0 + (kin_avg - kin) * 4.0)) if kin else 60.0
    F["F11_性別"] = {"牡": 60.0, "牝": 62.0, "セ": 58.0}.get(h.get("sex"), 60.0)
    F["F12_年齢"] = {2: 80, 3: 88, 4: 98, 5: 95, 6: 85, 7: 75}.get(h.get("age"), 68.0)
    g = race.get("grade", "")
    F["F13_クラス"] = 90.0 if "G1" in g else 83.0 if "G2" in g else 77.0 if "G3" in g else 72.0

    f14 = float(SURFACE_SC.get((surface, venue), 70))
    ss = [p for p in past if p.get("trackkind") == track_now]
    if ss:
        good = sum(1 for p in ss if p.get("rank") and p["rank"] <= 3)
        f14 = f14 * 0.7 + good / len(ss) * 100.0 * 0.3
    F["F14_馬場"] = f14

    F["F15_EV"] = 50.0                                     # オッズ未発表
    F["F16_乖離"] = 50.0
    F["F17_頭数"] = max(40.0, 100.0 - (n - 8) * 3.0)

    key = {"F01_後3F": "後3F能力", "F02_タイム": "タイム指数", "F03_着差": "着差スコア", "F04_騎手": "騎手",
           "F05_厩舎": "厩舎", "F06_枠": "枠バイアス", "F07_馬番": "馬番内外", "F08_距離": "距離適性",
           "F09_体重": "馬体重変化", "F10_斤量": "斤量", "F11_性別": "性別", "F12_年齢": "年齢",
           "F13_クラス": "クラス", "F14_馬場": "馬場適性", "F15_EV": "EV", "F16_乖離": "人気乖離",
           "F17_頭数": "頭数影響"}
    total = sum(v * WEIGHTS[key[k]] for k, v in F.items())
    return round(min(100.0, max(0.0, total)), 1), {k: round(v, 1) for k, v in F.items()}, len(past)


def main():
    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    out = []
    for race in data["races"]:
        hs = race["horses"]
        kins = [h["kin"] for h in hs if h.get("kin")]
        kin_avg = sum(kins) / len(kins) if kins else 57.0
        n = len(hs)
        ranked = []
        for h in hs:
            s, F, nrun = score(h, race, kin_avg, n)
            ranked.append({"name": h["name"], "index": s, "runs": nrun, "factors": F,
                           "age": h.get("age"), "kin": h.get("kin"),
                           "waku": h.get("waku"), "umaban": h.get("umaban"),
                           "prev_rank": h.get("prev_rank"), "prev_index": h.get("prev_index")})
        ranked.sort(key=lambda x: -x["index"])
        for i, r in enumerate(ranked, 1):
            r["rank"] = i
        out.append({"race": race["name"], "venue": race["venue"],
                    "course": f"{race['surface']}{race['distance']}m", "horses": ranked})
        print(f"\n■ {race['name']}（{race['venue']} {race['surface']}{race['distance']}m・{n}頭）")
        print(f"{'順':>3} {'馬名':<14}{'指数':>6}{'走':>4}  主な内訳（タイム/着差/騎手/距離/馬場）")
        for r in ranked:
            F = r["factors"]
            print(f"{r['rank']:>3} {r['name']:<14}{r['index']:>6}{r['runs']:>4}  "
                  f"{F['F02_タイム']:>5.0f}/{F['F03_着差']:>5.0f}/{F['F04_騎手']:>5.0f}/"
                  f"{F['F08_距離']:>5.0f}/{F['F14_馬場']:>5.0f}")
    dst = src.parent / "index_ranking.json"
    import datetime
    drawn = all(h.get("waku") for race in data["races"] for h in race["horses"])
    stage = ("枠順確定後（枠・馬番を反映。馬体重・オッズの3因子は全馬同点＝順位に影響しない）" if drawn
             else "枠順確定前（枠・馬番・馬体重・オッズの5因子は全馬同点＝順位に影響しない）")
    dst.write_text(json.dumps({"compiled": datetime.date.today().isoformat(), "stage": stage,
                               "races": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存: {dst}")


if __name__ == "__main__":
    main()
