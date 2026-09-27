# -*- coding: utf-8 -*-
"""
policy_validation.py — 買い方の「選び方」そのものを検証する（2026-09-11）
==========================================================================
ユーザー方針（9/11）: 「いろいろ試して、積み重ねて、年間回収率100%超えを目指す」

pattern_by_segment.py は「全期間を見て、区分ごとに一番良かった買い方」を出した。
それは**同じデータで選んで同じデータで評価**しているので、偶然を拾っている可能性がある。
ここでは実運用と同じく「過去だけを見て選び、まだ見ていない日に当てる」で測る。

  検証1 時系列（ウォークフォワード）: 日付順に、それまでの日だけで区分ごとの買い方を選び、翌日に当てる
         比較: 固定の買い方（前半で一番だったもの／馬連BOX3＋ワイド◎流し4／混成型／複勝◎）
  検証2 前半で選んで後半に当てる／後半で選んで前半に当てる（2分割の入れ替え）
  検証3 見送りルール: ◎が4番人気以下なら買わない 等
  検証4 旧ガードを足した場合: ◎抜き1点／◎からのワイド／◎○▲の3連複／1点上限30%
  検証5 配分方法: 全点同額／推定配当に反比例／その中間（平方根）／反比例＋1点上限30%

データ: レース前に作った印のみ（engine_backtest.drop_leaky）×確定払戻。印=脚質補正後のAI予測順位。
⚠ 385レース・12日しかない。時系列検証は後半の6〜7日分しか評価に使えない。
"""
from __future__ import annotations
import json, math, random, sys, io
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import engine_backtest as B
import structure_backtest as SB
import pattern_by_segment  # noqa: F401  SB.STRUCTS に候補を追加
from payout_estimator import estimate

OUT = Path.home() / 'Desktop' / '競馬予想レポート' / '20260912' / 'research'
DUMMY = {k: str(i) for i, k in enumerate(['◎', '○', '▲', '△1', '△2', '穴'])}


# ── 旧ガードを足した買い方を登録 ───────────────────────────
def S(m, *k):
    return [m[x] for x in k]


GUARD = {
    'G◎抜き': lambda m: [('3連複', sorted(S(m, '○', '▲', '△1')), 1)],
    'G◎ワイド': lambda m: [('ワイド', sorted(S(m, '◎', '○')), 1)],
    'G◎○▲3連複': lambda m: [('3連複', sorted(S(m, '◎', '○', '▲')), 1)],
}
BASES_FOR_GUARD = ['馬連BOX3(◎○▲)', '馬連◎流し(相手4)', '今週の混成型(S型7点)', '馬連BOX3＋ワイド◎流し4(7点)']
for bname in BASES_FOR_GUARD:
    for gname, gf in GUARD.items():
        SB.STRUCTS[f"{bname}+{gname}"] = (lambda bf, gf: (lambda m: bf(m) + gf(m)))(SB.STRUCTS[bname], gf)


# ── 配分つきの実行（SB.run を拡張）──────────────────────────
def est_for(t, nums, odds):
    if t == '単勝':
        return odds.get(nums[0]) or 5.0
    if t == '複勝':
        return max(1.1, 1 + ((odds.get(nums[0]) or 5.0) - 1) * 0.25)
    e = estimate('3連複' if t == '3連単' else t, [odds.get(x) for x in nums]) or 10.0
    return e * 6 if t == '3連単' else e


def run_alloc(races, name, alloc, marks_cache):
    per = {}
    for key in sorted(races):
        d = races[key]
        m = marks_cache.get(key)
        if not m:
            continue
        bets = []
        seen = set()
        for t, nums, _w in SB.STRUCTS[name](m):
            k = (t, tuple(nums) if t in ('馬単', '3連単') else tuple(sorted(nums)))
            if k in seen:
                continue
            seen.add(k)
            bets.append((t, nums))
        ests = [est_for(t, n, d['odds']) for t, n in bets]
        if alloc == 'flat' or len(bets) == 1:
            ws = [1.0] * len(bets)
        elif alloc == 'even':
            ws = [1 / e for e in ests]
        elif alloc == 'sqrt':
            ws = [1 / math.sqrt(e) for e in ests]
        elif alloc == 'even_cap30':
            ws = [1 / e for e in ests]
            for _ in range(10):
                tot = sum(ws); cap = 0.30 * tot
                if all(w <= cap + 1e-12 for w in ws):
                    break
                over = sum(w - cap for w in ws if w > cap)
                free = [i for i, w in enumerate(ws) if w < cap]
                ws = [min(w, cap) for w in ws]
                if free:
                    fs = sum(ws[i] for i in free)
                    for i in free:
                        ws[i] += over * ws[i] / fs
        else:
            raise ValueError(alloc)
        tot = sum(ws)
        inv = ret = 0.0
        ok = True
        for (t, nums), w in zip(bets, ws):
            w = w / tot * 10
            yen = B.payout_for(t, nums, d['pay'], d['top3'])
            if yen is None:
                ok = False; break
            inv += 100 * w; ret += w * yen
        if ok and inv > 0:
            per[key] = (inv, ret)
    return per


def quick(lst):
    """ブートストラップなしの指標（選択用）"""
    if not lst:
        return None
    inv = sum(i for _, i, _ in lst); ret = sum(r for _, _, r in lst)
    by = sorted(lst, key=lambda x: -x[2])
    def roi(l):
        s = sum(i for _, i, _ in l); return sum(r for _, _, r in l) / s if s > 0 else 0.0
    return {'n': len(lst), 'roi': ret / inv, 'ex1': roi(by[1:]), 'ex3': roi(by[3:]),
            'hit': sum(1 for _, _, r in lst if r > 0) / len(lst)}


def seg_of(f):
    h = '1' if f['hon'] == 1 else '2-3' if f['hon'] <= 3 else '4+'
    t = '1-3' if f['tai'] <= 3 else '4+'
    return f"◎{h}×○{t}"


def choose_on(train_keys, feats, per_all, names):
    """kaime_20260912.choose と同じ規則を、学習期間のデータだけで行う"""
    overall = {}
    for n in names:
        q = quick([(k, *per_all[n][k]) for k in train_keys if k in per_all[n]])
        if q:
            overall[n] = q
    best_overall = max(overall, key=lambda n: (overall[n]['ex1'] + overall[n]['ex3']) / 2)
    pick = {}
    for seg in {seg_of(feats[k]) for k in feats}:
        keys = [k for k in train_keys if seg_of(feats[k]) == seg]
        if len(keys) < 15:
            pick[seg] = best_overall; continue
        rows = []
        for n in names:
            q = quick([(k, *per_all[n][k]) for k in keys if k in per_all[n]])
            if q:
                rows.append((n, q))
        r1 = {n: i for i, (n, _) in enumerate(sorted(rows, key=lambda x: -x[1]['ex1']))}
        r3 = {n: i for i, (n, _) in enumerate(sorted(rows, key=lambda x: -x[1]['ex3']))}
        stable = sorted(rows, key=lambda x: (r1[x[0]] + r3[x[0]]) / 2)[:8]
        cands = [(n, q) for n, q in stable if overall.get(n, {}).get('ex1', 0) >= 0.75]
        if not cands:
            pick[seg] = best_overall; continue
        best = max((q['ex1'] + q['ex3']) / 2 for _, q in cands)
        near = [(n, q) for n, q in cands if (q['ex1'] + q['ex3']) / 2 >= best - 0.03]
        pick[seg] = max(near, key=lambda x: ((x[1]['ex1'] + x[1]['ex3']) / 2) / max(x[1]['hit'], 0.01))[0]
    return pick, best_overall


def paired_diff(per_a, per_b, keys, boot=2000, seed=7):
    """同じレース集合での回収率の差（A−B）の95%区間"""
    ks = [k for k in keys if k in per_a and k in per_b]
    rng = random.Random(seed)
    diffs = []
    for _ in range(boot):
        smp = [ks[rng.randrange(len(ks))] for _ in ks]
        ia = sum(per_a[k][0] for k in smp); ib = sum(per_b[k][0] for k in smp)
        if ia > 0 and ib > 0:
            diffs.append(sum(per_a[k][1] for k in smp) / ia - sum(per_b[k][1] for k in smp) / ib)
    diffs.sort()
    ra = sum(per_a[k][1] for k in ks) / sum(per_a[k][0] for k in ks)
    rb = sum(per_b[k][1] for k in ks) / sum(per_b[k][0] for k in ks)
    return ra - rb, diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))], len(ks)


def fmt(q):
    return f"n{q['n']:>4} 回収{q['roi']*100:>5.0f}% 上位1除外{q['ex1']*100:>4.0f}% 上位3除外{q['ex3']*100:>4.0f}% 的中{q['hit']*100:>4.1f}%"


def main():
    races = B.drop_leaky(B.load_races(), verbose=False)
    marks_cache, feats = {}, {}
    for key, d in races.items():
        m = SB.race_marks(d, '印')
        if not m:
            continue
        marks_cache[key] = m
        order = sorted(d['odds'], key=lambda k: d['odds'][k])
        pr = {h: i + 1 for i, h in enumerate(order)}
        feats[key] = {'hon': pr[m['◎']], 'tai': pr[m['○']], 'n': len(d['odds']), 'date': key[0]}
    base_names = [n for n in SB.STRUCTS if '+G' not in n]
    print(f"対象 {len(feats)}レース / 日付 {sorted({k[0] for k in feats})}")

    per = {}
    for n in SB.STRUCTS:
        per[n] = run_alloc(races, n, 'flat' if len(SB.STRUCTS[n](DUMMY)) == 1 else 'even', marks_cache)
    report = {}

    # ── 検証1: 時系列ウォークフォワード ─────────────────────
    dates = sorted({k[0] for k in feats})
    wf = {'policy': [], 'fixed_train_best': [], '馬連BOX3＋ワイド◎流し4(7点)': [], '今週の混成型(S型7点)': [], '複勝◎': [],
          'policy_skip◎4+': []}
    picks_log = []
    for i in range(6, len(dates)):
        train = [k for k in feats if k[0] < dates[i]]
        test = [k for k in feats if k[0] == dates[i]]
        pick, best_overall = choose_on(train, feats, per, base_names)
        picks_log.append({'test_date': dates[i], 'best_overall': best_overall, 'pick': pick})
        for k in test:
            seg = seg_of(feats[k]); n = pick.get(seg, best_overall)
            if k in per[n]:
                wf['policy'].append((k, *per[n][k]))
                if feats[k]['hon'] <= 3:
                    wf['policy_skip◎4+'].append((k, *per[n][k]))
            if k in per[best_overall]:
                wf['fixed_train_best'].append((k, *per[best_overall][k]))
            for fixed in ('馬連BOX3＋ワイド◎流し4(7点)', '今週の混成型(S型7点)', '複勝◎'):
                if k in per[fixed]:
                    wf[fixed].append((k, *per[fixed][k]))
    print("\n■ 検証1 時系列ウォークフォワード（それまでの日だけで選び、翌日に当てる。評価は後半"
          f"{len(dates) - 6}日）")
    for label, lst in wf.items():
        q = quick(lst)
        s = SB.metrics(lst)
        print(f"  {label:<34s} {fmt(q)}  95%区間[{s['lo']*100:.0f}〜{s['hi']*100:.0f}%]")
        report[f"WF|{label}"] = q
    pol = {k: (i, r) for k, i, r in wf['policy']}
    for other in ('fixed_train_best', '馬連BOX3＋ワイド◎流し4(7点)', '今週の混成型(S型7点)', '複勝◎'):
        o = {k: (i, r) for k, i, r in wf[other]}
        d, lo, hi, n = paired_diff(pol, o, list(pol))
        print(f"  差（区分別に選ぶ − {other}）: {d*100:+.1f}pt  95%区間[{lo*100:+.0f}〜{hi*100:+.0f}pt]（{n}レース）")
    print("  各日の選択: " + " ／ ".join(f"{p['test_date'][4:]}:" + ",".join(f"{s}={v[:10]}" for s, v in sorted(p['pick'].items())) for p in picks_log[-2:]))

    # ── 検証2: 2分割の入れ替え ─────────────────────────────
    half = dates[:len(dates) // 2], dates[len(dates) // 2:]
    print("\n■ 検証2 2分割の入れ替え（片方で選び、もう片方に当てる）")
    for a, b, label in ((half[0], half[1], '前半で選ぶ→後半'), (half[1], half[0], '後半で選ぶ→前半')):
        train = [k for k in feats if k[0] in a]; test = [k for k in feats if k[0] in b]
        pick, best_overall = choose_on(train, feats, per, base_names)
        lst = [(k, *per[pick.get(seg_of(feats[k]), best_overall)][k]) for k in test if k in per[pick.get(seg_of(feats[k]), best_overall)]]
        fixed = [(k, *per[best_overall][k]) for k in test if k in per[best_overall]]
        q, qf = quick(lst), quick(fixed)
        print(f"  {label}: 区分別に選ぶ {fmt(q)}")
        print(f"  {'':<14s}固定（学習側の最良 {best_overall}） {fmt(qf)}")
        report[f"SPLIT|{label}|policy"] = q; report[f"SPLIT|{label}|fixed"] = qf

    # ── 検証3: 見送りルール ─────────────────────────────────
    print("\n■ 検証3 見送りルール（全期間・固定の買い方に適用。見送りは投資0）")
    rules = {
        'すべて買う': lambda f: True,
        '◎が1-3番人気のときだけ': lambda f: f['hon'] <= 3,
        '◎が1-3番人気かつ○が1-3番人気': lambda f: f['hon'] <= 3 and f['tai'] <= 3,
        '◎が1番人気のときだけ': lambda f: f['hon'] == 1,
        '15頭以上のときだけ': lambda f: f['n'] >= 15,
    }
    for n in ('馬連BOX3(◎○▲)', '馬連BOX3＋ワイド◎流し4(7点)', '今週の混成型(S型7点)', '馬連◎流し(相手4)'):
        for rn, rf in rules.items():
            lst = [(k, *per[n][k]) for k in per[n] if rf(feats[k])]
            q = quick(lst)
            print(f"  {n[:24]:<26s}{rn:<24s} {fmt(q)}")
            report[f"SKIP|{n}|{rn}"] = q

    # ── 検証4: 旧ガードを足すと得か損か ──────────────────────
    print("\n■ 検証4 旧ガードを足した場合（全期間・同じレースで比較。差の95%区間つき）")
    for bname in BASES_FOR_GUARD:
        for g in GUARD:
            gn = f"{bname}+{g}"
            d, lo, hi, n = paired_diff(per[gn], per[bname], list(per[bname]))
            qa, qb = quick([(k, *per[gn][k]) for k in per[gn]]), quick([(k, *per[bname][k]) for k in per[bname]])
            print(f"  {bname[:24]:<26s}+{g:<10s} 回収率差{d*100:+5.1f}pt [{lo*100:+.0f}〜{hi*100:+.0f}]"
                  f" ／ 上位1除外 {qb['ex1']*100:.0f}%→{qa['ex1']*100:.0f}% ／ 的中 {qb['hit']*100:.0f}%→{qa['hit']*100:.0f}%")
            report[f"GUARD|{gn}"] = {'diff': d, 'lo': lo, 'hi': hi, 'ex1_before': qb['ex1'], 'ex1_after': qa['ex1'], 'hit_before': qb['hit'], 'hit_after': qa['hit']}

    # ── 検証5: 配分方法 ─────────────────────────────────────
    print("\n■ 検証5 配分方法（全期間）")
    for n in ('馬連BOX3(◎○▲)', '馬連BOX3＋ワイド◎流し4(7点)', '今週の混成型(S型7点)', '馬連◎流し(相手4)', '3連複◎軸流し(相手5・10点)'):
        for alloc in ('flat', 'sqrt', 'even', 'even_cap30'):
            pa = run_alloc(races, n, alloc, marks_cache)
            q = quick([(k, *pa[k]) for k in pa])
            print(f"  {n[:24]:<26s}{alloc:<11s} {fmt(q)}")
            report[f"ALLOC|{n}|{alloc}"] = q

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({'report': report, 'picks': picks_log}, open(OUT / 'policy_validation_20260911.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1, default=str)
    print(f"\nsaved {OUT / 'policy_validation_20260911.json'}")


if __name__ == '__main__':
    main()
