"""web_recent.py — web_live.py が出したレースの各馬について、蓄積DBから近5走を出す（2026-11-06 新設）
  python web_recent.py --date 20261107 --race 東京11 [--n 5]
JV版の entry_digest.py の代わり（調教は無し）。出力: 標準出力と {OUT}/{日付}_{レース}_recent.md
"""
import argparse
import collections
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import ev_live as L
import web_live as WL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--race", required=True)
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args()
    race = json.load(open(WL.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"][a.race]
    names = {h["name"].replace(" ", ""): h for h in race["horses"]}
    res, _ = L.jv_results_and_entries("00000000")
    rows = [r for r in E.load_rows() + res if r["馬名"].replace(" ", "") in names]
    by = collections.defaultdict(dict)
    for r in rows:
        by[r["馬名"].replace(" ", "")][(r["date"], r["競馬場"], r["R"])] = r
    out = [f"# {race['title']} 近{a.n}走（蓄積DB・{a.date}時点）", ""]
    for nm, h in sorted(names.items(), key=lambda x: x[1]["uma"]):
        rs = sorted(by.get(nm, {}).values(), key=lambda r: r["date"], reverse=True)[:a.n]
        out.append(f"## {h['uma']} {h['name']}（{h['jockey']}／{h['trainer']}）")
        if not rs:
            out.append("- 近走データなし（初出走、または海外・地方のみ）")
        for r in rs:
            cn = "-".join(str(c) for c in (r.get("コーナー通過") or "").split("-") if c) if isinstance(r.get("コーナー通過"), str) else ""
            out.append(f"- {r['date'][:4]}/{r['date'][4:6]}/{r['date'][6:]} {r['競馬場']}{r['R']}R {r.get('レース名') or r.get('条件')} {r['距離']} {r.get('馬場状態') or ''} "
                       f"{r.get('着順') or '?'}着/{r.get('頭数') or '?'}頭 {r.get('人気') or '?'}番人気 {r.get('騎手')} {r.get('斤量_kg')}kg 通過{cn or '-'} 上がり{r.get('後3F') or '-'}({r.get('後3F順位') or '-'}位) 馬体重{r.get('馬体重') or '-'}")
        out.append("")
    txt = "\n".join(out)
    print(txt)
    (WL.OUT / f"{a.date}_{a.race}_recent.md").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main()
