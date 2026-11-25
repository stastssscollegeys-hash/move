# -*- coding: utf-8 -*-
"""展開予想を【1レース分（スタート→ゴール）】で走らせるための「予想のレース結果」を作る（2026-11-20）
ユーザー「展開予想はちゃんと全部やる予定でした。ちゃんと1レース分作ってやる予定だった」
「自分の理論で言ったらこういう着順になる…自分のそこまでの予想とか買い方と矛盾がないように」
「脚質からの上がりを見込んでどういう着地になるのか」

入力: from_forecast.py の出力（隊列＝脚質の順・ラップ）＋ 予想の着順（印の順に馬番を並べる）
      ＋（任意）各馬の前走までの上がり3F（--l3 に JSON {"馬番": [34.1, 33.8, …]}）
決め方:
  途中の位置   … 展開予想と同じ隊列（脚質の順・同じ脚質は1馬身・脚質が替わると2.5馬身・4コーナーで0.75倍に詰まる）
  着順         … --order の馬番の順（印の順＝◎○▲△穴 …）。残りの馬は「4コーナーの遅れ＋前走までの上がり」の見込みの順
  着差         … --order の馬は --margins（秒・既定 0.1 ずつ）。残りはその後ろに見込みの差（0.1秒以上あける）
  上がり3F     … 4コーナーの遅れと着差がつながるように決める（＝先頭の上がり＋着差−4コーナーの遅れ）。
                 前走までの上がりと並べて表に出す（速すぎる見込みは ⚠）
出力: build_frames.py に渡せる race2d の JSON（mode＝prediction。3D・2D の帯は「予想の順位／予想の着順」と出る）
使い方: python from_prediction.py <forecast.json> <出力.json> --order 13,16,11,1,8 [--margins 0.1,0.1,0.1,0.1] [--l3 l3.json]
"""
import json, sys, argparse, statistics
from pathlib import Path

LEN = 2.4   # 1馬身（m）＝build_frames.py と同じ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("forecast"); ap.add_argument("out")
    ap.add_argument("--order", required=True, help="予想の着順（馬番をカンマで）。印の順に並べる")
    ap.add_argument("--margins", default="", help="--order の馬の着差（秒・カンマで）。既定 0.1 ずつ")
    ap.add_argument("--l3", help='前走までの上がり3F の JSON {"馬番": [秒, …]}')
    a = ap.parse_args()
    fc = json.loads(Path(a.forecast).read_text(encoding="utf-8"))
    race = dict(fc["race"]); horses = [dict(h) for h in fc["horses"]]
    laps = race["laps"]; lead_T = sum(laps); L3 = sum(laps[-3:])
    v = 200 / (sum(laps) / len(laps))
    # 隊列（build_frames.py の展開予想と同じ並べ方）
    rows = sorted(horses, key=lambda h: (h.get("style") or 3, h["umaban"]))
    g, prev = 0.0, None
    for k, h in enumerate(rows):
        st = h.get("style") or 3
        if k: g += LEN * (1.0 if st == prev else 2.5)
        prev = st
        h["g6"] = g * 0.75 / v; h["pos"] = k + 1
    l3s = json.loads(Path(a.l3).read_text(encoding="utf-8")) if a.l3 else {}
    est = {h["umaban"]: statistics.mean(l3s[str(h["umaban"])]) for h in horses if l3s.get(str(h["umaban"]))}
    base = statistics.median(est.values()) if est else 35.0
    for h in horses:
        h["est_l3"] = est.get(h["umaban"], base + 0.5)            # 上がりの分からない馬は少し遅めに見込む
    order = [int(x) for x in a.order.split(",") if x.strip()]
    by = {h["umaban"]: h for h in horses}
    miss = [u for u in order if u not in by]
    if miss: sys.exit(f"--order の馬番 {miss} が出走馬にいません")
    m = [float(x) for x in a.margins.split(",") if x.strip()] or [0.1] * (len(order) - 1)
    gF = {order[0]: 0.0}
    for i, u in enumerate(order[1:]):
        gF[u] = gF[order[i]] + (m[i] if i < len(m) else 0.1)
    # 残りの馬：自然な見込み（4コーナーの遅れ＋上がりの差）の順に、印の馬の後ろへ並べる
    fastest = min(h["est_l3"] for h in horses)
    rest = sorted((h for h in horses if h["umaban"] not in gF), key=lambda h: (h["g6"] + h["est_l3"] - fastest, h["umaban"]))
    t = gF[order[-1]]; last_nat = None
    for h in rest:
        nat = h["g6"] + h["est_l3"] - fastest
        step = 0.15 if last_nat is None else min(0.6, max(0.1, nat - last_nat))
        t += step; gF[h["umaban"]] = round(t, 2); last_nat = nat
    fin = sorted(horses, key=lambda h: gF[h["umaban"]])
    for r, h in enumerate(fin, 1):
        h["finish"] = r
        h["gF"] = gF[h["umaban"]]
        h["time"] = round(lead_T + h["gF"], 2)
        h["last3f"] = round(L3 + h["gF"] - h["g6"], 2)            # 4コーナーの遅れと着差がつながる上がり
        h["corners"] = {"1c": None, "2c": None, "3c": h["pos"], "4c": h["pos"]}
    out = dict(source="prediction", mode="prediction", race_id=fc.get("race_id", ""), race=race, forecast=fc.get("forecast"),
               prediction=dict(order=order, margins=m, lead_last3f=round(L3, 1), note="アスメシの印・脚質・前走の上がりから組んだ着順の予想（タイムは推定）"),
               horses=sorted(horses, key=lambda h: h["umaban"]))
    for h in out["horses"]:
        for k in ("g6", "pos", "gF"): h.pop(k, None)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {a.out}  {race.get('name', '')}  予想の着順 {'-'.join(str(h['umaban']) for h in fin[:5])} …  先頭の上がり見込み {L3:.1f}秒")
    print("   着順 馬番 馬名            4角 上がり（見込み） 前走までの上がり")
    for h in fin:
        warn = "  ⚠ 前走までより0.8秒以上速い" if h["umaban"] in est and h["last3f"] < est[h["umaban"]] - 0.8 else ""
        print(f"   {h['finish']:>2}  {h['umaban']:>3}  {h['name'][:9]:<9}  {h['corners']['4c']:>2}番手  {h['last3f']:.1f}  {est.get(h['umaban'], float('nan')):.1f}{warn}")


if __name__ == "__main__":
    main()
