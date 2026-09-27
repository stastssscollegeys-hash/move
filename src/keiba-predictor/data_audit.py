# -*- coding: utf-8 -*-
"""
data_audit.py — 予想データベースの欠損・品質を実測する（2026-09-03 新規）
==========================================================================
2026-09-02の重賞リサーチ中に「records に父の名前が無く、父勝率%が0.0の馬が多い」
「過去走キャッシュが距離と上がりしか持っていない」ことに気づいた。
思い込みで直すのではなく、まず欠損率を数える。

見るもの:
  ① records の各因子の欠損率（0埋め・未マッチがどれだけあるか）
  ② 過去走キャッシュが持っているフィールド
  ③ 血統マッピングの成功率
  ④ 蓄積DBのカバー範囲

使い方: python data_audit.py
"""
from __future__ import annotations
import json, io, sys, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
CACHE = Path(__file__).resolve().parent / '_cache' / 'netkeiba'
DB = BASE / 'daily_pdca' / 'db'


def load_all_records():
    out, files = [], []
    for f in sorted(BASE.glob('**/週末ビッグデータ_*_records.json')):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        recs = d.get('records', [])
        if recs:
            out += recs
            files.append((f.name, len(recs)))
    return out, files


def main():
    recs, files = load_all_records()
    print("=" * 96)
    print(f"■ 予想データベースの品質監査   records {len(recs):,}頭 / {len(files)}ファイル")
    print("=" * 96)

    # ── ① 因子の欠損率 ──
    print()
    print("【①】各因子が「0または欠損」の割合（高いほど因子が死んでいる）")
    print(f"{'因子':>18s} {'0/欠損':>9s} {'割合':>8s}   評価")
    print("-" * 96)
    FIELDS = ['父勝率%', '母父勝率%', '騎手勝率%', '厩舎勝率%', '近5走平均着',
              '近5走複勝率%', '平均上がり', '同距離走数', '同距離複勝率%',
              'ML能力%', '独自指数', '中日数', '脚質',
              'DB出走数', 'DB平均指数', 'DB最高指数']
    bad = []
    for k in FIELDS:
        z = sum(1 for r in recs if not r.get(k) or r.get(k) in (0, 0.0, '', '?'))
        pct = 100 * z / len(recs)
        if pct >= 50:
            ev = "🚨 半数以上が無効。因子として機能していない"
            bad.append((k, pct))
        elif pct >= 20:
            ev = "⚠ 2割以上が無効"
            bad.append((k, pct))
        elif pct >= 5:
            ev = "△ 一部欠損"
        else:
            ev = "OK"
        print(f"{k:>18s} {z:9,d} {pct:7.1f}%   {ev}")

    # ── ② 過去走キャッシュの中身 ──
    print()
    print("【②】過去走キャッシュが実際に保持しているフィールド")
    try:
        past = json.loads((CACHE / 'horse_past.json').read_text(encoding='utf-8'))
        keys = collections.Counter()
        nonempty = collections.Counter()
        n_horse = len(past)
        n_run = 0
        for hid, rows in past.items():
            for row in rows:
                n_run += 1
                for k, v in row.items():
                    keys[k] += 1
                    if v not in (None, '', '--', 0):
                        nonempty[k] += 1
        print(f"   馬 {n_horse:,}頭 / 延べ過去走 {n_run:,}件")
        print(f"   {'フィールド':>14s} {'保持':>8s} {'有効値':>8s}")
        print("   " + "-" * 40)
        for k, c in keys.most_common():
            print(f"   {k:>14s} {c:8,d} {nonempty[k]:8,d}")
        MISSING = ['finish', 'popularity', 'odds', 'passing', 'margin',
                   'race_name', 'field_size', 'condition', 'horse_weight']
        lack = [m for m in MISSING if m not in keys]
        if lack:
            print(f"   🚨 取得できるのに保持していない: {', '.join(lack)}")
    except Exception as e:
        print("   読み込み失敗:", e)

    # ── ③ 血統マッピングの成功率 ──
    print()
    print("【③】血統マッピングの成功率（父勝率%が入っているか）")
    by_race = collections.defaultdict(list)
    for r in recs:
        by_race[(r['date'], r['競馬場'], int(r['R']))].append(r)
    full0 = sum(1 for v in by_race.values()
                if all(not x.get('父勝率%') for x in v))
    print(f"   全出走馬の父勝率%が0のレース: {full0}/{len(by_race)} "
          f"({100*full0/len(by_race):.1f}%)")
    print("   → このレースでは血統因子 sc[6] が全頭で機能していない")

    # ── ④ 蓄積DBのカバー範囲 ──
    print()
    print("【④】蓄積DB（race_results.json）のカバー範囲")
    try:
        res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
        dates = sorted({r['date'] for r in res})
        ven = collections.Counter(r['競馬場'] for r in res)
        print(f"   {len(res):,}行 / {len(dates)}日（{dates[0]}〜{dates[-1]}）")
        print(f"   競馬場: " + " ".join(f"{k}{v}" for k, v in ven.most_common()))
        missing = [v for v in ('東京', '中山', '阪神', '京都', '中京', '新潟',
                               '福島', '小倉', '札幌', '函館') if v not in ven]
        if missing:
            print(f"   🚨 蓄積が無い競馬場: {', '.join(missing)}")
    except Exception as e:
        print("   読み込み失敗:", e)

    # ── ⑤ 払戻DB ──
    print()
    print("【⑤】払戻DB（2026-09-02構築）")
    try:
        pay = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
        print(f"   {len(pay):,}レース分（7券種）")
    except Exception:
        print("   なし")

    print()
    print("=" * 96)
    print("■ 優先度の高い欠陥")
    print("=" * 96)
    for k, pct in sorted(bad, key=lambda x: -x[1]):
        print(f"  ・{k}: {pct:.1f}% が無効")


if __name__ == '__main__':
    main()
