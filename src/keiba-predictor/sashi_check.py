# -*- coding: utf-8 -*-
"""
sashi_check.py — 差し馬バイアス補正のチェッカー（2026-08-31新設 / v6.0）
=========================================================================
検証で唯一確認できたエッジ「モデルは差し馬を系統的に過小評価している」を
実戦の予想フローに組み込むための検出ツール。

  市場1-3番人気 × 脚質「差し」          … 単勝回収率 107%（n=422）
  ＋ エンジンが4位以下に落としている場合 … 125〜148%
  （同じ条件でも脚質が先行なら 25% と真逆なので、脚質の確認が必須）

**追試前なので印を自動で書き換えることはしない。**
「この馬は昇格を検討すべき」と提示し、最終判断は人が行う。

使い方:
  python sashi_check.py --date 20260906
  python sashi_check.py --date 20260906 --odds-file odds_20260906.json
"""
from __future__ import annotations
import json, argparse, collections
from pathlib import Path

BASE = Path.home() / 'Desktop' / '競馬予想レポート'


def load_day(day):
    f = BASE / day / ("週末ビッグデータ_%s-%s_records.json" % (day, day[4:]))
    if not f.exists():
        raise SystemExit("records.json が見つかりません: %s" % f)
    data = json.load(open(f, encoding='utf-8'))
    races = collections.defaultdict(list)
    for r in data['records']:
        races[(r['競馬場'], int(r['R']))].append(r)
    for k in races:
        races[k].sort(key=lambda x: int(x.get('AI予測順位') or 99))
    return races


def market_rank(recs, odds):
    """実オッズがあれば人気順、なければ大衆スコア順で市場評価の順位を返す"""
    if odds:
        pairs = [(r['馬番'], odds.get(str(r['馬番']))) for r in recs]
        pairs = [(n, o) for n, o in pairs if o]
        pairs.sort(key=lambda x: x[1])
        return {n: i + 1 for i, (n, o) in enumerate(pairs)}
    # 実オッズが無い場合は近走着順とML能力から簡易に推定
    sc = []
    for r in recs:
        s = -(r.get('近5走平均着') or 9) * 0.5 + (r.get('ML能力%') or 0) * 0.1
        sc.append((r['馬番'], s))
    sc.sort(key=lambda x: -x[1])
    return {n: i + 1 for i, (n, s) in enumerate(sc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--odds-file')
    args = ap.parse_args()

    odds_all = json.load(open(args.odds_file, encoding='utf-8')) if args.odds_file else {}
    races = load_day(args.date)

    print("=" * 104)
    print("■ 差し馬バイアス チェック（v6.0）  %s" % args.date)
    print("=" * 104)
    print("検証結果: 市場1-3番人気の差し馬=回収率107% ／ エンジンが4位以下に落とした場合=125〜148%")
    print("　　　　　同条件でも脚質が先行なら25%なので、脚質を必ず確認すること")
    print()

    hits, warns = [], []
    for (venue, rno), recs in sorted(races.items()):
        okey_candidates = ["%s_%s_%d" % (args.date, venue, rno), "%s%d" % (venue, rno)]
        odds = None
        for k in okey_candidates:
            if k in odds_all:
                odds = odds_all[k]
                break
        mrank = market_rank(recs, odds)
        name = recs[0].get('レース名', '')
        for r in recs:
            num = r['馬番']
            e_rank = int(r.get('AI予測順位') or 99)
            m_rank = mrank.get(num, 99)
            style = r.get('脚質') or ''
            if m_rank <= 3 and style == '差し' and e_rank >= 4:
                o = odds.get(str(num)) if odds else None
                hits.append((venue, rno, name, num, r['馬名'], e_rank, m_rank, o,
                             r.get('総合指数'), '実' if odds else '推定'))
            if m_rank <= 3 and style == '先行' and e_rank >= 7:
                warns.append((venue, rno, name, num, r['馬名'], e_rank, m_rank))

    if hits:
        print("★ 昇格を検討すべき馬（市場上位 × 差し × エンジン4位以下）: %d頭" % len(hits))
        print("%-6s %3s %-16s %4s %-16s %6s %6s %8s %8s %s" %
              ("競馬場", "R", "レース名", "馬番", "馬名", "指数順", "市場順", "オッズ", "総合指数", "市場"))
        print("-" * 104)
        for v, rn, nm, num, hn, er, mr, o, sg, src in hits:
            print("%-6s %3d %-16s %4d %-16s %5d位 %5d位 %7s %8.1f %s" %
                  (v, rn, nm[:16], num, hn[:16], er, mr,
                   ("%.1f倍" % o) if o else "-", sg or 0, src))
        print()
        print("→ この馬たちは、検証データでは回収率125〜148%の帯にいる。")
        print("　 エンジンの印が低くても、買い目の相手には必ず入れること。")
    else:
        print("該当なし（市場上位 × 差し × エンジン低評価 の馬はいません）")

    if warns:
        print()
        print("⚠ 注意すべき馬（市場上位 × 先行 × エンジン7位以下）: %d頭" % len(warns))
        print("　 同じ食い違いでも先行馬は回収率25%。人気でも過信しないこと。")
        for v, rn, nm, num, hn, er, mr in warns[:15]:
            print("   %s%dR %s  %d番 %s（指数%d位 / 市場%d位）" % (v, rn, nm[:14], num, hn[:14], er, mr))

    print()
    print("※ このエッジは13開催・6,269頭の検証結果。9月以降の追試が済むまでは")
    print("   印を自動で書き換えず、人が最終判断すること。")


if __name__ == '__main__':
    main()
