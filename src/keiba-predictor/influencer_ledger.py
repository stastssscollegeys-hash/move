# -*- coding: utf-8 -*-
"""
influencer_ledger.py — YouTube予想チャンネル（インフルエンサー）のソース別的中記録台帳

背景:
  ensemble_v2.py のソース別重み（アジフライ777×1.5、競馬全レース予想TV・情報通のウマ談義・
  しろクロ競馬×1.2、SPAIA・義英真×0.8、他×1.0）は2026-08-18に「仮」で決められ、
  「4週トラッキングで確定」とされたが記録ファイルが存在しなかった。
  本スクリプトはその記録を作り、重みの妥当性を判断可能にする（重みそのものは変更しない）。

出力:
  C:\\Users\\User\\Desktop\\競馬予想レポート\\daily_pdca\\db\\influencer_ledger.json
  行 = {week, date, race, venue, source, horse, kind, finish, popularity, win_odds, data_origin}

使い方:
  python influencer_ledger.py --build
      過去に見つかった構造化データ（ensemble_*_v2.json）＋明示的に本命/穴/消しと
      記述されたdocx記述（手動記録・data_originで明示）から台帳を再構築する。

  python influencer_ledger.py --add-week <research_dir> --date YYYYMMDD
      research_dir 内の *_influencer.json（{"race":..., "signals":[{"source","horse","kind","confidence"}...]}）
      からシグナルを読み込み、race_results.json と照合して台帳に追記する。
      confidence == "ambiguous" のシグナルは除外する。

  python influencer_ledger.py --report
      ソース別集計（本命 勝率/複勝率/件数、穴 複勝率/件数、消し 3着内率/件数、
      追い切り1位 複勝率/件数）と、同じレース群の市場1〜3番人気複勝率を表示する。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

LEDGER_PATH = r"C:\Users\User\Desktop\競馬予想レポート\daily_pdca\db\influencer_ledger.json"
RESULTS_PATH = r"C:\Users\User\Desktop\競馬予想レポート\daily_pdca\db\race_results.json"

DETAIL_RE = re.compile(r'^(?P<source>.*?):(?P<kind>honmei|ana|posi|nega|oikiri1|premium)(?P<pts>[+-]\d+(?:\.\d+)?)$')

KIND_JP = {
    'honmei': '本命', 'ana': '穴', 'posi': 'ポジ', 'nega': '消し',
    'oikiri1': '追い切り1位', 'premium': 'プレミアム',
}

# ---------------------------------------------------------------------------
# 過去分（2026-08-13週〜2026-09-06週）の所在調査結果
#   構造化ファイル（ensemble_*_v2.json の detail 配列）が残っていたのはこの2レースのみ。
#   他週（0816のうち中京記念／0830／0905-06）は最終合算ランキングと更新理由の"要約プローズ"
#   のみが残っており、本命/穴/消しの語が明示された馬に限り MANUAL_SIGNALS で復元する。
#   それ以外（ソース名不明・「推奨」等の非定型表現）は推測せず取り込まない。
# ---------------------------------------------------------------------------
HISTORICAL_ENSEMBLE_FILES = [
    {
        "path": r"C:\Users\User\Desktop\競馬予想レポート\20260823\ensemble_keeneland_v2.json",
        "week": "2026-08-23", "date": "20260823", "race": "キーンランドC", "venue": "札幌",
        "data_origin": "ensemble_json:ensemble_keeneland_v2.json",
    },
    {
        "path": r"C:\Users\User\Desktop\競馬予想レポート\20260823\ensemble_niigata2_v2.json",
        "week": "2026-08-23", "date": "20260823", "race": "新潟2歳S", "venue": "新潟",
        "data_origin": "ensemble_json:ensemble_niigata2_v2.json",
    },
]

# 20260816週・札幌記念: 構造化jsonが残っていないため、
# 「20260816_最終予想_独自指数×インフルエンサー合算版.docx」本文中で
# ソース名＋本命/穴/消しの語が明示されている箇所のみ手動で復元（推測での補完はしない）。
# 中京記念は同docx内に「SPAIA支持」「〇〇推し」等の非定型表現しかなく、本命/穴/消しの
# 明示がないため一切採用していない（＝データなしとして扱う）。
MANUAL_SIGNALS = [
    {
        "week": "2026-08-16", "date": "20260816", "race": "札幌記念", "venue": "札幌",
        "source": "アジフライ777", "horse": "マジックサンズ", "kind": "honmei",
        "data_origin": "prose_manual_20260816_docx",
    },
    {
        "week": "2026-08-16", "date": "20260816", "race": "札幌記念", "venue": "札幌",
        "source": "ドンズバTV", "horse": "マジックサンズ", "kind": "ana",
        "data_origin": "prose_manual_20260816_docx",
    },
    {
        "week": "2026-08-16", "date": "20260816", "race": "札幌記念", "venue": "札幌",
        "source": "うまログ", "horse": "グランディア", "kind": "honmei",
        "data_origin": "prose_manual_20260816_docx",
    },
    {
        "week": "2026-08-16", "date": "20260816", "race": "札幌記念", "venue": "札幌",
        "source": "アジフライ777", "horse": "グランディア", "kind": "nega",
        "data_origin": "prose_manual_20260816_docx",
    },
    {
        "week": "2026-08-16", "date": "20260816", "race": "札幌記念", "venue": "札幌",
        "source": "うまログ", "horse": "ショウヘイ", "kind": "honmei",
        "data_origin": "prose_manual_20260816_docx",
    },
]

# 週ごとのデータ有無ログ（--build 実行時にそのままレポートへ転記する）
WEEK_DATA_STATUS = [
    ("2026-08-13週(8/15-16)", "札幌記念", "残っていた（手動復元・本命/穴/消し明記部分のみ。5件）"),
    ("2026-08-13週(8/15-16)", "中京記念", "残っていない（合算ランキングのみ。ソース別本命/穴/消しの明記なし）"),
    ("2026-08-22週(8/22-23)", "キーンランドC", "残っていた（ensemble_keeneland_v2.json フル構造化）"),
    ("2026-08-22週(8/22-23)", "新潟2歳S", "残っていた（ensemble_niigata2_v2.json フル構造化）"),
    ("2026-08-29週(8/29-30)", "新潟記念", "残っていない（SPAIA編集部3名の個別推奨はあるが本命/穴/消しの定型語なし）"),
    ("2026-08-29週(8/29-30)", "中京2歳S", "残っていない（枠データ分析のみ、インフルエンサー個別記述なし）"),
    ("2026-09-05週(9/5-6)", "紫苑S", "部分的に残っていた（内部参照表で馬別の重み付合算＋本命ソース数はあるが、ソース名の個別対応が失われている＝ソース別集計不可）"),
    ("2026-09-05週(9/5-6)", "セントウルS", "残っていない（外部データ収集がレース発走に間に合わず内部参照表自体が作成されていない）"),
    ("2026-09-05週(9/5-6)", "紫苑S以外の期待値レース(慶成杯・札幌2歳S等)", "残っていない（重賞4本SNS投稿案にソース別内訳なし）"),
]


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_results_index():
    data = load_json(RESULTS_PATH)
    idx = {}
    by_date_horse = defaultdict(list)
    for r in data:
        date = r.get('date')
        race = r.get('レース名')
        horse = r.get('馬名')
        if not (date and race and horse):
            continue
        rec = {
            'finish': r.get('着順int'),
            'popularity': r.get('人気'),
            'win_odds': r.get('単勝オッズ'),
            'venue': r.get('競馬場'),
        }
        idx[(date, race, horse)] = rec
        by_date_horse[(date, horse)].append((race, rec))
    return idx, by_date_horse


def lookup_result(idx, by_date_horse, date, race, horse):
    rec = idx.get((date, race, horse))
    if rec is not None:
        return rec
    cands = by_date_horse.get((date, horse), [])
    if len(cands) == 1:
        return cands[0][1]
    for r, rec2 in cands:
        if race in r or r in race:
            return rec2
    return None


def rows_from_ensemble_json(entry, idx, by_date_horse, unmatched):
    rows = []
    horses = load_json(entry['path'])
    for h in horses:
        horse_name = h.get('name')
        for detail in h.get('detail', []):
            m = DETAIL_RE.match(detail)
            if not m:
                continue
            source = m.group('source')
            kind = m.group('kind')
            rec = lookup_result(idx, by_date_horse, entry['date'], entry['race'], horse_name)
            if rec is None:
                unmatched.append((entry['race'], horse_name, source, kind))
                continue
            rows.append({
                'week': entry['week'], 'date': entry['date'], 'race': entry['race'], 'venue': entry['venue'],
                'source': source, 'horse': horse_name, 'kind': kind,
                'finish': rec['finish'], 'popularity': rec['popularity'], 'win_odds': rec['win_odds'],
                'data_origin': entry['data_origin'],
            })
    return rows


def rows_from_manual(idx, by_date_horse, unmatched):
    rows = []
    for sig in MANUAL_SIGNALS:
        rec = lookup_result(idx, by_date_horse, sig['date'], sig['race'], sig['horse'])
        if rec is None:
            unmatched.append((sig['race'], sig['horse'], sig['source'], sig['kind']))
            continue
        rows.append({
            'week': sig['week'], 'date': sig['date'], 'race': sig['race'], 'venue': sig['venue'],
            'source': sig['source'], 'horse': sig['horse'], 'kind': sig['kind'],
            'finish': rec['finish'], 'popularity': rec['popularity'], 'win_odds': rec['win_odds'],
            'data_origin': sig['data_origin'],
        })
    return rows


def cmd_build():
    idx, by_date_horse = load_results_index()
    unmatched = []
    all_rows = []
    for entry in HISTORICAL_ENSEMBLE_FILES:
        if not os.path.exists(entry['path']):
            print(f"[SKIP] not found: {entry['path']}")
            continue
        rows = rows_from_ensemble_json(entry, idx, by_date_horse, unmatched)
        print(f"[OK] {entry['race']} ({entry['date']}): {len(rows)} signal rows")
        all_rows.extend(rows)
    manual_rows = rows_from_manual(idx, by_date_horse, unmatched)
    print(f"[OK] 手動復元(0816 札幌記念): {len(manual_rows)} signal rows")
    all_rows.extend(manual_rows)

    if unmatched:
        print(f"[WARN] 馬名が一致せず除外: {len(unmatched)}件")
        for race, horse, source, kind in unmatched[:20]:
            print(f"    - {race} / {horse} / {source} / {kind}")

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=1)
    print(f"[DONE] {len(all_rows)} rows -> {LEDGER_PATH}")


def cmd_add_week(research_dir, date):
    idx, by_date_horse = load_results_index()
    if os.path.exists(LEDGER_PATH):
        all_rows = load_json(LEDGER_PATH)
    else:
        all_rows = []

    files = glob.glob(os.path.join(research_dir, '*_influencer.json'))
    if not files:
        print(f"[WARN] *_influencer.json が見つかりません: {research_dir}")
        return

    week = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    added = 0
    skipped_ambiguous = 0
    unmatched = []
    for fp in files:
        data = load_json(fp)
        race = data.get('race', os.path.basename(fp))
        signals = data.get('signals', [])
        for sig in signals:
            if sig.get('confidence') == 'ambiguous':
                skipped_ambiguous += 1
                continue
            source = sig.get('source')
            horse = sig.get('horse')
            kind = sig.get('kind')
            if kind not in KIND_JP:
                continue
            rec = lookup_result(idx, by_date_horse, date, race, horse)
            if rec is None:
                unmatched.append((race, horse, source, kind))
                continue
            all_rows.append({
                'week': week, 'date': date, 'race': race, 'venue': rec.get('venue'),
                'source': source, 'horse': horse, 'kind': kind,
                'finish': rec['finish'], 'popularity': rec['popularity'], 'win_odds': rec['win_odds'],
                'data_origin': f"add_week:{os.path.basename(fp)}",
            })
            added += 1
        print(f"[OK] {fp} ({race})")

    with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=1)
    print(f"[DONE] added {added} rows / skipped(ambiguous) {skipped_ambiguous} / unmatched {len(unmatched)}")
    for race, horse, source, kind in unmatched[:20]:
        print(f"    - unmatched: {race} / {horse} / {source} / {kind}")
    print(f"total rows now: {len(all_rows)} -> {LEDGER_PATH}")


def fukusho(finish):
    return finish is not None and finish <= 3


def cmd_report():
    if not os.path.exists(LEDGER_PATH):
        print("台帳がありません。先に --build を実行してください。")
        return
    rows = load_json(LEDGER_PATH)

    races = sorted(set((r['date'], r['race']) for r in rows))
    print(f"台帳: {len(rows)}行 / {len(races)}レース")
    for d, r in races:
        print(f"  - {d} {r}")

    print()
    print("=== 週ごとのデータ有無 ===")
    for week, race, status in WEEK_DATA_STATUS:
        print(f"  [{week}] {race}: {status}")

    by_source = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_source[r['source']][r['kind']].append(r)

    print()
    print("=== ソース別集計 ===")
    header = f"{'ソース':<20}{'本命件数':>8}{'本命勝率':>10}{'本命複勝率':>12}{'穴件数':>8}{'穴複勝率':>10}{'消し件数':>8}{'消し3着内率':>12}{'追切1位件数':>12}{'追切1位複勝率':>14}"
    print(header)
    for source in sorted(by_source.keys()):
        kinds = by_source[source]
        honmei = kinds.get('honmei', [])
        ana = kinds.get('ana', [])
        nega = kinds.get('nega', [])
        oik = kinds.get('oikiri1', [])

        def rate(lst, pred):
            if not lst:
                return None
            return sum(1 for x in lst if pred(x)) / len(lst) * 100

        h_win = rate(honmei, lambda x: x['finish'] == 1)
        h_fuku = rate(honmei, lambda x: fukusho(x['finish']))
        a_fuku = rate(ana, lambda x: fukusho(x['finish']))
        n_sanchaku = rate(nega, lambda x: fukusho(x['finish']))
        o_fuku = rate(oik, lambda x: fukusho(x['finish']))

        def fmt(v):
            return f"{v:.1f}%" if v is not None else "-"

        flag = " 【判定不能(本命<10件)】" if len(honmei) < 10 and honmei else ""
        print(f"{source:<20}{len(honmei):>8}{fmt(h_win):>10}{fmt(h_fuku):>12}{len(ana):>8}{fmt(a_fuku):>10}{len(nega):>8}{fmt(n_sanchaku):>12}{len(oik):>12}{fmt(o_fuku):>14}{flag}")

    # 市場1-3番人気 複勝率（台帳に含まれるレース群のみ）
    idx, by_date_horse = load_results_index()
    all_results = load_json(RESULTS_PATH)
    market_hits = 0
    market_total = 0
    for d, race in races:
        field = [r for r in all_results if r.get('date') == d and r.get('レース名') == race]
        for r in field:
            pop = r.get('人気')
            if pop is not None and pop <= 3:
                market_total += 1
                if r.get('着順int') is not None and r.get('着順int') <= 3:
                    market_hits += 1
    print()
    if market_total:
        print(f"=== 市場1〜3番人気 複勝率（台帳の{len(races)}レース内） ===")
        print(f"  {market_hits}/{market_total} = {market_hits/market_total*100:.1f}%")

    # 大穴1件除外チェック（ana / oikiri1 カテゴリで最高オッズの的中を除いても傾向が同じか）
    print()
    print("=== 最高配当1件を除いた場合の再確認 ===")
    for kind in ('ana', 'oikiri1'):
        flat = [r for r in rows if r['kind'] == kind and fukusho(r['finish'])]
        if not flat:
            continue
        top = max(flat, key=lambda x: (x['win_odds'] or 0))
        for source in sorted(by_source.keys()):
            lst = by_source[source].get(kind, [])
            if not lst:
                continue
            without = [x for x in lst if x is not top]
            if len(without) == len(lst):
                continue
            r1 = sum(1 for x in lst if fukusho(x['finish'])) / len(lst) * 100
            r2 = (sum(1 for x in without if fukusho(x['finish'])) / len(without) * 100) if without else None
            print(f"  {source} [{KIND_JP[kind]}]: 全体{r1:.1f}%({len(lst)}件) → 最高配当1件除外{('%.1f%%' % r2) if r2 is not None else '-'}({len(without)}件) [最高配当={top['horse']} {top['win_odds']}倍]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--add-week', metavar='RESEARCH_DIR')
    ap.add_argument('--date', metavar='YYYYMMDD')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    if args.build:
        cmd_build()
    elif args.add_week:
        if not args.date:
            print("--add-week には --date YYYYMMDD が必要です")
            sys.exit(1)
        cmd_add_week(args.add_week, args.date)
    elif args.report:
        cmd_report()
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
