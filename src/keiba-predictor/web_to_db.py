# -*- coding: utf-8 -*-
"""web_to_db.py — web_results.py の結果を蓄積DBの形に直して追記する（2026-11-07 新設・JRA-VAN終了後の「DB更新」）
  python web_to_db.py --date 20261107     → {DB}/history_web/results_web_{日付}.json（同じ日付は置き換え）
ev_engine.load_rows が history_web も読む。history_target（JV由来）は触らない。
人気は単勝確定オッズの順位。血統（父・母父）と天候は取れないので空。障害は含まない。"""
import argparse, json, sys
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import web_live as W
from course_profile import style_of

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    R = json.load(open(W.OUT / f"{a.date}_web_results.json", encoding="utf-8"))
    P = json.load(open(W.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"]
    hid, jk = W.hist_maps()
    rows, unm = [], set()
    for k, r in R.items():
        if not r["rows"]:
            continue
        pr = P[k]; venue, Rn = r["venue"], r["R"]
        cond, rname = W.class_of(pr["title"], pr.get("cond", ""))
        n = len(r["rows"]); lap = r.get("lap") or []
        l3 = {h["uma"]: float(h["l3"]) for h in r["rows"] if h["l3"].replace(".", "").isdigit()}
        l3rank = {u: i + 1 for i, u in enumerate(sorted(l3, key=l3.get))}
        for h in r["rows"]:
            name = h["name"]; key = name.replace(" ", "")
            jkey, ok = W.jockey_key(h["jockey"], jk)
            if not ok: unm.add((h["jockey"], jkey))
            corner = r.get("corners", {}).get(str(h["uma"]), "")
            sexage = h["body"].split("/")[0]
            wt = h["body"].split("/")[1] if "/" in h["body"] else ""
            hp = [x for x in pr["horses"] if x["uma"] == h["uma"]]
            rows.append({"date": a.date, "競馬場": venue, "R": Rn, "race_id": f"{a.date}-{venue}-{Rn}", "レース名": rname, "距離": r["dist"], "馬場状態": r["baba"], "天候": "",
                "条件": cond, "コース情報": f'{r["dist"]} / 天候 :  / {r["dist"][0]} : {r["baba"]}', "枠": h["waku"], "馬番": h["uma"], "馬名": name, "horse_id": hid.get(key) or "web:" + key,
                "性齢": sexage, "前3F_レース": round(sum(lap[:3]), 1) if len(lap) >= 3 else None, "後3F_レース": round(sum(lap[-3:]), 1) if len(lap) >= 3 else None, "ラップ": lap,
                "斤量_kg": float(h["kin"]) if h["kin"].replace(".", "").isdigit() else 0.0, "騎手": jkey, "タイム": h["time"], "着差": h["margin"] if h["margin"] != "-" else "", "コーナー通過": corner,
                "後3F": l3.get(h["uma"]), "単勝オッズ": h["odds"] or 0.0, "人気": h.get("pop") or 0, "馬体重": wt, "厩舎": W.nfkc(h["trainer"]), "着順": str(h["rank"]), "着順int": h["rank"],
                "後3F順位": l3rank.get(h["uma"]), "脚質": style_of(corner, n), "頭数": n, "父": "", "母父": "", "_web": True})
    d = E.DB / "history_web"; d.mkdir(exist_ok=True)
    (d / f"results_web_{a.date}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(len(rows), "行を追記 →", d / f"results_web_{a.date}.json", "| 騎手が合わない:", sorted(unm)[:10])

if __name__ == "__main__":
    main()
