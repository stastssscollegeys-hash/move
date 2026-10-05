# -*- coding: utf-8 -*-
"""
history_backfill.py — 過去のレース結果を netkeiba の無料公開ページから集める（2026-10-02新規）
==========================================================================================
目的: 回収率エンジン（ev_engine.py）の学習用に、過去数年分の「結果＋確定オッズ＋払戻」を貯める。
      蓄積DB（race_results.json）は2026年1月〜の2,448レースしかなく、市場に勝つモデルを作るにも
      優位を確かめるにも足りない（docs/keiba_jravan_setup.md）。

取得元（すべて無料で見られるページ。有料会員向けの列＝タイム指数・調教・厩舎コメントは空のまま）
  開催日     race.netkeiba.com/top/calendar.html?year=Y&month=M
  レースID   race.netkeiba.com/top/race_list_sub.html?kaisai_date=YYYYMMDD
  結果・払戻 db.netkeiba.com/race/{race_id}/ （EUC-JP）
1ページごとに間隔を空ける（fetch_payouts と同じ1.5秒＋取得時間）。1年分は約3,450レース・3時間前後。

保存先（年ごと・1日終わるたびに保存。途中で止めても続きから再開できる）
  daily_pdca/db/history/results_YYYY.json   [ {date, 競馬場, R, race_id, レース名, 距離, 馬場状態, 天候, 枠, 馬番, 馬名, horse_id,
                                               性齢, 斤量_kg, 騎手, タイム, 着差, コーナー通過, 後3F, 後3F順位, 単勝オッズ, 人気,
                                               馬体重, 厩舎, 着順, 着順int, 脚質, 中日数}, ... ]
  daily_pdca/db/history/payouts_YYYY.json   { race_id: {date, venue, R, payouts} }
  ※ 蓄積DB（race_results.json）とは別ファイル。旧エンジンや既存の台帳には影響しない。
  ※ 脚質はそのレースの通過順から付けた「結果」。予測に使うときは必ず過去走の分だけを使う（ev_engine はそうしている）。

使い方
  python history_backfill.py --years 2026 2025 2024 2023 2022 2021     # 指定した年を新しい順に
  python history_backfill.py --years 2025 --limit-days 2               # 試し取り
  python history_backfill.py --status                                   # どこまで貯まったか
"""
from __future__ import annotations
import argparse, datetime, json, re, sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

from bs4 import BeautifulSoup
import fetch_payouts as fp

OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history"
VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
         "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}


def style_of(early_rank, n):
    """daily_pdca/scorer.classify_kyakushitsu と同じ基準"""
    if not early_rank or n <= 0:
        return ""
    if early_rank <= 2:
        return "逃げ"
    if early_rank <= max(2.0, n * 0.35):
        return "先行"
    if early_rank <= n * 0.65:
        return "差し"
    return "追込"


def race_days(s, year: int) -> list[str]:
    days = set()
    for m in range(1, 13):
        html = fp.get(s, f"https://race.netkeiba.com/top/calendar.html?year={year}&month={m}", "utf-8")
        days |= {d for d in re.findall(r"kaisai_date=(\d{8})", html or "") if d.startswith(str(year))}
    today = datetime.date.today().strftime("%Y%m%d")
    return sorted(d for d in days if d < today)


def parse_race(html: str, rid: str, date: str) -> list[dict]:
    sp = BeautifulSoup(html, "html.parser")
    tb = sp.select_one("table.race_table_01")
    if not tb:
        return []
    head = [th.get_text(strip=True) for th in tb.select("tr")[0].select("th")]

    def col(name):
        return next((i for i, h in enumerate(head) if h.startswith(name)), None)
    ix = {k: col(k) for k in ("着順", "枠番", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "通過", "上り", "単勝", "人気", "馬体重", "調教師")}
    info = sp.select_one("diary_snap_cut span")
    info = re.sub(r"\s+", " ", info.get_text(" ", strip=True)) if info else ""
    m = re.search(r"(芝|ダ|障)[^0-9]*?(\d{3,4})m", info)
    dist = f"{m.group(1)}{m.group(2)}m" if m else ""
    w = re.search(r"天候\s*:\s*(\S+)", info)
    b = re.search(r"(?:芝|ダート)\s*:\s*(\S+)", info)
    h1 = sp.select_one("dl.racedata h1")
    cond = sp.select_one("p.smalltxt")                       # 例「2022年10月09日 4回東京2日目 3歳以上オープン (国際)(指)(別定)」
    cond = re.sub(r"\s+", " ", cond.get_text(" ", strip=True)) if cond else ""
    rows = []
    for tr in tb.select("tr")[1:]:
        td = [x.get_text(strip=True) for x in tr.select("td")]
        if len(td) < len(head):
            continue

        def g(k):
            return td[ix[k]] if ix[k] is not None else ""
        a = tr.select_one('a[href*="/horse/"]')
        hid = re.search(r"/horse/(\w+)", a.get("href")).group(1) if a else ""
        fin = g("着順")
        try:
            odds = float(g("単勝"))
        except ValueError:
            odds = None
        rows.append({
            "date": date, "競馬場": VENUE.get(rid[4:6], "?"), "R": int(rid[10:12]), "race_id": rid,
            "レース名": h1.get_text(strip=True) if h1 else "", "距離": dist,
            "馬場状態": b.group(1) if b else "", "天候": w.group(1) if w else "",
            "条件": cond, "コース情報": info,
            "枠": int(g("枠番")) if g("枠番").isdigit() else None, "馬番": int(g("馬番")) if g("馬番").isdigit() else None,
            "馬名": g("馬名"), "horse_id": hid, "性齢": g("性齢"),
            "斤量_kg": float(g("斤量")) if re.fullmatch(r"[\d.]+", g("斤量")) else None,
            "騎手": g("騎手"), "タイム": g("タイム"), "着差": g("着差"), "コーナー通過": g("通過"),
            "後3F": float(g("上り")) if re.fullmatch(r"[\d.]+", g("上り")) else None,
            "単勝オッズ": odds, "人気": int(g("人気")) if g("人気").isdigit() else None,
            "馬体重": g("馬体重"), "厩舎": re.sub(r"^\[.\]", "", g("調教師")),
            "着順": fin, "着順int": int(fin) if fin.isdigit() else None,
        })
    n = len(rows)
    l3 = sorted(r["後3F"] for r in rows if r["後3F"])
    for r in rows:
        r["後3F順位"] = l3.index(r["後3F"]) + 1 if r["後3F"] else None
        c = [int(x) for x in re.findall(r"\d+", r["コーナー通過"])]
        r["脚質"] = style_of(c[0], n) if c else ""
    return rows


def load(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def add_gaps(rows: list[dict]) -> None:
    """中日数（前走からの日数）を horse_id ごとに付ける。年をまたぐ分は status/ev_engine 側で全年を並べて付け直す"""
    last = {}
    for r in sorted(rows, key=lambda r: (r["date"], r["R"])):
        k = r.get("horse_id") or r["馬名"]
        d = datetime.date(int(r["date"][:4]), int(r["date"][4:6]), int(r["date"][6:]))
        r["中日数"] = (d - last[k]).days if k in last else None
        last[k] = d


def run(years, limit_days):
    OUT.mkdir(parents=True, exist_ok=True)
    s = fp.session()
    for y in years:
        rp, pp = OUT / f"results_{y}.json", OUT / f"payouts_{y}.json"
        rows, pays = load(rp, []), load(pp, {})
        done_days = {r["date"] for r in rows}
        days = [d for d in race_days(s, y) if d not in done_days]
        if limit_days:
            days = days[-limit_days:]
        print(f"■ {y}年: 取得済み {len(done_days)}日 / これから {len(days)}日")
        for d in reversed(days):                      # 新しい日から
            ids = fp.race_ids_for(s, d)
            day_rows, day_pays, ng = [], {}, 0
            for rid in ids:
                html = fp.get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
                rr = parse_race(html, rid, d) if html else []
                if not rr:
                    ng += 1
                    continue
                day_rows += rr
                day_pays[rid] = {"date": d, "venue": VENUE.get(rid[4:6], "?"), "R": int(rid[10:12]),
                                 "payouts": fp.parse_payouts(html)}
            if not day_rows:
                print(f"  {d}: 取得0（{len(ids)}レース中 失敗{ng}）— スキップ")
                continue
            rows += day_rows
            pays.update(day_pays)
            add_gaps(rows)
            rp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            pp.write_text(json.dumps(pays, ensure_ascii=False), encoding="utf-8")
            print(f"  {d}: {len(ids) - ng}レース {len(day_rows)}頭 保存（失敗{ng}）／{y}年累計 {len({r['race_id'] for r in rows}):,}レース "
                  f"[{datetime.datetime.now():%m/%d %H:%M}]")
    print("完了")


def fill_cond():
    """「条件」（クラス）を保存していなかった初期取得分に、後から足す。1レース1ページ"""
    s = fp.session()
    for p in sorted(OUT.glob("results_*.json"), reverse=True):
        rows = json.loads(p.read_text(encoding="utf-8"))
        need = sorted({r["race_id"] for r in rows if "条件" not in r})
        print(f"■ {p.stem[-4:]}年: 条件の無いレース {len(need):,}")
        by = {}
        for r in rows:
            by.setdefault(r["race_id"], []).append(r)
        for i, rid in enumerate(need, 1):
            html = fp.get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
            if not html:
                continue
            sp = BeautifulSoup(html, "html.parser")
            c, info = sp.select_one("p.smalltxt"), sp.select_one("diary_snap_cut span")
            c = re.sub(r"\s+", " ", c.get_text(" ", strip=True)) if c else ""
            info = re.sub(r"\s+", " ", info.get_text(" ", strip=True)) if info else ""
            for r in by[rid]:
                r["条件"], r["コース情報"] = c, info
            if i % 100 == 0 or i == len(need):
                p.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
                print(f"  {i:,}/{len(need):,} [{datetime.datetime.now():%m/%d %H:%M}]")
    print("完了")


def status():
    tot = 0
    for p in sorted(OUT.glob("results_*.json")):
        rows = json.loads(p.read_text(encoding="utf-8"))
        n = len({r["race_id"] for r in rows})
        ds = sorted({r["date"] for r in rows})
        tot += n
        print(f"  {p.stem[-4:]}年: {len(ds):>3}日 {n:>5,}レース {len(rows):>6,}頭  {ds[0]}〜{ds[-1]}")
    print(f"  合計 {tot:,}レース")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int)
    ap.add_argument("--limit-days", type=int)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--fill-cond", action="store_true", help="条件（クラス）が無い取得済みレースに後から足す")
    a = ap.parse_args()
    if a.fill_cond:
        fill_cond()
    elif a.status or not a.years:
        status()
    else:
        run(a.years, a.limit_days)
