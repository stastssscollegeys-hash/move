# -*- coding: utf-8 -*-
"""
structure_backtest.py — 買い方（券種・組み方・配分）の比較バックテスト（2026-09-11）
======================================================================================
ユーザー指摘「3連複・馬単・ワイドをばらばらに混ぜる買い方は一般的でない。本当に理にかなっているか。
予想（印）は良いので買い目が大事」を受けて、**同じレース集合・同じ印**で買い方だけを変えて比べる。

データ:
  - 印: レース前に作られた records（週末ビッグデータ_*_records.json）。レース後に作られたファイルは除外（engine_backtest.drop_leaky）
  - 払戻: daily_pdca/db/payouts.json（確定払戻・全券種）
印の割り当て（2通り＋混合）:
  - 印ベース  : 脚質補正後のAI予測順位 1=◎ 2=○ 3=▲ 4,5=△ 6=穴（運用と同じ）
  - 市場ベース: 確定単勝オッズの人気順で同じ割り当て（比較用の基準）
  - 混合      : ◎だけ印ベース、○以下は◎を除いた市場人気順
配分: flat（全点同額）／ even（推定配当に反比例＝どれが当たっても払戻がほぼ同じ）
指標: 的中率・回収率(95%区間)・最高配当1レース除外・期間3分割・当たったのに損する率・最長連敗

⚠ 限界:
  - 確定オッズで人気と推定配当を作っているので、前日時点より少しだけ有利な条件になる
  - 払戻が全頭の着順に依存する3連単系は分散が大きい
  - 300本の買い方を比べると偶然で良く見えるものが出る。**3分割すべて・上位1件除外でも同じ順位か**で判断する

使い方:
  python structure_backtest.py
"""
from __future__ import annotations
import collections, json, random, sys, io
from itertools import combinations, permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B
from payout_estimator import estimate

OUT = Path.home() / 'Desktop' / '競馬予想レポート' / '20260912' / 'research'
BOOT = 1000


# ── 買い方の定義 ─────────────────────────────────────────────
# m = {'◎':馬番, '○':..., '▲':..., '△1':..., '△2':..., '穴':...}
# 戻り値: [(券種, [馬番...], 重み)]  重みは flat 配分では無視する
def S(m, *keys):
    return [m[k] for k in keys]


def tri_form(m, c1, c2, c3):
    """3連複フォーメーション（重複除去）"""
    seen, out = set(), []
    for a in c1:
        for b in c2:
            for c in c3:
                s = frozenset([m[a], m[b], m[c]])
                if len(s) == 3 and s not in seen:
                    seen.add(s); out.append(('3連複', sorted(s), 1))
    return out


STRUCTS = {
    # 今週の混成型（チャレンジCの配分比率をテンプレート化）
    '今週の混成型(S型7点)': lambda m: [
        ('3連複', S(m, '◎', '○', '△1'), 30), ('馬単', S(m, '◎', '○'), 17.5), ('3連複', S(m, '◎', '▲', '△1'), 15),
        ('ワイド', S(m, '◎', '穴'), 16), ('3連複', S(m, '◎', '△2', '△1'), 10), ('3連複', S(m, '○', '▲', '△1'), 9),
        ('3連複', S(m, '◎', '○', '▲'), 2.5)],
    '単勝◎': lambda m: [('単勝', S(m, '◎'), 1)],
    '複勝◎': lambda m: [('複勝', S(m, '◎'), 1)],
    '馬連◎-○': lambda m: [('馬連', S(m, '◎', '○'), 1)],
    'ワイド◎-○': lambda m: [('ワイド', S(m, '◎', '○'), 1)],
    '馬単◎→○': lambda m: [('馬単', S(m, '◎', '○'), 1)],
    '3連複◎○▲(1点)': lambda m: [('3連複', S(m, '◎', '○', '▲'), 1)],
    '馬連◎流し(相手4)': lambda m: [('馬連', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')],
    'ワイド◎流し(相手4)': lambda m: [('ワイド', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')],
    '馬単◎1着流し(相手4)': lambda m: [('馬単', S(m, '◎', k), 1) for k in ('○', '▲', '△1', '△2')],
    'ワイドBOX3(◎○▲)': lambda m: [('ワイド', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)],
    '馬連BOX3(◎○▲)': lambda m: [('馬連', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲'), 2)],
    '3連複◎軸流し(相手4・6点)': lambda m: [('3連複', sorted([m['◎'], *c]), 1) for c in combinations(S(m, '○', '▲', '△1', '△2'), 2)],
    '3連複◎軸流し(相手5・10点)': lambda m: [('3連複', sorted([m['◎'], *c]), 1) for c in combinations(S(m, '○', '▲', '△1', '△2', '穴'), 2)],
    '3連複◎○2頭軸(相手4)': lambda m: [('3連複', sorted([m['◎'], m['○'], m[k]]), 1) for k in ('▲', '△1', '△2', '穴')],
    '3連複F ◎-○▲-○▲△△(5点)': lambda m: tri_form(m, ['◎'], ['○', '▲'], ['○', '▲', '△1', '△2']),
    '3連複F ◎-○▲-○▲△△穴(7点)': lambda m: tri_form(m, ['◎'], ['○', '▲'], ['○', '▲', '△1', '△2', '穴']),
    '3連複F ◎○-◎○▲-全印(9点)': lambda m: tri_form(m, ['◎', '○'], ['◎', '○', '▲'], ['○', '▲', '△1', '△2', '穴']),
    '3連複BOX4(◎○▲△)': lambda m: [('3連複', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲', '△1'), 3)],
    '3連複BOX5(◎○▲△△)': lambda m: [('3連複', sorted(c), 1) for c in combinations(S(m, '◎', '○', '▲', '△1', '△2'), 3)],
    '3連単◎1着-○▲-○▲△△(6点)': lambda m: [('3連単', [m['◎'], m[b], m[c]], 1) for b in ('○', '▲') for c in ('○', '▲', '△1', '△2') if b != c],
    '馬連◎-○＋3連複F5点': lambda m: [('馬連', S(m, '◎', '○'), 5)] + [(t, n, 1) for t, n, _ in tri_form(m, ['◎'], ['○', '▲'], ['○', '▲', '△1', '△2'])],
    'ワイド◎-○＋3連複◎軸6点': lambda m: [('ワイド', S(m, '◎', '○'), 3)] + [('3連複', sorted([m['◎'], *c]), 1) for c in combinations(S(m, '○', '▲', '△1', '△2'), 2)],
    '◎抜き40%分散(3連複◎軸6点＋○▲△BOX4点)': lambda m: [('3連複', sorted([m['◎'], *c]), 1) for c in combinations(S(m, '○', '▲', '△1', '△2'), 2)]
                                           + [('3連複', sorted(c), 1) for c in combinations(S(m, '○', '▲', '△1', '△2'), 3)],
}


def marks_from(order: list[str]) -> dict:
    keys = ['◎', '○', '▲', '△1', '△2', '穴']
    return {k: order[i] for i, k in enumerate(keys)} if len(order) >= 6 else {}


def race_marks(d, base):
    odds = d['odds']
    mkt = sorted(odds, key=lambda k: odds[k])
    if base == '市場':
        return marks_from(mkt)
    recs = B.styled(d['recs'])
    ai = [str(r['馬番']) for r in sorted(recs, key=lambda r: r.get('AI予測順位') or 99)]
    if base == '印':
        return marks_from(ai)
    if base == '混合':     # ◎は印、残りは市場人気順
        hon = ai[0]
        return marks_from([hon] + [x for x in mkt if x != hon])
    raise ValueError(base)


def run(races, name, base, alloc):
    per = []
    for key in sorted(races):
        d = races[key]
        m = race_marks(d, base)
        if not m:
            continue
        bets = STRUCTS[name](m)
        if alloc == 'even':
            ws = []
            for t, nums, _w in bets:
                e = estimate(t if t != '3連単' else '3連複', [d['odds'].get(x) for x in nums]) or 10.0
                if t == '3連単': e *= 6
                if t in ('単勝', '複勝'): e = d['odds'].get(nums[0]) or 5.0
                ws.append(1.0 / e)
            tot = sum(ws)
            bets = [(t, n, w / tot * 10) for (t, n, _), w in zip(bets, ws)]
        inv = ret = 0.0
        ok = True
        for t, nums, w in bets:
            w = 1.0 if alloc == 'flat' else w
            yen = B.payout_for(t, nums, d['pay'], d['top3'])
            if yen is None:
                ok = False; break
            inv += 100 * w
            ret += w * yen
        if ok and inv > 0:
            per.append((key, inv, ret))
    return per


def metrics(per):
    s = B.summarize(per, boot=BOOT)
    if not s:
        return None
    def roi(lst):
        inv = sum(i for _, i, _ in lst)
        return sum(r for _, _, r in lst) / inv if inv > 0 else 0.0
    by_ret = sorted(per, key=lambda x: -x[2])
    s['roi_ex1'] = roi(by_ret[1:])
    s['roi_ex3'] = roi(by_ret[3:])
    n = len(per); thirds = [per[:n // 3], per[n // 3:2 * n // 3], per[2 * n // 3:]]
    s['roi_thirds'] = [roi(t) for t in thirds]
    hitr = [x for x in per if x[2] > 0]
    s['gami'] = sum(1 for _, i, r in hitr if r < i) / len(hitr) if hitr else 0
    streak = best = 0
    for _, _, r in per:
        streak = streak + 1 if r == 0 else 0
        best = max(best, streak)
    s['max_losing'] = best
    return s


def main():
    cond_only = '--cond-only' in sys.argv
    races = B.drop_leaky(B.load_races(), verbose=False)
    dates = sorted({k[0] for k in races})
    print("=" * 110)
    print(f"■ 買い方の比較（レース前に作った印のみ・{len(races)}レース・{dates[0]}〜{dates[-1]}・{len(dates)}日）")
    print("=" * 110)
    results = {}
    for base in (() if cond_only else ('印', '市場', '混合')):
        for alloc in ('flat', 'even'):
            rows = []
            for name in STRUCTS:
                if alloc == 'even' and len(STRUCTS[name]({k: str(i) for i, k in enumerate(['◎', '○', '▲', '△1', '△2', '穴'])})) == 1:
                    continue
                s = metrics(run(races, name, base, alloc))
                if s:
                    rows.append((name, s)); results[f"{base}|{alloc}|{name}"] = s
            rows.sort(key=lambda x: -x[1]['roi_ex1'])
            print(f"\n【印の基準: {base} ／ 配分: {'全点同額' if alloc == 'flat' else '推定配当に反比例'}】")
            print(f"{'買い方':<40s}{'R':>5s}{'的中率':>7s}{'回収率':>7s}{'95%区間':>12s}{'上位1除外':>9s}{'上位3除外':>9s}{'前期/中期/後期':>18s}{'損する率':>8s}{'最長連敗':>7s}")
            for name, s in rows:
                th = "/".join(f"{x*100:.0f}" for x in s['roi_thirds'])
                print(f"{name:<40s}{s['races']:>5d}{s['hit']*100:>6.1f}%{s['roi']*100:>6.0f}%"
                      f"  [{s['lo']*100:>3.0f}〜{s['hi']*100:>3.0f}%]{s['roi_ex1']*100:>8.0f}%{s['roi_ex3']*100:>8.0f}%{th:>18s}"
                      f"{s['gami']*100:>7.0f}%{s['max_losing']:>7d}")

    # 条件別: 1番人気のオッズと頭数で分ける（実運用に近い「推定配当に反比例」配分で、印ベースと混合の2通り）
    conds = {
        '堅い(1人気<3.0倍)': lambda d: min(d['odds'].values()) < 3.0,
        '中間(3.0〜4.9倍)': lambda d: 3.0 <= min(d['odds'].values()) < 5.0,
        '混戦(5.0倍以上)': lambda d: min(d['odds'].values()) >= 5.0,
        '少頭数(12頭以下)': lambda d: len(d['odds']) <= 12,
        '多頭数(15頭以上)': lambda d: len(d['odds']) >= 15,
    }
    cond_res = {}
    names = [n for n in STRUCTS if len(STRUCTS[n]({k: str(i) for i, k in enumerate(['◎', '○', '▲', '△1', '△2', '穴'])})) > 1]
    subsets = {c: {k: v for k, v in races.items() if f(v)} for c, f in conds.items()}
    for base in ('印', '混合'):
        print(f"\n\n■ 条件別（印の基準: {base} ／ 推定配当に反比例）: 上位1除外の回収率 / 的中率 （n=レース数）")
        print(f"{'買い方':<40s}" + "".join(f"{c:>22s}" for c in conds))
        for name in names:
            cells = []
            for c in conds:
                s = metrics(run(subsets[c], name, base, 'even'))
                cond_res[f"{base}|{c}|{name}"] = s
                cells.append(f"{s['roi_ex1']*100:>4.0f}%/{s['hit']*100:>4.1f}%(n{s['races']})" if s else "—")
            print(f"{name:<40s}" + "".join(f"{x:>22s}" for x in cells))

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({'races': len(races), 'dates': dates, 'results': results, 'by_condition': cond_res},
              open(OUT / 'structure_backtest_20260911.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(f"\nsaved {OUT / 'structure_backtest_20260911.json'}")


if __name__ == '__main__':
    main()
