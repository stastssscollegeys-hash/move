# -*- coding: utf-8 -*-
"""
review_weekend.py — 週末に公開した買い目の答え合わせ（2026-09-16 新規）
========================================================================
review_20260912.py（9/12専用・買い目を手で転記）を汎用化したもの。
その週に公開した SNS投稿案 docx から買い目・印をそのまま読み取り、確定払戻
（payouts.json）と突き合わせて、投資・払戻・回収率・印の来方を出す。

読む成果物（レース前に作ったもの）:
  {日付フォルダ}/週末自信度7以上_SNS投稿案.docx   （gen_digest_sns.py 出力・平場）
  {週フォルダ}/research/kaime_*.json              （kaime_*.py 出力・重賞/ルールR1）

さらに「同じ印で買い方だけ変えたらどうだったか」を、確定払戻の実額で比較する。
手で転記しないので、翌週以降もそのまま使える。

使い方:
  python review_weekend.py --dates 20260912 20260913
  python review_weekend.py --dates 20260913 --no-alt     # 買い方比較を省く
"""
from __future__ import annotations
import argparse, collections, glob, json, re, sys, io
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = Path.home() / 'Desktop' / '競馬予想レポート'
DB = BASE / 'daily_pdca' / 'db'

CIRCLED = {chr(0x2460 + i): i + 1 for i in range(20)}
TICKETS = ('単勝', '複勝', '枠連', '馬連', 'ワイド', '馬単', '3連複', '3連単')


def num(tok: str) -> int | None:
    if tok in CIRCLED:
        return CIRCLED[tok]
    return int(tok) if tok.isdigit() else None


def nums(s: str) -> list[int]:
    out = [num(c) for c in s if c in CIRCLED or c.isdigit()]
    return [x for x in out if x]


# ── 公開した買い目を docx から読む ───────────────────────────────
def parse_digest(day: str) -> dict:
    """{(競馬場, R): {budget, marks, bets}} を返す。スレッド本文をそのまま読む。"""
    from docx import Document
    f = BASE / day / '週末自信度7以上_SNS投稿案.docx'
    if not f.exists():
        return {}
    ps = [p.text for p in Document(str(f)).paragraphs if p.text.strip()]
    out = {}
    for i, t in enumerate(ps):
        m = re.match(r'スレッド\d+/\d+:\s*(\S+?)(\d+)R\s', t)
        if not m or i + 1 >= len(ps):
            continue
        venue, R = m.group(1), int(m.group(2))
        marks, bets, ticket = {}, [], None
        for line in ps[i + 1].splitlines():
            line = line.strip()
            mk = re.match(r'^(◎|○|▲|△|🔥穴)\s*([①-⑳])', line)
            if mk:
                k, v = mk.group(1), CIRCLED[mk.group(2)]
                if k in ('△', '🔥穴'):
                    marks.setdefault(k, []).append(v)
                else:
                    marks[k] = v
                continue
            tk = re.match(r'^【(%s)】' % '|'.join(TICKETS), line)
            if tk:
                ticket = tk.group(1)
                # 1点だけの券種は見出し行に直接書かれる: 【ワイド】⑫-⑬ 4,000円（1点）
                one = re.search(r'([①-⑳\d]+(?:\s*[-→]\s*[①-⑳\d]+)+)\s+([\d,]+)円（1点）$', line)
                if one:
                    combo = [num(x.strip()) for x in re.split(r'[-→]', one.group(1))]
                    if all(combo):
                        bets.append((ticket, tuple(combo), int(one.group(2).replace(',', ''))))
                continue
            bt = re.match(r'^([①-⑳\d]+(?:\s*[-→]\s*[①-⑳\d]+)+)\s+([\d,]+)円$', line)
            if bt and ticket:
                combo = [num(x.strip()) for x in re.split(r'[-→]', bt.group(1))]
                if all(combo):
                    bets.append((ticket, tuple(combo), int(bt.group(2).replace(',', ''))))
        if bets:
            out[(venue, R)] = dict(budget=sum(b[2] for b in bets), marks=marks, bets=bets, day=day)
    return out


def parse_kaime(day: str, rname: dict | None = None) -> dict:
    """重賞側（kaime_*.json）。見送りは budget=0 で入れる。
    旧形式（kaime_{日付}*.json・bets に combo を持つ）と、
    新形式（kaime_mixed.py 出力・race/marks/design を持ち日付を含まない）の両方を読む。
    新形式はファイル名に日付が無いので、レース名がその日の結果にあるものだけ採る。"""
    out = {}
    for f in sorted(glob.glob(str(BASE / '**' / 'research' / f'kaime_{day}*.json'), recursive=True)):
        for name, k in json.load(open(f, encoding='utf-8')).items():
            out[name] = dict(budget=k['budget'], marks=k['marks'], pattern=k['pattern'],
                             bets=[(b['t'], tuple(b['combo']), b['amt']) for b in k['bets']], day=day)
    if rname is None:
        return out
    titles = [v for v in rname.values() if v]
    for f in sorted(glob.glob(str(BASE / '**' / 'research' / 'kaime_*.json'), recursive=True)):
        k = json.load(open(f, encoding='utf-8'))
        if not (isinstance(k, dict) and 'design' in k and 'race' in k):
            continue
        name = k['race']
        stem = name.replace('S', '').replace('ステークス', '')
        if not any(stem and stem in t for t in titles):
            continue                                   # その日のレースではない
        d = k['design']
        if name in out:
            continue
        out[name] = dict(budget=d.get('budget', 0), marks=k.get('marks', {}),
                         pattern=d.get('arch', '混合型 ◎は指数・相手は人気上位'),
                         bets=[(b['t'], tuple(sorted((d['hon'], b['u']))), b['amt'])
                               for b in d.get('bets', [])], day=day)
    return out


# ── 結果・払戻 ───────────────────────────────────────────────────
def load_day(day: str):
    pays = json.load(open(DB / 'payouts.json', encoding='utf-8'))
    res = json.load(open(DB / 'race_results.json', encoding='utf-8'))
    P = {(v['venue'], int(v['R'])): v for v in pays.values() if v.get('date') == day}
    fin = collections.defaultdict(dict)
    name = {}
    for r in res:
        if r.get('date') != day:
            continue
        key = (r['競馬場'], int(r['R']))
        name[key] = r.get('レース名')
        try:
            fin[key][int(float(r['馬番']))] = (r.get('着順int') or 99, float(r['単勝オッズ']),
                                              int(float(r.get('人気') or 99)), r.get('馬名'))
        except (TypeError, ValueError):
            continue
    return P, fin, name


def payout_of(pay, t, combo):
    rows = pay['payouts'].get(t) if pay else None
    if rows is None:
        return None
    want = sorted(int(x) for x in combo)
    for x in rows:
        got = [int(v) for v in x['combo'].split('-')]
        if t in ('馬単', '3連単'):
            if got == list(combo):
                return x['yen']
        elif sorted(got) == want:
            return x['yen']
    return 0


def show(title, d, pay, fr):
    print(f"\n■ {title}（投資{d['budget']:,}円）")
    if fr:
        top3 = sorted([(v[0], u) for u, v in fr.items() if v[0] <= 3])
        print("  結果: " + " ".join(f"{r}着{u}番{fr[u][3]}({fr[u][2]}人気)" for r, u in top3))
        line = []
        for k in ('◎', '○', '▲', '△', '🔥穴'):
            if k not in d['marks']:
                continue
            for u in (d['marks'][k] if isinstance(d['marks'][k], list) else [d['marks'][k]]):
                v = fr.get(int(u))
                line.append(f"{k}{u}={v[0] if v and v[0] < 99 else '−'}着" if v else f"{k}{u}=取消")
        print("  印: " + " ".join(line))
    ret = 0
    for t, combo, amt in d['bets']:
        y = payout_of(pay, t, combo)
        r = amt * y / 100 if y else 0
        ret += r
        print(f"  {t} {'-'.join(map(str, combo))} {amt:,}円 → " +
              (f"的中 {int(r):,}円" if r else ('ハズレ' if y is not None else '券種データなし')))
    if d['budget']:
        print(f"  → 払戻 {int(ret):,}円 ／ 回収率 {ret/d['budget']*100:.0f}%")
    else:
        print("  → 見送り（投資0円）")
    return d['budget'], ret


# ── 同じ印で買い方だけ変えたら ───────────────────────────────────
def alt_structures(marks: dict) -> dict:
    m = {'◎': marks.get('◎'), '○': marks.get('○'), '▲': marks.get('▲')}
    an = (marks.get('🔥穴') or [None])[0]
    dd = marks.get('△') or []
    if not all((m['◎'], m['○'], m['▲'])):
        return {}
    o = [m['◎'], m['○'], m['▲']]
    s = {
        '単勝◎': [('単勝', (m['◎'],))],
        '複勝◎': [('複勝', (m['◎'],))],
        '馬連◎-○': [('馬連', (m['◎'], m['○']))],
        'ワイド◎-○': [('ワイド', (m['◎'], m['○']))],
        '馬連BOX3(◎○▲)': [('馬連', c) for c in combinations(o, 2)],
        'ワイドBOX3(◎○▲)': [('ワイド', c) for c in combinations(o, 2)],
        '3連複◎○▲(1点)': [('3連複', tuple(o))],
    }
    if dd:
        rel = [m['○'], m['▲']] + dd[:2]
        s['馬連◎流し(相手4)'] = [('馬連', (m['◎'], k)) for k in rel]
        s['ワイド◎流し(相手4)'] = [('ワイド', (m['◎'], k)) for k in rel]
        s['3連複◎軸流し(相手4・6点)'] = [('3連複', (m['◎'], *c)) for c in combinations(rel, 2)]
    if an:
        s['ワイド穴軸(相手◎○)'] = [('ワイド', (an, m['◎'])), ('ワイド', (an, m['○']))]
        s['3連複◎○穴(1点)'] = [('3連複', (m['◎'], m['○'], an))]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', nargs='+', required=True)
    ap.add_argument('--no-alt', action='store_true')
    a = ap.parse_args()

    grand_inv = grand_ret = 0
    all_races = []           # (ラベル, marks, pay, fr)
    for day in a.dates:
        P, fin, rname = load_day(day)
        if not P:
            print(f'[WARN] payouts.json に {day} が無い（fetch_payouts.py --dates {day} を先に）')
            continue
        print("=" * 78)
        print(f"■ {day[:4]}/{day[4:6]}/{day[6:]} 公開した買い目の答え合わせ")
        print("=" * 78)
        inv_d = ret_d = 0
        for name, d in parse_kaime(day, rname).items():
            key = next((k for k in rname if rname[k] and name.replace('S', '').replace('ステークス', '') in rname[k]), None)
            if key is None:
                key = next((k for k in rname if rname[k] and rname[k].startswith(name[:4])), None)
            pay, fr = (P.get(key), fin.get(key)) if key else (None, None)
            i, r = show(f"{name}（重賞・ルールR1）", d, pay, fr)
            inv_d += i; ret_d += r
            if fr:
                all_races.append((f"{day} {name}", d['marks'], pay, fr))
        for (v, R), d in sorted(parse_digest(day).items()):
            i, r = show(f"{v}{R}R {rname.get((v, R), '')} ＝ 従来手順（自信度7以上）", d, P.get((v, R)), fin.get((v, R)))
            inv_d += i; ret_d += r
            if fin.get((v, R)):
                all_races.append((f"{day} {v}{R}R", d['marks'], P.get((v, R)), fin[(v, R)]))
        grand_inv += inv_d; grand_ret += ret_d
        print(f"\n  ◇ {day} 合計 投資{inv_d:,}円 → 払戻{int(ret_d):,}円"
              f"（回収率{ret_d/inv_d*100:.0f}%）" if inv_d else f"\n  ◇ {day} 投資なし")

        # 印の実績（全レース・エンジンではなく公開した印は上で見たので、ここは市場との比較）
        n = h1 = h3 = f1 = f3 = 0
        for key, fr in fin.items():
            fav = [u for u, v in fr.items() if v[2] == 1]
            if not fav:
                continue
            n += 1
            f1 += fr[fav[0]][0] == 1; f3 += fr[fav[0]][0] <= 3
        print(f"  ◇ {day} 市場1番人気: 1着 {f1}/{n}（{f1/n*100:.0f}%）／3着内 {f3}/{n}（{f3/n*100:.0f}%）")

    if grand_inv:
        print("\n" + "=" * 78)
        print(f"■ 週末合計 投資{grand_inv:,}円 → 払戻{int(grand_ret):,}円（回収率{grand_ret/grand_inv*100:.1f}%）")
        print("=" * 78)

    if a.no_alt or not all_races:
        return
    print("\n■ 同じ印のまま買い方だけ変えたら（公開した各レース・1レース1万円を各点に均等）")
    print(f"{'買い方':<26s}{'R':>4s}{'的中':>5s}{'投資':>10s}{'払戻':>12s}{'回収率':>8s}   内訳")
    agg = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, []])
    for label, marks, pay, fr in all_races:
        for sname, bets in alt_structures(marks).items():
            unit = 10000 / len(bets)
            got = 0.0
            ok = True
            for t, combo in bets:
                y = payout_of(pay, t, combo)
                if y is None:
                    ok = False; break
                got += unit * y / 100
            if not ok:
                continue
            a_ = agg[sname]
            a_[0] += 1; a_[1] += got > 0; a_[2] += 10000; a_[3] += got
            if got > 0:
                a_[4].append(f"{label.split()[-1]}{int(got):,}円")
    for sname, (R, hit, inv, ret, det) in sorted(agg.items(), key=lambda x: -x[1][3]):
        print(f"{sname:<26s}{R:>4d}{hit:>5d}{int(inv):>10,}{int(ret):>12,}{ret/inv*100:>7.0f}%   {' '.join(det[:4])}")
    print("\n※ 少数レースの比較なので順位は偶然に大きく動く。方針の決定は structure_backtest.py（全期間）で行うこと")


if __name__ == '__main__':
    main()
