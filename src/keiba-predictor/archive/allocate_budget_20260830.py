# -*- coding: utf-8 -*-
"""
2026-08-30 資金配分の期待値ベース再計算
=========================================
ユーザー方針（2026-08-29）:
  「重賞だからお金をかけるっていうのも変な話。
   期待値が取れるレースはその分お金をかけるのが当たり前」

従来はレースの格（重賞/平場）と自信度だけで予算が決まっていたため、
期待回収率125%のレースに15,100円、224%のレースに5,000円という
逆転した配分になっていた。ここを期待値ベースの按分に組み替える。

配分ロジック:
  重み = (E[回収率] − 1.0) × 信頼度係数 × sqrt(的中率)
    ・(E−1.0) …… 期待値のエッジそのもの。大きいほど厚く張る
    ・信頼度係数 …… 実オッズあり=1.0 / 推定オッズのみ=0.6
        推定オッズの期待値は「妙味の幻影」で膨らむ（8/22に穴軸2戦0勝−30,000円）
    ・sqrt(的中率) …… 的中率が極端に低いレースへの一極集中を緩和する
  総予算を重み比で按分し、1レース上限=総予算の30%、下限=2,000円でクリップ。
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_weekend_confidence_report import calc_confidence
from flat_race_rules import assign_marks, build_kaime, roles_from_marks
from v55_guard import apply_young_cap
from gen_kaime_v5 import public_probs

DAY = "20260830"
TOTAL_BUDGET = 53000          # 現行の総額（重賞16,000＋平場37,100）を維持
CONF_MIN = 7
GRADE_NAMES = ('新潟記念', '中京２歳', '中京2歳')
CAP_RATIO = 0.30              # 1レース上限＝総予算の30%
FLOOR = 2000                  # 買う以上は意味のある額
ODDS_FILE = Path.home() / 'Desktop' / '競馬予想レポート' / DAY / f'odds_{DAY}.json'

# 重賞2本は手組み（ev_manual_20260830.py の採用構成の実測値）
GRADE_ROWS = [
    # (表示名, E[回収率], 的中率, 実オッズあり, 現行額, 構成)
    ("新潟記念(G3) 新潟8R",   1.42, 0.123, True, 9700, "3連複🔥⑩軸6点＋ワイド2点"),
    ("中京2歳S(G3) 中京7R",   1.70, 0.527, True, 6300, "馬連3点＋3連複○④軸6点"),
]


def load_flat():
    base = Path.home() / 'Desktop' / '競馬予想レポート' / DAY
    js = next(base.glob(f'週末ビッグデータ_{DAY}*_records.json'), None)
    if not js:
        raise SystemExit("records.json が見つかりません")
    data = json.load(open(js, encoding='utf-8'))
    odds_all = json.load(open(ODDS_FILE, encoding='utf-8')) if ODDS_FILE.exists() else {}

    races = defaultdict(list)
    for r in data['records']:
        races[(r['date'], r['競馬場'], r['R'])].append(r)
    for k in races:
        races[k].sort(key=lambda x: x['AI予測順位'])
    conf = {k: calc_confidence(v) for k, v in races.items()}

    keys = [k for k in races if conf[k][0] >= CONF_MIN
            and not any(g in (races[k][0].get('レース名') or '') for g in GRADE_NAMES)]
    keep, dropped = apply_young_cap(set(keys), races, conf)

    rows = []
    for k in sorted(keys, key=lambda x: (x[1], x[2])):
        recs = races[k]
        if k not in keep:
            continue
        # 実オッズは重賞2本しか無いので平場は推定（＝信頼度係数0.6）
        okey = f"{k[0]}_{k[1]}_{k[2]}"
        odds = odds_all.get(okey)
        marks, roles, info = assign_marks(recs, q=public_probs(recs, odds) if odds else None)
        for r in recs:
            mk = marks.get(r['馬番'], '')
            r['AI印'] = '' if mk == '❌' else mk
        roles2 = roles_from_marks(marks, recs) if 'roles_from_marks' in dir() else roles
        kai = build_kaime(recs, conf[k][0], marks, roles, info, odds_override=odds)
        if kai.get('skip') or not kai.get('res'):
            continue
        res = kai['res']
        rows.append(dict(
            name=f"{recs[0]['レース名']} {k[1]}{k[2]}R",
            E=res['E_rate'], hit=res.get('P_hit', 0.0),
            real_odds=bool(odds), cur=kai.get('budget') or res.get('total', 0),
            comp=kai.get('arch_name', ''), conf=conf[k][0],
        ))
    return rows


def main():
    rows = []
    for nm, E, hit, ro, cur, comp in GRADE_ROWS:
        rows.append(dict(name=nm, E=E, hit=hit, real_odds=ro, cur=cur, comp=comp, conf='重賞'))
    rows += load_flat()

    # ── E[回収率]のキャップ（2026-08-30追加）────────────────────────
    # 実オッズを入れた途端、平場でE627%・E495%といった値が出た。的中率49.6%で
    # 回収627%＝「半分の確率で12.6倍が返る」計算になり、現実にはありえない。
    # モデル勝率pと市場qの乖離をHarville近似で配当に換算する構造上、
    # 「高確率×高配当」という矛盾した評価が生まれる（＝妙味の幻影）。
    # 配分にそのまま使うと危険なので、重み計算ではEを上限でクリップする。
    E_CAP = 3.0
    for r in rows:
        trust = 1.0 if r['real_odds'] else 0.6
        e_eff = min(r['E'], E_CAP)
        r['capped'] = r['E'] > E_CAP
        r['w'] = max(0.0, e_eff - 1.0) * trust * math.sqrt(max(r['hit'], 0.01))

    tw = sum(r['w'] for r in rows) or 1.0
    cap = TOTAL_BUDGET * CAP_RATIO
    for r in rows:
        raw = TOTAL_BUDGET * r['w'] / tw
        r['new'] = int(round(min(max(raw, FLOOR), cap) / 100) * 100)

    # クリップで総額がずれるので、上限・下限に当たっていないレースで調整
    diff = TOTAL_BUDGET - sum(r['new'] for r in rows)
    adj = [r for r in rows if FLOOR < r['new'] < cap]
    if adj and abs(diff) >= 100:
        aw = sum(r['w'] for r in adj) or 1.0
        for r in adj:
            r['new'] = int(round((r['new'] + diff * r['w'] / aw) / 100) * 100)

    print("=" * 112)
    print("■ 2026/08/30 資金配分 期待値ベース再計算   総予算 %s円" % f"{TOTAL_BUDGET:,}")
    print("  重み = (E−1.0) × 信頼度係数(実オッズ1.0/推定0.6) × √的中率")
    print("=" * 112)
    print("%-34s %8s %8s %6s %10s %10s %8s" %
          ("レース", "E[回収率]", "的中率", "オッズ", "現行", "新配分", "増減"))
    print("-" * 112)
    for r in sorted(rows, key=lambda x: -x['E']):
        d = r['new'] - r['cur']
        print("%-34s %7.0f%%%1s %6.1f%% %6s %9s円 %9s円 %+8s" % (
            r['name'][:34], r['E'] * 100, "※" if r.get('capped') else "", r['hit'] * 100,
            "実" if r['real_odds'] else "推定",
            f"{r['cur']:,}", f"{r['new']:,}", f"{d:+,}"))
    print("-" * 112)
    print("%-34s %7s %7s %6s %9s円 %9s円" % (
        "合計", "", "", "", f"{sum(r['cur'] for r in rows):,}", f"{sum(r['new'] for r in rows):,}"))
    print()
    print("  ※印 = 期待回収率が300%%を超えたため、配分計算では300%%に丸めています（妙味の幻影対策）。")
    print("    的中率と両立しない高E値をそのまま重みにすると、1レースへの過剰集中を招くため。")


if __name__ == "__main__":
    main()
