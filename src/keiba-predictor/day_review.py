# -*- coding: utf-8 -*-
"""
day_review.py — その日の結果を JV-Link（速報・成績）から取り込み、①馬場・脚質・枠・ペース・時計の特徴 ②自分の予想の答え合わせ を出す（2026-10-03新規）
使い方: 32bit PowerShell で jv/jv_rt.ps1 -Spec 0B12 -Key YYYYMMDD → python day_review.py --date YYYYMMDD
出力: {日付}/research/day_review_{日付}.json ／ {日付}/{日付}_振り返り.md
"""
from __future__ import annotations
import argparse, collections, json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import target_import as T
import ev_engine as E
import predict_day as P

BASE = P.BASE
RT = Path("C:/keiba_db/jv_raw/RT")


def sec(t):
    try:
        m, s = str(t).split(":")
        return int(m) * 60 + float(s)
    except Exception:
        return None


def surf(d):
    return d[:1]


def fmt(v, spec="+.1f"):
    return "" if v is None else format(v, spec)


def load_day(date):
    ras, ses, pay = {}, {}, {}
    b = (RT / f"RA_{date}.txt").read_bytes()
    for i in range(0, len(b) - 1271, 1272):
        x = T.parse_ra(b[i:i + 1272])
        if x and x["R"]:
            ras[(x["date"], x["venue"], x["R"])] = x
    b = (RT / f"SE_{date}.txt").read_bytes()
    for i in range(0, len(b) - 554, 555):
        x = T.parse_se(b[i:i + 555])
        if x and x["R"] and x["uma"] and x["date"] == date:
            ses[(x["date"], x["venue"], x["R"], x["uma"])] = x
    b = (RT / f"HR_{date}.txt").read_bytes()
    for i in range(0, len(b) - 718, 719):
        x = T.parse_hr(b[i:i + 719])
        if x:
            pay[(x["venue"], x["R"])] = x["pay"]
    return T.build_rows(ras, ses), pay


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    date = ap.parse_args().date
    rows, pay = load_day(date)
    rows = [r for r in rows if r["着順int"]]
    P.E.SOURCE = P.HIST
    hist = [r for r in E.load_rows() if r["date"] < "20260901" and r.get("着順int")]
    Tn = P.Tends([r for r in hist if r.get("人気")])
    res = dict(date=date, venues={}, races=[], review={})
    out = [f"# {date[:4]}年{int(date[4:6])}月{int(date[6:])}日 振り返り（JRA-VANの成績データ）", ""]
    races = collections.defaultdict(list)
    for r in rows:
        races[(r["競馬場"], r["R"])].append(r)

    ref = collections.defaultdict(list)
    ref2 = collections.defaultdict(list)
    for r in hist:
        if r["着順int"] == 1 and r["馬場状態"] == "良" and sec(r["タイム"]):
            ref[(r["競馬場"], r["距離"], r["条件"])].append(sec(r["タイム"]))
            ref2[(r["競馬場"], r["距離"])].append(sec(r["タイム"]))
    pace_ref = collections.defaultdict(list)
    for r in hist:
        if r["着順int"] == 1 and r.get("前3F_レース") and r.get("後3F_レース"):
            m = int("".join(ch for ch in r["距離"] if ch.isdigit()))
            pace_ref[(surf(r["距離"]), P.band(m))].append(r["前3F_レース"] - r["後3F_レース"])

    race_info = []
    for (v, R), hs in sorted(races.items()):
        h0 = hs[0]
        win = next((h for h in hs if h["着順int"] == 1), None)
        m = int("".join(ch for ch in h0["距離"] if ch.isdigit()))
        base = ref.get((v, h0["距離"], h0["条件"])) or []
        if len(base) < 5:
            base = ref2.get((v, h0["距離"])) or []
        dt = (sec(win["タイム"]) - statistics.mean(base)) if win and len(base) >= 5 and sec(win["タイム"]) else None
        pr = pace_ref.get((surf(h0["距離"]), P.band(m)), [])
        pdiff = (h0["前3F_レース"] - h0["後3F_レース"]) if h0.get("前3F_レース") and h0.get("後3F_レース") else None
        pnorm = (pdiff - statistics.mean(pr)) if pdiff is not None and len(pr) >= 20 else None
        race_info.append(dict(venue=v, R=R, name=h0["レース名"] or h0["条件"], dist=h0["距離"], baba=h0["馬場状態"], weather=h0["天候"], n=len(hs),
                              win_time=win["タイム"] if win else None, dt=dt, f3=h0.get("前3F_レース"), b3=h0.get("後3F_レース"),
                              pace_diff=pdiff, pace_vs_normal=pnorm, win_style=win["脚質"] if win else "", win_pop=win["人気"] if win else None))
    res["races"] = race_info

    out.append("## 1. 競馬場ごとの特徴（今日）")
    out.append("")
    for (v, sf) in sorted({(r["競馬場"], surf(r["距離"])) for r in rows}):
        rs = [x for x in race_info if x["venue"] == v and surf(x["dist"]) == sf]
        sub = [r for r in rows if r["競馬場"] == v and surf(r["距離"]) == sf]
        if not rs:
            continue
        bab = collections.Counter(x["baba"] for x in rs)
        dts = [x["dt"] for x in rs if x["dt"] is not None]
        pns = [x["pace_vs_normal"] for x in rs if x["pace_vs_normal"] is not None]
        sty = {k: Tn.ratio(sub, P.style_of_row, k) for k in ("逃げ", "先行", "差し", "追込")}
        wk = {k: Tn.ratio(sub, P.waku_of_row, k) for k in ("内", "中", "外")}
        win_sty = collections.Counter(r["脚質"] for r in sub if r["着順int"] == 1)
        n1 = sum(1 for r in sub if r["人気"] == 1)
        w1 = sum(1 for r in sub if r["人気"] == 1 and r["着順int"] == 1)
        tm = statistics.mean(dts) if dts else None
        pc = statistics.mean(pns) if pns else None
        res["venues"][f"{v}{sf}"] = dict(races=len(rs), baba=dict(bab), time_vs_normal=tm, pace_vs_normal=pc,
                                         style={k: (x and dict(n=x["n"], ratio=round(x["ratio"], 2))) for k, x in sty.items()},
                                         waku={k: (x and dict(n=x["n"], ratio=round(x["ratio"], 2))) for k, x in wk.items()},
                                         win_style=dict(win_sty), fav_win=f"{w1}/{n1}")
        out.append(f"### {v}{'芝' if sf == '芝' else 'ダート'}（{len(rs)}レース）")
        out.append("- 馬場状態: " + " / ".join(f"{k}{n}R" for k, n in bab.items()))
        if tm is not None:
            out.append(f"- 勝ち時計: 同じコース・距離・クラスの過去の良馬場平均より {tm:+.2f}秒（マイナス＝速い）。" +
                       ("→ 時計が出る馬場" if tm <= -0.4 else "→ 時計がかかる馬場" if tm >= 0.4 else "→ 平均的"))
        if pc is not None:
            out.append(f"- ペース（前3F−後3F）: 同じ距離帯の過去平均より {pc:+.2f}秒 → " +
                       ("速い流れ（差し・追い込み向き）" if pc >= 0.4 else "遅い流れ（前向き）" if pc <= -0.4 else "平均的"))
        out.append("- 脚質（人気から期待される3着内に対する実際の比・「逃げ」は最初のコーナー2番手以内）: " + " ／ ".join(f"{k}{x['ratio']:.2f}倍({x['n']}頭)" for k, x in sty.items() if x))
        out.append("- 枠: " + " ／ ".join(f"{k}{x['ratio']:.2f}倍({x['n']}頭)" for k, x in wk.items() if x))
        out.append(f"- 勝ち馬の脚質: {dict(win_sty)} ／ 1番人気の勝ち {w1}/{n1}")
        out.append("")

    out.append("## 2. 全レース一覧（勝ち時計・ペース）")
    out.append("")
    out.append("| 場R | 条件 | 距離 | 馬場 | 勝ち時計 | 時計差 | 前3F-後3F | ペース差 | 勝ち馬 脚質/人気 |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for x in race_info:
        out.append(f"| {x['venue']}{x['R']} | {(x['name'] or '')[:12]} | {x['dist']} | {x['baba']} | {x['win_time']} | {fmt(x['dt'])} | {fmt(x['pace_diff'])} | {fmt(x['pace_vs_normal'])} | {x['win_style']}/{x['win_pop']}人気 |")

    cf = BASE / date / "research" / f"cards_{date}.json"
    if cf.exists():
        cards = json.loads(cf.read_text(encoding="utf-8"))["cards"]
        fin = {(r["競馬場"], r["R"], r["馬番"]): r["着順int"] for r in rows}
        n, hit3, win = collections.Counter(), collections.Counter(), collections.Counter()
        stake, ret, detail = collections.defaultdict(float), collections.defaultdict(float), []
        for c in cards:
            for k, mk in c["marks"].items():
                f = fin.get((c["venue"], c["R"], int(k)))
                if f:
                    n[mk] += 1; hit3[mk] += f <= 3; win[mk] += f == 1
            if (c["venue"], c["R"]) not in pay:
                continue
            pp = pay[(c["venue"], c["R"])]
            for b in (c["bets"] or c["ref_bets"]):
                key = tuple(b["combo"]) if b["type"] in ("馬単", "3連単") else tuple(sorted(b["combo"]))
                got = pp.get(b["type"], {}).get(key, 0) * b["stake"] / 100.0
                kind = "E2" if c["bets"] else "参考"
                stake[kind] += b["stake"]; ret[kind] += got
                detail.append(dict(venue=c["venue"], R=c["R"], type=b["type"], combo=b["combo"], stake=b["stake"], ret=got, kind=kind))
        out += ["", "## 3. 今日の予想の答え合わせ（新エンジンの印）", "", "| 印 | 頭数 | 勝ち | 3着内 | 3着内率 |", "|---|---|---|---|---|"]
        for mk in ("◎", "○", "▲", "△", "🔥"):
            if n[mk]:
                out.append(f"| {mk} | {n[mk]} | {win[mk]} | {hit3[mk]} | {hit3[mk] / n[mk] * 100:.0f}% |")
        out.append("")
        for kind in ("E2", "参考"):
            if stake[kind]:
                out.append(f"- {kind}の買い目: 賭け金{int(stake[kind]):,}円 → 払戻{int(ret[kind]):,}円（回収率{ret[kind] / stake[kind] * 100:.0f}%）")
        res["review"] = dict(marks={k: dict(n=n[k], win=win[k], top3=hit3[k]) for k in n}, bets=detail,
                             roi={k: dict(stake=stake[k], ret=ret[k]) for k in stake})
    (BASE / date / "research").mkdir(parents=True, exist_ok=True)
    (BASE / date / "research" / f"day_review_{date}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (BASE / date / f"{date}_振り返り.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
