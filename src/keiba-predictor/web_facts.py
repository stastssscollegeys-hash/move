# -*- coding: utf-8 -*-
"""web_facts.py — 印の根拠に使う「馬ごとの事実」を蓄積DBから出す（2026-11-06 新設）
前走からの間隔／距離変化／芝ダ替わり／同じコース・同じ距離の成績／想定脚質（前走までの最初のコーナー位置）／前走の上がり／斤量の変化／馬体重
  python web_facts.py --date 20261107 --race 東京9 --uma 6,15,2
JV版の entry_digest.py の代わり（調教なし）。出力: 標準出力と {OUT}/{日付}_{レース}_facts.json
"""
import argparse
import collections
import datetime
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import ev_live as L
import web_live as WL


def days(a, b):
    f = lambda s: datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return (f(b) - f(a)).days


def meters(d):
    n = "".join(c for c in str(d or "") if c.isdigit())
    return int(n) if n else 0


def facts_for(race, ums, rows_by_name, date):
    out = []
    cur_surf = race["dist"][0]
    cur_m = meters(race["dist"])
    for h in race["horses"]:
        if ums and h["uma"] not in ums:
            continue
        rs = sorted(rows_by_name.get(h["name"].replace(" ", ""), {}).values(), key=lambda r: r["date"], reverse=True)
        f = dict(uma=h["uma"], name=h["name"], jockey=h["jockey"], trainer=h["trainer"], n_runs=len(rs))
        if rs:
            last = rs[0]
            f["interval_days"] = days(last["date"], date)
            f["last"] = f"{last['date'][4:6]}/{last['date'][6:]} {last['競馬場']} {last.get('レース名') or last.get('条件')} {last['距離']} {last.get('着順') or '?'}着/{last.get('頭数') or '?'}頭 {last.get('人気') or '?'}番人気"
            f["last_dist_change"] = meters(last["距離"]) - cur_m
            f["surface_change"] = (last["距離"][0] != cur_surf)
            f["last_l3_rank"] = last.get("後3F順位")
            f["last_weight"] = last.get("馬体重")
            f["kin_change"] = None
            # 想定脚質: 直近4走の最初のコーナー位置/頭数
            pos = []
            for r in rs[:4]:
                try:
                    c1 = int(str(r.get("コーナー通過") or "").split("-")[0])
                    pos.append(c1 / float(r.get("頭数") or 1))
                except (ValueError, TypeError):
                    pass
            if pos:
                avg = sum(pos) / len(pos)
                f["style"] = "逃げ・先行" if avg <= 0.3 else "好位〜中団" if avg <= 0.6 else "差し・追込"
                f["first_corner_avg"] = round(avg, 2)
            same_c = [r for r in rs if r["競馬場"] == race["venue"] and r["距離"] == race["dist"]]
            same_d = [r for r in rs if r["距離"] == race["dist"]]
            top3 = lambda L_: sum(1 for r in L_ if str(r.get("着順")).isdigit() and int(r["着順"]) <= 3)
            wins = lambda L_: sum(1 for r in L_ if str(r.get("着順")) == "1")
            f["same_course"] = f"{len(same_c)}戦{wins(same_c)}勝・3着内{top3(same_c)}"
            f["same_dist"] = f"{len(same_d)}戦{wins(same_d)}勝・3着内{top3(same_d)}"
            f["recent"] = [r.get("着順") or "?" for r in rs[:5]]
        out.append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--race", nargs="+", required=True)
    ap.add_argument("--uma", default="")
    a = ap.parse_args()
    d = json.load(open(WL.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"]
    res, _ = L.jv_results_and_entries("00000000")
    names = {h["name"].replace(" ", "") for k in a.race for h in d[k]["horses"]}
    by = collections.defaultdict(dict)
    for r in E.load_rows() + res:
        n = r["馬名"].replace(" ", "")
        if n in names:
            by[n][(r["date"], r["競馬場"], r["R"])] = r
    ums = {int(x) for x in a.uma.split(",") if x}
    for k in a.race:
        fs = facts_for(d[k], ums, by, a.date)
        (WL.OUT / f"{a.date}_{k}_facts.json").write_text(json.dumps(fs, ensure_ascii=False, indent=1), encoding="utf-8")
        print("■", k, d[k]["title"], d[k]["dist"], d[k]["baba"])
        for f in fs:
            print(" ", f["uma"], f["name"], "|", f"間隔{f.get('interval_days')}日 距離{f.get('last_dist_change'):+}m" if f.get("last_dist_change") is not None else "初", "芝ダ替" if f.get("surface_change") else "",
                  "|", f.get("style"), f.get("first_corner_avg"), "| 同コース", f.get("same_course"), "| 同距離", f.get("same_dist"), "| 前走", f.get("last"), "上がり順位", f.get("last_l3_rank"), "体重", f.get("last_weight"))


if __name__ == "__main__":
    main()
