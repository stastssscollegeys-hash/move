# -*- coding: utf-8 -*-
"""
weekly_forward_test.py — 週次フォワードテスト（2026-09-02 新規）
================================================================
毎週末のレース終了後に1回叩くだけで、以下を自動で行う。

  ① その日の確定払戻を取得（fetch_payouts.py）
  ② その日の records の素性を検証（レース前に作られたものか＝リークが無いか）
  ③ その日単独と累積の両方でエンジンの実測ROIを算出
  ④ 台帳 daily_pdca/db/forward_test.json に追記
  ⑤ サンプルが増えて信頼区間がどこまで狭まったかを表示

なぜ必要か
----------
2026-09-02時点の判定材料は346レースしかなく、95%信頼区間が±37pt。
エンジンの実測ROI 69.4% が「無スキル基準線と同等」なのか「本当は勝てる/勝てない」
のかを区別できない。**サンプルを積むことでしか解決しない。**

2026-08-31のバックフィルで作った records には結果リークがあり、混ぜるとROIが
54pt過大に出た。②の素性検証を必ず通し、レース後に作った records は弾く。

使い方
------
  python weekly_forward_test.py --date 20260906
  python weekly_forward_test.py --date 20260905 20260906
  python weekly_forward_test.py --report-only      # 取得せず現状の集計だけ
"""
from __future__ import annotations
import argparse, json, subprocess, sys, io, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'
LEDGER = DB / 'forward_test.json'


def fetch(dates: list[str]) -> None:
    print("■ 確定払戻を取得")
    r = subprocess.run([sys.executable, str(HERE / 'fetch_payouts.py'), '--dates', *dates],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    print((r.stdout or '').rstrip())
    if r.returncode != 0:
        print("⚠ 取得に失敗:", (r.stderr or '')[-400:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', nargs='+', help='対象日 YYYYMMDD（複数可）')
    ap.add_argument('--report-only', action='store_true')
    ap.add_argument('--budget', type=int, default=10000)
    ap.add_argument('--boot', type=int, default=2000)
    args = ap.parse_args()

    if args.date and not args.report_only:
        fetch(args.date)
        # 蓄積DBの「枠」を馬番と頭数から復元する（2026-09-04追加）。
        # accumulate_db が枠を書いておらず14,036行すべてNoneだったため、
        # 枠順バイアスの検証が一切できていなかった。冪等なので毎回通してよい。
        print()
        print("■ 蓄積DBの枠を復元")
        r = subprocess.run([sys.executable, str(HERE / 'fix_waku.py')],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        for ln in (r.stdout or '').splitlines():
            if '復元' in ln or '保存' in ln or '枠あり' in ln:
                print("  " + ln.strip())

    races_all = B.load_races()

    # ── 素性チェック（新しい日にリークが混ざっていないか）──
    if args.date:
        print()
        print("■ records の素性チェック")
        for d in args.date:
            keys = [k for k in races_all if k[0] == d]
            if not keys:
                print(f"   {d}: records が見つからない（予想を保存していない日？）")
                continue
            pv = B.PROVENANCE.get(keys[0], {})
            mark = "🚨 レース後に作成＝リーク。集計から除外される" if pv.get('backfilled') \
                   else "✅ レース前に作成＝事前予測として有効"
            print(f"   {d}: {len(keys)}R  {pv.get('file','?')[:40]} "
                  f"(更新 {pv.get('mtime','?')})  {mark}")

    races = B.drop_leaky(races_all, verbose=False)
    n_drop = len(races_all) - len(races)

    def stats(sub):
        if not sub:
            return None
        return B.summarize(B.run_engine(sub, args.budget, B.G.EV_MIN, True), args.boot)

    # ── その日単独 ──
    if args.date:
        print()
        print("■ 今回の日の成績（エンジンが選ぶ買い目・1レース%s円）" % f"{args.budget:,}")
        print(f"{'日付':>10s} {'R':>5s} {'的中率':>8s} {'回収率':>9s}")
        print("-" * 40)
        for d in args.date:
            sub = {k: v for k, v in races.items() if k[0] == d}
            s = stats(sub)
            if s:
                print(f"{d:>10s} {s['races']:5d} {100*s['hit']:7.1f}% {100*s['roi']:8.1f}%")
            else:
                print(f"{d:>10s}     — （リーク除外またはrecordsなし）")

    # ── 累積 ──
    s_all = stats(races)
    dates = sorted({k[0] for k in races})
    print()
    print("■ 累積（リーク除外後の全期間）")
    print(f"   対象      : {len(races)}レース / {len(dates)}日"
          f"（{dates[0]}〜{dates[-1]}）")
    if n_drop:
        print(f"   除外      : {n_drop}レース（レース後に作られたrecords）")
    if s_all:
        w = s_all['hi'] - s_all['lo']
        print(f"   実測ROI   : {100*s_all['roi']:.1f}%  的中率 {100*s_all['hit']:.1f}%")
        print(f"   95%信頼区間: [{100*s_all['lo']:.0f}〜{100*s_all['hi']:.0f}%]  幅 {100*w:.0f}pt")
        print()
        if s_all['lo'] > 1.0:
            print("   → 下限が100%超。統計的に勝てていると言える")
        elif s_all['hi'] < 1.0:
            print("   → 上限が100%未満。統計的に勝てていないと言える。設計の見直しが要る")
        else:
            print("   → 区間が100%をまたぐ。まだ判定できない。サンプルを積むこと")
            need = int(len(races) * (w / 0.40) ** 2)
            print(f"      （幅40pt まで狭めるには概算 {need:,}レース≒"
                  f"あと{max(0,(need-len(races))//70)}週末）")

    # ── 台帳に追記 ──
    led = json.loads(LEDGER.read_text(encoding='utf-8')) if LEDGER.exists() else []
    led = [r for r in led if r.get('as_of') != datetime.date.today().isoformat()]
    if s_all:
        led.append({
            'as_of': datetime.date.today().isoformat(),
            'added_dates': args.date or [],
            'races': len(races), 'days': len(dates),
            'roi': round(s_all['roi'], 4), 'hit': round(s_all['hit'], 4),
            'ci_lo': round(s_all['lo'], 4), 'ci_hi': round(s_all['hi'], 4),
            'dropped_leaky': n_drop,
        })
        LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding='utf-8')
        print()
        print(f"台帳に追記 → {LEDGER}")
        if len(led) > 1:
            print()
            print("■ 累積ROIの推移（サンプルが増えるほど区間が狭まる）")
            print(f"{'記録日':>12s} {'R数':>7s} {'ROI':>8s} {'95%区間':>18s}")
            print("-" * 50)
            for r in led[-8:]:
                print(f"{r['as_of']:>12s} {r['races']:7d} {100*r['roi']:7.1f}% "
                      f"{'[%.0f〜%.0f%%]' % (100*r['ci_lo'], 100*r['ci_hi']):>18s}")


if __name__ == '__main__':
    main()
