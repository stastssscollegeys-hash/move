# -*- coding: utf-8 -*-
"""web_preview_probs.py — 出走確定・枠順・発売の前に、登録馬と予想オッズからモデル確率を出す（2026-11-18 新設）

きっかけ（2026-11-18 ユーザー指示「アップデートした内容を使って週末の3重賞を予想し直して」）:
  新しい決まり（◎の割安さ＝モデル÷市場 で 見送り／通常／単勝本線）を、枠順の前に当ててみる。web_live.py は Yahoo の出馬表（枠順確定後）が要るので、
  登録馬（registrants*.json）＋予想オッズ（個人サイト・netkeiba の AI 予想など）から同じ形の行を作り、同じエンジン（ev_engine・同じ係数）で確率を出す。
  枠が分からないので、枠と馬番をばらばらに入れ替えたレースを K 個作り、確率を平均する（枠の影響を消す）。
注意: 割安さは仮。予想オッズは発売後のオッズと違う（11/7 は確定が中央値1.64倍にずれた）。強さの判定は、発売が始まってから web_live → web_compose でやり直す。
注意: 公開しない（印・買い目は枠順確定・発売後に出す決まり）。出力は {OUT}/{日付}_web_probs_preview.json（web_probs と同じ形・馬番は仮の通し番号）
  python web_preview_probs.py --spec preview_spec.json [--k 12]
spec: [{"date","venue","R","title"（例 "福島記念 GIII"）,"dist"（例 "芝2000m"）,"start","horses":[{"name","sexage","kin","jockey","trainer","odds"}]}]
"""
import argparse
import collections
import datetime
import json
import pickle
import random
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import ev_live as L
import web_live as WL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--model", default="")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    hid, known = WL.hist_maps()
    ped = {}
    for r in E.load_rows():
        if r.get("horse_id") and (r.get("父") or r.get("母父")):
            ped[r["horse_id"]] = (r.get("父") or "", r.get("母父") or "")
    rows, meta = [], {}
    rnd = random.Random(20261118)
    for sp in spec:
        hs = [h for h in sp["horses"] if h.get("odds")]
        n = len(hs)
        cond, rname = WL.class_of(sp["title"], "")
        for k in range(a.k):
            order = list(range(n))
            rnd.shuffle(order)
            R = sp["R"] * 100 + k
            meta[(sp["venue"], R)] = f"{sp['venue']}{sp['R']}"
            for slot, i in enumerate(order):
                h = hs[i]
                uma = slot + 1
                waku = min(8, 1 + (slot * 8) // n) if n > 8 else uma
                nm = h["name"].replace(" ", "")
                hid_ = hid.get(nm) or "web:" + nm
                jkey, _ = WL.jockey_key(h.get("jockey") or "", set(known))
                f, mf = ped.get(hid_, ("", ""))
                surf = sp["dist"][0]
                rows.append({
                    "date": sp["date"], "競馬場": sp["venue"], "R": R, "race_id": f"{sp['date']}-{sp['venue']}-{R}", "レース名": rname, "距離": sp["dist"],
                    "馬場状態": "良", "天候": "晴", "条件": cond, "コース情報": f"{sp['dist']} / 天候 : 晴 / {surf} : 良", "枠": waku, "馬番": uma,
                    "馬名": h["name"], "horse_id": hid_, "性齢": h["sexage"], "前3F_レース": None, "後3F_レース": None, "ラップ": [],
                    "斤量_kg": float(h["kin"]), "騎手": jkey, "タイム": "", "着差": "", "コーナー通過": "", "後3F": None,
                    "単勝オッズ": float(h["odds"]), "人気": 0, "馬体重": "", "体重表示": "", "厩舎": WL.nfkc(h.get("trainer") or ""),
                    "着順": "", "着順int": None, "後3F順位": None, "脚質": "", "頭数": n, "父": f, "母父": mf, "_live": True, "_web": True})
    newcomers = sorted({r["馬名"] for r in rows if r["horse_id"].startswith("web:")})
    cf = sorted(f for f in (L.DB / "ev_cache").glob("2026*.pkl") if "replay" not in f.name)
    mfile = (L.DB / "ev_cache" / f"{a.model}.pkl") if a.model else cf[-1]
    cache = pickle.loads(mfile.read_bytes())
    beta, w = cache["beta"], cache["w"]
    print("係数:", mfile.name, "／ 行", len(rows), "／ DBに無い馬", newcomers)
    n_hist, extra, last = L.train_all()
    orig = E.load_rows
    E.load_rows = lambda: orig() + extra
    races, _ = E.build(extra_rows=rows)
    E.load_rows = orig
    name_of = {(r["競馬場"], r["R"], r["馬番"]): r["馬名"] for r in rows}
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    qq = {}
    for r in [x for x in races if x["part"] == "live"]:
        v, R = r["key"][1], r["key"][2]
        base = meta[(v, R)]
        p = E.probs(r, beta, w)
        for u, pi, qi in zip(r["uma"], p, r["q"]):
            nm = name_of[(v, R, u)]
            acc[base][nm].append(float(pi))
            qq[(base, nm)] = float(qi)
    for sp in spec:
        base = f"{sp['venue']}{sp['R']}"
        if base not in acc:
            print("計算できず:", base)
            continue
        hs = []
        for i, h in enumerate([h for h in sp["horses"] if h.get("odds")]):
            ps = acc[base].get(h["name"]) or [0.0]
            hs.append(dict(uma=i + 1, name=h["name"], odds=float(h["odds"]), p_model=float(np.mean(ps)), p_model_sd=round(float(np.std(ps)), 4),
                           p_market=round(qq.get((base, h["name"]), 0.0), 4), jockey=h.get("jockey", ""), trainer=h.get("trainer", ""), new=h["name"] in newcomers))
        s = sum(x["p_model"] for x in hs) or 1.0
        for x in hs:
            x["p_model"] = round(x["p_model"] / s, 4)
        race = dict(venue=sp["venue"], R=sp["R"], n=len(hs), title=sp["title"], start=sp.get("start", ""), dist=sp["dist"], baba="",
                    cond=WL.class_of(sp["title"], "")[0], rid="", horses=hs)
        f = WL.OUT / f"{sp['date']}_web_probs_preview.json"
        old = json.load(open(f, encoding="utf-8"))["races"] if f.exists() else {}
        old[base] = race
        f.write_text(json.dumps(dict(made_at=datetime.datetime.now().isoformat(timespec="minutes"), model=mfile.name, preview=True, k=a.k, races=old),
                                ensure_ascii=False, indent=1), encoding="utf-8")
        print("保存:", f, base, len(hs), "頭")


if __name__ == "__main__":
    main()
