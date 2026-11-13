# -*- coding: utf-8 -*-
"""build_digest_20261114.py — 11/14（土）の重賞2つ（武蔵野S・デイリー杯2歳S）の各馬の近5走を蓄積DBから出す。
蓄積DBは JRA のみ・2026-10-18 まで → それ以降のレースと地方のレースは収集メモ（musashino_info / daily_info、winsight・keibachannel 由来）から手で補う（MANUAL）。
出力: entry_digest_武蔵野S.json / entry_digest_デイリー杯2歳S.json（エリザベス女王杯の entry_digest と同じ形。調教は無し）
"""
import json, sys, collections, datetime as dt
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).resolve().parent
SRC = Path(r"C:\Users\User\Desktop\競馬予想レポート\daily_pdca\db\history_target")
RACE_DATE = dt.date(2026, 11, 14)

RACES = {
 "武蔵野S": {"venue": "東京", "surf": "ダ", "dist": 1600, "horses": [
   (1, 1, "ダノンフィーゴ", "牡4", 57, "T.マーカンド", "栗東・友道"), (1, 2, "クールブロン", "牡6", 57, "A.プーシャン", "栗東・井上智"),
   (2, 3, "バトルクライ", "牡7", 57, "原優介", "美浦・高木登"), (2, 4, "アピーリングルック", "牝5", 55, "大野拓弥", "美浦・辻"),
   (3, 5, "オメガギネス", "牡6", 57, "岩田康誠", "栗東・安田翔"), (3, 6, "ドンインザムード", "牡4", 57, "荻野極", "栗東・今野"),
   (4, 7, "ヘニーガイスト", "牡4", 57, "横山武史", "美浦・加藤征"), (4, 8, "エンペラーワケア", "牡6", 57, "西村淳也", "栗東・杉山晴"),
   (5, 9, "トリリオンボーイ", "セ4", 57, "菅原明良", "美浦・武井"), (5, 10, "ジェイパームス", "セ6", 57, "田辺裕信", "美浦・堀"),
   (6, 11, "ドンエレクトス", "牡3", 56, "三浦皇成", "美浦・高木登"), (6, 12, "ロックターミガン", "牡3", 57, "津村明秀", "栗東・石坂公"),
   (7, 13, "ライノ", "セ4", 57, "戸崎圭太", "栗東・高野"), (7, 14, "ハセドン", "牡7", 57, "佐々木大輔", "美浦・大和田"),
   (8, 15, "ルヴァレドクール", "セ4", 57, "横山和生", "美浦・手塚貴"), (8, 16, "ジャスティンアース", "牡5", 57, "C.ルメール", "栗東・杉山晴")]},
 "デイリー杯2歳S": {"venue": "京都", "surf": "芝", "dist": 1600, "horses": [
   (1, 1, "ルースソラール", "牡2", 56, "M.デムーロ", "栗東・吉岡"), (2, 2, "スマートピナクル", "牝2", 55, "武豊", "栗東・石橋守"),
   (3, 3, "レオンティウス", "牡2", 56, "丸山元気", "美浦・田中勝"), (4, 4, "インカルナータ", "牡2", 56, "北村友一", "栗東・西園翔"),
   (4, 5, "ブラッドバローズ", "牡2", 56, "松山弘平", "栗東・杉山晴"), (5, 6, "トップチェッカー", "牡2", 56, "C.デムーロ", "栗東・武英"),
   (5, 7, "リュウトウコヤク", "牡2", 56, "浜中俊", "栗東・鈴木孝"), (6, 8, "キューティボンド", "牝2", 55, "川田将雅", "栗東・福永"),
   (6, 9, "コルサロ", "牡2", 56, "幸英明", "栗東・中竹"), (7, 10, "スーサンコルティナ", "牡2", 56, "田口貫太", "栗東・鈴木孝"),
   (7, 11, "シェフザーデ", "牡2", 56, "吉村誠之助", "栗東・野中"), (8, 12, "ヒアカムズザサン", "牡2", 56, "坂井瑠星", "栗東・中竹"),
   (8, 13, "ブレイクアウェイ", "牡2", 56, "岩田望来", "栗東・上村")]},
}

# DBに無い走り（10/19以降・地方）。(date, venue, race, cond, dist, baba, fin, n, pop, corner, f3rank, weight)
MANUAL = {
 "ダノンフィーゴ": [("20260923", "浦和", "テレ玉杯オーバルスプリント", "Jpn3", "ダ1400m", "", "4", 12, 2, "", None, ""),
                 ("20260324", "高知", "黒船賞", "Jpn3", "ダ1400m", "", "2", 12, 1, "", None, ""),
                 ("20260223", "名古屋", "交流特別", "特別", "ダ1500m", "", "1", 12, 1, "", None, "")],
 "クールブロン": [("20261031", "東京", "ペルセウスステークス", "OP", "ダ1600m", "良", "5", 16, 6, "", None, "")],
 "アピーリングルック": [("20261006", "大井", "特別", "特別", "ダ1800m", "", "5", 14, 5, "", None, ""), ("20260708", "川崎", "特別", "特別", "ダ1600m", "", "3", 14, 2, "", None, ""),
                     ("20260513", "川崎", "特別", "特別", "ダ2100m", "", "5", 14, 3, "", None, ""), ("20260211", "船橋", "特別", "特別", "ダ1800m", "", "4", 14, 3, "", None, ""),
                     ("20251224", "名古屋", "特別", "特別", "ダ2000m", "", "1", 12, 5, "", None, "")],
 "エンペラーワケア": [("20250904", "佐賀", "サマーチャンピオン", "Jpn3", "ダ1400m", "", "2", 12, 1, "", None, ""), ("20250625", "浦和", "さきたま杯", "Jpn1", "ダ1400m", "", "3", 12, 3, "", None, ""),
                   ("20250325", "高知", "黒船賞", "Jpn3", "ダ1400m", "", "3", 12, 1, "", None, "")],
 "ジェイパームス": [("20261031", "東京", "ペルセウスステークス", "OP", "ダ1600m", "良", "1", 16, 3, "", None, "")],
 "ロックターミガン": [("20261007", "大井", "ジャパンダートクラシック", "Jpn1", "ダ2000m", "", "6", 16, 7, "", None, ""), ("20260901", "盛岡", "不来方賞", "Jpn2", "ダ2000m", "", "2", 12, 3, "", None, ""),
                   ("20260610", "大井", "東京ダービー", "Jpn1", "ダ2000m", "", "4", 16, 3, "", None, ""), ("20260429", "大井", "羽田盃", "Jpn1", "ダ1800m", "", "2", 16, 1, "", None, ""),
                   ("20260325", "大井", "京浜盃", "Jpn2", "ダ1700m", "", "1", 16, 2, "", None, "")],
 "ハセドン": [("20261031", "東京", "ペルセウスステークス", "OP", "ダ1600m", "良", "10", 16, 14, "", None, "")],
 "スマートピナクル": [("20261024", "京都", "2歳新馬", "新馬", "芝1600m", "稍重", "1", 14, 1, "", 1, "456")],
 "コルサロ": [("20261025", "京都", "2歳未勝利", "未勝利", "芝1600m", "重", "1", 16, 4, "", None, "436")],
}

def style_of(corner, n):
    if not corner or not n: return None
    try: p = [int(x) for x in str(corner).split("-")]
    except ValueError: return None
    c = p[-2] if len(p) >= 2 else p[-1]
    if c <= 2: return "逃げ"
    if c <= max(3, n * 0.3): return "先行"
    if c <= n * 0.6: return "中団"
    return "後方"

def main():
    names = {h[2] for r in RACES.values() for h in r["horses"]}
    runs = collections.defaultdict(list)
    for f in sorted(SRC.glob("results_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            if r["馬名"] in names and r.get("着順int"):
                runs[r["馬名"]].append(dict(date=r["date"], venue=r["競馬場"], race=r["レース名"] or r["条件"], cond=str(r.get("条件", "")), dist=r["距離"],
                    baba=r["馬場状態"], fin=str(r["着順int"]), n=r.get("頭数"), pop=r.get("人気"), corner=r.get("コーナー通過", ""), f3=r.get("後3F"),
                    f3rank=r.get("後3F順位"), weight=r.get("馬体重", ""), kin=r.get("斤量_kg"), jockey=r.get("騎手", ""), hid=r.get("horse_id", "")))
    for nm, L in MANUAL.items():
        for (d, v, rc, cd, ds, bb, fin, n, pop, corner, f3r, w) in L:
            runs[nm].append(dict(date=d, venue=v, race=rc, cond=cd, dist=ds, baba=bb, fin=fin, n=n, pop=pop, corner=corner, f3=None, f3rank=f3r, weight=w, kin=None, jockey="", hid="", manual=True))
    for race, R in RACES.items():
        out = {"race": {"name": race, "date": "20261114", "venue": R["venue"], "course": f"{R['surf']}{R['dist']}m", "horses": []}, "horses": []}
        for waku, uma, nm, sa, kin, jk, tr in R["horses"]:
            L = sorted(runs.get(nm, []), key=lambda r: r["date"])
            if sa.endswith("2"):   # 2歳馬: 同名の旧馬（例: ヒアカムズザサン 2025年の3歳馬）を除く
                L = [r for r in L if r["date"] >= "20260601"]
            last5 = L[-5:]
            gap = (RACE_DATE - dt.datetime.strptime(L[-1]["date"], "%Y%m%d").date()).days if L else None
            same = [r for r in L if r["venue"] == R["venue"] and r["dist"] == f"{R['surf']}{R['dist']}m"]
            vs = [r for r in L if r["venue"] == R["venue"] and r["dist"].startswith(R["surf"])]
            rec = lambda X: "-".join(str(sum(1 for r in X if int(r["fin"]) == k)) for k in (1, 2, 3)) + "-" + str(sum(1 for r in X if int(r["fin"]) >= 4))
            sty = [style_of(r["corner"], r["n"]) for r in last5]; sty = [s for s in sty if s]
            style = collections.Counter(sty).most_common(1)[0][0] if sty else "不明"
            hid = next((r["hid"] for r in L if r.get("hid")), "")
            out["race"]["horses"].append({"waku": waku, "uma": uma, "name": nm, "status": "出走予定"})
            out["horses"].append(dict(waku=waku, uma=uma, name=nm, sexage=sa, kin=kin, jockey=jk, trainer=tr, hid=hid, starts=len(L), record=rec(L) if L else "",
                                      course=rec(same) if same else "", course_n=len(same), venue_surf=rec(vs) if vs else "", gap=gap, style=style, last5=last5,
                                      manual_runs=sum(1 for r in L if r.get("manual"))))
        p = H / f"entry_digest_{race}.json"; p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"■ {race}（{R['venue']}{R['surf']}{R['dist']}m）")
        for h in out["horses"]:
            l5 = " / ".join(f"{r['date'][4:6]}.{r['date'][6:]} {r['race'][:8]} {r['fin']}着({r['pop']}人)" for r in h["last5"][::-1])
            print(f"  {h['uma']:>2} {h['name']:<10} {h['starts']}戦 {h['record']:<9} 同コース{h['course'] or '-':<9} 間隔{h['gap']}日 {h['style']} ｜ {l5}")
        print(f"→ {p.name}")

if __name__ == "__main__":
    main()
