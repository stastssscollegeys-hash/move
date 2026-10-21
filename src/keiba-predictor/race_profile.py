# -*- coding: utf-8 -*-
"""
race_profile.py — 対象レースの過去10年分（同じレース名）を集めて傾向をまとめる（2026-10-02新規）
==========================================================================================
重賞・特別を予想するとき、同じレースの過去の開催（最大10回）から次をまとめる:
  ・各回の勝ち馬（人気・オッズ・前走）・3連単の配当・ペース（前3F−後3F）・ラップ・勝ち時計・馬場
  ・人気別の成績（1番人気は信頼できるか）／脚質別／枠別／年齢別／性別／斤量／馬体重の増減
  ・ローテーション（勝ち馬・3着内馬の前走のレースとクラス）
  ・「型」の判定: 堅い（1〜3番人気が勝つ割合・3連単中央値）／荒れる
出力: Desktop/競馬予想レポート/{日付}/research/race_profile_{レース名}.md と .json
      このJSONは gen_watch_sns.py / draw_final.py の本文の素材、および ev_engine の「このレース〜」特徴量の説明に使う。
      （予想に効く形の数値は ev_engine が同じ履歴から自動で作る。ここは人が読む・文章に使う用）
使い方: python race_profile.py 毎日王冠 [--dir 20261004] [--years 10]
        改称・同名の別レースがあるとき: --alias 旧名1,旧名2 --dist 芝1800 --grade G2 --month 10（2026-10-08追加。名前だけだと別時期の同名レースが混ざる）
"""
from __future__ import annotations
import argparse, collections, json, re, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from course_profile import style_of

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
SRC = BASE / "daily_pdca" / "db" / "history_target"


def norm(name):
    return re.sub(r"第\d+回|\(.*?\)|（.*?）|\s", "", str(name or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--dir")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--alias", default="", help="改称前の名前（カンマ区切り）。例: アイルランドトロフィー府中牝馬ステークス,府中牝馬ステークス")
    ap.add_argument("--dist", default="", help="距離で絞る（例: 芝1800）。同名の別レース（条件戦・別時期）の混入を防ぐ")
    ap.add_argument("--grade", default="", help="格で絞る（例: G2）")
    ap.add_argument("--month", default="", help="開催月で絞る（例: 10）")
    a = ap.parse_args()
    target = norm(a.name)
    names = {target} | {norm(x) for x in a.alias.split(",") if x}
    rows, pays = [], {}
    for f in sorted(SRC.glob("results_*.json")):
        rows += json.loads(f.read_text(encoding="utf-8"))
    for f in sorted(SRC.glob("payouts_*.json")):
        pays.update(json.loads(f.read_text(encoding="utf-8")))
    by_horse = collections.defaultdict(list)
    for r in rows:
        by_horse[r["horse_id"]].append(r)
    for v in by_horse.values():
        v.sort(key=lambda r: (r["date"], r["R"]))
    eds = collections.defaultdict(list)
    for r in rows:
        if (norm(r["レース名"]) in names and r.get("着順int") and r.get("人気")
                and (not a.dist or str(r["距離"]).startswith(a.dist)) and (not a.grade or str(r.get("条件", "")).startswith(a.grade))
                and (not a.month or r["date"][4:6] == a.month.zfill(2))):
            eds[(r["date"], r["競馬場"], r["R"])].append(r)
    keys = sorted(eds)[-a.years:]
    if not keys:
        print("該当レースなし:", a.name)
        return
    cur = eds[keys[-1]][0]
    md = [f"# {a.name} 過去{len(keys)}回の傾向（{keys[0][0][:4]}〜{keys[-1][0][:4]}）\n",
          f"コース: {cur['競馬場']} {cur['距離']}（直近の開催）／条件: {cur['条件']}\n", "## 1. 各回の結果\n",
          "| 年 | 頭数 | 勝ち馬 | 人気 | 単勝 | 前走 | 馬場 | ペース(前3F/後3F) | 勝ち時計 | 3連単 |", "|---|---|---|---|---|---|---|---|---|---|"]
    J = {"race": a.name, "editions": [], "pop": {}, "style": {}, "waku": {}, "age": {}, "sex": {}, "rotation": {}}
    allrows = []
    for k in keys:
        hs = eds[k]
        w = next((h for h in hs if h["着順int"] == 1), None)
        if not w:
            continue
        prev = [p for p in by_horse[w["horse_id"]] if p["date"] < w["date"]]
        pv = f"{prev[-1]['レース名'][:10]}({prev[-1]['着順']}着)" if prev else "初出走"
        pk = f"{k[0]}|{k[1]}|{k[2]}"
        t3 = (pays.get(pk, {}).get("3連単") or {})
        t3v = next(iter(t3.values()), None)
        md.append(f"| {k[0][:4]} | {len(hs)} | {w['馬名']} | {w['人気']} | {w['単勝オッズ']} | {pv} | {w['馬場状態']} | "
                  f"{w.get('前3F_レース')}/{w.get('後3F_レース')} | {w['タイム']} | {t3v:,}円 |" if t3v else
                  f"| {k[0][:4]} | {len(hs)} | {w['馬名']} | {w['人気']} | {w['単勝オッズ']} | {pv} | {w['馬場状態']} | {w.get('前3F_レース')}/{w.get('後3F_レース')} | {w['タイム']} | - |")
        J["editions"].append(dict(year=k[0][:4], n=len(hs), winner=w["馬名"], pop=w["人気"], odds=w["単勝オッズ"], prev=pv, baba=w["馬場状態"],
                                  pace=[w.get("前3F_レース"), w.get("後3F_レース")], time=w["タイム"], trifecta=t3v, laps=w.get("ラップ")))
        for h in hs:
            h["_prev"] = [p for p in by_horse[h["horse_id"]] if p["date"] < h["date"]]
            allrows.append(h)
    # 人気別・属性別
    def tab(keyf, label, minn=1):
        g = collections.defaultdict(lambda: [0, 0, 0])
        for h in allrows:
            kk = keyf(h)
            if kk is None:
                continue
            g[kk][0] += 1
            g[kk][1] += h["着順int"] == 1
            g[kk][2] += h["着順int"] <= 3
        return {kk: v for kk, v in g.items() if v[0] >= minn}
    md.append("\n## 2. 人気別（このレースの1番人気は信頼できるか）\n")
    md.append("| 人気 | 頭数 | 勝ち | 3着内 | 勝率 | 3着内率 |\n|---|---|---|---|---|---|")
    pt = tab(lambda h: min(int(h["人気"]), 8), "人気")
    for kk in sorted(pt):
        n, w_, t_ = pt[kk]
        md.append(f"| {kk}{'番人気以下' if kk == 8 else '番人気'} | {n} | {w_} | {t_} | {w_/n*100:.0f}% | {t_/n*100:.0f}% |")
        J["pop"][str(kk)] = dict(n=n, win=w_, top3=t_)
    top3 = [(h["人気"]) for h in allrows if h["着順int"] == 1]
    md.append(f"\n勝ち馬の人気: {sorted(int(x) for x in top3)}（1〜3番人気が勝った割合 {sum(1 for x in top3 if x <= 3)/len(top3)*100:.0f}%）")
    tri = [e["trifecta"] for e in J["editions"] if e["trifecta"]]
    if tri:
        md.append(f"3連単の中央値 {int(statistics.median(tri)):,}円 ／ 10万円超 {sum(1 for x in tri if x >= 100000)}回／{len(tri)}回")
        kind = "堅い型" if statistics.median(tri) < 30000 and sum(1 for x in top3 if x <= 3) / len(top3) >= 0.6 else "荒れる型" if statistics.median(tri) >= 80000 or sum(1 for x in top3 if x <= 3) / len(top3) <= 0.4 else "標準"
        md.append(f"→ **{kind}**")
        J["kind"] = kind
    for label, keyf, name in (("脚質（そのレースの通過順位から付け直し）", lambda h: style_of(h.get("コーナー通過"), h.get("頭数")) or None, "style"),   # 元データの「脚質」は2番手以内を全部「逃げ」にしている（2026-10-19修正・旧版は先行を過小・差しを過大に出していた）
                              ("枠", lambda h: ("内1-3" if h["枠"] <= 3 else "中4-5" if h["枠"] <= 5 else "外6-8") if h.get("枠") else None, "waku"),
                              ("年齢", lambda h: re.sub(r"[^\d]", "", h["性齢"]) or None, "age"), ("性別", lambda h: h["性齢"][:1], "sex")):
        t = tab(keyf, label)
        md.append(f"\n## {label}\n")
        md.append("| 区分 | 頭数 | 勝ち | 3着内 | 3着内率 |\n|---|---|---|---|---|")
        for kk, (n, w_, t_) in sorted(t.items(), key=lambda kv: -kv[1][0]):
            md.append(f"| {kk} | {n} | {w_} | {t_} | {t_/n*100:.0f}% |")
            J[name][str(kk)] = dict(n=n, win=w_, top3=t_)
    # 前走ローテ
    md.append("\n## 3. 前走のレース（3着内に来た馬）\n")
    rot = collections.Counter()
    for h in allrows:
        if h["着順int"] <= 3 and h["_prev"]:
            rot[norm(h["_prev"][-1]["レース名"]) or "不明"] += 1
    md.append(" ／ ".join(f"{k} {v}頭" for k, v in rot.most_common(12)))
    J["rotation"] = dict(rot.most_common(12))
    # 前走からの間隔・馬体重
    gaps = [(h["date"], h["_prev"][-1]["date"]) for h in allrows if h["着順int"] <= 3 and h["_prev"]]
    import datetime
    def dd(a_, b_):
        return (datetime.date(int(a_[:4]), int(a_[4:6]), int(a_[6:])) - datetime.date(int(b_[:4]), int(b_[4:6]), int(b_[6:]))).days
    if gaps:
        ds = sorted(dd(x, y) for x, y in gaps)
        md.append(f"\n3着内馬の前走からの間隔: 中央値 {ds[len(ds)//2]}日（短い {ds[len(ds)//4]}日〜長い {ds[len(ds)*3//4]}日）")
    wt = [int(re.search(r"\(([+-]?\d+)\)", h["馬体重"]).group(1)) for h in allrows if h["着順int"] <= 3 and re.search(r"\(([+-]?\d+)\)", str(h.get("馬体重") or ""))]
    if wt:
        md.append(f"3着内馬の馬体重増減: 平均 {statistics.mean(wt):+.1f}kg（-10kg以下 {sum(1 for x in wt if x <= -10)}頭／+10kg以上 {sum(1 for x in wt if x >= 10)}頭／{len(wt)}頭中）")
    out_dir = BASE / (a.dir or "profiles") / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"race_profile_{target}.md").write_text("\n".join(md), encoding="utf-8")
    (out_dir / f"race_profile_{target}.json").write_text(json.dumps(J, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md))
    print(f"\n保存: {out_dir / ('race_profile_' + target + '.md')}")


if __name__ == "__main__":
    main()
