# -*- coding: utf-8 -*-
"""public_ledger.py — 事前に出した予想（印・買い目・金額）と結果を、1年ぶん同じ形で残す台帳（2026-11-18 新設）

きっかけ: 2026年の総まとめ（docs/keiba_2026_summary_20261118.md）で、時期ごとに記録の形が違い（5〜9月は金額だけ・10月は全レース・11月は日ごとのメモ）、
1年ぶんを同じ集計で比べられなかった。以後は公開（または参考として作成）した予想を、レース単位でここに足す。
台帳: Desktop/競馬予想レポート/daily_pdca/db/public_ledger.json（1行＝1レース。日ごとの合計しか無い古い記録は kind="日合計"）

  python public_ledger.py rebuild            # 2026-11-15 までの既存の記録（roi_ledger・postmortem_all・11月の振り返り）から作り直す
  python public_ledger.py add --date 20261121 --race 福島11 --name 福島記念 --grade G3 --kind 公開 \
         --marks "◎8,○3,▲5,△1,△2" --top3 "5,8,3" --pops "2,1,6" --stake 10000 --ret 4200 --hits "ワイド 5-8 1000 420" --tier 通常 --ratio 1.21 --s3 14 --s4 10
         （--tier 強さ・--ratio ◎の割安さ・--s3 候補S3の穴・--s4 候補S4の5頭目。どれも web_compose の出力から）
  python public_ledger.py report [--year 2026]   # 出資・回収・回収率・的中率／印ごとの1着・2着内・3着内／月ごと
決まり: 実際には買っていない（買ったとした場合の計算）。レース後に必ず足す（当たりも外れも）。後から印や買い目を書き換えない。
"""
import argparse, collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
LEDGER = BASE / "daily_pdca" / "db" / "public_ledger.json"


def load(): return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
def save(L): LEDGER.write_text(json.dumps(sorted(L, key=lambda r: (r["date"], r.get("venue") or "", r.get("R") or 0)), ensure_ascii=False, indent=1), encoding="utf-8")


def rebuild():
    L = []
    for x in json.loads((BASE / "daily_pdca/db/roi_ledger.json").read_text(encoding="utf-8"))["records"]:
        L.append(dict(date=x["date"].replace("-", ""), kind="日合計", src="roi_ledger", name=x["race"], stake=x["invest"], ret=x["payout"], note=x.get("note", "")))
    for q in json.loads((BASE / "20261101/research/postmortem_all.json").read_text(encoding="utf-8")):
        fin = {}
        for u, r in q["reasons"].items():
            if r.get("fin"): fin[str(u)] = r["fin"]
        L.append(dict(date=q["date"], kind="全レース参考", src="postmortem_all", venue=q["venue"], R=q["R"], name=q["name"], grade=q["grade"], n=q["n"],
                      marks={str(u): m for u, m in q["marks"].items()}, fin=fin, top3=q["top3"], top3_pop=q["top3_pop"], stake=q["stake"], ret=q["ret"], hits=q.get("hit_types") or [], cause=q.get("cause", "")))
    d = json.loads((BASE / "20261115/research/day_ledger_20261115.json").read_text(encoding="utf-8"))
    for x in d["done"]:
        L.append(dict(date="20261115", kind="公開", src="day_ledger", name=x["race"], venue=x["race"][:2], R=int(x["race"][2:]), stake=x["cost"], ret=x["ret"], hits=x["hits"]))
    for dt, nm, st, rt, nr, nh in (("20261107", "公開6レース", 60100, 29600, 6, 2), ("20261108", "注目5選", 50000, 35090, 5, 2), ("20261114", "公開7レース", 73000, 61110, 7, 3)):
        L.append(dict(date=dt, kind="日合計", src="振り返りメモ", name=nm, stake=st, ret=rt, races=nr, hit_races=nh))
    save(L); print("作り直し", len(L), "行 →", LEDGER)


def add(a):
    L = load()
    marks = {}
    for t in filter(None, (a.marks or "").split(",")):
        marks[t.strip()[1:]] = t.strip()[0]
    top3 = [int(x) for x in (a.top3 or "").split(",") if x]; pops = [int(x) for x in (a.pops or "").split(",") if x]
    fin = {str(u): i + 1 for i, u in enumerate(top3)}
    venue, R = a.race[:2], int(a.race[2:])
    L = [r for r in L if not (r["date"] == a.date and r.get("venue") == venue and r.get("R") == R and r.get("kind") == a.kind)]
    hits = [h.split() for h in (a.hits or "").split(";") if h.strip()]
    L.append(dict(date=a.date, kind=a.kind, src="add", venue=venue, R=R, name=a.name or "", grade=a.grade or "", marks=marks, fin=fin, top3=top3, top3_pop=pops, stake=a.stake, ret=a.ret, hits=hits, note=a.note or "", tier=a.tier or "", ratio=a.ratio, s3=a.s3, s4=a.s4,
                  s3_fin=fin.get(str(a.s3), 99) if a.s3 else None, s4_fin=fin.get(str(a.s4), 99) if a.s4 else None))
    save(L); print("追加", a.date, a.race, a.name, f"{a.stake:,}円→{a.ret:,}円")


def report(year):
    L = [r for r in load() if r["date"].startswith(str(year))]
    if not L: print("記録なし"); return
    st = sum(r["stake"] for r in L); rt = sum(r["ret"] for r in L)
    nr = sum(r.get("races", 1) for r in L if r["stake"] > 0); nh = sum(r.get("hit_races", 1 if r["ret"] > 0 else 0) for r in L if r["stake"] > 0)
    print(f"■ {year}年 合計（{L[0]['date']}〜{L[-1]['date']}）\n  出資 {st:,.0f}円 → 回収 {rt:,.0f}円 ／ 回収率 {rt/st*100:.1f}% ／ 差し引き {rt-st:+,.0f}円 ／ 買ったレース {nr}・的中 {nh}（{nh/nr*100:.1f}%）")
    top = sorted(L, key=lambda r: -r["ret"])[:2]; cut = rt - sum(r["ret"] for r in top); cs = st - sum(r["stake"] for r in top)
    print(f"  いちばん大きい2本を除くと {cut:,.0f}円／{cs:,.0f}円＝{cut/cs*100:.1f}%（{', '.join(str(r['date'])+' '+str(r.get('name',''))[:14] for r in top)}）")
    print("\n■ 月ごと\n  月      レース  出資        回収        回収率  的中")
    M = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in L:
        if r["stake"] <= 0: continue
        m = M[r["date"][:6]]; m[0] += r.get("races", 1); m[1] += r["stake"]; m[2] += r["ret"]; m[3] += r.get("hit_races", 1 if r["ret"] > 0 else 0)
    for k, m in sorted(M.items()): print(f"  {k[4:]}月  {m[0]:5d}  {m[1]:10,.0f}  {m[2]:10,.0f}  {m[2]/m[1]*100:5.1f}%  {m[3]}（{m[3]/m[0]*100:.0f}%）")
    K = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in L:
        if r["stake"] <= 0: continue
        m = K[r["kind"]]; m[0] += r.get("races", 1); m[1] += r["stake"]; m[2] += r["ret"]; m[3] += r.get("hit_races", 1 if r["ret"] > 0 else 0)
    print("\n■ 種類ごと"); [print(f"  {k:8s} {m[0]:4d}R  {m[1]:10,.0f}円 → {m[2]:10,.0f}円  {m[2]/m[1]*100:5.1f}%  的中 {m[3]}") for k, m in K.items()]
    mk = collections.defaultdict(lambda: [0, 0, 0, 0]); nmark = 0; unw = 0
    for r in L:
        if not r.get("marks") or not r.get("top3"): continue
        nmark += 1; unw += str(r["top3"][0]) not in r["marks"]
        for u, m in r["marks"].items():
            f = r["fin"].get(str(u)) or (r["top3"].index(int(u)) + 1 if int(u) in r["top3"] else 99)
            a = mk[m]; a[0] += 1; a[1] += f == 1; a[2] += f <= 2; a[3] += f <= 3
    if nmark:
        print(f"\n■ 印ごと（印と着順の記録があるレース {nmark}）\n  印   頭数  1着  2着内  3着内   勝率   連対率  3着内率")
        for m in "◎○▲△☆🔥":
            if m in mk:
                a = mk[m]; print(f"  {m}  {a[0]:5d} {a[1]:4d} {a[2]:5d} {a[3]:5d}  {a[1]/a[0]*100:5.1f}%  {a[2]/a[0]*100:5.1f}%  {a[3]/a[0]*100:5.1f}%")
        print(f"  勝ち馬が無印 {unw}／{nmark}（{unw/nmark*100:.1f}%）")
    T = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in L:
        if r.get("tier") and r["stake"] > 0:
            t = T[r["tier"]]; t[0] += 1; t[1] += r["stake"]; t[2] += r["ret"]; t[3] += r["ret"] > 0
    if T:
        print("\n■ 強さ（◎の割安さ）ごと"); [print(f"  {k:6s} {t[0]:4d}R  {t[1]:9,.0f}円 → {t[2]:9,.0f}円  {t[2]/t[1]*100:5.1f}%  的中 {t[3]}") for k, t in T.items()]
    for key, lab in (("s3", "候補S3の穴"), ("s4", "候補S4の5頭目")):
        g = [r for r in L if r.get(key)]
        if g: print(f"  {lab}: {len(g)}頭 ／ 1着 {sum(r[key+'_fin']==1 for r in g)}・3着内 {sum(r[key+'_fin']<=3 for r in g)}")
    print("\n（実際には買っていない。買ったとした場合の計算。種類ごとに対象が違うので合計は目安）")


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("rebuild")
    p = sp.add_parser("add")
    for k in ("date", "race"): p.add_argument("--" + k, required=True)
    for k in ("name", "grade", "marks", "top3", "pops", "hits", "note", "tier"): p.add_argument("--" + k)
    p.add_argument("--ratio", type=float, help="◎の割安さ"); p.add_argument("--s3", type=int, help="候補S3の穴の馬番"); p.add_argument("--s4", type=int, help="候補S4の5頭目の馬番")
    p.add_argument("--kind", default="公開"); p.add_argument("--stake", type=int, required=True); p.add_argument("--ret", type=int, required=True)
    p = sp.add_parser("report"); p.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    {"rebuild": rebuild, "add": lambda: add(a), "report": lambda: report(a.year)}[a.cmd]()


if __name__ == "__main__":
    main()
