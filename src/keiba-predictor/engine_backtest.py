# -*- coding: utf-8 -*-
"""
engine_backtest.py — 買い目エンジン全体のバックテスト（2026-09-02 新規）
========================================================================
これまでの検証（ev_calibration.py）は「候補点をフラットに賭けたら」という
仮想的な買い方での評価だった。本スクリプトは **エンジンが実際に選んだ買い目**
（choose_pattern が返す3.2点前後の構成・配分金額込み）を確定払戻に当てて、
本物の回収率を出す。

測るもの:
  ① payout_correction の有無でエンジンの成績が変わるか
  ② EV_MIN（現行1.15）を動かすと成績がどう変わるか ← 保留中の判断材料
  ③ 単純ルール（◎○▲3連複1点 等）と比べてエンジンに価値があるか

注意:
  - サンプルは497レースと少なく、3連単系の分散が大きい。
    ROIの誤差は大きいので **ブートストラップ信頼区間を必ず併記** する。
  - 補正係数はこの497レースを含む期間で作られている。
    そのため train/valid 分割の結果を主に見ること。
  - 大衆確率qは確定単勝オッズから作る（＝実オッズを渡した想定。
    払戻補正の較正条件と一致させるため）。

使い方:
  python engine_backtest.py
  python engine_backtest.py --budget 10000 --boot 2000
"""
from __future__ import annotations
import argparse, collections, json, random, statistics, sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import payout_correction
import style_correction
import gen_kaime_v5 as G

# 印は AI予測順位 の純粋な関数（346レース全件で確認: ◎=1位 ○=2位 ▲=3位 △=4,5位 無印=6位以下）。
# よって脚質補正で順位が変われば印も変わり、買い目構成が丸ごと変わる。
# 実運用（gen_digest_sns / flat_race_rules 経由）を再現するには印の再付与まで含める必要がある。
RANK_TO_MARK = {1: '◎', 2: '○', 3: '▲', 4: '△', 5: '△'}


def styled(recs: list) -> list:
    """脚質補正を当てた records のコピーを返す（順位の振り直しと印の再付与まで行う）。"""
    cp = [dict(r) for r in recs]
    style_correction.apply_style_correction(cp, enabled=True)
    for r in cp:
        r['AI印'] = RANK_TO_MARK.get(r.get('AI予測順位'), '')
    return cp

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
DB = BASE / 'daily_pdca' / 'db'


def payout_for(btype, nums, pay, top3):
    """その買い目の実払戻（円/100円）。当たっていなければ0、券種が無ければNone。"""
    rows = pay.get(btype)
    if not rows:
        return None
    s = set(nums)
    if btype == '単勝':
        return rows[0]['yen'] if nums[0] == top3[0] else 0
    if btype == '複勝':
        for x in rows:
            if x['combo'] == nums[0]:
                return x['yen']
        return 0
    if btype == '馬連':
        return rows[0]['yen'] if s == set(top3[:2]) else 0
    if btype == '馬単':
        return rows[0]['yen'] if list(nums) == top3[:2] else 0
    if btype == 'ワイド':
        if not s <= set(top3):
            return 0
        for x in rows:
            if set(x['combo'].split('-')) == s:
                return x['yen']
        return 0
    if btype == '3連複':
        return rows[0]['yen'] if s == set(top3) else 0
    if btype == '3連単':
        return rows[0]['yen'] if list(nums) == top3 else 0
    return None


def load_races():
    """(key -> dict(recs, odds, top3, payouts)) を作る。"""
    payouts = json.loads((DB / 'payouts.json').read_text(encoding='utf-8'))
    res = json.loads((DB / 'race_results.json').read_text(encoding='utf-8'))
    res_by = collections.defaultdict(list)
    for r in res:
        res_by[(r['date'], r['競馬場'], int(r['R']))].append(r)

    pre = {}
    global PROVENANCE
    PROVENANCE = {}
    for f in sorted(BASE.glob('**/週末ビッグデータ_*_records.json')):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        recs_in = d.get('records', [])
        if not recs_in:
            continue
        # 素性判定: ファイルの更新時刻が「収録レースの最終日」より後なら
        # レース後に再構築されたもの（バックフィル）＝結果リークの疑い
        import datetime
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).date()
        last_race = max(r['date'] for r in recs_in)
        last_race_d = datetime.date(int(last_race[:4]), int(last_race[4:6]), int(last_race[6:8]))
        backfilled = mtime > last_race_d
        for r in recs_in:
            key = (r['date'], r['競馬場'], int(r['R']))
            pre.setdefault(key, []).append(r)
            PROVENANCE[key] = {'file': f.name, 'mtime': mtime, 'backfilled': backfilled}

    out = {}
    for rid, v in payouts.items():
        key = (v['date'], v['venue'], v['R'])
        recs = pre.get(key)
        rows = res_by.get(key)
        if not recs or not rows or len(recs) < 8:
            continue
        odds, fin = {}, []
        for r in rows:
            try:
                num = str(int(float(r['馬番'])))
                o = float(r['単勝オッズ'])
            except (TypeError, ValueError):
                continue
            odds[num] = o
            if r.get('着順int'):
                fin.append((num, r['着順int']))
        if len(fin) < 3:
            continue
        fin.sort(key=lambda x: x[1])
        top3 = [fin[0][0], fin[1][0], fin[2][0]]
        # recs の馬番がオッズ表に揃っているか
        if not all(str(r.get('馬番')) in odds for r in recs):
            continue
        out[key] = {'recs': recs, 'odds': odds, 'top3': top3, 'pay': v['payouts']}
    return out


# ── 結果リーク検出（2026-09-02）───────────────────────────────────
# 【原因】2026-08-31に走らせた backfill_records.py が生成した records は、
# レース後のデータを使って印を付け直しており、事前予測ではない。
# 該当ファイル（5/16, 5/17, 5/23, 5/24, 5/30, 7/26）は全て mtime が 08/31。
# 症状: ◎の3着内率が55〜86%（本物は29〜54%）。市場の1番人気成績は同期間で正常
# なので、レースが簡単だったのではなくデータが汚染されている。
#
# 【判定方法】統計的なしきい値ではなく **ファイルの素性** で判定する。
# ファイル更新時刻 > 収録レースの最終日 → レース後に作られた ＝ 除外。
# しきい値方式だと7/26（◎3着内55.9%）のように汚染ファイルがすり抜ける。
LEAK_THRESHOLD = 0.60      # 参考表示用（判定には使わない）
PROVENANCE: dict = {}      # key -> {file, mtime, backfilled}


def leak_scan(races: dict) -> dict:
    """日別の ◎3着内率 と 1番人気1着率 を返す。"""
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])   # ◎あり, ◎3着内, R, 1番人気1着
    for (d, _v, _r), info in races.items():
        recs, top3 = info['recs'], info['top3']
        a = agg[d]
        a[2] += 1
        hon = [str(x['馬番']) for x in recs if x.get('AI印') == '◎']
        if hon:
            a[0] += 1
            if hon[0] in top3:
                a[1] += 1
        fav = min(info['odds'], key=lambda k: info['odds'][k])
        if fav == top3[0]:
            a[3] += 1
    return {d: {'hon_rate': a[1] / a[0] if a[0] else 0.0,
                'fav_rate': a[3] / a[2] if a[2] else 0.0,
                'races': a[2]} for d, a in agg.items()}


def drop_leaky(races: dict, verbose: bool = True):
    """レース後に作られた records（バックフィル産）を除外する。"""
    scan = leak_scan(races)
    bad_keys = {k for k in races if PROVENANCE.get(k, {}).get('backfilled')}
    bad_days = sorted({k[0] for k in bad_keys})
    if verbose and bad_days:
        print()
        print("⚠ レース後に作られた records（結果リーク）のため除外:")
        print(f"   {'日付':>10s} {'R':>4s} {'◎3着内':>8s} {'1番人気1着':>10s}  生成ファイル(更新日)")
        for d in bad_days:
            s = scan.get(d, {})
            k = next(k for k in bad_keys if k[0] == d)
            pv = PROVENANCE[k]
            print(f"   {d:>10s} {s.get('races',0):4d} {100*s.get('hon_rate',0):7.1f}% "
                  f"{100*s.get('fav_rate',0):9.1f}%  {pv['file'][:34]} ({pv['mtime']})")
        print("   ※1番人気1着率が正常なのに◎だけ突出＝レースが簡単だったのではない")
    return {k: v for k, v in races.items() if k not in bad_keys}


def run_engine(races, budget, ev_min, corrected, style=False, marks=True):
    """条件を1つ指定してエンジンを走らせ、レースごとの (投資, 払戻) を返す。

    style=True で脚質補正v6.0を適用する。
    marks=False にすると総合指数だけ補正して印は元のまま（効果の分解用）。
    """
    old_ev, old_en = G.EV_MIN, payout_correction.ENABLED
    G.EV_MIN = ev_min
    payout_correction.ENABLED = corrected
    per_race = []
    try:
        for key, d in races.items():
            recs = d['recs']
            if style:
                recs = [dict(r) for r in recs]
                style_correction.apply_style_correction(recs, enabled=True)
                if marks:
                    for r in recs:
                        r['AI印'] = RANK_TO_MARK.get(r.get('AI予測順位'), '')
            try:
                out = G.choose_pattern(recs, budget, odds_override=d['odds'])
            except Exception:
                continue
            name, res = out[0], out[2]
            if not name or not res:
                per_race.append((key, 0, 0))     # 見送り
                continue
            inv = ret = 0
            for btype, idxs, amount, _odds in res['bets']:
                nums = [str(recs[i]['馬番']) for i in idxs]
                yen = payout_for(btype, nums, d['pay'], d['top3'])
                if yen is None:
                    continue
                inv += amount
                ret += amount * yen / 100.0
            per_race.append((key, inv, ret))
    finally:
        G.EV_MIN, payout_correction.ENABLED = old_ev, old_en
    return per_race


def run_engine_types(races, budget, allow: set | None, style=True):
    """券種を制限してエンジンを走らせる（2026-09-02・②券種構成の検証）。

    エンジンが出す ranking（全パターンを評価順に並べたもの）から、
    許可券種だけで構成されるパターンの最上位を選ぶ。
    allow=None なら制限なし＝現行と同じ。
    どのパターンも通らなければ見送り扱い。

    背景: 券種ごとの無スキル基準線は ワイド76.7% > 3連複71.7% > 馬連70.9% > 3連単67.5%。
    エンジンは3連複・3連単中心なので、不利な券種に寄っている可能性を検証する。
    """
    per_race = []
    for key, d in races.items():
        recs = d['recs']
        if style:
            recs = [dict(r) for r in recs]
            style_correction.apply_style_correction(recs, enabled=True)
            for r in recs:
                r['AI印'] = RANK_TO_MARK.get(r.get('AI予測順位'), '')
        try:
            out = G.choose_pattern(recs, budget, odds_override=d['odds'])
        except Exception:
            continue
        ranking = out[3] or []
        pick = None
        for _name, _desc, res in ranking:
            types = {bt for bt, _i, _a, _o in res['bets']}
            if allow is None or types <= allow:
                pick = res
                break
        if pick is None:
            per_race.append((key, 0, 0))
            continue
        inv = ret = 0
        for btype, idxs, amount, _odds in pick['bets']:
            nums = [str(recs[i]['馬番']) for i in idxs]
            yen = payout_for(btype, nums, d['pay'], d['top3'])
            if yen is None:
                continue
            inv += amount
            ret += amount * yen / 100.0
        per_race.append((key, inv, ret))
    return per_race


def simple_rule(races, budget, rule):
    """比較用の単純ルール。"""
    per_race = []
    for key, d in races.items():
        recs = d['recs']
        marks = {r.get('AI印'): str(r['馬番']) for r in recs if r.get('AI印') in ('◎', '○', '▲')}
        if rule == '◎○▲3連複':
            need = ('◎', '○', '▲')
            if not all(m in marks for m in need):
                per_race.append((key, 0, 0)); continue
            bt, nums = '3連複', [marks[m] for m in need]
        elif rule == '◎○ワイド':
            if not all(m in marks for m in ('◎', '○')):
                per_race.append((key, 0, 0)); continue
            bt, nums = 'ワイド', [marks['◎'], marks['○']]
        elif rule == '◎単勝':
            if '◎' not in marks:
                per_race.append((key, 0, 0)); continue
            bt, nums = '単勝', [marks['◎']]
        else:
            raise ValueError(rule)
        yen = payout_for(bt, nums, d['pay'], d['top3'])
        if yen is None:
            per_race.append((key, 0, 0)); continue
        per_race.append((key, budget, budget * yen / 100.0))
    return per_race


def summarize(per_race, boot=2000, seed=42):
    """ROIとブートストラップ95%信頼区間。レース単位でリサンプルする。"""
    act = [(i, r) for _, i, r in per_race if i > 0]
    if not act:
        return None
    inv = sum(i for i, _ in act)
    ret = sum(r for _, r in act)
    roi = ret / inv
    hit = sum(1 for _, r in act if r > 0) / len(act)
    rng = random.Random(seed)
    rois = []
    for _ in range(boot):
        smp = [act[rng.randrange(len(act))] for _ in range(len(act))]
        si = sum(i for i, _ in smp)
        if si > 0:
            rois.append(sum(r for _, r in smp) / si)
    rois.sort()
    lo = rois[int(0.025 * len(rois))] if rois else roi
    hi = rois[int(0.975 * len(rois))] if rois else roi
    return {'races': len(act), 'inv': inv, 'ret': ret, 'roi': roi,
            'hit': hit, 'lo': lo, 'hi': hi,
            'skip': sum(1 for _, i, _ in per_race if i == 0)}


def row(label, s):
    if not s:
        print(f"{label:>26s}   —")
        return
    print(f"{label:>26s} {s['races']:6d} {s['skip']:6d} {100*s['hit']:7.1f}% "
          f"{100*s['roi']:9.1f}%   [{100*s['lo']:.0f}〜{100*s['hi']:.0f}%]")


def header(title):
    print()
    print("=" * 100)
    print("■ " + title)
    print("=" * 100)
    print(f"{'条件':>26s} {'買った':>6s} {'見送':>6s} {'的中率':>8s} {'回収率':>10s}   95%信頼区間")
    print("-" * 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--budget', type=int, default=10000)
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--keep-leaky', action='store_true',
                    help='リーク疑いの日を除外せずに含める（比較検証用）')
    args = ap.parse_args()

    races = load_races()
    n0 = len(races)
    if not args.keep_leaky:
        races = drop_leaky(races)
        print(f"\n除外後: {len(races)}レース（除外前 {n0}）")
    dates = sorted({k[0] for k in races})
    half = len(dates) // 2
    tr_d, va_d = set(dates[:half]), set(dates[half:])
    tr = {k: v for k, v in races.items() if k[0] in tr_d}
    va = {k: v for k, v in races.items() if k[0] in va_d}

    print(f"対象: {len(races)}レース / {len(dates)}日  "
          f"(train {len(tr)}レース {len(tr_d)}日 / valid {len(va)}レース {len(va_d)}日)")
    print(f"予算: 1レース{args.budget:,}円  大衆確率qは確定単勝オッズから生成")

    for scope, label in ((races, "全期間"), (va, "valid のみ（補正の較正に使っていない後半）")):
        header(f"⭐脚質補正v6.0のエンジンへの効果 [{label}]  ※これが本番の運用状態")
        for style, marks, lab in (
                (False, True,  "脚質補正なし（=これまで測っていた状態）"),
                (True,  False, "脚質補正あり・印は据え置き（pだけ変わる）"),
                (True,  True,  "脚質補正あり・印も再付与（★本番と同じ）")):
            s = summarize(run_engine(scope, args.budget, 1.15, True, style, marks), args.boot)
            row(lab, s)

        header(f"払戻補正の効果 [{label}]  ※EV_MINは現行1.15・脚質補正は本番と同じON")
        for corrected in (False, True):
            s = summarize(run_engine(scope, args.budget, 1.15, corrected, True, True), args.boot)
            row("払戻補正あり" if corrected else "払戻補正なし", s)

        header(f"EV_MIN を動かす [{label}]  ※補正あり")
        for ev in (0.0, 1.00, 1.15, 1.30, 1.50, 2.00):
            s = summarize(run_engine(scope, args.budget, ev, True), args.boot)
            row(f"EV_MIN={ev:.2f}" + ("  ← 現行" if abs(ev - 1.15) < 1e-6 else ""), s)

        header(f"⭐券種構成を変える [{label}]  ※脚質補正ON・EV_MIN1.15")
        ALL = {'単勝', '複勝', '馬連', 'ワイド', '馬単', '3連複', '3連単'}
        for allow, lab in (
                (None,                              "現行（全券種）"),
                (ALL - {'3連単'},                    "3連単を除く"),
                (ALL - {'3連単', '馬単'},             "3連単・馬単を除く"),
                ({'ワイド', '馬連', '3連複'},          "ワイド・馬連・3連複のみ"),
                ({'ワイド', '馬連'},                  "ワイド・馬連のみ"),
                ({'ワイド'},                         "ワイドのみ"),
                (ALL - {'3連複'},                    "3連複を除く（対照）")):
            s = summarize(run_engine_types(scope, args.budget, allow), args.boot)
            row(lab, s)

        header(f"単純ルールとの比較 [{label}]  ※1レース1点だけ買う")
        for rule in ('◎○▲3連複', '◎○ワイド', '◎単勝'):
            s = summarize(simple_rule(scope, args.budget, rule), args.boot)
            row(rule, s)

    print()
    print("【読み方】信頼区間が100%をまたぐ条件は「勝てるとは言えない」。")
    print("　条件間の差も、区間が大きく重なっていれば差があるとは言えない。")


if __name__ == '__main__':
    main()
