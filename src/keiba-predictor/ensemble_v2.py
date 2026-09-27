# -*- coding: utf-8 -*-
"""
ensemble_v2.py — インフルエンサー合算 v2（SKILL.md「インフルエンサー合算 v2」準拠）の再採点ユーティリティ

入力: 20因子スコア{馬番: 点} と ソース別シグナル [(ソース名, 馬番, 種別), ...]
  種別: 'honmei'(本命+3) / 'ana'(穴・高評価+2) / 'posi'(ポジ言及+1) / 'nega'(ネガ・消し-2) / 'oikiri1'(追い切り1位 → 最低保証の判定のみ)
処理: 補正点×ソース重み → 合算点 = 20因子 + Σ補正
      最低保証: 本命 or 追切1位 が2ソース以上重なった馬は最低△（買い目の紐に必ず）
      プレミアム: 1ソースでも 'premium' 指定があれば紐1点
出力: 合算ランキング・保証フラグ・ソース別内訳
"""
from collections import defaultdict

WEIGHT = {
    'アジフライ777': 1.5,
    '競馬全レース予想TV': 1.2, '情報通のウマ談義': 1.2, 'しろクロ競馬': 1.2,
    'SPAIA': 0.8, 'SPAIA競馬ch': 0.8, '義英真': 0.8,
}
POINT = {'honmei': 3, 'ana': 2, 'posi': 1, 'nega': -2, 'oikiri1': 0, 'premium': 2}


def weight(src):
    for k, w in WEIGHT.items():
        if k in src:
            return w
    return 1.0


def ensemble(sc20, signals, names):
    """sc20={num:pts}, signals=[(src,num,kind)], names={num:name} → dict"""
    adj = defaultdict(float); detail = defaultdict(list)
    honmei_src = defaultdict(set); oik_src = defaultdict(set); prem = defaultdict(set); nega_src = defaultdict(set)
    for src, num, kind in signals:
        w = weight(src); pts = POINT.get(kind, 0) * w
        adj[num] += pts; detail[num].append(f"{src}:{kind}{pts:+.1f}")
        if kind == 'honmei': honmei_src[num].add(src)
        if kind == 'oikiri1': oik_src[num].add(src)
        if kind == 'premium': prem[num].add(src)
        if kind == 'nega': nega_src[num].add(src)
    rows = []
    for num in names:
        base = sc20.get(num, 0); total = base + adj[num]
        guar = len(honmei_src[num] | oik_src[num]) >= 2
        rows.append({'num': num, 'name': names[num], 'base': base, 'adj': round(adj[num], 1), 'total': round(total, 1),
                     'min_delta': guar, 'premium': bool(prem[num]), 'honmei': sorted(honmei_src[num]),
                     'oikiri1': sorted(oik_src[num]), 'nega': sorted(nega_src[num]), 'detail': detail[num]})
    rows.sort(key=lambda r: -r['total'])
    return rows


def print_rows(rows):
    for i, r in enumerate(rows, 1):
        flags = ("【最低保証△】" if r['min_delta'] else "") + ("【プレミアム紐】" if r['premium'] else "")
        print(f"{i:>2}. {r['num']:>2} {r['name']:<12} 合算{r['total']:>6} (基礎{r['base']:>3} 補正{r['adj']:+5.1f}) {flags} 本命={len(r['honmei'])} 追切1位={len(r['oikiri1'])} ネガ={len(r['nega'])}")
        if r['detail']:
            print("      " + " / ".join(r['detail']))
