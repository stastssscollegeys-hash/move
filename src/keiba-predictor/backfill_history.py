# -*- coding: utf-8 -*-
"""
backfill_history.py — 過去のレース結果を遡って蓄積DBに追加する
==========================================================================
なぜ必要か
----------
2026-09-08の185帯スキャンで有望な2帯が出たが、**見つけたデータそのもので
測った数字なので証拠にならない**。本来はこれから貯める forward データで
検証するしかなく、馬連4-6人気で約5ヶ月かかる計算だった。

しかし蓄積DBは 2026-05-16 以降しか無い。**それ以前を取りに行けば、
発見に一切使っていない検証データが今すぐ手に入る。**
（時間的には過去だが、帯の定義は人気順位だけで決まる機械的なルールなので、
  「発見に使っていない」という意味で正当な hold-out になる）

取得元は fetch_payouts.py と同じ netkeiba のレース結果ページ。
このスクリプトは **結果（馬番・人気・着順・単勝オッズ）** を埋める。
払戻はこの後 `python fetch_payouts.py --dates ...` で埋める。

使い方
------
    python backfill_history.py --from 20260101 --to 20260510          # 確認のみ
    python backfill_history.py --from 20260101 --to 20260510 --write  # 実際に追加
"""
from __future__ import annotations
import argparse, json, re, sys, io, shutil
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from fetch_payouts import session, get, race_ids_for, VENUE

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
RESULTS = DB / "race_results.json"


def weekend_dates(a: str, b: str) -> list[str]:
    """土日のみ（中央競馬の開催日）"""
    d0 = date(int(a[:4]), int(a[4:6]), int(a[6:]))
    d1 = date(int(b[:4]), int(b[4:6]), int(b[6:]))
    out, d = [], d0
    while d <= d1:
        if d.weekday() >= 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def style_of(passing: str) -> str:
    """通過順から脚質を決める（race_history.py と同じ基準に揃える）"""
    nums = [int(x) for x in re.findall(r"\d+", passing or "")]
    if not nums:
        return "?"
    first, last = nums[0], nums[-1]
    if first <= 2:
        return "逃げ"
    if first <= 4:
        return "先行"
    return "差し" if last <= 8 else "追込"


def parse_result(html: str, race_id: str, date_s: str) -> list[dict]:
    """レース結果ページから1頭ずつの 馬番・人気・着順・単勝オッズ を取り出す"""
    soup = BeautifulSoup(html, "html.parser")
    tbl = soup.select_one("table.race_table_01, table#All_Result_Table, table.RaceTable01")
    if not tbl:
        return []

    # ヘッダから列位置を決める（netkeibaは表構造が版によって違う）
    heads = [th.get_text(strip=True) for th in tbl.select("tr")[0].select("th,td")]
    def col(*names):
        for i, h in enumerate(heads):
            if any(n in h for n in names):
                return i
        return None
    i_rank, i_num = col("着順"), col("馬番")
    i_name, i_odds = col("馬名"), col("単勝", "オッズ")
    i_pop = col("人気")
    # 2026-09-09追加: 距離・枠・通過順が抜けていたため、取得しても
    # **コース傾向・脚質傾向の分析にまったく使えなかった**（4月分309頭が距離None）。
    i_waku, i_pass = col("枠番"), col("通過")
    if i_rank is None or i_num is None or i_pop is None:
        return []

    venue = VENUE.get(race_id[4:6], "")
    rno = int(race_id[10:12])

    # レース条件（芝ダ・距離）はページ見出しから取る。結果表には無い。
    course = ""
    head = soup.select_one("diary_snap_cut span, .data_intro span, dl.racedata span")
    if head:
        m = re.search(r"(芝|ダ)\D*?(\d{3,4})", head.get_text(" ", strip=True))
        if m:
            course = f"{'ダート' if m.group(1) == 'ダ' else '芝'}{m.group(2)}m"

    out = []
    for tr in tbl.select("tr")[1:]:
        td = tr.select("td")
        if len(td) <= max(x for x in (i_rank, i_num, i_pop) if x is not None):
            continue
        def cell(i):
            return td[i].get_text(strip=True) if i is not None and i < len(td) else ""
        try:
            rank = cell(i_rank)
            if not rank.isdigit():      # 中止・除外
                continue
            passing = cell(i_pass)
            row = {
                "date": date_s, "競馬場": venue, "R": rno,
                "馬番": int(cell(i_num)), "着順": rank,
                "人気": float(cell(i_pop)),
                "単勝オッズ": float(cell(i_odds) or 0),
                "馬名": cell(i_name),
                "距離": course,
                "枠": int(cell(i_waku)) if cell(i_waku).isdigit() else None,
                "コーナー通過": passing,
                "脚質": style_of(passing),
            }
        except ValueError:
            continue
        if row["単勝オッズ"] <= 0:
            continue
        out.append(row)
    return out


def main(a: str, b: str, write: bool) -> None:
    """
    ⚠ 2026-09-09改修: **1日ごとに逐次保存する**。
      以前は全日ぶんをメモリに溜めて最後に一括保存していたため、
      OSにメモリ不足でプロセスを落とされた際に37日ぶんの取得が丸ごと消えた。
      逐次保存なら、途中で落ちても再実行すれば続きから再開できる
      （取得済みの日は have_dates で自動スキップされる）。
    """
    rows = json.load(open(RESULTS, encoding="utf-8"))
    have_dates = {str(r.get("date")) for r in rows}
    print(f"蓄積DB: {len(rows):,}頭 / {len(have_dates)}日\n")

    dates = [d for d in weekend_dates(a, b) if d not in have_dates]
    print(f"対象（土日・未取得）: {len(dates)}日  {dates[:3]}…{dates[-3:] if dates else ''}\n")
    if not dates:
        print("追加すべき日がありません。")
        return
    if not write:
        print("※ ドライラン。実際に追加するには --write")
        return

    bak = RESULTS.with_suffix(".json.bak_before_history")
    if not bak.exists():
        shutil.copy2(RESULTS, bak)
        print(f"バックアップ: {bak.name}\n")

    del rows            # 保持し続けない（メモリを空ける）

    s = session()
    total, done = 0, []
    for i, d in enumerate(dates, 1):
        ids = race_ids_for(s, d)
        if not ids:
            print(f"[{i}/{len(dates)}] {d} 開催なし", flush=True)
            continue
        day: list[dict] = []
        for rid in ids:
            html = get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
            if not html:
                continue
            day += parse_result(html, rid, d)
        if not day:
            print(f"[{i}/{len(dates)}] {d} 取得0", flush=True)
            continue

        # その日のぶんだけを読み書きして即座に保存する
        cur = json.load(open(RESULTS, encoding="utf-8"))
        cur.extend(day)
        tmp = RESULTS.with_suffix(".json.tmp")
        json.dump(cur, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        tmp.replace(RESULTS)            # 書き込み途中で落ちてもDBが壊れない
        total += len(day)
        done.append(d)
        n = len(cur)
        del cur
        print(f"[{i}/{len(dates)}] {d} {len(day)}頭 保存 / DB {n:,}頭", flush=True)

    print(f"\n═══ 結果 ═══")
    print(f"  追加: {total:,}頭 / {len(done)}日")
    if done:
        print(f"\n次にこれを実行して払戻を埋めてください:")
        print(f"  python fetch_payouts.py --dates {' '.join(done)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", required=True)
    ap.add_argument("--to", dest="b", required=True)
    ap.add_argument("--write", action="store_true")
    x = ap.parse_args()
    main(x.a, x.b, x.write)
