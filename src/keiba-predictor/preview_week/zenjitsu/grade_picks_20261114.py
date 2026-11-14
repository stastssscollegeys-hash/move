# 公開した7レースの買い目（picks2の【買い目】）を確定払戻で照合する
import json, re, sys
TAG = sys.argv[1] if len(sys.argv) > 1 else ''
B = r'C:\Users\User\Desktop\競馬予想レポート'
CIR = {chr(0x2460+i): i+1 for i in range(20)}
KEY = {'fukushima6':'福島6','kyoto7':'京都7','fukushima10':'福島10','kyoto10':'京都10',
       'tokyo11':'東京11','kyoto11':'京都11','tokyo12':'東京12'}
p = json.load(open(B+r'\20261114\research\picks2_20261114'+TAG+'.json', encoding='utf-8'))
res = json.load(open(B+r'\daily_pdca\web_live\20261114_web_results.json', encoding='utf-8'))
out = []; T = R = 0
for k, rk in KEY.items():
    if k not in p: continue
    t = p[k]['x']; a = t.index('【買い目'); b = t.index('・どれか', a); sec = t[a:b]
    marks = {}
    for m in re.finditer(r'^([◎○▲△☆])\s*([⑴-⒇①-⑳])(\S+?)（', t[t.index('【印】'):a], re.M):
        marks[CIR[m.group(2)]] = (m.group(1), m.group(3))
    bets = [(tuple(sorted((CIR[x], CIR[y]))), int(amt.replace(',', '')))
            for x, y, amt in re.findall(r'([①-⑳])-([①-⑳])\s*([\d,]+)円', sec)]
    r = res[rk]; wide = {tuple(sorted(map(int, w['comb'].split('-')))): w['yen'] for w in r['pay']['ワイド']}
    top3 = [(row['rank'], row['uma'], row['name'], row['pop']) for row in r['rows'][:3]]
    cost = sum(x for _, x in bets); ret = 0; hits = []
    for c, amt in bets:
        if c in wide: ret += wide[c] * amt // 100; hits.append((c, amt, wide[c]))
    T += cost; R += ret
    mk = {u: marks.get(u, ('-',))[0] for _, u, _, _ in top3}
    out.append(dict(race=rk, cost=cost, ret=ret, hits=hits, top3=top3, marks_top3=mk,
                    marks={u: v[0] for u, v in marks.items()}))
    print(rk, f'{cost:,}→{ret:,}円', 'hit' if hits else '-', [f'{c[0]}-{c[1]} {amt}円×{y/100:.1f}倍' for c, amt, y in hits],
          '| 1-3着', [(u, n, f'{pp}人', mk[u]) for _, u, n, pp in top3])
print(f'合計 {T:,}→{R:,}円 回収{R/T*100:.1f}%')
json.dump(dict(races=out, total_cost=T, total_ret=R), open(B+r'\20261114\research\grade_picks_20261114'+TAG+'.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
