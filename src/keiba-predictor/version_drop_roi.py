# -*- coding: utf-8 -*-
"""version_drop_roi.py — 版が進んで印が消えた馬／増えた馬を、そのまま単勝・複勝で買った回収率（実払戻）。
対照＝同じレースで一度も印が付かなかった馬のうち、倍率が近い馬（消えた馬の倍率の0.5〜2倍）。2026-10-31新規"""
import json,glob,os,sys,random,statistics
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import day_review as DR
B=os.path.join(os.path.expanduser("~"),"Desktop","競馬予想レポート")
dates=["20261011","20261012","20261017","20261018","20261024","20261025","20261031"]
G={"消えた":[], "増えた":[], "対照":[]}
random.seed(1)
for d in dates:
    vs=sorted(glob.glob(os.path.join(B,d,"research","cards_versions","cards_%s_*.json"%d)),key=os.path.getmtime)
    last=os.path.join(B,d,"research","cards_%s.json"%d)
    rs,py=DR.load_day(d)
    fin={(r["競馬場"],r["R"],r["馬番"]):r["着順int"] for r in rs if r["着順int"]}
    Lm={(c["venue"],c["R"]):c for c in json.load(open(last,encoding="utf-8"))["cards"]}
    first={}
    for f in vs:
        for x in json.load(open(f,encoding="utf-8"))["cards"]: first.setdefault((x["venue"],x["R"]),x)
    for k,x in first.items():
        if k not in Lm or x["marks"]==Lm[k]["marks"]: continue
        y=Lm[k]; nm={h["uma"]:h for h in y["horses"]}; om={h["uma"] for h in x["horses"]}
        pk=py.get(k,{})
        def rec(g,u):
            f=fin.get((k[0],k[1],u))
            if f is None or u not in nm: return
            G[g].append(dict(d=d,k=k,u=u,odds=nm[u]["odds"],fin=f,tan=pk.get("単勝",{}).get((u,),0),fuku=pk.get("複勝",{}).get((u,),0),
                             trio=min([v for kk,v in pk.get("3連複",{}).items() if u in kk],default=0)))
        for u in x["marks"]:
            if u not in y["marks"]: rec("消えた",int(u))
        for u in y["marks"]:
            if u not in x["marks"]: rec("増えた",int(u))
        ever=set(map(int,x["marks"]))|set(map(int,y["marks"]))
        dropped=[nm[int(u)]["odds"] for u in x["marks"] if u not in y["marks"] and int(u) in nm]
        if dropped:
            lo,hi=min(dropped)*0.5,max(dropped)*2
            pool=[u for u,h in nm.items() if u not in ever and lo<=h["odds"]<=hi]
            for u in pool: rec("対照",u)
def boot(vals,n=4000):
    m=[]; 
    for _ in range(n): m.append(sum(random.choices(vals,k=len(vals)))/len(vals))
    m.sort(); return m[int(n*0.025)],m[int(n*0.975)]
print("%-4s %4s %6s %8s %-18s %8s %-18s"%("区分","頭数","3着内","単勝回収","95%区間","複勝回収","95%区間"))
for g,L in G.items():
    n=len(L)
    if not n: continue
    tv=[x["tan"]/100 for x in L]; fv=[x["fuku"]/100 for x in L]
    a=boot(tv); b=boot(fv)
    print("%-4s %4d %6d %7.0f%% [%4.0f〜%4.0f]%% %7.0f%% [%4.0f〜%4.0f]%%  倍率中央値%.0f倍"%(g,n,sum(1 for x in L if x["fin"]<=3),sum(tv)/n*100,a[0]*100,a[1]*100,sum(fv)/n*100,b[0]*100,b[1]*100,statistics.median(x["odds"] for x in L)))
print("\n消えた馬が3着内に来たレース（複勝配当・その馬が絡む3連複の最小配当）")
for x in G["消えた"]:
    if x["fin"]<=3: print(x["d"],x["k"],"馬番",x["u"],"%.0f倍"%x["odds"],"%d着"%x["fin"],"複勝",x["fuku"],"円","3連複",x["trio"],"円")
