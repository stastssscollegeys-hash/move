# -*- coding: utf-8 -*-
"""
odds_snapshot.py — レース前・全券種オッズのスナップショット保存（2026-09-11 新規）
==========================================================================
目的
----
回収率100%超えを狙う上で「券種間のオッズの矛盾」（例: 単勝オッズから逆算した組み合わせの
的中確率に対して、馬連・3連複の実際のオッズが割高になっている組み合わせ）を探したい。
しかし過去データ（fetch_payouts.py）には**当たった組み合わせの払戻しか残っておらず**、
外れた組み合わせのオッズが無いため検証できない。本スクリプトは発売中の全券種オッズを
時刻つきでそのまま保存し、今週から毎週貯めていくための取得ツール。

取得元（netkeiba 非公式API・実機で確認した仕様。2026-09-11 20時台にチャレンジC
202609040311 / セントライト記念 202606040411 / ローズS 202609040411 で確認）
--------------------------------------------------------------------------
  エンドポイント: https://race.netkeiba.com/api/api_get_jra_odds.html
                   ?race_id={race_id}&type={type}&action=init
  応答はJSON（charset=UTF-8）。共通構造:
    {"status": "...", "data": {"official_datetime": "...", "odds": {...}},
     "update_count": "...", "reason": "..."}

  type と data.odds のキーの対応（16頭立てチャレンジCで理論値と一致確認済み）:
    type=1 → odds["1"] = 単勝  {umaban(2桁文字列): [オッズ, "0", 人気]}           件数=頭数
             odds["2"] = 複勝  {umaban: [下限オッズ, 上限オッズ, 人気]}           件数=頭数
             （type=2 は複勝だけを返す。type=1に含まれるので使わない＝1回省略できる）
    type=3 → odds["3"] = 枠連  {"枠番枠番"(各2桁,昇順): [オッズ, "0", 人気]}      件数=w(w+1)/2
    type=4 → odds["4"] = 馬連  {"馬番馬番"(各2桁,昇順): [オッズ, "0", 人気]}      件数=nC2
    type=5 → odds["5"] = ワイド{"馬番馬番"(各2桁,昇順): [下限, 上限, 人気]}       件数=nC2
    type=6 → odds["6"] = 馬単  {"馬番馬番"(各2桁,着順)  : [オッズ, "0", 人気]}     件数=n(n-1)
    type=7 → odds["7"] = 3連複 {"馬番馬番馬番"(各2桁,昇順): [オッズ, "0", 人気]}   件数=nC3
    type=8 → odds["8"] = 3連単 {"馬番馬番馬番"(各2桁,着順)  : [オッズ, "0", 人気]} 件数=n(n-1)(n-2)

  status / reason はAPIが返す値を無加工でそのまま保存する。
  ★ユーザー指示では「status が 'yoso' の間は予想オッズ」とされていたが、2026-09-11(金)
    20時台の実測では3レースとも status="middle", reason="result odds empty" だった。
    'yoso' になるケースは未確認 — 推測で意味づけせず生値をそのまま記録する。

  馬番と馬名の対応: https://race.netkeiba.com/race/shutuba.html?race_id={race_id}
    table.Shutuba_Table の各 <tr class="HorseList"> について、**同じ行の中で**
      馬番 = td[class^="Umaban"] のテキスト
      馬名 = .HorseName a のテキスト
    をペアにする（全体セレクタを別々に取って出現順で対応させると、取消等で行数が
    ズレたときに壊れるため、必ず行単位=同じtr内で対応させること）。
    ついでに td[class^="Waku"] から枠番も拾い、枠連の理論件数チェックに使う。
    ページは utf-8（db.netkeiba.com とは違い euc-jp ではない。実測で確認済み）。

保存先
------
  {Desktop}/競馬予想レポート/daily_pdca/db/odds_snapshots/{YYYYMMDD}/{race_id}_{HHMM}.json
  （race_date はレース自体の開催日。shutuba.htmlのtitle "2026年9月12日" 等から取得する。
    --date 指定時はそれをフォールバックにするだけで、実際の開催日を優先する）

使い方
------
  python odds_snapshot.py --date 20260912
      その日の中央開催 全レースの全券種オッズを取得
  python odds_snapshot.py --race-ids 202609040311 202606040411 202609040411
      指定レースのみ取得（重賞3レースの確認等に）
  python odds_snapshot.py --summary
  python odds_snapshot.py --summary --date 20260912
      保存済みスナップショットの件数・時刻・status・頭数・理論件数チェックを一覧表示

禁止事項（厳守）
----------------
  - 取得に失敗した券種は空 {} で保存し、理由を odds_meta に記録してログに出す。
    他券種のオッズや前後の値から推測して埋めることはしない。処理も止めない。
  - 既存スクリプトは一切編集しない。fetch_payouts.py の race_ids_for()/VENUE を
    読み取り専用でimportして再利用する（開催日→レースID一覧の取得ロジックの重複を避ける）。
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from datetime import datetime
from math import comb
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_payouts import race_ids_for, VENUE  # noqa: E402  既存ロジックを読み取り専用で再利用

OUT_BASE = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'odds_snapshots'

SLEEP = 1.2   # netkeibaへの間隔（1リクエスト1秒以上あける指示に対し余裕を持たせる）
RETRY = 3

ODDS_API = "https://race.netkeiba.com/api/api_get_jra_odds.html"
SHUTUBA_URL = "https://race.netkeiba.com/race/shutuba.html"

# type番号 → [(data.oddsのキー, 保存する券種名), ...]
TICKET_DEFS: list[tuple[int, list[tuple[str, str]]]] = [
    (1, [("1", "単勝"), ("2", "複勝")]),
    (3, [("3", "枠連")]),
    (4, [("4", "馬連")]),
    (5, [("5", "ワイド")]),
    (6, [("6", "馬単")]),
    (7, [("7", "3連複")]),
    (8, [("8", "3連単")]),
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en;q=0.9",
        "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
        "Referer": "https://race.netkeiba.com/",
    })
    return s


def _get(s: requests.Session, url: str) -> requests.Response | None:
    for _ in range(RETRY):
        try:
            time.sleep(SLEEP)
            r = s.get(url, timeout=20)
            if r.status_code == 200:
                return r
        except Exception:
            time.sleep(2)
    return None


# ──────────────────────────────────────────────────────────────
# オッズAPI取得
# ──────────────────────────────────────────────────────────────

def fetch_odds_type(s: requests.Session, race_id: str, type_num: int) -> dict | None:
    url = f"{ODDS_API}?race_id={race_id}&type={type_num}&action=init"
    r = _get(s, url)
    if r is None:
        return None
    try:
        return r.json()
    except Exception:
        return None


def fetch_all_odds(s: requests.Session, race_id: str) -> tuple[dict, dict]:
    """全券種のオッズを取得する。失敗した券種は空{}で返し、理由はodds_metaに残す。"""
    odds_out: dict[str, dict] = {}
    meta_out: dict[str, dict] = {}
    for type_num, mapping in TICKET_DEFS:
        payload = fetch_odds_type(s, race_id, type_num)
        if payload is None:
            for _, name in mapping:
                odds_out[name] = {}
                meta_out[name] = {"ok": False, "error": f"type={type_num} HTTP取得失敗/タイムアウト", "count": 0}
                print(f"    [失敗] {name} (type={type_num}): HTTP取得失敗/タイムアウト")
            continue

        status = payload.get("status")
        reason = payload.get("reason")
        data = payload.get("data") or {}
        odds_all = data.get("odds") or {}
        official_dt = data.get("official_datetime")

        for key, name in mapping:
            sub = odds_all.get(key)
            if not sub:
                odds_out[name] = {}
                meta_out[name] = {
                    "ok": False, "status": status, "reason": reason,
                    "error": "data.odds に該当キーなし、または空", "count": 0,
                    "official_datetime": official_dt,
                }
                print(f"    [空] {name} (type={type_num}, key={key}): status={status} reason={reason}")
            else:
                odds_out[name] = sub
                meta_out[name] = {
                    "ok": True, "status": status, "reason": reason,
                    "count": len(sub), "official_datetime": official_dt,
                }
    return odds_out, meta_out


# ──────────────────────────────────────────────────────────────
# 馬番⇔馬名（出馬表）
# ──────────────────────────────────────────────────────────────

def fetch_horse_map(s: requests.Session, race_id: str) -> tuple[dict, dict, str | None]:
    """馬番⇔馬名・枠番と、タイトルから取れるレース開催日・タイトルを返す。

    Returns
    -------
    (horses, meta, error)
      horses: {umaban(2桁文字列): {"umaban": int, "waku": int|None, "horse_name": str}}
      meta:   {"race_date": "YYYYMMDD"|None, "title": str}
      error:  失敗理由の文字列。成功時はNone。
    """
    url = f"{SHUTUBA_URL}?race_id={race_id}"
    r = _get(s, url)
    if r is None:
        return {}, {"race_date": None, "title": ""}, "出馬表ページ取得失敗（HTTP/タイムアウト）"

    r.encoding = "utf-8"  # race.netkeiba.com は utf-8（db.netkeiba.comのeuc-jpとは異なる。実測確認済み）
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""
    date_m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title)
    race_date = f"{date_m.group(1)}{int(date_m.group(2)):02d}{int(date_m.group(3)):02d}" if date_m else None
    meta = {"race_date": race_date, "title": title}

    table = soup.select_one("table.Shutuba_Table")
    if not table:
        return {}, meta, "table.Shutuba_Table が見つからない"

    horses: dict[str, dict] = {}
    for row in table.select("tr.HorseList"):
        uma_td = row.select_one('td[class^="Umaban"]')
        waku_td = row.select_one('td[class^="Waku"]')
        name_a = row.select_one(".HorseName a")
        if uma_td is None or name_a is None:
            continue
        try:
            umaban = int(uma_td.get_text(strip=True))
        except ValueError:
            continue
        waku = None
        if waku_td is not None:
            try:
                waku = int(waku_td.get_text(strip=True))
            except ValueError:
                waku = None
        horses[f"{umaban:02d}"] = {
            "umaban": umaban,
            "waku": waku,
            "horse_name": name_a.get_text(strip=True),
        }

    if not horses:
        return {}, meta, "出馬表テーブルの解析失敗（0頭）"
    return horses, meta, None


# ──────────────────────────────────────────────────────────────
# 理論件数チェック（16頭立て等で正しく全通り取れているかの自己診断）
# ──────────────────────────────────────────────────────────────

def theoretical_counts(horses: dict) -> dict[str, int | None]:
    n = len(horses)
    if n == 0:
        return {}
    wakus = sorted({h["waku"] for h in horses.values() if h.get("waku")})
    w = len(wakus)
    return {
        "単勝": n,
        "複勝": n,
        "枠連": (w * (w + 1) // 2) if w else None,
        "馬連": comb(n, 2),
        "ワイド": comb(n, 2),
        "馬単": n * (n - 1),
        "3連複": comb(n, 3),
        "3連単": n * (n - 1) * (n - 2),
    }


# ──────────────────────────────────────────────────────────────
# スナップショット組み立て・保存
# ──────────────────────────────────────────────────────────────

def build_snapshot(race_id: str, horses: dict, shutuba_meta: dict, shutuba_error: str | None,
                    odds_out: dict, odds_meta: dict, fallback_date: str | None) -> dict:
    now = datetime.now()
    counts = {name: len(v) for name, v in odds_out.items()}
    expected = theoretical_counts(horses)
    count_check = {}
    for name, actual in counts.items():
        exp = expected.get(name)
        count_check[name] = {"actual": actual, "expected": exp, "match": (exp is not None and actual == exp)}

    race_date = shutuba_meta.get("race_date") or fallback_date
    venue_cd = race_id[4:6] if len(race_id) >= 6 else "?"

    return {
        "race_id": race_id,
        "race_date": race_date,
        "venue": VENUE.get(venue_cd, "?"),
        "R": int(race_id[10:12]) if len(race_id) >= 12 else None,
        "title": shutuba_meta.get("title"),
        "fetched_at": now.isoformat(timespec="seconds"),
        "fetched_hhmm": now.strftime("%H%M"),
        "horses": horses,
        "horse_count": len(horses),
        "shutuba_error": shutuba_error,
        "odds": odds_out,
        "odds_meta": odds_meta,
        "counts": counts,
        "expected_counts": expected,
        "count_check": count_check,
    }


def save_snapshot(snap: dict) -> Path:
    date8 = snap.get("race_date") or "unknown_date"
    out_dir = OUT_BASE / date8
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{snap['race_id']}_{snap['fetched_hhmm']}.json"
    path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    return path


def fetch_one_race(s: requests.Session, race_id: str, fallback_date: str | None = None) -> dict:
    print(f"  [出馬表] {race_id} 取得中...")
    horses, shutuba_meta, shutuba_error = fetch_horse_map(s, race_id)
    if shutuba_error:
        print(f"    [出馬表エラー] {shutuba_error}")

    print(f"  [オッズ] {race_id} 全券種取得中...")
    odds_out, odds_meta = fetch_all_odds(s, race_id)

    return build_snapshot(race_id, horses, shutuba_meta, shutuba_error, odds_out, odds_meta, fallback_date)


# ──────────────────────────────────────────────────────────────
# --summary
# ──────────────────────────────────────────────────────────────

def print_summary(date_filter: str | None) -> None:
    if not OUT_BASE.exists():
        print(f"スナップショットはまだありません（{OUT_BASE}）")
        return

    date_dirs = sorted(d for d in OUT_BASE.iterdir() if d.is_dir())
    if date_filter:
        date_dirs = [d for d in date_dirs if d.name == date_filter]
    if not date_dirs:
        print("該当するスナップショットがありません")
        return

    total = 0
    for d in date_dirs:
        files = sorted(d.glob("*.json"))
        print(f"\n=== {d.name} ({len(files)}件) ===")
        for f in files:
            try:
                snap = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  {f.name}: 読み込み失敗 ({e})")
                continue
            statuses = sorted({m.get("status") for m in snap.get("odds_meta", {}).values() if m.get("status")})
            ng = [name for name, c in snap.get("count_check", {}).items()
                  if c.get("expected") is not None and not c.get("match")]
            zero = [name for name, c in snap.get("counts", {}).items() if c == 0]
            print(f"  {f.name}  {snap.get('venue')}{snap.get('R')}R {snap.get('title', '')}"
                  f"  取得={snap.get('fetched_at')}  status={'/'.join(statuses) or '?'}"
                  f"  頭数={snap.get('horse_count')}"
                  f"  件数不一致={ng or 'なし'}  空券種={zero or 'なし'}")
            total += 1
    print(f"\n合計 {total} 件")


# ──────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="レース前の全券種オッズを時刻つきで保存する")
    ap.add_argument("--date", help="取得する開催日 YYYYMMDD（中央の全レースを対象）")
    ap.add_argument("--race-ids", nargs="*", help="取得するrace_idを直接指定（複数可）")
    ap.add_argument("--summary", action="store_true", help="保存済みスナップショットを一覧表示")
    args = ap.parse_args()

    if args.summary:
        print_summary(args.date)
        return

    if args.race_ids:
        race_ids = args.race_ids
        fallback_date = args.date
    elif args.date:
        s0 = session()
        race_ids = race_ids_for(s0, args.date)
        fallback_date = args.date
        if not race_ids:
            print(f"{args.date}: レースID取得失敗（開催がない、または取得エラー）")
            return
        print(f"{args.date}: {len(race_ids)}レース対象")
    else:
        print("--date か --race-ids のいずれかを指定してください（一覧表示は --summary）")
        return

    s = session()
    ok = 0
    for i, rid in enumerate(race_ids, 1):
        print(f"[{i}/{len(race_ids)}] {rid}")
        try:
            snap = fetch_one_race(s, rid, fallback_date)
        except Exception as e:
            print(f"  [レース全体失敗] {rid}: {e} — スキップして続行")
            continue
        path = save_snapshot(snap)
        ng = [name for name, c in snap["count_check"].items()
              if c.get("expected") is not None and not c.get("match")]
        print(f"  → 保存: {path}")
        print(f"     頭数={snap['horse_count']}  券数={snap['counts']}  件数不一致={ng or 'なし'}")
        ok += 1

    print(f"\n完了: {ok}/{len(race_ids)} レース保存 → {OUT_BASE}")


if __name__ == "__main__":
    main()
