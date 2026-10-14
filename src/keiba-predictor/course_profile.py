# -*- coding: utf-8 -*-
"""
course_profile.py — コースの型・重賞の型を10年分でまとめる「型カード」（2026-10-14新規）
========================================================================================
「このコース（重賞）は、どんな馬が・どんなペースで・どう決着してきたか」を1枚で引けるようにする。
course_trends.py（人気から期待される3着内との差＝安定した偏り）と役割を分け、こちらは記述統計の型カード。
  コース = 競馬場 × 芝ダ × 距離（例: 京都芝2000m）。内回り・外回りは元データで区別できないので同じ距離はまとめて扱う
  重賞   = 条件が G1/G2/G3 のレース名ごと（過去の回ごとの勝ち馬一覧つき）
各カードの数字:
  勝ち馬の人気（1番人気の勝率・3着内率、1〜3番人気の勝ち、6番人気以下の勝ち、勝ち馬オッズの中央値）／配当（馬連・3連単の中央値）
  枠（枠ごとの3着内率）／脚質（勝ち馬の脚質・脚質ごとの3着内率）／上がり最速の馬の勝率・3着内率
  ペース（前3F−後3F の平均、ハイ・平均・スローの割合、良馬場の勝ちタイム中央値、平均ラップ）とペース別の前後の有利不利
  種牡馬（10年）・騎手（直近3年）の 出走・勝率・3着内率・単勝回収率
  今年（最新年）の値を10年の値と並べる（今年は内が有利か、ペースが速いか など）
⚠ 脚質・ペース・上がりは結果から付けた値。レース前には確定しない → 「この型ならこういう馬が来る」の読み・説明用。
   種牡馬・騎手の回収率は件数が少ないと偶然が大きい（n を必ず併記）。確率モデル（ev_engine）の入力とは別物。
出力: daily_pdca/db/course_profile.json ／ docs/keiba_course_profile.md（索引と全カード）／ 競馬予想レポート/コース傾向/*.md（1コース1ファイル）
使い方:
  python course_profile.py                    # 全部作り直す（1〜2分）
  python course_profile.py --course 京都芝2000m
  python course_profile.py --race 秋華賞
"""
from __future__ import annotations
import argparse, collections, json, re, statistics, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
SRC = BASE / "daily_pdca" / "db" / "history_target"
OUT_JSON = BASE / "daily_pdca" / "db" / "course_profile.json"
TRENDS = BASE / "daily_pdca" / "db" / "course_trends.json"
OUT_MD = Path(__file__).resolve().parents[2] / "docs" / "keiba_course_profile.md"
OUT_DIR = BASE / "コース傾向"
MIN_COURSE = 60          # コースカードを作る最小レース数
MIN_SIRE, MIN_JOCKEY = 20, 30


def meters(d):
    n = "".join(c for c in str(d or "") if c.isdigit())
    return int(n) if n else 0


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def pct(a, b):
    return round(a / b * 100, 1) if b else None


def tsec(t):
    m = re.match(r"(?:(\d+):)?(\d+(?:\.\d+)?)", str(t or ""))
    if not m:
        return None
    return (int(m.group(1)) * 60 if m.group(1) else 0) + float(m.group(2))


def fmt_t(s):
    return f"{int(s // 60)}:{s % 60:04.1f}" if s else "－"


def grade_of(cond):
    c = str(cond or "")
    return "G1" if c.startswith("G1") else "G2" if c.startswith("G2") else "G3" if c.startswith("G3") else None


def style_of(corner, n):
    """コーナー通過順から脚質を付け直す。元データの「脚質」は最初のコーナー2番手以内を全部「逃げ」にしていて
    1レースに逃げが2〜3頭いる（2025年: 2頭のレースが7割）。ここでは
      逃げ＝最初のコーナーで先頭／先行＝最初のコーナーか4角で頭数の1/3以内／差し＝4角で2/3以内／追込＝それより後ろ"""
    try:
        ps = [int(x) for x in str(corner or "").split("-") if x.strip()]
    except ValueError:
        return ""
    if not ps or not n:
        return ""
    first, last = ps[0], ps[-1]
    if first == 1:
        return "逃げ"
    if first <= n / 3 or last <= n / 3:
        return "先行"
    if last <= n * 2 / 3:
        return "差し"
    return "追込"


def pace_of(f3, b3):
    if not (f3 and b3):
        return None
    d = f3 - b3
    return "ハイ" if d <= -0.6 else "スロー" if d >= 0.6 else "平均"


# ── 読み込み ─────────────────────────────────────────────────────
def load():
    rows = []
    for f in sorted(SRC.glob("results_*.json")):
        rows += [r for r in json.loads(f.read_text(encoding="utf-8")) if not str(r.get("距離") or "").startswith("障")]
    pay = {}
    for f in sorted(SRC.glob("payouts_*.json")):
        pay.update(json.loads(f.read_text(encoding="utf-8")))
    races = collections.defaultdict(list)
    for r in rows:
        if r.get("着順int") and r.get("人気"):
            races[(r["date"], r["競馬場"], int(float(r["R"])))].append(r)
    out = []
    for k, hs in races.items():
        if sum(1 for h in hs if h["着順int"] == 1) != 1:
            continue
        h0 = hs[0]
        win = next(h for h in hs if h["着順int"] == 1)
        ups = [h.get("後3F") for h in hs if h.get("後3F")]
        fastest = min(ups) if ups else None
        p = pay.get(f"{k[0]}|{k[1]}|{k[2]}") or {}
        out.append(dict(
            key=k, date=k[0], year=k[0][:4], venue=k[1], course=f"{k[1]}{h0['距離']}", surf=str(h0["距離"])[:1], m=meters(h0["距離"]),
            name=(h0.get("レース名") or "").strip(), grade=grade_of(h0.get("条件")), baba=h0.get("馬場状態") or "",
            n=len(hs), f3=h0.get("前3F_レース"), b3=h0.get("後3F_レース"), lap=h0.get("ラップ") or [],
            pace=pace_of(h0.get("前3F_レース"), h0.get("後3F_レース")), wtime=tsec(win.get("タイム")),
            umaren=sum((p.get("馬連") or {}).values()) or None, sanrentan=sum((p.get("3連単") or {}).values()) or None,
            horses=[dict(f=h["着順int"], pop=int(h["人気"]), odds=float(h.get("単勝オッズ") or 0), waku=h.get("枠"),
                         style=style_of(h.get("コーナー通過"), len(hs)), up=h.get("後3F"), upfast=(fastest is not None and h.get("後3F") == fastest),
                         sire=h.get("父") or "", jockey=h.get("騎手") or "", name=h.get("馬名") or "", corner=h.get("コーナー通過") or "",
                         sexage=h.get("性齢") or "") for h in hs]))
    out.sort(key=lambda r: r["key"])
    return out


# ── 1枚のカード（レースの集合から）─────────────────────────────────
def card(rs, recent_from=None):
    R = len(rs)
    W = [next(h for h in r["horses"] if h["f"] == 1) for r in rs]
    all_h = [h for r in rs for h in r["horses"]]
    c = {"races": R, "span": f"{rs[0]['date']}〜{rs[-1]['date']}"}
    # 人気
    fav = [next((h for h in r["horses"] if h["pop"] == 1), None) for r in rs]
    fav = [h for h in fav if h]
    c["fav_win"] = pct(sum(h["f"] == 1 for h in fav), len(fav))
    c["fav_top3"] = pct(sum(h["f"] <= 3 for h in fav), len(fav))
    c["top3pop_win"] = pct(sum(w["pop"] <= 3 for w in W), R)
    c["pop6plus_win"] = pct(sum(w["pop"] >= 6 for w in W), R)
    c["win_odds_med"] = med([w["odds"] for w in W])
    c["umaren_med"] = med([r["umaren"] for r in rs])
    c["sanrentan_med"] = med([r["sanrentan"] for r in rs])
    c["sanrentan_100k"] = pct(sum(1 for r in rs if (r["sanrentan"] or 0) >= 100000), sum(1 for r in rs if r["sanrentan"]))
    # 枠
    wk = collections.defaultdict(lambda: [0, 0])
    for h in all_h:
        if h["waku"]:
            wk[h["waku"]][0] += 1
            wk[h["waku"]][1] += h["f"] <= 3
    c["waku_top3"] = {str(k): pct(v[1], v[0]) for k, v in sorted(wk.items())}
    inner = [h for h in all_h if h["waku"] and h["waku"] <= 3]
    outer = [h for h in all_h if h["waku"] and h["waku"] >= 6]
    c["inner_top3"], c["outer_top3"] = pct(sum(h["f"] <= 3 for h in inner), len(inner)), pct(sum(h["f"] <= 3 for h in outer), len(outer))
    # 脚質・上がり
    Ws = [w for w in W if w["style"]]                     # 直線コース（新潟芝1000m）はコーナーが無く脚質を付けられない
    c["win_style"] = {s: pct(sum(w["style"] == s for w in Ws), len(Ws)) for s in ("逃げ", "先行", "差し", "追込")}
    st = collections.defaultdict(lambda: [0, 0])
    for h in all_h:
        if h["style"]:
            st[h["style"]][0] += 1
            st[h["style"]][1] += h["f"] <= 3
    c["style_top3"] = {s: pct(st[s][1], st[s][0]) for s in ("逃げ", "先行", "差し", "追込")}
    uf = [h for h in all_h if h["upfast"]]
    c["upfast_win"], c["upfast_top3"] = pct(sum(h["f"] == 1 for h in uf), len(uf)), pct(sum(h["f"] <= 3 for h in uf), len(uf))
    # ペース
    pd = [r["f3"] - r["b3"] for r in rs if r["f3"] and r["b3"]]
    c["pace_diff"] = round(statistics.mean(pd), 2) if pd else None
    c["f3_mean"] = round(statistics.mean(r["f3"] for r in rs if r["f3"]), 2) if any(r["f3"] for r in rs) else None
    c["b3_mean"] = round(statistics.mean(r["b3"] for r in rs if r["b3"]), 2) if any(r["b3"] for r in rs) else None
    pc = collections.Counter(r["pace"] for r in rs if r["pace"])
    tot = sum(pc.values())
    c["pace_share"] = {k: pct(pc[k], tot) for k in ("ハイ", "平均", "スロー")}
    c["wtime_good_med"] = med([r["wtime"] for r in rs if r["baba"] == "良"])
    laps = [r["lap"] for r in rs if r["lap"]]
    if laps:
        L = collections.Counter(len(x) for x in laps).most_common(1)[0][0]
        c["lap_mean"] = [round(statistics.mean(x[i] for x in laps if len(x) == L), 1) for i in range(L)]
    # ペース別の 前（逃げ・先行）と 後（差し・追込）の3着内率
    pv = {}
    for pace in ("ハイ", "平均", "スロー"):
        hs = [h for r in rs if r["pace"] == pace for h in r["horses"] if h["style"]]
        fr = [h for h in hs if h["style"] in ("逃げ", "先行")]
        bk = [h for h in hs if h["style"] in ("差し", "追込")]
        if len(fr) >= 30 and len(bk) >= 30:
            pv[pace] = dict(front=pct(sum(h["f"] <= 3 for h in fr), len(fr)), back=pct(sum(h["f"] <= 3 for h in bk), len(bk)))
    c["pace_x_style"] = pv
    # 種牡馬（全期間）・騎手（直近）
    def table(key, hs, mn):
        g = collections.defaultdict(lambda: [0, 0, 0, 0.0])
        for h in hs:
            if h[key]:
                a = g[h[key]]
                a[0] += 1; a[1] += h["f"] == 1; a[2] += h["f"] <= 3; a[3] += h["odds"] * 100 if h["f"] == 1 else 0
        rows_ = [(k, v[0], pct(v[1], v[0]), pct(v[2], v[0]), round(v[3] / v[0], 0)) for k, v in g.items() if v[0] >= mn]
        return sorted(rows_, key=lambda x: (-x[3], -x[1]))[:8]
    c["sire"] = table("sire", all_h, MIN_SIRE)
    rec = [h for r in rs if (recent_from is None or r["year"] >= recent_from) for h in r["horses"]]
    c["jockey"] = table("jockey", rec, MIN_JOCKEY if recent_from else 5)
    return c


def compare_year(rs, y):
    """最新年の値（同じ指標を今年だけで）"""
    sub = [r for r in rs if r["year"] == y]
    if len(sub) < 8:
        return None
    k = card(sub)
    return {x: k[x] for x in ("races", "fav_win", "inner_top3", "outer_top3", "pace_diff", "pace_share", "win_style", "upfast_top3", "wtime_good_med")}


# ── 表示 ──────────────────────────────────────────────────────────
def md_card(title, c, now=None, trend=None, winners=None):
    L = [f"### {title}", f"{c['span']}・{c['races']}レース"]
    L.append(f"- **人気**: 1番人気 勝率{c['fav_win']}%・3着内{c['fav_top3']}%／1〜3番人気の勝ち{c['top3pop_win']}%／6番人気以下の勝ち{c['pop6plus_win']}%／勝ち馬の単勝中央値 {c['win_odds_med']}倍")
    L.append(f"- **配当**: 馬連中央値 {c['umaren_med'] and int(c['umaren_med']):,}円／3連単中央値 {c['sanrentan_med'] and int(c['sanrentan_med']):,}円・10万円超 {c['sanrentan_100k']}%"
             if c["umaren_med"] and c["sanrentan_med"] else "- **配当**: －")
    L.append(f"- **枠（3着内率）**: 内1〜3枠 {c['inner_top3']}% ／ 外6〜8枠 {c['outer_top3']}% ／ 枠別 " + " ".join(f"{k}:{v}" for k, v in c["waku_top3"].items()))
    L.append("- **脚質**: 勝ち馬 " + "・".join(f"{k}{v}%" if v is not None else f"{k}－" for k, v in c["win_style"].items()) +
             " ／ 3着内率 " + "・".join(f"{k}{v}%" if v is not None else f"{k}－" for k, v in c["style_top3"].items()) +
             f" ／ 上がり最速の馬 勝率{c['upfast_win']}%・3着内{c['upfast_top3']}%")
    ps = c["pace_share"]
    L.append(f"- **ペース**: 前3F {c['f3_mean']} − 後3F {c['b3_mean']} ＝ {c['pace_diff']:+.2f}秒（マイナス＝前半が速い）／ハイ{ps['ハイ']}%・平均{ps['平均']}%・スロー{ps['スロー']}%"
             f"／良馬場の勝ちタイム中央値 {fmt_t(c['wtime_good_med'])}" if c["pace_diff"] is not None else "- **ペース**: －")
    if c.get("lap_mean"):
        L.append(f"- **平均ラップ**: {'-'.join(str(x) for x in c['lap_mean'])}")
    if c["pace_x_style"]:
        L.append("- **ペース別 前(逃先)/後(差追)の3着内率**: " + "／".join(f"{k} 前{v['front']}%・後{v['back']}%" for k, v in c["pace_x_style"].items()))
    if c["sire"]:
        L.append("- **種牡馬（3着内率順・20走以上）**: " + "／".join(f"{s}（{n}走 勝{w}% 3内{t}% 単回{int(r)}%）" for s, n, w, t, r in c["sire"][:6]))
    if c["jockey"]:
        L.append("- **騎手（3着内率順）**: " + "／".join(f"{s}（{n}騎乗 勝{w}% 3内{t}% 単回{int(r)}%）" for s, n, w, t, r in c["jockey"][:6]))
    if now:
        ps2 = now["pace_share"]
        L.append(f"- **今年（{now['races']}レース）**: 1番人気勝率{now['fav_win']}%（10年{c['fav_win']}%）／内1〜3枠3着内{now['inner_top3']}%（{c['inner_top3']}%）・外6〜8枠{now['outer_top3']}%（{c['outer_top3']}%）"
                 f"／前3F−後3F {now['pace_diff']:+.2f}秒（{c['pace_diff']:+.2f}）・ハイ{ps2['ハイ']}%（{ps['ハイ']}%）"
                 f"／勝ち馬 逃げ{now['win_style']['逃げ']}%・先行{now['win_style']['先行']}%（{c['win_style']['逃げ']}%・{c['win_style']['先行']}%）"
                 f"／良の勝ちタイム {fmt_t(now['wtime_good_med'])}（{fmt_t(c['wtime_good_med'])}）")
    if trend:
        L.append("- **人気より走る・走らない条件（前半・後半とも同じ向き＝course_trends）**: " + "／".join(
            f"{k.split('|')[0]} {k.split('|')[1]} 比{v['ratio']:.2f}" for k, v in sorted(trend.items(), key=lambda kv: -abs(kv[1]['z']))[:5]))
    if winners:
        L.append("\n| 年 | 勝ち馬 | 人気 | 枠 | 脚質 | 通過 | 上がり | 前3F-後3F | 馬場 | 勝ちタイム | 3連単 |")
        L.append("|---|---|---:|---:|---|---|---|---|---|---|---:|")
        for w in winners:
            L.append(f"| {w['year']} | {w['name']} | {w['pop']} | {w['waku']} | {w['style']} | {w['corner']} | {w['up']} | {w['f3']}-{w['b3']}（{w['pace']}） | {w['baba']} | {fmt_t(w['wtime'])} | {w['sanrentan'] and int(w['sanrentan']):,} |")
    return "\n".join(L)


def winners_list(rs):
    out = []
    for r in rs:
        w = next(h for h in r["horses"] if h["f"] == 1)
        out.append(dict(year=r["year"], date=r["date"], course=r["course"], name=w["name"], pop=w["pop"], waku=w["waku"], style=w["style"],
                        corner=w["corner"], up=w["up"], f3=r["f3"], b3=r["b3"], pace=r["pace"] or "－", baba=r["baba"], wtime=r["wtime"],
                        sanrentan=r["sanrentan"] or 0))
    return out


def build():
    rs = load()
    latest = max(r["year"] for r in rs)
    recent_from = str(int(latest) - 2)
    trends = json.loads(TRENDS.read_text(encoding="utf-8")).get("course", {}) if TRENDS.exists() else {}
    J = {"generated": rs[-1]["date"], "span": f"{rs[0]['date']}〜{rs[-1]['date']}", "latest_year": latest, "course": {}, "race": {}}
    by_c = collections.defaultdict(list)
    for r in rs:
        by_c[r["course"]].append(r)
    by_g = collections.defaultdict(list)
    for r in rs:
        if r["grade"] and r["name"]:
            by_g[r["name"]].append(r)
    OUT_DIR.mkdir(exist_ok=True)
    md = [f"# コースの型・重賞の型（{J['span']}）\n",
          "10年分の結果から「どんな馬が・どんなペースで・どう決着したか」をまとめた型カード。`python course_profile.py --course 京都芝2000m` / `--race 秋華賞` で1枚ずつ引ける。",
          "⚠ 脚質・ペース・上がりは結果から付けた値（レース前には確定しない）。読み・説明用。種牡馬・騎手の回収率は件数が少ないと偶然が大きい。内回り・外回りは区別していない。\n",
          "## 索引（コース）\n", "| コース | レース | 1番人気勝率 | 内1-3枠 3着内 | 外6-8枠 3着内 | 前3F−後3F | ハイ% | 勝ち馬 逃げ+先行% | 3連単中央値 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    cards = []
    for name, sub in sorted(by_c.items(), key=lambda kv: (kv[0][:2], kv[1][0]["surf"], kv[1][0]["m"])):
        if len(sub) < MIN_COURSE:
            continue
        c = card(sub, recent_from)
        now = compare_year(sub, latest)
        tr = (trends.get(name) or {}).get("stable")
        J["course"][name] = dict(c, now=now)
        md.append(f"| {name} | {c['races']} | {c['fav_win']}% | {c['inner_top3']}% | {c['outer_top3']}% | {c['pace_diff']:+.2f} | {c['pace_share']['ハイ']}% | "
                  f"{(c['win_style']['逃げ'] or 0) + (c['win_style']['先行'] or 0):.0f}% | {c['sanrentan_med'] and int(c['sanrentan_med']):,} |")
        text = md_card(name, c, now, tr)
        cards.append(text)
        (OUT_DIR / f"{name}.md").write_text(f"# {name} の型\n\n" + text + "\n", encoding="utf-8")
    md.append("\n## 索引（重賞）\n")
    md.append("| 重賞 | 格 | 回数 | 1番人気勝率 | 1〜3番人気の勝ち | 前3F−後3F | 勝ち馬 逃げ+先行% | 3連単中央値 |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|")
    rcards = []
    for name, sub in sorted(by_g.items(), key=lambda kv: (kv[1][-1]["grade"], kv[0])):
        if len(sub) < 4:
            continue
        c = card(sub)
        wl = winners_list(sub)
        J["race"][name] = dict(c, grade=sub[-1]["grade"], courses=sorted({r["course"] for r in sub}), winners=wl)
        md.append(f"| {name} | {sub[-1]['grade']} | {len(sub)} | {c['fav_win']}% | {c['top3pop_win']}% | {c['pace_diff']:+.2f} | "
                  f"{(c['win_style']['逃げ'] or 0) + (c['win_style']['先行'] or 0):.0f}% | {c['sanrentan_med'] and int(c['sanrentan_med']):,} |")
        text = md_card(f"{name}（{sub[-1]['grade']}・{'/'.join(sorted({r['course'] for r in sub}))}）", c, winners=wl)
        rcards.append(text)
        (OUT_DIR / f"重賞_{name}.md").write_text(f"# {name} の型\n\n" + text + "\n", encoding="utf-8")
    md.append("\n## コースの型カード\n")
    md += [x + "\n" for x in cards]
    md.append("\n## 重賞の型カード\n")
    md += [x + "\n" for x in rcards]
    OUT_JSON.write_text(json.dumps(J, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"コース {len(J['course'])} ／ 重賞 {len(J['race'])}\n保存: {OUT_JSON}\n保存: {OUT_MD}\n保存: {OUT_DIR}\\*.md")


def show(kind, name):
    J = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    pool = J[kind]
    hit = [k for k in pool if k == name] or [k for k in pool if name in k]
    if not hit:
        print(f"見つからない: {name}")
        return
    for k in hit[:3]:
        c = pool[k]
        print(md_card(k, c, c.get("now"), winners=c.get("winners")))
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--course")
    ap.add_argument("--race")
    a = ap.parse_args()
    if a.course:
        show("course", a.course)
    elif a.race:
        show("race", a.race)
    else:
        build()
