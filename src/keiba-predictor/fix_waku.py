# -*- coding: utf-8 -*-
"""
fix_waku.py — 蓄積DBの欠損している「枠」を馬番と頭数から復元する（2026-09-04）
==============================================================================
発見: race_results.json 14,036行すべてで 枠 が None だった。
そのため枠順バイアスを自前データで検証できず、独自指数のF06（枠順バイアス表）が
正しいかどうかを一度も確かめられていなかった。

馬番と頭数があれば枠はJRAの規則で一意に決まる:
  base = 頭数 // 8, rem = 頭数 % 8
  枠1〜(8-rem) には base 頭、枠(8-rem+1)〜8 には base+1 頭を割り当てる
  （余りは外枠に寄せる。例: 9頭なら枠8だけ2頭、18頭なら枠7-8が3頭ずつ）

使い方:
  python fix_waku.py --dry-run   # 検証のみ
  python fix_waku.py             # race_results.json を更新（バックアップを取る）
"""
from __future__ import annotations
import argparse, json, io, sys, shutil, collections
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db'
SRC = DB / 'race_results.json'


def waku_of(umaban: int, tosu: int) -> int | None:
    """馬番と頭数から枠番を求める（JRAの枠割り規則）"""
    if not umaban or not tosu or umaban < 1 or umaban > tosu or tosu < 1:
        return None
    if tosu <= 8:
        return umaban
    base, rem = divmod(tosu, 8)
    n = 0
    for w in range(1, 9):
        cnt = base + (1 if w > 8 - rem else 0)
        n += cnt
        if umaban <= n:
            return w
    return 8


def selftest():
    """規則が正しいか既知のケースで検算する"""
    cases = {
        9:  {1: 1, 7: 7, 8: 8, 9: 8},
        10: {1: 1, 6: 6, 7: 7, 8: 7, 9: 8, 10: 8},
        16: {1: 1, 2: 1, 3: 2, 15: 8, 16: 8},
        18: {1: 1, 12: 6, 13: 7, 15: 7, 16: 8, 18: 8},
    }
    ok = True
    for tosu, want in cases.items():
        for uma, w in want.items():
            got = waku_of(uma, tosu)
            if got != w:
                print(f"  ❌ {tosu}頭 馬番{uma} → {got}（期待{w}）")
                ok = False
    print("  ✅ 枠割り規則の検算に全て合格" if ok else "  ❌ 検算に失敗")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    print("■ 枠割り規則の検算")
    if not selftest():
        sys.exit(1)

    res = json.loads(SRC.read_text(encoding='utf-8'))
    print(f"\n■ 蓄積DB {len(res):,}行")
    before = sum(1 for r in res if r.get('枠'))
    print(f"  枠あり: {before}行")

    # レースごとの頭数を数える
    tosu = collections.Counter()
    for r in res:
        tosu[(r['date'], r['競馬場'], r['R'])] += 1

    filled = skipped = 0
    for r in res:
        if r.get('枠'):
            continue
        try:
            uma = int(float(r.get('馬番')))
        except (TypeError, ValueError):
            skipped += 1
            continue
        n = tosu[(r['date'], r['競馬場'], r['R'])]
        w = waku_of(uma, n)
        if w:
            r['枠'] = w
            filled += 1
        else:
            skipped += 1

    print(f"  復元: {filled:,}行 / 失敗: {skipped}行")
    dist = collections.Counter(r.get('枠') for r in res if r.get('枠'))
    print("  枠の分布: " + " ".join(f"{k}枠{v}" for k, v in sorted(dist.items()) if k))

    if args.dry_run:
        print("\n  （--dry-run のため書き込みませんでした）")
        return
    bak = SRC.with_suffix('.json.bak_waku')
    shutil.copy2(SRC, bak)
    SRC.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    print(f"\n  保存しました（バックアップ: {bak.name}）")


if __name__ == '__main__':
    main()
