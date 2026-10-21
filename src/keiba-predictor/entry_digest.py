# -*- coding: utf-8 -*-
"""
entry_digest.py — 重賞の登録馬（JRA-VAN 特別登録 TK）について、1頭ずつ材料を集める（2026-10-08新規・§3b ③の道具）
==========================================================================================================
枠順・オッズが出る前（登録段階）に、各馬の「レース前に分かる」材料を JRA-VAN のデータだけで並べる。印・買い目は出さない。
  ・近5走: 日付・場・距離・馬場・着順/頭数・人気・着差・通過順・上がり3F（順位）・馬体重・斤量
  ・このコース（場×芝ダ×距離±200m）とこの場の芝ダの成績、前走からの間隔、今回の斤量と前走の斤量
  ・想定脚質（直近5走の通過順から。結果の脚質ではない）
  ・調教: 直近14日の最速（その日・そのトレセンの中央値との差。マイナスほど速い）と、その馬のふだん（過去1年の中央値）との差
  ・目印（理由つき）: 前走で上がり3位以内なのに4着以下／前走人気より大きく上の着順／前走が重賞で僅差／休み明け（90日超）／初コース など
入力: C:/keiba_db/jv_raw_new/TOKU/TK_{年}.txt（jv_extract.ps1 -Spec TOKU -From {週初}000000 -Option 1 -Keep TK -OutDir C:\\keiba_db\\jv_raw_new）
出力: Desktop/競馬予想レポート/{日付}/research/entry_digest_{レース名}.json と .md
使い方: python entry_digest.py --from 20261010 --to 20261012 [--grade ABC]（A=G1 B=G2 C=G3 L=リステッド）
"""
from __future__ import annotations
import argparse, collections, datetime, json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import target_import as T
import jv_odds as J
import chokyo

BASE = Path.home() / "Desktop" / "競馬予想レポート"
H = BASE / "daily_pdca" / "db" / "history_target"
TK_LEN = 21657
GRADE = {"A": "G1", "B": "G2", "C": "G3", "L": "L"}
TRACK_SURF = lambda c: "芝" if c.startswith("1") else "ダ" if c.startswith("2") else "障"


def registrations(d0, d1, grades):
    out = []
    for f in sorted(Path("C:/keiba_db/jv_raw_new/TOKU").glob("TK_*.txt")):
        b = f.read_bytes()
        for i in range(0, len(b) - TK_LEN + 1, TK_LEN):
            r = b[i:i + TK_LEN]
            s = lambda a, n: T.seg(r, a, n)
            date, g = s(12, 8), s(615, 1)
            if not (d0 <= date <= d1) or g not in grades:
                continue
            horses = []
            for j in range(int(s(653, 3) or 0)):
                o = 656 + 70 * j
                horses.append(dict(hid=s(o + 3, 10), name=s(o + 13, 36), sex={"1": "牡", "2": "牝", "3": "セ"}.get(s(o + 51, 1), "?"),
                                   trainer=s(o + 58, 8), kin=int(s(o + 66, 3) or 0) / 10))
            out.append(dict(date=date, venue=J.VENUE.get(s(20, 2)), R=int(s(26, 2)), name=s(33, 60), grade=GRADE.get(g, g),
                            dist=int(s(637, 4)), surf=TRACK_SURF(s(641, 2)), made=s(4, 8), horses=horses))
    best = {}
    for x in out:                                    # 同じレースは作成日の新しい版だけ
        k = (x["date"], x["venue"], x["R"])
        if k not in best or x["made"] >= best[k]["made"]:
            best[k] = x
    for x in best.values():                          # 出走表（JV 0B15 → RT/entry）が出ていれば、実際に出る馬だけに絞って騎手を足す
        f = Path("C:/keiba_db/jv_raw/RT/entry") / f"SE_{x['date']}.txt"
        if not f.exists():
            continue
        b, ent = f.read_bytes(), {}
        for i in range(0, len(b) - 554, 555):
            e = T.parse_se(b[i:i + 555], entry=True)
            if e and e["venue"] == x["venue"] and e["R"] == x["R"]:
                ent[e["hid"]] = e
        if ent:
            x["horses"] = [dict(h, jockey=ent[h["hid"]]["jockey"], kin=ent[h["hid"]]["kin"], uma=ent[h["hid"]]["uma"]) for h in x["horses"] if h["hid"] in ent]
            x["fixed"] = True
    return sorted(best.values(), key=lambda x: (x["date"], x["venue"]))


def dnum(s):
    try:
        return int(str(s).replace("m", "")[1:])
    except ValueError:
        return None


def corner_first(c):
    xs = [int(x) for x in str(c or "").replace("-", " ").split() if x.isdigit()]
    return xs[0] if xs else None


def style_guess(runs):
    rel = [corner_first(r.get("コーナー通過")) / max(1, int(r.get("頭数") or 0)) for r in runs if corner_first(r.get("コーナー通過")) and r.get("頭数")]
    if len(rel) < 2:
        return "不明"
    m = statistics.mean(rel)
    return "逃げ・先行" if m <= 0.25 else "好位" if m <= 0.45 else "中団" if m <= 0.65 else "後方"


def main(A):
    races = registrations(A.frm, A.to, set(A.grade))
    if not races:
        print("登録データなし（TOKU を取り直す）"); return
    need = {h["hid"] for x in races for h in x["horses"]}
    runs = collections.defaultdict(list)
    for y in range(2019, int(A.to[:4]) + 1):
        f = H / f"results_{y}.json"
        if f.exists():
            for r in json.loads(f.read_text(encoding="utf-8")):
                if r.get("horse_id") in need:
                    runs[r["horse_id"]].append(r)
    CK = chokyo.load()
    for x in races:
        d0 = datetime.date(int(x["date"][:4]), int(x["date"][4:6]), int(x["date"][6:]))
        md = [f"# {x['name']}（{x['grade']}）{x['date'][4:6]}/{x['date'][6:]} {x['venue']} {x['surf']}{x['dist']}m {'出走' if x.get('fixed') else '登録'}{len(x['horses'])}頭\n",
              "数字は JRA-VAN の成績・調教データ。印・買い目は枠順とオッズが出てから。\n"]
        rows = []
        for h in x["horses"]:
            rs = sorted((r for r in runs[h["hid"]] if r["date"] < x["date"]), key=lambda r: (r["date"], r["R"]))
            last5 = rs[-5:]
            sd = lambda r: dnum(r["距離"])
            course = [r for r in rs if r["競馬場"] == x["venue"] and str(r["距離"])[:1] == x["surf"] and sd(r) and abs(sd(r) - x["dist"]) <= 200]
            vsurf = [r for r in rs if r["競馬場"] == x["venue"] and str(r["距離"])[:1] == x["surf"]]
            rec = lambda L: f"{sum(1 for r in L if r.get('着順int') == 1)}-{sum(1 for r in L if r.get('着順int') == 2)}-{sum(1 for r in L if r.get('着順int') == 3)}-{sum(1 for r in L if (r.get('着順int') or 99) > 3)}"
            prev = rs[-1] if rs else None
            gap = (d0 - datetime.date(int(prev["date"][:4]), int(prev["date"][4:6]), int(prev["date"][6:]))).days if prev else None
            # 調教
            ck = CK.get(h["hid"]) or []
            lim14 = (d0 - datetime.timedelta(days=16)).strftime("%Y%m%d")
            lim365 = (d0 - datetime.timedelta(days=365)).strftime("%Y%m%d")
            # 比べ方: その馬がレース前にふだん使うコース（坂路／ウッド）だけで、生の時計を「過去のレース前（直近8走それぞれの前16日）の最速」の中央値と比べる。
            #   ・坂路とウッドは時計の尺度が違うので混ぜない ・全調教の中央値と比べると軽めの調整が混ざって誰でも速く見える（2026-10-08に2回直した）
            per = collections.defaultdict(list)
            for pr in rs[-8:]:
                pd = datetime.date(int(pr["date"][:4]), int(pr["date"][4:6]), int(pr["date"][6:]))
                lo = (pd - datetime.timedelta(days=16)).strftime("%Y%m%d")
                pk = collections.defaultdict(list)
                for c in ck:
                    if lo <= c[0] < pr["date"]:
                        pk[c[1]].append(c[2])
                for k, v in pk.items():
                    per[k].append(min(v))
            recent = [c for c in ck if c[0] >= lim14]
            kinds = sorted({c[1] for c in recent}, key=lambda k: -len(per.get(k, [])))
            kind = kinds[0] if kinds else None
            best = min((c for c in recent if c[1] == kind), key=lambda c: c[2]) if kind else None
            usual = per.get(kind, [])
            week = (d0 - datetime.timedelta(days=7)).strftime("%Y%m%d")
            final_done = any(c[0] >= week and c[1] == kind for c in ck)
            ck_txt = ("直近の記録なし" if not best else
                      f"{best[1]} {best[2]}秒（{best[0][4:6]}/{best[0][6:]}）" + (f"・過去のレース前の最速の中央値 {statistics.median(usual):.1f}秒" if usual else "")
                      + ("" if final_done else "・今週の最終追い切りはまだ"))
            ck_up = round(best[2] - statistics.median(usual), 2) if best and len(usual) >= 3 and final_done else None
            flags = []
            if prev:
                f3, fin, pop = prev.get("後3F順位"), prev.get("着順int"), int(prev.get("人気") or 0)
                if f3 and int(f3) <= 3 and fin and fin >= 4:
                    flags.append(f"前走は上がり{f3}位の脚を使って{fin}着（届かなかっただけ）")
                if fin and pop and pop - fin >= 4 and fin <= 5:      # 15番人気11着のような「負けたが人気よりは上」は目印にしない
                    flags.append(f"前走は{pop}番人気で{fin}着（人気より走った）")
                if fin and pop and fin - pop >= 5 and pop <= 3:
                    flags.append(f"前走は{pop}番人気で{fin}着の大敗（巻き返しか下降か要確認）")
                if gap and gap > 90:
                    flags.append(f"休み明け（{gap}日）")
            if not vsurf:
                flags.append(f"{x['venue']}{x['surf']}は初めて")
            if ck_up is not None and ck_up <= -1.0:
                flags.append(f"調教が過去のレース前より{-ck_up:.1f}秒速い（上向き）")
            row = dict(hid=h["hid"], name=h["name"], sex=h["sex"], kin=h["kin"], trainer=h["trainer"], jockey=h.get("jockey"), starts=len(rs),
                       record=rec(rs), course=rec(course), venue_surf=rec(vsurf), gap=gap, style=style_guess(last5), chokyo=ck_txt, chokyo_up=ck_up,
                       flags=flags, last5=[dict(date=r["date"], venue=r["競馬場"], race=r["レース名"] or r["条件"], cond=str(r["条件"])[:2], dist=r["距離"], baba=r["馬場状態"],
                                                fin=r.get("着順"), n=r.get("頭数"), pop=r.get("人気"), margin=r.get("着差"), corner=r.get("コーナー通過"),
                                                f3=r.get("後3F"), f3rank=r.get("後3F順位"), weight=r.get("馬体重"), kin=r.get("斤量_kg"), jockey=r.get("騎手")) for r in last5])
            rows.append(row)
            md.append(f"## {h['name']}（{h['sex']}・{h['kin']:.0f}kg・{h['trainer']}" + (f"・{h['jockey']}" if h.get("jockey") else "") + "）")
            md.append(f"- 通算 {row['record']} ／ このコース {row['course']} ／ {x['venue']}{x['surf']} {row['venue_surf']} ／ 間隔 {gap if gap is not None else '-'}日 ／ 想定脚質 {row['style']}")
            md.append(f"- 調教: {ck_txt}")
            for r in reversed(row["last5"]):
                md.append(f"  - {r['date'][2:4]}/{r['date'][4:6]}/{r['date'][6:]} {r['venue']} {r['race'][:14]} {r['dist']} {r['baba']} "
                          f"{r['fin']}着/{r['n']}頭 {r['pop']}人気 通過{r['corner'] or '-'} 上がり{r['f3'] or '-'}({r['f3rank'] or '-'}位) {r['weight'] or ''} {r['kin']}kg {r['jockey']}")
            if flags:
                md.append("- 目印: " + "／".join(flags))
            md.append("")
        out = BASE / x["date"] / "research"
        out.mkdir(parents=True, exist_ok=True)
        stem = f"entry_digest_{x['name']}"
        (out / f"{stem}.json").write_text(json.dumps(dict(race=x, horses=rows), ensure_ascii=False, indent=1), encoding="utf-8")
        (out / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")
        print(f"■ {x['date']} {x['venue']}{x['R']}R {x['name']}（{x['grade']}）{len(rows)}頭 → {out / (stem + '.md')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--grade", default="ABC")
    main(ap.parse_args())
