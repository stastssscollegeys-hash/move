# -*- coding: utf-8 -*-
"""
flat_race_deep.py — 平場を重賞と同じ厚さで分析する（2026-09-25 ユーザー指示）
=============================================================================
重賞では「同じレースの過去10回＋馬柱＋追い切り＋外部サイト」で20因子を作っていたが、
平場はエンジンの17因子だけで、条件の癖も馬の格も見ていなかった。
ここでは平場でも取れるものだけで、できるだけ同じ形に寄せる。

取るもの
  ① 同条件の実測（累積DB 32,736行）: 同じ競馬場×距離（必要ならクラス帯も）で
     人気帯別の1着率・3着内率・単勝回収率、枠別・脚質別の3着内率、荒れ度（3連単の中央値）
  ② 馬柱（shutuba_past.py）: 近走の会場・距離・格・着順 → sc[18]同コース実績 / sc[19]格 / 距離実績
  ③ 追い切り（oikiri_factor）: 2ソース平均。平場は評価が無いことが多く、その場合は中立
  ④ レース前の records（17因子・脚質・枠・人気）

出すもの
  ・20因子ライトの採点（取れない項目は中立のまま。何が中立かを明示する）
  ・このレースは「狙えるか」の判定（堅い/中間/荒れ、指数と市場の重なり、サンプル数つき）
⚠ 期待値そのものは出さない。前日推定の期待回収率は過大に出ることが実測で分かっているため
  （[[keiba-published-bets-reality]]）、ここでは「条件の実測」と「重なり」だけを材料にする。

使い方:
  python flat_race_deep.py --date 20260920 --venue 中山 --R 1
  python flat_race_deep.py --date 20260920 --venue 中山 --R 1 --no-form   （馬柱を取りに行かない）
"""
from __future__ import annotations
import argparse, glob, json, re, statistics, sys, io
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
DB = ROOT / "daily_pdca" / "db"
CLASSES = ["新馬", "未勝利", "1勝", "2勝", "3勝", "オープン", "L", "G"]
POP_BANDS = [("1番人気", 1, 1), ("2番人気", 2, 2), ("3番人気", 3, 3), ("4〜5番人気", 4, 5),
             ("6〜9番人気", 6, 9), ("10番人気以下", 10, 99)]


def norm_dist(d: str | None) -> str:
    """距離表記を揃える。records は「ダ1800m」、累積DBは「ダート1800m」で書かれている。"""
    if not d:
        return ""
    m = re.match(r"^([芝ダ障])\D*(\d{3,4})", str(d))
    return f"{m.group(1)}{m.group(2)}" if m else str(d)


def fin_of(r: dict) -> int | None:
    """着順。累積DBは着順intが欠けている行が多い（中山ダ1800では大半）ので文字列からも拾う。"""
    v = r.get("着順int")
    if v:
        try:
            return int(float(v))
        except (TypeError, ValueError):
            pass
    m = re.match(r"\s*(\d+)", str(r.get("着順") or ""))
    return int(m.group(1)) if m else None


def klass(name: str) -> str:
    for c in ("新馬", "未勝利", "1勝", "2勝", "3勝"):
        if c in name:
            return c
    if re.search(r"G[ⅠⅡⅢI1-3]", name):
        return "重賞"
    return "オープン"


def load_records(date: str, venue: str, r: int) -> list[dict]:
    for f in sorted(glob.glob(str(ROOT / "*" / "週末ビッグデータ_*_records.json"))):
        try:
            rows = json.loads(Path(f).read_text(encoding="utf-8"))["records"]
        except Exception:
            continue
        hit = [x for x in rows if x["date"] == date and x["競馬場"] == venue and int(x["R"]) == r]
        if hit:
            return sorted(hit, key=lambda x: x.get("AI予測順位") or 99)
    return []


def condition_stats(venue: str, dist: str, cls: str) -> dict:
    res = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
    pay = json.loads((DB / "payouts.json").read_text(encoding="utf-8"))
    key = norm_dist(dist)
    same = [r for r in res if r.get("競馬場") == venue and norm_dist(r.get("距離")) == key]
    narrow = [r for r in same if klass(r.get("レース名", "")) == cls]
    rows, scope = (narrow, f"{venue}{dist}・{cls}クラス") if len({(r["date"], r["R"]) for r in narrow}) >= 12 else (same, f"{venue}{dist}（クラス不問）")
    races = {(r["date"], r["R"]) for r in rows}
    out = {"scope": scope, "n_races": len(races), "n_horses": len(rows)}

    def rate(sub):
        n = len(sub)
        if not n:
            return None
        win = sum(fin_of(r) == 1 for r in sub)
        top3 = sum((fin_of(r) or 99) <= 3 for r in sub)
        ret = sum((r.get("単勝オッズ") or 0) * 100 for r in sub if fin_of(r) == 1) / (n * 100)
        return {"n": n, "win": win / n, "top3": top3 / n, "roi": ret}

    out["pop"] = {lab: rate([r for r in rows if lo <= (r.get("人気") or 99) <= hi]) for lab, lo, hi in POP_BANDS}
    out["waku"] = {w: rate([r for r in rows if r.get("枠") == w]) for w in range(1, 9)}
    out["style"] = {s: rate([r for r in rows if r.get("脚質") == s]) for s in ("逃げ", "先行", "差し", "追込")}
    # 荒れ度: 同条件レースの3連単配当の中央値
    tan3 = []
    for v in pay.values():
        if (v["date"], float(v["R"])) in races or (v["date"], v["R"]) in races:
            t = v["payouts"].get("3連単")
            if t:
                tan3.append(t[0]["yen"])
    out["tan3_median"] = statistics.median(tan3) if tan3 else None
    out["tan3_n"] = len(tan3)
    return out


def sire_note(sire: str, venue: str, dist: str) -> tuple[float, str]:
    """血統は「消す理由」にだけ使う（[[keiba-bloodline-analysis]]）。同条件で明確に不振なら減点。"""
    if not sire:
        return 6.5, ""
    res = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
    sub = [r for r in res if r.get("父") == sire and r.get("競馬場") == venue and norm_dist(r.get("距離")) == norm_dist(dist)]
    if len(sub) < 15:
        return 6.5, ""
    top3 = sum((fin_of(r) or 99) <= 3 for r in sub) / len(sub)
    if top3 < 0.12:
        return 5.0, f"父{sire}は同条件{len(sub)}走で3着内率{top3*100:.0f}%と不振"
    return 6.5, ""


def lin(v, lo, hi, vmin=0.0, vmax=100.0):
    if v is None:
        return (lo + hi) / 2
    x = max(vmin, min(vmax, float(v)))
    return lo + (hi - lo) * (x - vmin) / (vmax - vmin)


LV = {"GI": 11, "GII": 10, "GIII": 9.5, "G1": 11, "G2": 10, "G3": 9.5, "L": 8.5, "OP": 8.5,
      "3勝": 8, "2勝": 7.5, "1勝": 7, "未勝利": 6, "新馬": 6, "": 7}


def sc12_19_18(runs: list[dict], venue: str, surf: str, dist: int) -> tuple:
    if not runs:
        return (7.0, "近走なし"), (4.0, "近走なし"), (5.0, "近走なし")
    r0 = runs[0]
    v = LV.get(r0.get("grade", ""), 7)
    v += 0.5 if r0["fin"] <= 3 else (-2 if r0["fin"] >= 10 else 0)
    sc12 = (max(6, min(11, v)), f"前走 {r0.get('race','')}({r0.get('grade') or '条件'}) {r0['fin']}着")
    best, why = 4.0, "3勝クラス以下"
    for r in runs:
        g, k = r.get("grade", ""), r["fin"]
        val = None
        if g in ("GI", "G1") and k <= 3: val = 7
        elif (g in ("GI", "G1") and k <= 5) or (g in ("GII", "GIII", "G2", "G3") and k == 1): val = 6.5
        elif g in ("GII", "GIII", "G2", "G3") and k <= 3: val = 6
        elif (g in ("L", "OP") and k == 1) or (g in ("GI", "GII", "GIII", "G1", "G2", "G3") and k <= 5): val = 5.5
        elif g == "3勝" and k == 1: val = 5
        if val and val > best:
            best, why = val, f"{r.get('race','')}({g}) {k}着"
    sc19 = (best, why)
    same = [r for r in runs if r.get("ven") == venue and r.get("surf") == surf and abs((r.get("dist") or 0) - dist) <= 200]
    if not same:
        sd = [r for r in runs if r.get("surf") == surf and abs((r.get("dist") or 0) - dist) <= 200]
        if sd:
            b = min(r["fin"] for r in sd)
            sc18 = (6.5 if b <= 3 else 5.5, f"同距離帯{len(sd)}走・最高{b}着（別コース）")
        else:
            sc18 = (5.0, "同距離帯の経験なし（減点しない）")
    else:
        b = min(r["fin"] for r in same)
        sc18 = (8.0 if b == 1 else 7.0 if b <= 3 else 6.0 if b <= 5 else 4.5, f"同コース{len(same)}走・最高{b}着")
    return sc12, sc19, sc18


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--venue", required=True)
    ap.add_argument("--R", type=int, required=True); ap.add_argument("--race-id")
    ap.add_argument("--no-form", action="store_true")
    a = ap.parse_args()
    recs = load_records(a.date, a.venue, a.R)
    if not recs:
        print("[ERROR] records が見つかりません（先に collect_weekend_bigdata.py）"); return
    info = recs[0]
    dist, name = info["距離"], info.get("レース名", "")
    surf = "芝" if dist.startswith("芝") else ("ダート" if dist.startswith("ダ") else "障害")
    dist_m = int(re.search(r"(\d{3,4})", dist).group(1))
    cls = klass(name)
    st = condition_stats(a.venue, dist, cls)

    form = {}
    if not a.no_form:
        try:
            from shutuba_past import fetch_form
            rid = a.race_id
            if not rid:
                sh = json.loads((Path(__file__).resolve().parent / "_cache" / "netkeiba" / "shutuba.json").read_text(encoding="utf-8"))
                names = {r["馬名"] for r in recs}
                rid = max(sh, key=lambda k: len(names & {h["horse_name"] for h in sh[k]["horses"]}), default=None)
                if rid and len(names & {h["horse_name"] for h in sh[rid]["horses"]}) < len(names) * 0.8:
                    rid = None
            if rid:
                form = {h["name"]: h["runs"] for h in fetch_form(rid)}
        except Exception as e:
            print("[WARN] 馬柱の取得に失敗:", str(e)[:100])

    try:
        from oikiri_factor import load_oikiri
        oik = load_oikiri(a.date, a.venue, a.R)
    except Exception:
        oik = None

    # レース前の records には人気・オッズが入っていないので、その日のオッズファイルから補う
    odds_map, pop_map = {}, {}
    op = ROOT / a.date / f"odds_{a.date}.json"
    if op.exists():
        od = json.loads(op.read_text(encoding="utf-8")).get(f"{a.date}_{a.venue}_{a.R}") or {}
        odds_map = {int(k): float(v) for k, v in od.items()}
        pop_map = {u: i + 1 for i, (u, _) in enumerate(sorted(odds_map.items(), key=lambda kv: kv[1]))}

    n_nige = sum(1 for r in recs if r.get("脚質") == "逃げ")
    pace = "前が残りやすい（逃げ1頭）" if n_nige <= 1 else ("流れそう（逃げ%d頭）" % n_nige if n_nige >= 3 else "平均的")
    rows = []
    for r in recs:
        nm = r["馬名"]
        runs = form.get(nm, [])
        sc = {}
        sc[1] = lin(r.get("F02_タイム"), 5, 12); sc[2] = lin(r.get("F03_着差"), 6, 11)
        s_style = (st["style"].get(r.get("脚質")) or {}).get("top3")
        sc[3] = lin((s_style or 0.25) * 100, 6, 10, 0, 45)
        sc[4] = lin(r.get("近5走複勝率%"), 6, 11)
        sc[5] = lin(r.get("F04_騎手"), 5, 8)
        sc[6], sire_why = sire_note(r.get("父"), a.venue, dist)
        w_top3 = (st["waku"].get(int(r.get("枠") or 0)) or {}).get("top3")
        sc[7] = lin((w_top3 or 0.25) * 100, 3, 7, 0, 46)
        sc[8] = {"逃げ": 8 if n_nige <= 1 else 6, "先行": 8 if n_nige <= 1 else 7,
                 "差し": 7 if n_nige <= 1 else 8, "追込": 6 if n_nige <= 1 else 7}.get(r.get("脚質"), 7)
        sc[9] = oik.point(nm) if oik else 6.5
        sc[10] = 7.0; sc[11] = 9.5
        (sc[12], w12), (sc[19], w19), (sc[18], w18) = sc12_19_18(runs, a.venue, surf, dist_m)
        sc[13] = lin(r.get("F05_厩舎"), 6, 9); sc[14] = lin(r.get("F10_斤量"), 6, 8)
        sc[15] = lin(r.get("F12_年齢"), 6, 8, 60, 100); sc[16] = lin(r.get("F14_馬場"), 3, 9)
        sc[17] = 4.0; sc[20] = 3.0
        uma = int(r["馬番"])
        rows.append({"馬名": nm, "馬番": uma, "枠": r.get("枠"), "脚質": r.get("脚質"),
                     "人気": r.get("人気") or pop_map.get(uma), "オッズ": r.get("単勝オッズ") or odds_map.get(uma),
                     "総合指数": r.get("総合指数"),
                     "sc": sc, "total": round(sum(sc.values()), 1), "why": {"12": w12, "18": w18, "19": w19, "6": sire_why},
                     "oikiri": (oik.detail(nm) if oik else "—"), "runs": len(runs)})
    rows.sort(key=lambda x: -x["total"])

    # ── 出力 ──
    L = [f"# {a.date} {a.venue}{a.R}R {name}（{dist}・{len(recs)}頭）平場ディープ分析", "",
         f"## 1. 同条件の実測（{st['scope']} / {st['n_races']}レース {st['n_horses']}頭）", "",
         "| 人気帯 | 頭数 | 1着率 | 3着内率 | 単勝回収率 |", "|---|---|---|---|---|"]
    for lab, _, _ in POP_BANDS:
        s = st["pop"].get(lab)
        if s:
            L.append(f"| {lab} | {s['n']} | {s['win']*100:.1f}% | {s['top3']*100:.1f}% | {s['roi']*100:.0f}% |")
    w = [(k, v) for k, v in st["waku"].items() if v and v["n"] >= 10]
    L += ["", "枠別3着内率: " + " / ".join(f"{k}枠{v['top3']*100:.0f}%({v['n']})" for k, v in w),
          "脚質別3着内率: " + " / ".join(f"{k}{v['top3']*100:.0f}%({v['n']})" for k, v in st["style"].items() if v and v["n"] >= 10)]
    if st["tan3_median"]:
        L.append(f"3連単の中央値: {st['tan3_median']:,.0f}円（{st['tan3_n']}レース）")
    L += ["", f"想定ペース: {pace}", "", "## 2. 20因子ライトの採点", "",
          "| 順 | 馬番 | 馬名 | 脚質 | 人気 | 合計 | sc7枠 | sc9追切 | sc12前走 | sc18コース | sc19格 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, x in enumerate(rows, 1):
        s = x["sc"]
        L.append(f"| {i} | {x['馬番']} | {x['馬名']} | {x['脚質'] or '—'} | {x['人気'] or '—'} | **{x['total']}** | "
                 f"{s[7]:.1f} | {s[9]:.1f} | {s[12]:.1f} | {s[18]:.1f} | {s[19]:.1f} |")
    L += ["", "根拠（上位5頭）"]
    for x in rows[:5]:
        L.append(f"- {x['馬名']}: {x['why']['12']}／{x['why']['18']}／格 {x['why']['19']}"
                 + (f"／{x['why']['6']}" if x["why"]["6"] else "") + (f"／追切 {x['oikiri']}" if x["oikiri"] not in ("—", "評価なし") else ""))

    # ── 3. 狙えるかの判定 ──
    p1 = st["pop"].get("1番人気") or {}
    hard = (p1.get("top3") or 0) >= 0.60
    ara = st["tan3_median"] and st["tan3_median"] >= 80000
    kata = "堅い" if hard and not ara else ("荒れ" if ara else "中間")
    mk = {x["馬名"]: x["人気"] for x in rows if x["人気"]}
    top3_idx = [x["馬名"] for x in rows[:3]]
    top3_mkt = [nm for nm, p in sorted(mk.items(), key=lambda kv: kv[1])[:3]]
    overlap = len(set(top3_idx) & set(top3_mkt))
    no_form = sum(1 for x in rows if x["runs"] == 0)
    L += ["", "## 3. 狙えるか", "",
          f"- レース型: **{kata}**（1番人気の3着内率{(p1.get('top3') or 0)*100:.0f}%"
          + (f"・3連単中央値{st['tan3_median']:,.0f}円" if st["tan3_median"] else "") + "）",
          f"- 指数上位3頭と市場上位3頭の重なり: **{overlap}/3**",
          f"- 中立のままの項目: sc10体重・sc11期待値・sc17輸送・sc20外部指数" + ("・sc9追い切り（平場は評価なし）" if not oik or all(oik.sources(x['馬名']) == 0 for x in rows) else ""),
          f"- 馬柱が取れなかった馬: {no_form}頭" if no_form else "- 馬柱: 全頭取得",
          ""]
    if overlap >= 2 and kata == "堅い":
        L.append("判定: **参加を検討**。指数と市場が同じ方向を向き、条件も堅い決着が多い。ただし配当は小さい。")
    elif overlap == 0:
        L.append("判定: **見送り寄り**。指数と市場が食い違っている。実測では、食い違うときは市場の方が当たっている（モデル優位62% vs 市場優位84%）。")
    else:
        L.append("判定: **条件つきで検討**。相手は市場の上位人気から取り、1点だけ当たって損になる組み合わせは外す。")
    L += ["", f"※ この判定は条件の実測と重なりだけで出している。期待回収率は前日推定だと過大に出るため載せていない。",
          f"※ 同条件のサンプルは{st['n_races']}レース。少ない場合は偶然の幅が大きい。"]

    out = ROOT / a.date / "research" / f"flat_deep_{a.venue}{a.R}R.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print("\n保存:", out)


if __name__ == "__main__":
    main()
