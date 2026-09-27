# -*- coding: utf-8 -*-
"""
score_v33_20260926.py — 2026/9/26 シリウスS(G3・阪神ダ2000) と 9/27 スプリンターズS(G1・中山芝1200) の20因子v3.3採点
=====================================================================================================================
score_v33_20260919.py と同じ規則。変更点はレース設定と入力ファイルだけ。
  - sc[3]脚質・sc[7]枠: race_history.py の「このレース自体の過去集計」（2026-09-25実行）
  - sc[9]: 追い切り2ソース平均（oikiri_factor・2026-09-25のルール改定）
  - sc[12]/sc[18]/sc[19]: 馬柱（shutuba_past.py）
出力: Desktop/競馬予想レポート/20260926/research/score20_20260925.json
"""
from __future__ import annotations
import json, re, sys, io
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from oikiri_factor import load_oikiri
from pace_factor import table as pace_table
from shutuba_past import fetch_form

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
BASE = ROOT / "20260926"
RES = BASE / "research"

RACES = {
    "シリウスS": dict(date="20260926", venue="阪神", R=11, race_id="202609040811", dist=2000, surf="ダート",
                     records=ROOT / "20260926" / "週末ビッグデータ_20260926-0927_records.json",
                     # race_history.py シリウスS（阪神ダ2000の6回）
                     style={"逃げ": 30.8, "先行": 22.2, "差し": 29.2, "追込": 9.7},
                     waku={1: 0, 2: 38, 3: 36, 4: 9, 5: 25, 6: 8, 7: 25, 8: 25},
                     type="H型（3連単中央値111,770円・1〜3番人気の勝利50%）"),
    "スプリンターズS": dict(date="20260927", venue="中山", R=11, race_id="202606040911", dist=1200, surf="芝",
                     records=ROOT / "20260926" / "週末ビッグデータ_20260926-0927_records.json",
                     # race_history.py スプリンターズS（過去10回）
                     style={"逃げ": 22.7, "先行": 30.4, "差し": 22.5, "追込": 12.3},
                     waku={1: 40, 2: 15, 3: 30, 4: 25, 5: 16, 6: 5, 7: 11, 8: 10},
                     type="H型（3連単中央値106,170円・近3年は8・9・11番人気が勝利）"),
}
JOCKEY_FLAG = [("川田", "阪神", +2), ("ルメール", "中山", +2), ("横山武", "中山", +1)]
LV = {"GI": 11, "GII": 10, "GIII": 9.5, "G1": 11, "G2": 10, "G3": 9.5, "L": 8.5, "OP": 8.5,
      "3勝": 8, "2勝": 7.5, "1勝": 7, "未勝利": 6, "新馬": 6, "": 7}


def lin(v, lo, hi, vmin=0.0, vmax=100.0):
    if v is None:
        return (lo + hi) / 2
    x = max(vmin, min(vmax, float(v)))
    return lo + (hi - lo) * (x - vmin) / (vmax - vmin)


def sc12_19_18(runs, venue, surf, dist):
    if not runs:
        return (7.0, "近走なし"), (4.0, "近走なし"), (5.0, "近走なし")
    r0 = runs[0]
    v = LV.get(r0.get("grade", ""), 7) + (0.5 if r0["fin"] <= 3 else (-2 if r0["fin"] >= 10 else 0))
    sc12 = (max(6, min(11, v)), f"前走 {r0.get('race','')}({r0.get('grade') or '条件'}) {r0['fin']}着")
    best, why = 4.0, "3勝クラス以下"
    for r in runs:
        g, k = r.get("grade", ""), r["fin"]
        val = (7 if g in ("GI", "G1") and k <= 3 else
               6.5 if (g in ("GI", "G1") and k <= 5) or (g in ("GII", "GIII", "G2", "G3") and k == 1) else
               6 if g in ("GII", "GIII", "G2", "G3") and k <= 3 else
               5.5 if (g in ("L", "OP") and k == 1) or (g in ("GI", "GII", "GIII", "G1", "G2", "G3") and k <= 5) else
               5 if g == "3勝" and k == 1 else None)
        if val and val > best:
            best, why = val, f"{r.get('race','')}({g}) {k}着"
    same = [r for r in runs if r.get("ven") == venue and r.get("surf") == surf and abs((r.get("dist") or 0) - dist) <= 200]
    if same:
        b = min(r["fin"] for r in same)
        sc18 = (8.0 if b == 1 else 7.0 if b <= 3 else 6.0 if b <= 5 else 4.5, f"同コース{len(same)}走・最高{b}着")
    else:
        sd = [r for r in runs if r.get("surf") == surf and abs((r.get("dist") or 0) - dist) <= 200]
        sc18 = ((6.5 if min(r["fin"] for r in sd) <= 3 else 5.5, f"同距離帯{len(sd)}走・最高{min(r['fin'] for r in sd)}着（別コース）")
                if sd else (5.0, "同距離帯の経験なし（減点しない）"))
    return sc12, (best, why), sc18


def main():
    out = {}
    for name, cfg in RACES.items():
        recs = [r for r in json.loads(Path(cfg["records"]).read_text(encoding="utf-8"))["records"]
                if r["date"] == cfg["date"] and r["競馬場"] == cfg["venue"] and int(r["R"]) == cfg["R"]]
        if not recs:
            print(f"[WARN] {name}: records が無い"); continue
        oik = load_oikiri(cfg["date"], cfg["venue"], cfg["R"])
        form = {h["name"]: h["runs"] for h in fetch_form(cfg["race_id"])}
        jockeys = {h["name"]: h.get("jockey", "") for h in fetch_form(cfg["race_id"])} if False else {}
        n_nige = sum(1 for r in recs if r.get("脚質") == "逃げ")
        # sc[8] は「距離×ペース×馬場」の実測3着内率から出す（2026-09-27改定）。
        # 旧実装は逃げ馬が多いと差しを加点していたが、蓄積DB2,466Rで符号が逆と判明した。
        pace = pace_table(cfg["surf"], cfg["dist"], n_nige, cfg.get("baba"))
        table = []
        for r in recs:
            nm = r["馬名"]
            runs = form.get(nm, [])
            style = r.get("脚質") or "先行"
            s = {}
            s[1] = lin(r.get("F02_タイム"), 5, 12); s[2] = lin(r.get("F03_着差"), 6, 11)
            s[3] = lin(cfg["style"].get(style, 20), 6, 10, 0, 45)
            s[4] = lin(r.get("近5走複勝率%"), 6, 11)
            s[5] = min(8.0, lin(r.get("F04_騎手"), 5, 8))
            s[6] = 6.5
            s[7] = lin(cfg["waku"].get(int(r.get("枠") or 0), 20), 3, 7, 0, 46)
            s[8] = pace.get(style, 7)
            s[9] = oik.point(nm)
            s[10] = 7.0; s[11] = 9.5
            (s[12], w12), (s[19], w19), (s[18], w18) = sc12_19_18(runs, cfg["venue"], cfg["surf"], cfg["dist"])
            s[13] = lin(r.get("F05_厩舎"), 6, 9); s[14] = lin(r.get("F10_斤量"), 6, 8)
            s[15] = lin(r.get("F12_年齢"), 6, 8, 60, 100); s[16] = lin(r.get("F14_馬場"), 3, 9)
            s[17] = 4.0; s[20] = 3.0
            table.append({"name": nm, "waku": r.get("枠"), "uma": int(r["馬番"]), "style": style,
                          "sogo": r.get("総合指数"), "sc": {k: round(v, 2) for k, v in s.items()},
                          "final170": round(min(170.0, sum(s.values())), 1),
                          "oikiri": oik.detail(nm), "oikiri_promote": oik.can_promote(nm),
                          "why": {"sc12": w12, "sc18": w18, "sc19": w19}})
        table.sort(key=lambda x: -x["final170"])
        out[name] = {"type": cfg["type"], "n_nige": n_nige, "horses": table}
        print(f"\n### {name}（{cfg['venue']}{cfg['surf']}{cfg['dist']}m・{len(table)}頭）{cfg['type']}")
        print(" 順 枠-番 馬名             脚質 最終   追い切り            | sc7枠 sc9 sc12 sc18 sc19 | 根拠")
        for i, x in enumerate(table, 1):
            sc = x["sc"]
            print(f" {i:>2} {x['waku']}-{x['uma']:>2} {x['name']:<12} {x['style']:<2} {x['final170']:>6} "
                  f"{x['oikiri']:<20}{'★' if x['oikiri_promote'] else ' '}| {sc[7]:.1f} {sc[9]:.1f} {sc[12]:.1f} {sc[18]:.1f} {sc[19]:.1f} | "
                  f"{x['why']['sc12']} / {x['why']['sc18']}")
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "score20_20260925.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nsaved research/score20_20260925.json")


if __name__ == "__main__":
    main()
