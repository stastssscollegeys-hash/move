# -*- coding: utf-8 -*-
"""score_20261114.py — 11/14（土）武蔵野S・デイリー杯2歳S の「アスメシ独自指数」（100点満点・枠順確定後 11/13）
エリザベス女王杯（score_eri_20261115.py）と同じ考え方。配点は各レースの過去10年の3着内の傾向（race_profile）と
コースの型（course_profile）に合わせて手で決めた目安。前向き検証はしていない＝勝つ確率ではない。
  ①格と近走 30 ／ ②レースの型 25（前走のレース・間隔・年齢 or キャリア） ／ ③適性 25（同コース・同距離帯・上がり） ／ ④脚質 10 ／ ⑤状態 10（最終追い切りの評価と陣営の話＝収集メモ）
出力: score_{レース}.json ・ draw_input_{レース}.json（100万回シミュレーション用。想定オッズは発売前の目安）
"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).resolve().parent
CLS = {"G1": 1.0, "Jpn1": 1.0, "G2": .85, "Jpn2": .85, "G3": .75, "Jpn3": .75, "(L": .6, "OP": .6, "オープン": .6, "3勝": .5, "特別": .45, "2勝": .4, "1勝": .35, "新馬": .5, "未勝利": .5}
def cls(c): return next((v for k, v in CLS.items() if k in c), .5)
def finp(f):
    f = int(f) if str(f).isdigit() else 99
    return 1.0 if f == 1 else .8 if f == 2 else .65 if f == 3 else .45 if f <= 5 else .2 if f <= 9 else 0
def rec(s):
    if not s: return 0, None
    a = [int(x) for x in s.split("-")]; n = sum(a)
    return n, (a[0] + a[1] + a[2]) / n if n else None

# ⑤ 状態（最終追い切り 11/11〜12 の評価と陣営の話。musashino_info / daily_info 由来。10=そろって最上位 … 3=遅れ・不安）
COND = {
 "武蔵野S": {"ドンインザムード": (10, "最終追い切りは今週一番の評価（坂路52秒7）・陣営「前回より状態は上」"), "ルヴァレドクール": (9, "2サイトで最上位評価・前週は坂路51秒5の自己ベスト"),
            "ジェイパームス": (8, "坂路54秒6で軽快・状態維持"), "エンペラーワケア": (8, "坂路53秒7馬なり・休み明けでもリズムは変わらず"), "ダノンフィーゴ": (7, "ポリトラックで終い鋭い・チークピーシーズ着用後に良化"),
            "ロックターミガン": (7, "坂路53秒7で軽い動き・陣営「マイルは合う」"), "ジャスティンアース": (6, "評価が割れる（1週前は最上位・最終は普通）・休み明けから上向き"), "ヘニーガイスト": (6, "集中力は良いが最後に頭を振る・目の保護具の影響"),
            "ライノ": (6, "坂路54秒7・普通"), "アピーリングルック": (5, "普通"), "クールブロン": (5, "中2週で上積み乏しい"), "オメガギネス": (5, "評価が割れる（最上位と前脚の硬さ）"),
            "ハセドン": (4, "坂路54秒1・目立たず"), "トリリオンボーイ": (4, "時計目立たず"), "ドンエレクトス": (4, "最終は終いが遅く僚馬に遅れ・状態に不安の指摘"), "バトルクライ": (3, "一杯に追ってふらつき・頭が高い")},
 "デイリー杯2歳S": {"シェフザーデ": (10, "最終追い切りは3ソースとも最上位（坂路53秒6の自己ベストを馬なり）"), "キューティボンド": (9, "坂路52秒8馬なり・師「重賞でも通用」。直線で右にもたれる癖"),
            "ブラッドバローズ": (8, "坂路53秒7・師「新馬前より格段に向上」"), "リュウトウコヤク": (8, "CW自己ベスト・前走の出遅れ対策でゲート練習"), "ブレイクアウェイ": (8, "坂路52秒5の自己ベストを馬なり"),
            "スマートピナクル": (7, "CWで速い時計（予定より3〜4秒速い）・師は中2週のオーバーワークを懸念"), "インカルナータ": (7, "坂路54秒1馬なり・テンションが鍵"), "レオンティウス": (7, "3頭併せで先着・仕上がり良好"),
            "ルースソラール": (5, "軽め単走・普通"), "ヒアカムズザサン": (5, "強めに追って普通・気負うタイプで休み明け"), "トップチェッカー": (4, "一杯に追って普通・師「良くなるのは来春」"),
            "コルサロ": (4, "一杯に追って普通"), "スーサンコルティナ": (4, "軽めで目立たず")}}

def score_musashino(h):
    L = h["last5"]; r3 = L[::-1][:3]; age = int(h["sexage"][-1])
    s1 = 30 * sum(wi * cls(r["cond"]) * finp(r["fin"]) for wi, r in zip([.5, .3, .2], r3))
    last = L[-1]; rn = last["race"]
    if "グリーンチャンネル" in rn: pv = (10, "グリーンチャンネルC組（過去10年の3着内7頭・一番の型）")
    elif "ペルセウス" in rn: pv = (6, "ペルセウスS組（3着内2頭）")
    elif any(k in rn for k in ("プロキオン", "エルム", "フェブラリー")): pv = (7, f"{rn[:6]}組（3着内3頭）")
    elif any(k in rn for k in ("エニフ", "シリウス")): pv = (5, f"{rn[:5]}組（3着内2頭）")
    elif last["cond"].startswith("Jpn") or last["venue"] not in ("東京", "中山", "京都", "阪神", "中京", "新潟", "福島", "小倉", "札幌", "函館"): pv = (6, "地方交流組（勝ち馬はOP特別組か地方組）")
    elif "ステークス" in rn and "勝クラス" not in last["cond"]: pv = (4, "その他のOP特別組")
    else: pv = (2, "条件戦からの参戦（過去10年の3着内に例が少ない）")
    g = h["gap"]; gi = 8 if 33 <= g <= 146 else 5 if g < 33 else 2
    ag = {4: 7, 6: 5, 3: 4, 5: 4}.get(age, 3)
    s2 = pv[0] + gi + ag
    n, cr = rec(h["course"]); same = 10 * cr if n else 4
    mid = [r for r in L if r["dist"].startswith("ダ") and 1400 <= int(r["dist"][1:-1]) <= 1800]
    md = 10 * sum(1 for r in mid if int(r["fin"]) <= 3) / len(mid) if mid else 3
    f3 = [r["f3rank"] for r in r3 if r.get("f3rank")]; f3a = sum(f3) / len(f3) if f3 else None
    up = 2 if f3a is None else 5 if f3a <= 3 else 3 if f3a <= 5 else 1
    s3 = same + md + up
    s4, stxt = {"先行": (10, "先行（このコースの3着内30%）"), "逃げ": (9, "逃げ（3着内33%・過去10年2頭）"), "中団": (7, "差し（3着内19%）"), "後方": (5, "後方（追込は3着内9%。過去10年は11頭と多い）")}.get(h["style"], (6, "脚質は未集計（地方）"))
    s5, ctxt = COND["武蔵野S"][h["name"]]
    why = [f"近走: {r3[0]['race']} {r3[0]['fin']}着（{r3[0]['cond']}）", pv[1], f"前走から{g}日" + ("（3着内馬の範囲33〜146日）" if gi == 8 else "（中2週）" if g < 33 else "（3着内馬は最長146日）"),
           f"{age}歳", f"東京ダ1600m {h['course']}" if n else "東京ダ1600mは初めて", f"近5走のダ1400〜1800m {len(mid)}戦で3着内{sum(1 for r in mid if int(r['fin']) <= 3)}回" if mid else "近5走にダ1400〜1800mなし",
           f"直近3走の上がり順位 平均{f3a:.1f}位" if f3a else "上がり順位は未取得（地方）", stxt, ctxt]
    return s1, s2, s3, s4, s5, why

def score_daily(h):
    L = h["last5"]; R = L[::-1]
    w = [.6, .3, .1][:len(R)]; ws = sum(w)
    s1 = 30 * sum(wi * cls(r["cond"]) * finp(r["fin"]) for wi, r in zip(w, R)) / ws
    last = L[-1]; c = last["cond"]; f = int(last["fin"])
    if any(k in c for k in ("新馬", "未勝利")) and f == 1: pv = (10, "前走は新馬・未勝利勝ち（過去10年7勝の型）")
    elif "G" in c: pv = (3, "前走は重賞（過去10年の重賞組は1-1-1-17）")
    elif "勝クラス" in c: pv = (4 if f <= 3 else 2, "前走は1勝クラス")
    elif f <= 3: pv = (6, "前走はOP特別で3着内")
    else: pv = (3, "前走はOP特別で4着以下")
    d = int(last["dist"][1:-1]); dv = 5 if d == 1600 else 3 if d == 1400 else 2
    tr = 5 if h["trainer"].startswith("栗東") else 1
    car = 5 if h["starts"] <= 3 else 1
    s2 = pv[0] + dv + tr + car
    n, kr = rec(h["venue_surf"]); kyo = 8 * kr if n else 4
    m16 = [r for r in L if r["dist"] == "芝1600m"]
    mi = 8 if any(int(r["fin"]) <= 3 for r in m16) else 2 if m16 else 3
    fr = last.get("f3rank"); up = 4 if fr is None else 9 if fr <= 2 else 5 if fr <= 5 else 2
    s3 = kyo + mi + up
    s4, stxt = {"先行": (10, "先行（過去10年の3着内42%）"), "逃げ": (8, "逃げ（3着内30%）"), "中団": (8, "差し（3着内31%）"), "後方": (6, "後方（追込は29%）")}.get(h["style"], (7, "脚質は1戦で未確定"))
    s5, ctxt = COND["デイリー杯2歳S"][h["name"]]
    why = [f"近走: {last['race']} {last['fin']}着（{c}）", pv[1], f"前走は{last['dist']}", "栗東" if tr == 5 else "美浦（過去10年は苦戦）", f"キャリア{h['starts']}戦",
           f"京都芝 {h['venue_surf']}" if n else "京都は初めて", "芝1600mで3着内あり" if mi == 8 else "芝1600mは初めて" if mi == 3 else "芝1600m経験ありで3着内なし",
           f"前走の上がり{fr}位" if fr else "前走の上がり順位は未取得", stxt, ctxt]
    return s1, s2, s3, s4, s5, why

ODDS = {  # 想定オッズ（発売前の目安）
 "武蔵野S": ("競馬の魅力 11/12 の想定（2番人気4.5倍は掲載の表記が重複＝ドンエレクトスと仮置き）", {"ドンインザムード": 2.5, "ドンエレクトス": 4.5, "ヘニーガイスト": 6.5, "ジェイパームス": 7.0, "エンペラーワケア": 12.5, "ルヴァレドクール": 13.5, "ジャスティンアース": 14.0, "ライノ": 21.0, "ダノンフィーゴ": 30.0, "オメガギネス": 31.0, "ロックターミガン": 38.0, "クールブロン": 55.0, "アピーリングルック": 60.0, "バトルクライ": 70.0, "トリリオンボーイ": 80.0, "ハセドン": 100.0}),
 "デイリー杯2歳S": ("競馬の魅力 11/13 とウマニティ 11/13 の想定の中間（1番人気が割れる: キューティボンド3.0／ブラッドバローズ2.3）", {"ブラッドバローズ": 3.0, "キューティボンド": 4.0, "トップチェッカー": 6.2, "スマートピナクル": 8.0, "シェフザーデ": 10.3, "ブレイクアウェイ": 11.0, "リュウトウコヤク": 17.0, "インカルナータ": 20.0, "ルースソラール": 34.0, "スーサンコルティナ": 50.0, "ヒアカムズザサン": 60.0, "レオンティウス": 60.0, "コルサロ": 70.0})}

for race, fn in (("武蔵野S", score_musashino), ("デイリー杯2歳S", score_daily)):
    D = json.load(open(H / f"entry_digest_{race}.json", encoding="utf-8"))
    rows = []
    for h in D["horses"]:
        s1, s2, s3, s4, s5, why = fn(h)
        rows.append(dict(waku=h["waku"], uma=h["uma"], name=h["name"], sexage=h["sexage"], jockey=h["jockey"], score=round(s1 + s2 + s3 + s4 + s5, 1), form=round(s1, 1), type=round(s2, 1), fit=round(s3, 1),
                         style=s4, style_txt=h["style"], cond=s5, why=why, gap=h["gap"], last=h["last5"][-1]["race"], last_fin=h["last5"][-1]["fin"], odds_est=ODDS[race][1][h["name"]]))
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1): r["rank"] = i
    (H / f"score_{race}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    STY = {"逃げ": "逃げ", "先行": "先行", "中団": "中団", "後方": "後方"}
    di = {"odds_note": ODDS[race][0], "horses": [dict(waku=r["waku"], uma=r["uma"], name=r["name"], odds_est=r["odds_est"], style=STY.get(r["style_txt"], "好位"), score=r["score"]) for r in sorted(rows, key=lambda r: r["uma"])]}
    (H / f"draw_input_{race}.json").write_text(json.dumps(di, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"■ {race} 独自指数（100点）")
    for r in rows:
        print(f"{r['rank']:2d} {r['uma']:>2}{r['name']:<10} {r['score']:5.1f} ｜近走{r['form']:4.1f} 型{r['type']:4.1f} 適性{r['fit']:4.1f} 脚質{r['style']:2d} 状態{r['cond']:2d} ｜想定{r['odds_est']:>5}倍 ｜ " + " / ".join(r["why"][1:3]))
    print()
