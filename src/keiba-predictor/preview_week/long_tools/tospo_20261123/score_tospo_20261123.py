# -*- coding: utf-8 -*-
"""東京スポーツ杯2歳S（G2・東京芝1800m・11/23）登録段階の「アスメシ独自指数」（100点満点）。2026-11-16 作成。
2歳戦はキャリア1〜2戦なので、古馬の式（score_fukushima_20261121.py）を2歳向けに直した。順位の目安で、勝つ確率ではない。
  ①近走 40: 直近2走（重み 0.65/0.35。1戦の馬はその1走）× 格（重賞 1.0・オープン/リステッド 0.8・新馬/未勝利 0.6）× 着順
  ②型 20: 前走1着 8（過去10年の勝ち馬10頭のうち9頭が前走1着）・前走が重賞/オープンで3着内 6・ほか 2
           ＋間隔（42〜84日 7・それ以外で23〜160日 4）＋前走で上がり1位 5
  ③適性 20: 東京芝の3着内率×6（未出走は2）＋芝1800mの3着内率×8（未出走は3）＋上がり3Fの自己最速（33.5秒以下 6・34.0秒以下 4・ほか 2）
  ④脚質 10: 中団 10・好位 8・後方 6・逃げ 5（過去10年の3着内率 差し46%・先行24%・追込24%・逃げ20%）。1戦の馬はその1走の位置から
  ⑤状態 10: 1週前追い切りは時計だけ報道された馬が3頭（評価なし）＝全馬5点"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).parent
D = json.load(open(next(H.glob("entry_digest_*.json")), encoding="utf-8"))
REG = json.load(open(H / "registrants_tospo.json", encoding="utf-8")); ODDS = REG["odds"]
POP = {n: i for i, n in enumerate(sorted(ODDS, key=ODDS.get), 1)}
def cls(r):
    c = r["cond"] + r["race"]
    return 1.0 if any(k in c for k in ("G1", "G2", "G3")) else .8 if any(k in c for k in ("(L", "OP", "ステークス", "特別")) else .6
def finp(f):
    f = int(f) if str(f).isdigit() else 99
    return 1.0 if f == 1 else .8 if f == 2 else .65 if f == 3 else .45 if f <= 5 else .2
def rec(s):
    a = [int(x) for x in s.split("-")]; n = sum(a)
    return n, (a[0] + a[1] + a[2]) / n if n else None
def style1(r):
    ps = [int(x) for x in str(r.get("corner", "")).split("-") if x.isdigit()]; n = int(r.get("n") or 10)
    if not ps: return "中団"
    p = ps[-1]
    return "逃げ" if ps[0] == 1 and p <= 2 else "好位" if p <= max(3, n * .35) else "中団" if p <= n * .65 else "後方"
STY = {"中団": (10, "中団（差しの3着内46%）"), "好位": (8, "好位（先行の3着内24%）"), "逃げ・先行": (8, "逃げ・先行"), "後方": (6, "後方（追込の3着内24%）"), "逃げ": (5, "逃げ（3着内20%）")}
rows = []
for h in D["horses"]:
    L = h["last5"]; r2 = L[::-1][:2]; last = r2[0]; nm = h["name"]
    w = [1.0] if len(r2) == 1 else [.65, .35]
    s1 = 40 * sum(wi * cls(r) * finp(r["fin"]) for wi, r in zip(w, r2))
    f = int(last["fin"]); top = cls(last) >= .8
    pv = (8, "前走1着") if f == 1 else (6, "前走は重賞・オープンで3着内") if top and f <= 3 else (2, "前走は4着以下")
    g = h["gap"]; gi = 7 if 42 <= g <= 84 else 4
    u1 = 5 if last.get("f3rank") == 1 else 0
    s2 = pv[0] + gi + u1
    n, kr = rec(h["venue_surf"]); tk = 6 * kr if n else 2
    m18 = [r for r in L if r["dist"] == "芝1800m"]; t18 = sum(1 for r in m18 if int(r["fin"]) <= 3)
    d18 = 8 * t18 / len(m18) if m18 else 3
    best = min(float(r["f3"]) for r in L if r.get("f3")); up = 6 if best <= 33.5 else 4 if best <= 34.0 else 2
    s3 = tk + d18 + up
    st = h["style"] if h["style"] in STY else style1(last); s4, stxt = STY[st]
    rows.append(dict(name=nm, jockey=next(x["jockey_expected"] for x in REG["horses"] if x["name"] == nm), pop=POP[nm], odds=ODDS[nm],
        score=round(s1 + s2 + s3 + s4 + 5, 1), form=round(s1, 1), type=s2, fit=round(s3, 1), style=s4, cond=5, runs=len(L), gap=g, sty=st, best=best,
        last=f"{last['venue']} {last['race']} {last['dist']} {last['fin']}着", why=[pv[1], f"前走から{g}日", "前走は上がり1位" if u1 else "前走の上がりは1位ではない",
        f"東京芝 {h['venue_surf']}" if n else "東京芝は初めて", f"芝1800m {len(m18)}戦で3着内{t18}回" if m18 else "芝1800mは初めて", f"上がりの自己最速 {best}秒", stxt]))
rows.sort(key=lambda r: -r["score"])
for i, r in enumerate(rows, 1): r["rank"] = i
(H / "score_tospo.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
for r in rows: print(f"{r['rank']:2d} {r['name']:<10} {r['score']:5.1f} ｜近走{r['form']:4.1f} 型{r['type']:2d} 適性{r['fit']:4.1f} 脚質{r['style']:2d} ｜想定{r['pop']}人気 {r['sty']} " + " / ".join(r["why"][:5]))
