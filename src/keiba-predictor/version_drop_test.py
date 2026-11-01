import json,glob,os,collections,sys,itertools,math,statistics
sys.path.insert(0,r"C:\Users\User\dev\move\src\keiba-predictor")
import day_review as DR
B=r"C:\Users\User\Desktop\競馬予想レポート"
def p3_all(q,l2=0.8,l3=0.7):
    us=list(q); res={u:0.0 for u in us}
    for a in us:
        res[a]+=q[a]
        w2={k:q[k]**l2 for k in us if k!=a}; s2=sum(w2.values())
        for b in w2:
            pb=q[a]*w2[b]/s2; res[b]+=pb
            w3={k:q[k]**l3 for k in us if k not in(a,b)}; s3=sum(w3.values())
            for c in w3: res[c]+=pb*w3[c]/s3
    return res
dates=["20261011","20261012","20261017","20261018","20261024","20261025","20261031"]
drop=[];add=[];ratio_chg=collections.defaultdict(list)
for d in dates:
    vs=sorted(glob.glob(os.path.join(B,d,"research","cards_versions","cards_%s_*.json"%d)),key=os.path.getmtime)
    last=os.path.join(B,d,"research","cards_%s.json"%d)
    rs,py=DR.load_day(d)
    fin={(r["競馬場"],r["R"],r["馬番"]):r["着順int"] for r in rs if r["着順int"]}
    Lm={(c["venue"],c["R"]):c for c in json.load(open(last,encoding="utf-8"))["cards"]}
    first={}
    for f in vs:
        for x in json.load(open(f,encoding="utf-8"))["cards"]:
            first.setdefault((x["venue"],x["R"]),x)
    for k,x in first.items():
        if k not in Lm: continue
        y=Lm[k]
        om={h["uma"]:h for h in x["horses"]}; nm={h["uma"]:h for h in y["horses"]}
        q={u:h["p_market"] for u,h in nm.items() if h["p_market"]>0}
        if len(q)<5: continue
        s=sum(q.values()); q={u:v/s for u,v in q.items()}
        P3=p3_all(q)
        for u,h in nm.items():
            if u in om and u in q and not (math.isnan(h["ratio"]) or math.isnan(om[u]["ratio"])):
                b="~10倍" if h["odds"]<10 else "10〜30倍" if h["odds"]<30 else "30倍〜"
                ratio_chg[b].append(h["ratio"]-om[u]["ratio"])
        if x["marks"]==y["marks"]: continue
        for u,m in x["marks"].items():
            if u not in y["marks"] and int(u) in q and fin.get((k[0],k[1],int(u))):
                drop.append((P3[int(u)],fin[(k[0],k[1],int(u))]<=3,nm[int(u)]["odds"]))
        for u,m in y["marks"].items():
            if u not in x["marks"] and int(u) in q and fin.get((k[0],k[1],int(u))):
                add.append((P3[int(u)],fin[(k[0],k[1],int(u))]<=3,nm[int(u)]["odds"]))
def rep(name,L):
    n=len(L); exp=sum(a for a,_,_ in L); act=sum(1 for _,b,_ in L if b)
    var=sum(a*(1-a) for a,_,_ in L); z=(act-exp)/math.sqrt(var) if var else 0
    print("%s: %d頭  実際の3着内 %d  最終オッズから期待される3着内 %.1f  差 %+.1f（標準偏差 %.1f・z=%+.2f）"%(name,n,act,exp,act-exp,math.sqrt(var),z))
rep("印が消えた馬",drop); rep("印が増えた馬",add)
print("--- 版が進んだときの割安さ（比）の変化（最後の版−最初の版）")
for b in ("~10倍","10〜30倍","30倍〜"):
    L=ratio_chg[b]; print(b,"頭数",len(L),"平均 %+.3f"%statistics.mean(L),"下がった割合 %.0f%%"%(100*sum(1 for v in L if v<0)/len(L)))
