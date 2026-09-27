# -*- coding: utf-8 -*-
"""
style_correction.py — 脚質バイアス補正レイヤー（v6.0 / 2026-08-31）
====================================================================
【何を直すか】
現行の総合指数には明確な脚質バイアスがある。13開催・6,269頭の検証で判明:

  総合指数の平均   逃げ50.0 / 先行46.4 / 差し40.5
  実際の全馬構成   逃げ10.3% / 先行30.4% / 差し49.4%
  レース内1位の構成 逃げ23.3% / 先行40.2% / 差し27.1%
    → 逃げ馬を2.3倍に過大評価し、差し馬を半分に過小評価していた

原因は「近5走複勝率%」「同距離複勝率%」が差し馬で構造的に低く出ること
（市場1-3番人気で 差し39.5 vs 先行52.2）。差し馬は展開に左右されて着順が
安定しないため複勝率が低く出るが、モデルはそれを「能力が低い」と解釈していた。
市場は「展開次第で走る」と織り込んで人気にしており、馬券的には市場が正しい
（市場1-3番人気の差し馬は単勝回収率107%）。

【補正の中身】
脚質ごとの総合指数の平均を全体平均に揃えるだけ。パラメータは3つ。

  逃げ -6.7 / 先行 -3.1 / 差し +2.8

【効果（train/valid分割で検証済み・過学習ではない）】
  単勝回収率  74.4% → 84.1%（+9.7pt）
  1位の脚質構成 逃げ23.3%→12.0% / 差し27.1%→45.9%（実態にほぼ一致）

【設計方針】
既存の指数計算（collect_weekend_bigdata.py）には手を入れない後処理レイヤー。
呼ばなければ従来どおりの挙動になる。効果が確認できなくなればこの層を外すだけ。

【使い方】
    from style_correction import apply_style_correction
    apply_style_correction(recs)   # recs は1レース分のrecordsリスト（破壊的に更新）

    元の値は '総合指数_補正前' '_AI予測順位_補正前' に退避される。
"""
from __future__ import annotations
import collections, statistics

# 13開催・6,269頭から算出した補正値（2026-08-31時点）
# ※ 開催が進んだら recompute_offsets() で再計算し、ここを更新する
STYLE_OFFSET = {
    '逃げ': -6.7,
    '先行': -3.1,
    '差し': +2.8,
}

ENABLED = True   # False にすると補正を止められる（切り戻し用）


def apply_style_correction(recs, offsets=None, enabled=None):
    """1レース分のrecordsに脚質補正を当て、AI予測順位を振り直す。

    recs: collect_weekend_bigdata が出力する1レース分のリスト
          （'総合指数' '脚質' 'AI予測順位' を持つ）
    戻り値: (補正した頭数, 順位が変わった頭数)
    """
    if enabled is None:
        enabled = ENABLED
    if not enabled or not recs:
        return 0, 0
    off = offsets or STYLE_OFFSET

    # 補正前を退避
    for r in recs:
        if '総合指数_補正前' not in r:
            r['総合指数_補正前'] = r.get('総合指数')
            r['AI予測順位_補正前'] = r.get('AI予測順位')

    n = 0
    for r in recs:
        base = r.get('総合指数_補正前')
        if base is None:
            continue
        r['総合指数'] = round(base + off.get(r.get('脚質') or '', 0.0), 1)
        n += 1

    # 順位を振り直す
    order = sorted(recs, key=lambda x: -(x.get('総合指数') or 0))
    changed = 0
    for i, r in enumerate(order, start=1):
        if r.get('AI予測順位') != i:
            changed += 1
        r['AI予測順位'] = i
    return n, changed


def recompute_offsets(all_records):
    """蓄積データから補正値を再計算する（開催が進んだら定期的に実行）。

    all_records: 全レース分のrecordsをフラットにしたリスト
    戻り値: {脚質: 補正値}
    """
    by = collections.defaultdict(list)
    for r in all_records:
        s = r.get('脚質')
        v = r.get('総合指数_補正前', r.get('総合指数'))
        if s and v is not None:
            by[s].append(float(v))
    vals = [v for lst in by.values() for v in lst]
    if not vals:
        return {}
    gmean = statistics.mean(vals)
    return {s: round(gmean - statistics.mean(lst), 1)
            for s, lst in by.items() if len(lst) >= 30}


def describe():
    """現在の補正値を1行で返す（レポートへの注記用）"""
    return "脚質補正 " + " / ".join("%s%+.1f" % (s, v) for s, v in STYLE_OFFSET.items())
