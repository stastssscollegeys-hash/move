"""web_live.py — JRA-VANが無い日の「出走表をWebから取ってエンジンに渡す」橋渡し（2026-11-06 新設）

出走表・枠順・騎手・厩舎・斤量・単勝オッズ（中間）を Yahoo!スポーツナビ競馬から取り、蓄積DB（〜JV最終取得日）と
前回の学習済み係数（db/ev_cache/{日付}.pkl の beta, w）で、騎手・厩舎・馬の履歴を含むモデル確率を出す。
JV版（ev_live.py）との違い: 馬体重・調教（chokyo）は入らない（馬体重は発表後に --weights で足せる）。台帳には登録しない。

使い方:
  python web_live.py --date 20261107 --seed 2605050111            # 出走表を取って確率を出す
  出力: {OUT}/{日付}_web_probs.json（レースごとの 馬番・馬名・単勝・市場確率・モデル確率・騎手・厩舎）
"""
import argparse
import collections
import datetime
import json
import pickle
import re
import sys
import unicodedata

import numpy as np
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import ev_live as L

UA = {"User-Agent": "Mozilla/5.0"}
BASE = "https://sports.yahoo.co.jp/keiba/race/"
VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}
OUT = L.DB.parent / "web_live"


def get(url):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def nfkc(s):
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "")


def discover(seed):
    """seed のレースページに載っている『同じ日の各競馬場の一覧』から、競馬場ごとの接頭辞（例 26050501）を拾う"""
    soup = get(BASE + "denma/" + seed)
    pre = sorted({m.group(1) for a in soup.find_all("a", href=True) for m in [re.search(r"/keiba/race/list/(\d{8})", a["href"])] if m})
    return pre


def parse_race(rid):
    soup = get(BASE + "denma/" + rid)
    main = soup.find("main") or soup
    txt = main.get_text("\n", strip=True)
    lines = txt.split("\n")
    head = {}
    for i, ln in enumerate(lines):
        if ln.endswith("発走") and i + 2 < len(lines):
            title, j, grade = lines[i + 1], i + 2, ""
            if re.fullmatch(r"(GIII|GII|GI|L|J・GIII|J・GII|J・GI)", lines[j]):
                grade, j = lines[j], j + 1
            course = " ".join(lines[j:j + 14]).split("出馬表")[0].split("本賞金")[0].replace("： ", "：")     # 「芝・左 1400m」「天気：」「晴」「馬場：」「良」「2歳 …」が別の行に分かれている
            cm = re.search(r"(芝|ダート|障害)\S*\s*(\d{3,4})m", course)
            bm = re.search(r"馬場：(\S+)", course)
            wm = re.search(r"天気：(\S+)", course)
            km = re.search(r"馬場：\S+\s+(.+?)(?:\s+[（\[]|\s+馬齢|\s+定量|\s+別定|\s+ハンデ|$)", course)
            rn = re.search(r"(\d+)R", " ".join(lines[max(0, i - 6):i][::-1]))
            head = dict(R=int(rn.group(1)) if rn else 0, start=ln.replace("発走", ""), title=title + (" " + grade if grade else ""),
                        cond=km.group(1) if km else course, surf={"芝": "芝", "ダート": "ダ", "障害": "障"}[cm.group(1)] if cm else "",
                        dist=cm.group(2) if cm else "", baba=bm.group(1) if bm else "", wea=wm.group(1) if wm else "")
            break
    rows = []
    for tr in main.select("table tbody tr"):
        c = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) < 8:
            continue
        name_sex = c[2].split(" ")
        jk = re.match(r"(.+?) (\d+\.\d)$", c[3])
        tr_ = re.match(r"(.+?) \((.+)\)", c[4])
        fm = re.match(r"父：(.+?) 母：(.+?) \(母父：(.+?)\)", c[5])
        rows.append(dict(waku=int(c[0]), uma=int(c[1]), name=name_sex[0], sexage=name_sex[1].split("/")[0] if len(name_sex) > 1 else "",
                         jockey=jk.group(1) if jk else c[3], kin=float(jk.group(2)) if jk else 0.0, trainer=tr_.group(1) if tr_ else c[4],
                         sire=fm.group(1).strip() if fm else "", damsire=fm.group(3).strip() if fm else "", weight=c[6], pop_odds=c[7]))
    return head, rows


def tan_odds(rid):
    """中間オッズの単勝（tfw ページ）"""
    soup = get(BASE + "odds/tfw/" + rid)
    main = soup.find("main") or soup
    out = {}
    for tr in main.select("table tr"):
        c = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if len(c) >= 5 and c[1].isdigit():
            try:
                out[int(c[1])] = float(c[3])
            except ValueError:
                pass
    return out


def hist_maps():
    """蓄積DBから 馬名→horse_id と 騎手名の一覧"""
    rows = E.load_rows()
    hid, jk = {}, collections.Counter()
    for r in rows:
        if r.get("horse_id"):
            hid[r["馬名"].replace(" ", "")] = r["horse_id"]
        jk[r["騎手"]] += 1
    res, _ = L.jv_results_and_entries("00000000")
    for r in res:
        if r.get("horse_id"):
            hid[r["馬名"].replace(" ", "")] = r["horse_id"]
        jk[r["騎手"]] += 1
    return hid, jk


def jockey_key(name, known):
    """Yahoo の騎手名（例: 横山 武史 / C.ルメール / 佐々木 大輔）→ DB の表記（4文字に切った形・外国人は姓の頭）"""
    n = nfkc(name)
    if n in known:
        return n, True
    foreign = re.match(r"^([A-Za-z])\.(.+)$", n)
    if foreign:
        ini, rest = foreign.group(1), foreign.group(2)
        for cand in (f"{ini}．{rest[:2]}", f"{ini}．{rest[:3]}", rest, rest[:4], rest[:3]):
            c2 = unicodedata.normalize("NFKC", cand)
            for k in known:
                if unicodedata.normalize("NFKC", k) == c2:
                    return k, True
        for k in known:                                # 前方一致
            if unicodedata.normalize("NFKC", k).startswith(unicodedata.normalize("NFKC", rest[:3])):
                return k, True
        return rest[:4], False
    for cand in (n[:4], n[:3], n):
        for k in known:
            if unicodedata.normalize("NFKC", k) == cand:
                return k, True
    return n[:4], False


def class_of(title, cond):
    g = re.search(r"\b(GIII|GII|GI|J・GIII|J・GII|J・GI|L)\b", title)
    grade = {"GIII": "G3", "GII": "G2", "GI": "G1"}.get(g.group(1)) if g else None
    if "新馬" in cond:
        c = "新馬"
    elif "未勝利" in cond:
        c = "未勝利"
    elif "1勝" in cond:
        c = "1勝クラス"
    elif "2勝" in cond:
        c = "2勝クラス"
    elif "3勝" in cond:
        c = "3勝クラス"
    else:
        c = "オープン"
    nm = re.sub(r"\s*(GIII|GII|GI|J・GIII|L)$", "", title).strip()
    if grade:
        return f"{grade} オープン {nm}", nm
    if c in ("2勝クラス", "3勝クラス", "オープン") and not re.search(r"^サラ系|^\d", title):
        return f"特別 {c} {nm}", nm
    return c, ""


def build_rows(date, prefixes, hid, known_jk):
    rows, odds, meta, unmatched = [], {}, {}, set()
    for pre in prefixes:
        venue = VENUE[pre[2:4]]
        for R in range(1, 13):
            rid = f"{pre}{R:02d}"
            try:
                head, hs = parse_race(rid)
            except Exception as e:                      # 開催が無い場合など
                continue
            if not hs or not head:
                continue
            od = tan_odds(rid)
            surf = head["surf"]
            if surf == "障":
                continue
            dist = f"{surf}{head['dist']}m" if head["dist"] else ""
            cond, rname = class_of(head["title"], head["cond"])
            baba, wea = head["baba"], head["wea"]
            n = len(hs)
            meta[(venue, R)] = dict(title=head["title"], start=head["start"], dist=dist, baba=baba, cond=cond, rid=rid, n=n)
            for h in hs:
                jkey, ok = jockey_key(h["jockey"], known_jk)
                if not ok:
                    unmatched.add((h["jockey"], jkey))
                nm = h["name"].replace(" ", "")
                rows.append({
                    "date": date, "競馬場": venue, "R": R, "race_id": f"{date}-{venue}-{R}", "レース名": rname, "距離": dist, "馬場状態": baba, "天候": wea,
                    "条件": cond, "コース情報": f"{dist} / 天候 : {wea} / {surf} : {baba}", "枠": h["waku"], "馬番": h["uma"], "馬名": h["name"],
                    "horse_id": hid.get(nm) or "web:" + nm, "性齢": h["sexage"], "前3F_レース": None, "後3F_レース": None, "ラップ": [],
                    "斤量_kg": h["kin"], "騎手": jkey, "タイム": "", "着差": "", "コーナー通過": "", "後3F": None,
                    "単勝オッズ": od.get(h["uma"], 0.0), "人気": 0, "馬体重": "" if h["weight"].startswith("-") else h["weight"].split("(")[0], "体重表示": "" if h["weight"].startswith("-") else h["weight"],
                    "厩舎": nfkc(h["trainer"]), "着順": "", "着順int": None, "後3F順位": None, "脚質": "", "頭数": n,
                    "父": h["sire"], "母父": h["damsire"], "_live": True, "_web": True})
    return rows, meta, unmatched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--seed", help="その日のどれか1レースのID（例 2605050111）。同じ日の競馬場を自動で探す")
    ap.add_argument("--prefix", nargs="*", help="競馬場の接頭辞（例 26050501）を直接指定")
    ap.add_argument("--model", default="", help="学習済み係数のキャッシュ日付（既定: db/ev_cache の最新）")
    a = ap.parse_args()
    prefixes = a.prefix or discover(a.seed)
    print("競馬場:", [(p, VENUE[p[2:4]]) for p in prefixes])
    hid, known = hist_maps()
    print(f"馬 {len(hid):,}頭 ／ 騎手表記 {len(known)}")
    rows, meta, unmatched = build_rows(a.date, prefixes, hid, set(known))
    print(f"出走表 {len(rows)}頭 ／ {len(meta)}レース ／ 馬名がDBに無い（初出走）{sum(1 for r in rows if r['horse_id'].startswith('web:'))}頭")
    if unmatched:
        print("騎手がDBの表記に合わない:", sorted(unmatched))
    cf = sorted((L.DB / "ev_cache").glob("2026*.pkl"))
    cf = [f for f in cf if "replay" not in f.name]
    mf = (L.DB / "ev_cache" / f"{a.model}.pkl") if a.model else cf[-1]
    cache = pickle.loads(mf.read_bytes())
    beta, w = cache["beta"], cache["w"]
    print("係数:", mf.name, cache.get("made_at"))
    # 履歴＋最新成績＋当日の出走表で特徴量を作る（学習はしない＝前回の係数を使う）
    n_hist, extra, last = L.train_all()
    live = [r for r in rows if r["単勝オッズ"] and r["単勝オッズ"] < 900]
    orig = E.load_rows
    E.load_rows = lambda: orig() + extra
    races, _ = E.build(extra_rows=live)
    E.load_rows = orig
    liv = [r for r in races if r["part"] == "live"]
    print(f"履歴 {n_hist:,}レース（〜{last}） ／ 当日 {len(liv)}レース")
    info = {(r["競馬場"], r["R"], r["馬番"]): r for r in rows}
    # 単勝ルール B1（市場＋木のずれ・benter_live.py）の確率も付ける（2026-11-18 追加。JV 終了後も台帳を続けるため）。
    # 馬体重は発表済みなら入る。当日のトラックバイアスは入れない（終わったレースの成績を渡していない）。失敗しても本体は止めない
    b1 = {}
    try:
        import benter_live as BL
        wh, snap = {}, {}
        for r in liv:
            v, R = r["key"][1], r["key"][2]
            snap[(v, R)] = ({u: float(o) for u, o in zip(r["uma"], r["odds"])}, {}, dict(race_id=meta[(v, R)]["rid"], title=meta[(v, R)]["title"], fetched_at=""))
            for u in r["uma"]:
                wt = info[(v, R, u)].get("体重表示")
                if wt:
                    wh[(v, R, int(u))] = wt
        for x in BL.score(liv, snap, wh, [], a.date, cache.get("exp3") or {}):
            b1[(x["key"][1], x["key"][2])] = dict(zip(x["uma"], x["p"]))
        print(f"B1（市場＋木）: {len(b1)}レース")
    except Exception as e:
        print("B1 は計算できませんでした:", repr(e)[:200])
    out = {}
    for r in liv:
        v, R = r["key"][1], r["key"][2]
        p = E.probs(r, beta, w)
        q = r["q"]
        uma = r["uma"]
        hs = []
        for u, pi, qi, oi in zip(uma, p, q, r["odds"]):
            x = info[(v, R, u)]
            hs.append(dict(uma=int(u), name=x["馬名"], odds=float(oi), p_model=round(float(pi), 4), p_market=round(float(qi), 4),
                           jockey=x["騎手"], trainer=x["厩舎"], new=x["horse_id"].startswith("web:"), weight=x.get("体重表示", ""),
                           p_b1=(b1.get((v, R)) or {}).get(int(u))))   # weight=馬体重の表示（例 476(+4)・発表前は空）2026-11-15
        out[f"{v}{R}"] = dict(venue=v, R=R, n=len(uma), **{k: meta[(v, R)][k] for k in ("title", "start", "dist", "baba", "cond", "rid")}, horses=hs)
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{a.date}_web_probs.json"
    f.write_text(json.dumps(dict(made_at=datetime.datetime.now().isoformat(timespec="minutes"), model=mf.name, races=out), ensure_ascii=False, indent=1), encoding="utf-8")
    print("保存:", f)


if __name__ == "__main__":
    main()
