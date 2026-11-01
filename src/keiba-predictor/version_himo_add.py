# -*- coding: utf-8 -*-
"""version_himo_add.py — 「前日の版で印があったのに当日の版で消えた馬」を、紐に1頭足していたら回収率はどうなったか。
同じレースで、(X)最後の版の印だけで紐を組む と (Y)最後の版の印＋消えた馬を足して紐を組む を、
1レース10,000円・各点同額（100円単位）・実払戻で比べる。券種: ワイド◎流し／3連単マルチ◎○→紐／3連複◎○-紐。2026-10-31新規"""
import json,glob,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import day_review as DR
B=os.path.join(os.path.expanduser("~"),"Desktop","競馬予想レポート")
dates=["20261011","20261012","20261017","20261018","20261024","20261025","20261031"]
def plan(kind,a,b,himo):
    himo=[h for h in himo if h not in (a,b)]
    if kind=="ワイド◎流し": return "ワイド",[tuple(sorted((a,h))) for h in himo+[b]]
    if kind=="3連単マルチ◎○→紐": return "3連単",[(a,b,h) for h in himo]+[(b,a,h) for h in himo]
    if kind=="3連複◎○-紐": return "3連複",[tuple(sorted((a,b,h))) for h in himo]
def ret(pk,t,combos,st=None):
    n=len(combos)
    if st is None: st=max(100,int(10000/n//100)*100)      # 1万円に固定して均等割り
    return st*n, sum(st/100*pk.get(t,{}).get(c,0) for c in combos)
kinds=["ワイド◎流し","3連単マルチ◎○→紐","3連複◎○-紐"]
MODE=sys.argv[1] if len(sys.argv)>1 else "fixed"      # fixed=1万円に固定／add=1点の金額はそのまま・点を足す（1万円前後）
R={k:{"X":[0,0,0],"Y":[0,0,0]} for k in kinds}   # 賭け, 払戻, 当たったレース数
detail=[]; nraces=0
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
        if k not in Lm or x["marks"]==Lm[k]["marks"] or k not in py: continue
        y=Lm[k]; nm={h["uma"] for h in y["horses"]}
        inv={m:int(u) for u,m in y["marks"].items() if m in "◎○"}
        if "◎" not in inv or "○" not in inv: continue
        a,b=inv["◎"],inv["○"]
        himoL=[int(u) for u,m in y["marks"].items() if m not in "◎○"]
        drop=[int(u) for u in x["marks"] if u not in y["marks"] and int(u) in nm]
        if not drop: continue
        nraces+=1; himoY=himoL+drop
        row=[d,k,"消えた馬"+",".join(map(str,drop)),"着順"+",".join(str(fin.get((k[0],k[1],u),"-")) for u in drop)]
        for kd in kinds:
            tx,cx=plan(kd,a,b,himoL); ty,cy=plan(kd,a,b,himoY)
            sx=max(100,int(10000/len(cx)//100)*100)
            for tag,(t,cb) in (("X",(tx,cx)),("Y",(ty,cy))):
                st,rt=ret(py[k],t,cb,sx if MODE=="add" else None)
                R[kd][tag][0]+=st; R[kd][tag][1]+=rt; R[kd][tag][2]+= rt>0
            gx=ret(py[k],tx,cx,sx if MODE=="add" else None)[1]; gy=ret(py[k],ty,cy,sx if MODE=="add" else None)[1]
            if gx!=gy: row.append("%s X払戻%d→Y払戻%d"%(kd,gx,gy))
        detail.append(row)
print("印が前日から消えた馬がいて、結果と◎○が分かるレース:",nraces)
print("%-18s %-12s %8s %8s %8s %6s"%("券種","紐","賭け","払戻","回収率","的中"))
for kd in kinds:
    for tag,lab in (("X","最後の版の印だけ"),("Y","＋消えた馬を足す")):
        s,r,h=R[kd][tag]; print("%-18s %-12s %8d %8d %7.0f%% %4d/%d  損益%+d円  1レース平均賭け%.0f円"%(kd,lab,s,r,r/s*100,h,nraces,r-s,s/nraces))
print()
for r in detail:
    if len(r)>4: print(*r)
