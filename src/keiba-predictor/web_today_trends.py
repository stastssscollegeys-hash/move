# -*- coding: utf-8 -*-
"""web_today_trends.py — 当日の結果から「今日の傾向」を1枚にまとめ、次のレースの予想に使える形にする（2026-11-15 新設）
ユーザー指示（2026-11-15）: 「今までのデータ・今日のデータを集めて、トラックバイアスや今日の傾向を全部まとめて予想に活かせる状態に」。
入力: {OUT}/{日付}_web_results.json（web_results.py）／{OUT}/{前日}_web_results.json（あれば）／{日付}/research/course_cards/*.txt（course_profile.py）
      {日付}/research/web_compose_all_raw.txt（あれば＝事前に出した印と買い目の答え合わせ）
出力: Desktop/競馬予想レポート/{日付}/{日付}_今日の傾向.md と 標準出力。レースが終わるたびに回し直す。
  python web_results.py --date D && python web_today_trends.py --date D --prev 前日
中身: ①場×芝ダごとの 脚質・枠・ペース・勝ち時計（10年の中央値との差）・人気の決まり方・上がり最速の成績・前日との比較・予想に使うときの一言
      ②騎手の今日の成績（場をまたいで）③事前に出した印と買い目の答え合わせ（◎の着順・印の3着内・払戻）"""
import argparse, collections as C, json, re, statistics, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from course_profile import style_of
ROOT = Path("C:/Users/User/Desktop/競馬予想レポート"); OUT = ROOT / "daily_pdca/web_live"
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"


def tsec(t):
    m = re.match(r"(?:(\d+):)?(\d+)\.(\d)", str(t or ""))
    return int(m.group(1) or 0) * 60 + int(m.group(2)) + int(m.group(3)) / 10 if m else None


def med_time(date, venue, dist):
    f = ROOT / date / "research/course_cards" / f"{venue}{dist}.txt"
    if not f.exists(): return None
    m = re.search(r"良馬場の勝ちタイム中央値 ([\d:.]+)", f.read_text(encoding="utf-8"))
    return tsec(m.group(1)) if m else None


def load(date):
    f = OUT / f"{date}_web_results.json"
    return {k: v for k, v in json.load(open(f, encoding="utf-8")).items() if v.get("rows")} if f.exists() else {}


def surf_key(r):
    return (r["venue"], "芝" if r["dist"].startswith("芝") else "ダ")


def agg(R):
    S = C.defaultdict(lambda: dict(st=C.defaultdict(lambda: [0, 0, 0]), wk=C.defaultdict(lambda: [0, 0]), races=[], fav=[], l3=[0, 0, 0], baba=set()))
    for k, r in sorted(R.items(), key=lambda x: (x[1]["venue"], x[1]["R"])):
        s = S[surf_key(r)]; n = len(r["rows"]); s["baba"].add(r["baba"])
        for h in r["rows"]:
            st = style_of(r["corners"].get(str(h["uma"]), ""), n) or "不明"
            x = s["st"][st]; x[0] += 1; x[1] += h["rank"] <= 3; x[2] += h["rank"] == 1
            g = "内1-3枠" if h["waku"] <= 3 else "中4-6枠" if h["waku"] <= 6 else "外7-8枠"
            w = s["wk"][g]; w[0] += 1; w[1] += h["rank"] <= 3
        fav = min(r["rows"], key=lambda h: h.get("odds") or 999)
        s["fav"].append(fav["rank"])
        l3s = [(float(h["l3"]), h["rank"]) for h in r["rows"] if re.match(r"\d", str(h.get("l3") or ""))]
        if l3s:
            best = min(l3s)[1]; s["l3"][0] += 1; s["l3"][1] += best == 1; s["l3"][2] += best <= 3
        lap = r.get("lap") or []
        pace = round(sum(lap[:3]) - sum(lap[-3:]), 1) if len(lap) >= 6 else None
        top = sorted(r["rows"], key=lambda h: h["rank"])[:3]
        pay = r.get("pay", {})
        yen = lambda t: (pay.get(t) or [{}])[0].get("yen")
        s["races"].append(dict(R=r["R"], dist=r["dist"], baba=r["baba"], n=n, pace=pace, time=top[0].get("time"),
                               pops=[h.get("pop") for h in top], styles=[style_of(r["corners"].get(str(h["uma"]), ""), n) for h in top],
                               waku=[h["waku"] for h in top], win=yen("単勝"), umaren=yen("馬連"), trio=yen("3連複"), tri=yen("3連単")))
    return S


def ratio(st, s):
    tot = sum(v[0] for v in st.values()); t3 = sum(v[1] for v in st.values()); v = st.get(s)
    return (v[1] / t3) / (v[0] / tot) if v and v[0] and t3 else None


def hint(s):
    st = s["st"]; out = []
    fr = [ratio(st, x) for x in ("逃げ", "先行")]; bk = [ratio(st, x) for x in ("差し", "追込")]
    f = sum(x for x in fr if x) / max(1, sum(1 for x in fr if x)); b = sum(x for x in bk if x) / max(1, sum(1 for x in bk if x))
    good = [x for x in ("逃げ", "先行", "差し", "追込") if (ratio(st, x) or 0) >= 1.5]
    bad = [x for x in ("逃げ", "先行", "差し", "追込") if st.get(x) and st[x][0] >= 4 and (ratio(st, x) or 0) <= 0.5]
    if f >= 1.4 and b <= 0.8: out.append("前残り（逃げ・先行が有利）")
    elif b >= 1.2 and f <= 1.0: out.append("差しが届く（前が止まる）")
    elif good: out.append("・".join(good) + "が来ている" + ("（" + "・".join(bad) + "は苦戦）" if bad else ""))
    else: out.append("脚質の偏りは小さい")
    if bad and (f >= 1.4 and b <= 0.8 or b >= 1.2 and f <= 1.0): out.append("・".join(bad) + "は3着内が出走の半分以下")
    l3 = s["l3"]
    if l3[0] >= 3 and l3[1] >= l3[0] - 1: out.append(f"上がり最速の馬が{l3[0]}戦{l3[1]}勝")
    wk = s["wk"]; rate = {g: w[1] / w[0] for g, w in wk.items() if w[0] >= 6}
    if rate:
        hi, lo = max(rate, key=rate.get), min(rate, key=rate.get)
        if rate[hi] - rate[lo] >= 0.15: out.append(f"{hi}が良く{lo}が苦戦")
    fav = s["fav"]
    if fav:
        w = sum(1 for x in fav if x == 1); t3 = sum(1 for x in fav if x <= 3)
        out.append(f"1番人気 {len(fav)}戦{w}勝・3着内{t3}" + ("（人気馬が勝ち切れない）" if len(fav) >= 3 and w == 0 else ""))
    nr = len(s["races"])
    out.append(f"※{nr}レース分（" + ("少なすぎて傾向とは言えない" if nr < 3 else "まだ少ない") + "）。印は動かさず、相手選び・金額配分・説明の材料にする")
    return "／".join(out)


def grade(date, R):
    f = ROOT / date / "research/web_compose_all_raw.txt"
    if not f.exists(): return []
    rows, raw = [], f.read_text(encoding="utf-8")
    for b in raw.split("■ ")[1:]:
        key = b.split()[0]; r = R.get(key)
        if not r: continue
        m = re.search(r"印: (.*)", b); marks = re.findall(r"([◎○▲△穴])(\d+)", m.group(1)) if m else []
        rank = {h["uma"]: h["rank"] for h in r["rows"]}
        pay = r.get("pay", {}); ret = 0; stake = 0; hits = []
        for t, combo, amt in re.findall(r"^\s+(単勝|馬連|ワイド|3連複)\s+([\d-]+)\s+([\d,]+)円", b, re.M):
            a = int(amt.replace(",", "")); stake += a
            cs = "-".join(sorted(combo.split("-"), key=int))
            for p in pay.get(t, []):
                if "-".join(sorted(p["comb"].split("-"), key=int)) == cs:
                    ret += p["yen"] * a // 100; hits.append(f"{t}{combo}")
        hm = marks[0] if marks else None
        rows.append(dict(key=key, R=r["R"], venue=r["venue"], honmei=f"◎{CIRC[int(hm[1])-1]}{rank.get(int(hm[1]),'?')}着" if hm else "-",
                         marks=" ".join(f"{mk}{CIRC[int(u)-1]}{rank.get(int(u),'?')}" for mk, u in marks),
                         stake=stake, ret=ret, hits=hits))
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--prev", default=""); a = ap.parse_args()
    R = load(a.date); P = load(a.prev) if a.prev else {}
    S, SP = agg(R), agg(P)
    L = [f"# {a.date[4:6]}/{a.date[6:]} 今日の傾向（{len(R)}レース終了時点・内部用）",
         "レースが終わるたびに web_results.py → web_today_trends.py で更新。数字は今日の結果だけ（前日は比較用）。", ""]
    L.append("## 一言まとめ（場×芝ダ）")
    for key in sorted(S):
        L.append(f"- {key[0]}{key[1]}（{'・'.join(sorted(S[key]['baba']))}）: {hint(S[key])}")
    for key in sorted(S):
        s = S[key]; st = s["st"]
        L += ["", f"## {key[0]}{key[1]}（馬場 {'→'.join(sorted(s['baba']))}・{len(s['races'])}レース）"]
        L.append("脚質: " + " ／ ".join(f"{x} {st[x][1]}/{st[x][0]}（倍率{ratio(st, x):.2f}）" for x in ("逃げ", "先行", "差し", "追込") if st.get(x) and st[x][0]))
        L.append("枠: " + " ／ ".join(f"{g} {w[1]}/{w[0]}={w[1]/w[0]:.0%}" for g, w in sorted(s["wk"].items())))
        if s["l3"][0]: L.append(f"上がり最速の馬: {s['l3'][0]}戦 {s['l3'][1]}勝・3着内{s['l3'][2]}")
        if key in SP:
            p = SP[key]; L.append(f"前日（{'・'.join(sorted(p['baba']))}・{len(p['races'])}R）: " + hint(p).split("／※")[0])
        L.append("| R | 距離 | 馬場 | 頭数 | 前3F−後3F | 勝ち時計（良の中央値との差） | 1〜3着の人気 | 脚質 | 枠 | 単勝 | 馬連 | 3連複 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for x in s["races"]:
            mt = med_time(a.date, key[0], x["dist"]); t = tsec(x["time"])
            diff = f"{x['time']}（{t-mt:+.1f}秒）" if mt and t else str(x["time"])
            L.append(f"| {x['R']} | {x['dist']} | {x['baba']} | {x['n']} | {x['pace'] if x['pace'] is not None else '-'} | {diff} | {'-'.join(str(p) for p in x['pops'])} | {'・'.join(s_ or '?' for s_ in x['styles'])} | {'-'.join(map(str, x['waku']))} | {x['win']} | {x['umaren']} | {x['trio']} |")
    jk = C.defaultdict(lambda: [0, 0, 0, set()])
    for r in R.values():
        for h in r["rows"]:
            j = jk[h["jockey"]]; j[0] += 1; j[1] += h["rank"] == 1; j[2] += h["rank"] <= 3; j[3].add(r["venue"])
    L += ["", "## 騎手（今日・2勝以上か3着内3回以上）"]
    for name, j in sorted(jk.items(), key=lambda x: (-x[1][1], -x[1][2])):
        if j[1] >= 2 or j[2] >= 3: L.append(f"- {name}（{'・'.join(sorted(j[3]))}）: {j[0]}鞍 {j[1]}勝・3着内{j[2]}")
    nf = ROOT / a.date / "research/today_lessons.txt"      # 手で書く「今日の学び」（直前予想の答え合わせなど）
    if nf.exists(): L += ["", "## 今日の学び（手書き）"] + [x for x in nf.read_text(encoding="utf-8").splitlines() if x.strip()]
    G = grade(a.date, R)
    if G:
        st_, rt_ = sum(g["stake"] for g in G), sum(g["ret"] for g in G)
        L += ["", f"## 事前に出した印と買い目の答え合わせ（{len(G)}レース・朝の版 web_compose_all_raw）",
              f"合計 {st_:,}円 → {rt_:,}円（回収率 {rt_/max(1,st_):.0%}）／◎の3着内 {sum(1 for g in G if re.search(r'[123]着', g['honmei']))}/{len(G)}"]
        for g in sorted(G, key=lambda g: (g["venue"], g["R"])):
            L.append(f"- {g['key']}R {g['honmei']} ｜ 印 {g['marks']} ｜ {g['stake']:,}→{g['ret']:,}円" + (f"（{'・'.join(g['hits'])}）" if g["hits"] else ""))
    fb = ROOT / a.date / "research" / f"final_bets_{a.date}.json"     # 直前予想（最終版）の買い目＝{レース: [[券種, 組, 金額], …]}
    if fb.exists():
        B = json.load(open(fb, encoding="utf-8")); norm = lambda c_: "-".join(sorted(c_.split("-"), key=int)); ts = tr_ = 0; rows_ = []
        for k, bs in B.items():
            r = R.get(k)
            if not r: rows_.append(f"- {k}R 結果待ち"); continue
            st0 = sum(b_[2] for b_ in bs); rt0 = 0; hit = []
            for t, c_, amt in bs:
                for p_ in r.get("pay", {}).get(t, []):
                    if norm(p_["comb"]) == norm(c_): rt0 += p_["yen"] * amt // 100; hit.append(f"{t}{c_}")
            ts += st0; tr_ += rt0
            top = [h["uma"] for h in sorted(r["rows"], key=lambda h: h["rank"])[:3]]
            rows_.append(f"- {k}R 1〜3着 {'-'.join(map(str, top))} ｜ {st0:,}→{rt0:,}円" + (f"（{'・'.join(hit)}）" if hit else ""))
        L += ["", f"## 直前予想（最終版）の答え合わせ（final_bets_{a.date}.json）", f"合計 {ts:,}円 → {tr_:,}円（回収率 {tr_/max(1,ts):.1%}）"] + rows_
    txt = "\n".join(L) + "\n"
    f = ROOT / a.date / f"{a.date}_今日の傾向.md"; f.write_text(txt, encoding="utf-8-sig"); print(txt); print("保存:", f)


if __name__ == "__main__":
    main()
