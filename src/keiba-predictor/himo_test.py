import sys,collections,itertools
from pathlib import Path
import numpy as np
sys.path.insert(0,r"C:\Users\User\dev\move\src\keiba-predictor")
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import kaime_compose as K
from bet_structure_test import marks, pay_of
preds,pay=C.predictions(),C.load_pay()
S=collections.defaultdict(list)   # 戦略 -> [(賭け,払戻,年)]
n_races=0
def run(pp,t,combos):
    n=len(combos)
    if n==0: return None
    st=max(100,int(10000/n//100)*100)
    tot=st*n; ret=sum(st/100*pay_of(pp,t,list(c)) for c in combos)
    return tot,ret
for pr in preds:
    k=pr["key"]
    if int(k[0][:4])<2019: continue
    pp=pay.get(f"{k[0]}|{k[1]}|{k[2]}")
    if not pp or "3連複" not in pp or not pp["3連複"] or "3連単" not in pp or len(pr["uma"])<8: continue
    M,pop=marks(pr)
    if not all(x in M for x in ("◎","○","▲")): continue
    p=np.asarray(pr["p"],float); uma=list(pr["uma"]); p=p/p.sum()
    q=np.asarray(pr["q"],float); q=q/q.sum()
    y=k[0][:4]; n_races+=1
    a,b=M["◎"],M["○"]
    order=[uma[i] for i in np.argsort(-p) if uma[i] not in (a,b)]
    mk=[M[x] for x in ("▲","△1","△2","🔥") if x in M]
    def two_way(rest): return [(a,b,x) for x in rest]+[(b,a,x) for x in rest]
    cfg={}
    cfg["A 3連単マルチ・相手=印の4頭（現行）"]=("3連単",two_way(mk))
    cfg["B 3連単マルチ・相手=勝つ確率上位4頭"]=("3連単",two_way(order[:4]))
    cfg["C 3連単マルチ・相手=勝つ確率上位6頭"]=("3連単",two_way(order[:6]))
    un=list(dict.fromkeys(mk+order[:6]))[:6]
    cfg["D 3連単マルチ・相手=印4頭＋確率上位で6頭まで"]=("3連単",two_way(un))
    cfg["E 3連複 ◎○-相手 確率上位6頭（6点）"]=("3連複",[tuple(sorted((a,b,x))) for x in order[:6]])
    cfg["F 3連複 ◎○-相手 確率上位10頭（10点）"]=("3連複",[tuple(sorted((a,b,x))) for x in order[:10]])
    if "🔥" in M:
        f=M["🔥"]; core=[x for x in (a,b,M["▲"]) ]+[M[x] for x in ("△1","△2") if x in M]
        core=[x for x in core if x!=f]
        cfg["G 穴🔥軸の3連複・相手=印の馬から2頭組（印5頭→10点）"]=("3連複",[tuple(sorted((f,x,z))) for x,z in itertools.combinations(core,2)])
        wide=[u for u in order if u!=f][:6]
        cfg["H 穴🔥軸の3連複・相手=確率上位6頭から2頭組（15点）"]=("3連複",[tuple(sorted((f,x,z))) for x,z in itertools.combinations(wide,2)])
        cfg["I 穴🔥から3連複・🔥と◎○の3頭だけ（1点）"]=("3連複",[tuple(sorted((f,a,b)))])
    for nm,(t,cb) in cfg.items():
        r=run(pp,t,cb)
        if r: S[nm].append((r[0],r[1],y))
print("検証レース",n_races)
print("%-52s %7s %7s %-16s %6s"%("戦略","レース","回収率","95%区間","的中率"))
for nm in sorted(S):
    L=S[nm]; st=[x[0] for x in L]; rt=[x[1] for x in L]
    lo,hi=C.ci(st,rt); roi=sum(rt)/sum(st); hit=sum(1 for x in L if x[1]>0)/len(L)
    print("%-52s %7d %6.1f%% [%5.1f〜%5.1f] %5.1f%%"%(nm,len(L),roi*100,lo*100,hi*100,hit*100))
