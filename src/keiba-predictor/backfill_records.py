# -*- coding: utf-8 -*-
"""
backfill_records.py — 過去開催の事前予測データ(records.json)を遡って生成する
============================================================================
2026-08-31 作成。エッジ検証のサンプルを増やすため。
  現状: 8月の10開催・4,750頭しか事前予測データがない（季節・開催場が偏る）
  目標: 5〜7月の19開催を追加し、約14,000頭で再検証する

各日の処理:
  1) scripts/predict_and_report.py --netkeiba … netkeibaから出馬表をスクレイプ（約16分/日）
  2) collect_weekend_bigdata.py               … 事前予測 records.json を生成（数秒）
  3) 30秒スリープ                              … netkeibaへの負荷を抑える（BAN防止）

※ PowerShellスクリプト版は文字コードの問題（PS5.1がBOMなしUTF-8を誤読）で
   動かなかったため、Python版に統一した。

使い方: python backfill_records.py [--days 20260516 20260517 ...]
ログ:   Desktop/競馬予想レポート/backfill_log.txt
"""
from __future__ import annotations
import subprocess, sys, time, argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESK = Path.home() / 'Desktop' / '競馬予想レポート'
LOG = DESK / 'backfill_log.txt'

DEFAULT_DAYS = [
    '20260516', '20260517', '20260523', '20260524', '20260530', '20260531',
    '20260607', '20260613', '20260614', '20260621', '20260627', '20260628',
    '20260704', '20260705', '20260711', '20260712', '20260718', '20260719',
    '20260725',
]


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime('%H:%M:%S'), msg)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + "\n")


def records_path(day):
    return DESK / day / ("週末ビッグデータ_%s-%s_records.json" % (day, day[4:]))


def run(cmd, cwd):
    try:
        subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=3600)
        return True
    except Exception as e:
        log("  コマンド失敗: %s" % e)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', nargs='+', default=DEFAULT_DAYS)
    ap.add_argument('--sleep', type=int, default=30)
    args = ap.parse_args()

    log("=== backfill 開始 対象%d日 ===" % len(args.days))
    t0 = time.time()
    done, fail = 0, []

    for day in args.days:
        out = records_path(day)
        if out.exists():
            log("%s : 既に存在するためスキップ" % day)
            done += 1
            continue

        t1 = time.time()
        log("%s : 出馬表スクレイプ開始" % day)
        run([sys.executable, 'predict_and_report.py', '--date', day, '--netkeiba'], ROOT / 'scripts')
        run([sys.executable, 'collect_weekend_bigdata.py', '--dates', day], ROOT)

        el = (time.time() - t1) / 60
        if out.exists():
            log("%s : 完了 (%dKB / %.1f分)" % (day, out.stat().st_size // 1024, el))
            done += 1
        else:
            log("%s : ★失敗 records.json が生成されませんでした (%.1f分)" % (day, el))
            fail.append(day)
        time.sleep(args.sleep)

    log("=== backfill 終了 成功%d/%d 総所要%.1f分 ===" % (done, len(args.days), (time.time()-t0)/60))
    if fail:
        log("失敗した日: " + " ".join(fail))


if __name__ == '__main__':
    main()
