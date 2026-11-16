# -*- coding: utf-8 -*-
"""福島記念（G3・ハンデ・福島芝2000m・11/21）登録段階の「アスメシ独自指数」（100点満点）。2026-11-16 作成（雛形 20261122/research/score_mcs_20261122.py）
材料: entry_digest_福島記念.json ＋ race_profile_福島記念（過去10年）。配点は 近走40・型20・適性20・脚質10・状態10。順位の目安で、勝つ確率ではない。
  ①近走 40: 直近3走（重み0.5/0.3/0.2）× 格 × 着順（MCSと同じ）。ダートの走りは芝のレースなので 0.5倍
  ②型 20: 前走のレース（オクトーバーS 8・オールカマー/札幌記念/京都大賞典 6・毎日王冠/ケフェウスS 4・ほか0）
           ＋間隔（28〜70日 7・71〜126日 3・27日以下 3・127日以上 0。過去10年の3着内は最短14日・最長126日・真ん中の半分が28〜70日）
           ＋年齢（4歳 5・3歳 4・6歳/8歳 2・5歳 2・7歳 1・9歳以上 0。3着内率 4歳38%・3歳23%・8歳18%・6歳15%・5歳14%・7歳12%）
  ③適性 20: 福島芝の3着内率×8（未出走は3）＋近5走の芝1800〜2200mの3着内率×8（該当なしは2）＋直近3走の上がり順位の平均（3位以内4・5位以内2・ほか1）
  ④脚質 10: 想定脚質（好位 10・逃げ先行 10・中団 8・後方 2）。過去10年の3着内率 逃げ30%・差し27%・先行25%・追込2%（47頭で1頭）
  ⑤状態 10: 1週前追い切りの評価は未取得（11/16時点）＝全馬5点。評価が出たら COND を書き換える。
  対象: 出走圏の18頭（出走可能15頭＋抽選対象3頭）。除外対象と報道の5頭は入れない。ハンデは点に入れていない（過去10年の斤量別の集計が手元に無い）。"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).parent
D = json.load(open(H / "entry_digest_福島記念.json", encoding="utf-8"))
REG = {h["name"]: h for h in json.load(open(H / "registrants_fukushima.json", encoding="utf-8"))["horses"]}
OUTSIDE = {n for n, h in REG.items() if h["status"] == "除外対象"}
COND = {}
CLS = {"G1": 1.0, "G2": .85, "G3": .75, "(L": .6, "OP": .6, "特別": .5, "1勝": .35}
def cls(c): return next((v for k, v in CLS.items() if k in c), .5)
def finp(f):
    f = int(f) if str(f).isdigit() else 99
    return 1.0 if f == 1 else .8 if f == 2 else .65 if f == 3 else .45 if f <= 5 else .2 if f <= 9 else 0
PREV = [("オクトーバー", 8, "オクトーバーS組（過去10年の3着内4頭・一番多い）"), ("オールカマー", 6, "オールカマー組（3着内3頭）"), ("札幌記念", 6, "札幌記念組（3着内3頭）"),
        ("京都大賞典", 6, "京都大賞典組（3着内3頭）"), ("毎日王冠", 4, "毎日王冠組（3着内2頭）"), ("ケフェウス", 4, "ケフェウスS組（3着内2頭）")]
STY = {"好位": (10, "好位（先行の3着内25%）"), "逃げ・先行": (10, "逃げ・先行（逃げ30%・先行25%）"), "中団": (8, "中団（差しの3着内27%）"), "後方": (2, "後方（追込は47頭で3着内1頭）")}
AGE = {4: 5, 3: 4, 5: 2, 6: 2, 8: 2, 7: 1}
def rec(s):
    a = [int(x) for x in s.split("-")]; n = sum(a)
    return n, (a[0] + a[1] + a[2]) / n if n else None
rows = []
for h in D["horses"]:
    nm = h["name"]
    if nm in OUTSIDE: continue
    L = h.get("last5") or []; last = L[-1]; age = REG[nm]["age"]
    s5, ctxt = COND.get(nm, (5, "1週前追い切りの評価は未取得（全馬5点）"))
    r3 = L[::-1][:3]
    s1 = 40 * sum(wi * cls(r["cond"]) * finp(r["fin"]) * (.5 if r["dist"].startswith("ダ") else 1) for wi, r in zip([.5, .3, .2], r3))
    pv = next(((p, t) for k, p, t in PREV if k in last["race"]), (0, "過去10年の3着内に少ない前走"))
    g = h["gap"]; gi = 7 if 28 <= g <= 70 else 3 if g <= 126 else 0
    ag = AGE.get(age, 0); s2 = pv[0] + gi + ag
    n, kr = rec(h["venue_surf"]); fk = 8 * kr if n else 3
    mid = [r for r in L if r["dist"].startswith("芝") and 1800 <= int(r["dist"][1:-1]) <= 2200]
    mt = sum(1 for r in mid if str(r["fin"]).isdigit() and int(r["fin"]) <= 3)
    md = 8 * mt / len(mid) if mid else 2
    f3 = [r["f3rank"] for r in r3 if r.get("f3rank")]; f3a = sum(f3) / len(f3) if f3 else 9
    up = 4 if f3a <= 3 else 2 if f3a <= 5 else 1
    s3 = fk + md + up; s4, stxt = STY.get(h["style"], (6, h["style"]))
    why = [f"近走: {r3[0]['race']} {r3[0]['fin']}着（{r3[0]['cond']}）", pv[1],
           f"前走から{g}日" + ("（3着内馬の真ん中の半分は28〜70日）" if gi == 7 else "（過去10年の3着内馬の最短は14日）" if g < 14 else "（3着内馬は14〜126日）" if gi == 3 else "（過去10年の3着内馬の最長は126日）"),
           f"{age}歳", f"福島芝 {h['venue_surf']}" if n else "福島芝は初めて",
           f"近5走の芝1800〜2200m {len(mid)}戦で3着内{mt}回" if mid else "近5走に芝1800〜2200mなし",
           f"直近3走の上がり順位 平均{f3a:.1f}位", stxt, ctxt]
    rows.append(dict(name=nm, age=age, sex=REG[nm]["sex"], kin=REG[nm]["kin"], jockey=REG[nm]["jockey_expected"], status=REG[nm]["status"],
                     score=round(s1 + s2 + s3 + s4 + s5, 1), form=round(s1, 1), type=round(s2, 1), fit=round(s3, 1), style=s4, cond=s5,
                     why=why, gap=g, last=last["race"], last_fin=last["fin"]))
rows.sort(key=lambda r: -r["score"])
for i, r in enumerate(rows, 1): r["rank"] = i
(H / "score_fukushima.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
for r in rows:
    print(f"{r['rank']:2d} {r['name']:<10} {r['score']:5.1f} ｜近走{r['form']:4.1f} 型{r['type']:4.1f} 適性{r['fit']:4.1f} 脚質{r['style']:4.1f} ｜{r['kin']}kg {r['status'] or ''} " + " / ".join(r["why"][0:3])[:110])
