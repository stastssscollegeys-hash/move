# -*- coding: utf-8 -*-
"""
fetch_payouts.py — netkeiba から確定払戻データを取得する（2026-09-02 新規）
==========================================================================
背景
----
結果DB（race_results.json）には**単勝オッズしか無い**。そのため買い目の期待値は
Harville近似で推定するしかなく、「複勝・馬連・ワイド・3連複が実際いくら付いたか」を
検証できなかった。本スクリプトはその欠落を埋める。

取得元
------
  レースID一覧 : race.netkeiba.com/top/race_list_sub.html?kaisai_date=YYYYMMDD
                 （race_list.html はJS描画でIDが取れない。_sub の方を使うこと）
  払戻         : db.netkeiba.com/race/{race_id}/  の table.pay_table_01（2個）
                 ※ページはEUC-JP

race_id = YYYY CC KK DD RR （12桁）
          年 / 競馬場01-10 / 開催回 / 何日目 / レース番号

出力
----
  daily_pdca/db/payouts.json
    { race_id: {date, venue, R, payouts: {券種: [{combo, yen, pop}, ...]}} }

再開について
------------
1レース取得するたびにメモリに積み、**1日分終わるごとにファイルへ保存**する。
途中で落ちても、次回起動時に取得済みrace_idは自動スキップするので続きから再開できる。

使い方
------
  python fetch_payouts.py                  # 未取得の日を全部
  python fetch_payouts.py --dates 20260830 20260829
  python fetch_payouts.py --limit-days 5   # 未取得のうち先頭5日だけ（分割実行用）
"""
from __future__ import annotations
import argparse, json, re, sys, time, io
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
DB = BASE / 'daily_pdca' / 'db'
OUT = DB / 'payouts.json'

VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
         "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}

# netkeibaの表記 → 当システムの券種名
TICKET = {
    "単勝": "単勝", "複勝": "複勝", "枠連": "枠連", "馬連": "馬連",
    "ワイド": "ワイド", "馬単": "馬単",
    "三連複": "3連複", "3連複": "3連複",
    "三連単": "3連単", "3連単": "3連単",
}

SLEEP = 1.5          # netkeibaへの間隔
RETRY = 3


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://www.netkeiba.com/",
    })
    return s


def get(s: requests.Session, url: str, enc: str) -> str | None:
    for i in range(RETRY):
        try:
            time.sleep(SLEEP)
            r = s.get(url, timeout=25)
            if r.status_code != 200:
                continue
            r.encoding = enc
            return r.text
        except Exception:
            time.sleep(3)
    return None


def race_ids_for(s: requests.Session, date: str) -> list[str]:
    """その日のレースID一覧。中央開催のみ（venue 01-10）。"""
    html = get(s, f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date}", "utf-8")
    if not html:
        return []
    ids = set(re.findall(r"race_id=(\d{12})", html)) | set(re.findall(r"/race/(\d{12})", html))
    return sorted(i for i in ids if i[4:6] in VENUE)


def _cells(td) -> list[str]:
    """<br>区切りのセルを行ごとに分解する。"""
    return [x for x in td.get_text("\n", strip=True).split("\n") if x]


def parse_payouts(html: str) -> dict:
    """table.pay_table_01 から券種ごとの払戻を抜く。"""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, list[dict]] = {}
    for table in soup.select("table.pay_table_01"):
        for tr in table.select("tr"):
            th = tr.select_one("th")
            tds = tr.select("td")
            if not th or len(tds) < 2:
                continue
            name = TICKET.get(th.get_text(strip=True))
            if not name:
                continue
            combos = _cells(tds[0])
            yens = _cells(tds[1])
            pops = _cells(tds[2]) if len(tds) > 2 else []
            rows = []
            for i, c in enumerate(combos):
                if i >= len(yens):
                    break
                try:
                    yen = int(re.sub(r"[^\d]", "", yens[i]))
                except ValueError:
                    continue
                pop = None
                if i < len(pops):
                    try:
                        pop = int(re.sub(r"[^\d]", "", pops[i]))
                    except ValueError:
                        pop = None
                rows.append({"combo": c.replace("→", "-"), "yen": yen, "pop": pop})
            if rows:
                out[name] = rows
    return out


RESULT_CLASS = {"Tansho": ("単勝", 1), "Fukusho": ("複勝", 1), "Wakuren": ("枠連", 2), "Umaren": ("馬連", 2),
                "Wide": ("ワイド", 2), "Umatan": ("馬単", 2), "Fuku3": ("3連複", 3), "Tan3": ("3連単", 3)}


def parse_result_page(html: str) -> dict:
    """race.netkeiba.com の結果ページ（table.Payout_Detail_Table）から払戻を抜く。
    db.netkeiba.com はレース当日の夜まで払戻が空のことがある（9/12・9/19に発生）ためのフォールバック。"""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, list[dict]] = {}
    for tr in soup.select("table.Payout_Detail_Table tr"):
        cls = next((c for c in (tr.get("class") or []) if c in RESULT_CLASS), None)
        tds = tr.select("td")
        if not cls or len(tds) < 2:
            continue
        name, size = RESULT_CLASS[cls]
        nums = [x for x in tds[0].get_text("\n", strip=True).split("\n") if x.strip().isdigit()]
        yens = [int(re.sub(r"[^\d]", "", x)) for x in _cells(tds[1]) if re.sub(r"[^\d]", "", x)]
        pops = [int(re.sub(r"[^\d]", "", x)) for x in _cells(tds[2])] if len(tds) > 2 else []
        combos = ["-".join(nums[i:i + size]) for i in range(0, len(nums), size)]
        rows = [{"combo": c, "yen": y, "pop": pops[i] if i < len(pops) else None}
                for i, (c, y) in enumerate(zip(combos, yens))]
        if rows:
            out[name] = rows
    return out


def target_dates() -> list[str]:
    """結果DBに入っている日付＝払戻が必要な日付。"""
    db = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    return sorted({r['date'] for r in db})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', nargs='*', help='取得する日付（省略時は結果DBの全日付）')
    ap.add_argument('--limit-days', type=int, default=0, help='未取得のうち先頭N日だけ処理する')
    args = ap.parse_args()

    store: dict = {}
    if OUT.exists():
        store = json.loads(OUT.read_text(encoding='utf-8'))
        print(f"既存: {len(store)}レース分を読み込み")

    dates = args.dates or target_dates()
    done_by_date: dict[str, int] = {}
    for v in store.values():
        done_by_date[v['date']] = done_by_date.get(v['date'], 0) + 1

    # 未完了の日だけに絞る（1日=最大36レース。30以上取れていれば完了とみなす）
    todo = [d for d in dates if done_by_date.get(d, 0) < 30]
    if args.limit_days:
        todo = todo[:args.limit_days]

    print(f"対象日: {len(todo)}日 / 全{len(dates)}日（完了済み {len(dates)-len([d for d in dates if done_by_date.get(d,0) < 30])}日）")
    if not todo:
        print("すべて取得済みです")
        return

    s = session()
    for di, date in enumerate(todo, 1):
        ids = race_ids_for(s, date)
        if not ids:
            print(f"[{di}/{len(todo)}] {date} レースID取得失敗 — スキップ")
            continue
        new = 0
        fail = 0
        for rid in ids:
            if rid in store:
                continue
            html = get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
            pay = parse_payouts(html) if html else {}
            if not pay:
                html = get(s, f"https://race.netkeiba.com/race/result.html?race_id={rid}", "utf-8")
                pay = parse_result_page(html) if html else {}
            if not pay:
                fail += 1
                continue
            store[rid] = {
                "date": date,
                "venue": VENUE.get(rid[4:6], "?"),
                "R": int(rid[10:12]),
                "payouts": pay,
            }
            new += 1
        # 1日終わるごとに保存（中断しても失われない）
        OUT.write_text(json.dumps(store, ensure_ascii=False), encoding='utf-8')
        print(f"[{di}/{len(todo)}] {date} 取得{new}件 失敗{fail}件 累計{len(store)}件")

    print(f"\n完了: 累計 {len(store)} レース分 → {OUT}")


if __name__ == '__main__':
    main()
