# -*- coding: utf-8 -*-
"""
flat_preview.py — 平場の全レースを「人気馬に消し材料があるか」で並べ、印と買い目を出す（2026-10-02新規・汎用）
==========================================================================================================
kaime_core（K1）は検証済みの消し2つ（軽い斤量・馬体重-10kg）だけで期待値を測るので、前日はほぼ全レースが見送りになる。
SNSに出すレースを選ぶ物差しが無かったので、同じ確率の土台の上に **検証中の候補**（db/factor_candidates.json）も
「仮に効くとしたら」で重ねて、レースを並べる。

  確定の消し（prob_core.KESHI）        … 確率に掛ける。K1台帳と同じ
  検証中の候補（距離+400m超・芝ダ変更） … 並べ替えにだけ使う。**確率にも台帳にも入れない**（2回連続通過まで）

並べ方: ◎（確率1位）自身に材料が無く、相手になる上位人気に材料が多いレースほど上。
        仮lift ＝ 候補まで掛けたときの◎の確率 ÷ 市場の確率。1.25を超えて初めて期待値1.0（控除率20%）に届く。
印: 確率の順（◎○▲△△）。材料のある馬は印の横に「消」を付ける
買い目: オッズの形だけで型（1強／拮抗／標準）を決め、相手は候補まで掛けた確率の順（材料のある馬は外さず順位を下げる）。検査は draw_final.kaime_stage と共通

使い方: python flat_preview.py --date 20261003 [--top 6] [--budget 5000]
出力:   {date}/research/flat_preview.json ／ {date}/research/sns_kaime_flat_{date}.json
"""
from __future__ import annotations
import argparse, collections, glob, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from prob_core import market_probs, adjust, KESHI
from prob_core import top3_scenarios, ticket_probs
from draw_final import kaime_stage

BASE = Path.home() / "Desktop" / "競馬予想レポート"
DB = BASE / "daily_pdca" / "db"
# 検証中の候補の仮の倍率（在サンプルの 実測3着内率÷同人気帯の期待値）。確率・台帳には入れない
CAND = {"延長400超": 0.80, "芝ダ変更": 0.86}
GRADE_WORDS = ("G1", "G2", "G3", "(L)", "（L）")


def meters(d):
    n = "".join(c for c in str(d or "") if c.isdigit())
    return int(n) if n else None


def surf(d):
    return "芝" if str(d or "").startswith("芝") else "ダ"


def race_type(tan: dict) -> str:
    """レースの型をオッズの形だけで決める（指数は使わない＝市場に無い情報を持たないため）"""
    o = sorted(tan.values())
    if o[0] < 2.5:
        return "1強"
    if len(o) <= 10 or (o[0] >= 4.0 and len(o) > 3 and o[3] <= 8.0):
        return "拮抗"
    return "標準"


# 型ごとの買い方。struct_backtest.py（確定払戻つき全レース）で比べて決める。変えたら必ず測り直すこと
STRUCTURE = {"1強": "馬単流し", "拮抗": "BOX", "標準": "馬連流し"}


def build_bets(rtype: str, hon: int, aite: list, structure: str | None = None):
    """(見立ての説明, 買い目の組) を返す。aite は相手4頭（確率の順）"""
    st = structure or STRUCTURE[rtype]
    if st == "馬単流し":
        bets = [dict(t="馬単", combo=[hon, u], role="本線" if i < 2 else "相手") for i, u in enumerate(aite[:3])]
        bets.append(dict(t="ワイド", combo=sorted((aite[0], aite[1])), role="本命が飛んだときの保険"))
        view = "1頭が抜けている型。本命を1着に固定して2着を流す"
    elif st == "BOX":
        bets = [dict(t="馬連", combo=sorted(c), role="本線") for c in ((hon, aite[0]), (hon, aite[1]), (aite[0], aite[1]))]
        bets += [dict(t="ワイド", combo=sorted((hon, u)), role="相手") for u in aite[2:4]]
        view = "上位が拮抗している型。上位3頭の馬連BOXを中心にする"
    elif st == "単勝＋馬連流し":
        bets = [dict(t="単勝", combo=[hon], role="本線")]
        bets += [dict(t="馬連", combo=sorted((hon, u)), role="本線" if i < 1 else "相手") for i, u in enumerate(aite[:3])]
        bets.append(dict(t="馬連", combo=sorted((aite[0], aite[1])), role="本命が飛んだときの保険"))
        view = "本命が勝ち切る形を軸に、2着までの相手を3頭"
    elif st == "ワイド流し":
        bets = [dict(t="ワイド", combo=sorted((hon, u)), role="本線" if i < 2 else "相手") for i, u in enumerate(aite)]
        bets.append(dict(t="ワイド", combo=sorted((aite[0], aite[1])), role="本命が飛んだときの保険"))
        view = "本命が3着以内に入る形。相手を4頭に広げる"
    else:
        bets = [dict(t="馬連", combo=sorted((hon, u)), role="本線" if i < 2 else "相手") for i, u in enumerate(aite)]
        bets.append(dict(t="馬連", combo=sorted((aite[0], aite[1])), role="本命が飛んだときの保険"))
        view = "本命が1〜2着に入る形。相手は4頭"
    return view, bets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--budget", type=int, default=5000)
    a = ap.parse_args()

    recs = collections.defaultdict(dict)
    files = sorted(glob.glob(str(BASE / "*" / "週末ビッグデータ_*_records.json")), key=lambda f: Path(f).stat().st_mtime)
    for f in files:                                     # 新しいファイルが後から上書きする
        for r in json.loads(Path(f).read_text(encoding="utf-8"))["records"]:
            if r["date"] == a.date:
                recs[(r["競馬場"], int(r["R"]))][int(r["馬番"])] = r
    last = collections.defaultdict(list)                # 前走（距離変化・芝ダ変更の判定用）
    for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8")):
        if r.get("馬名") and r["date"] < a.date:
            last[r["馬名"]].append((r["date"], r.get("距離")))
    from odds_snapshot import latest_snapshots       # 取得時刻で最新を選ぶ
    latest = {rid: str(f) for rid, f in latest_snapshots(a.date).items()}

    rows = []
    for rid, f in sorted(latest.items()):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        key = (d["venue"], int(d["R"]))
        rec = recs.get(key, {})
        tan = {int(k): float(v[0]) for k, v in d["odds"].get("単勝", {}).items() if v and v[0]}
        tan = {u: o for u, o in tan.items() if o < 900}
        names = {h["umaban"]: h["horse_name"] for h in d["horses"].values()}
        if len(tan) < 5 or any(rec.get(u, {}).get("馬名") != names.get(u) for u in tan):
            continue
        any_rec = next(iter(rec.values()))
        title = any_rec.get("レース名", "")
        cur = any_rec.get("距離")
        flags, cand = {}, {}
        for u in tan:
            r = rec[u]
            wm = re.search(r"\(([+-]?\d+)\)", str(d["horses"].get(f"{u:02d}", {}).get("weight") or ""))
            flags[u] = {"kin70": float(r.get("F10_斤量") or 0) >= 70,
                        "wt_m10": bool(wm) and int(wm.group(1)) <= -10}     # 馬体重は発表後のスナップショットにだけ入る
            hist = sorted(last.get(r["馬名"], []))
            c = []
            jump = str(cur).startswith("障") or (hist and str(hist[-1][1] or "").startswith("障"))
            if hist and hist[-1][1] and not jump:      # 障害戦は芝ダの区別が無いので対象外
                if surf(hist[-1][1]) != surf(cur):
                    c.append("芝ダ変更")
                elif meters(cur) and meters(hist[-1][1]) and meters(cur) - meters(hist[-1][1]) > 400:
                    c.append("延長400超")
            cand[u] = c
        q = market_probs(tan)
        p = adjust(q, flags)
        ph = {u: v * (1.0 if not cand[u] else min(CAND[x] for x in cand[u])) for u, v in p.items()}
        s = sum(ph.values())
        ph = {u: v / s for u, v in ph.items()}
        order = sorted(p, key=lambda u: -p[u])
        pop = {u: i + 1 for i, u in enumerate(sorted(tan, key=lambda u: tan[u]))}
        hon = order[0]
        t3 = {k[0]: v for k, v in ticket_probs(top3_scenarios(p), p)["複勝"].items()}
        score = {u: float(rec[u].get("総合指数") or 0) for u in tan}
        rtype = race_type(tan)
        mat = {u: (["斤量"] if flags[u]["kin70"] else []) + (["馬体重"] if flags[u]["wt_m10"] else []) + cand[u] for u in tan}
        rows.append(dict(
            race_id=rid, venue=d["venue"], R=int(d["R"]), title=title, course=cur, n=len(tan),
            grade=any(w in title for w in GRADE_WORDS), young=("新馬" in title or "未勝利" in title),
            hon=hon, hon_clean=not mat[hon], lift_k1=round(p[hon] / q[hon], 3), lift_hyp=round(ph[hon] / q[hon], 3),
            flagged_top5=[u for u in sorted(tan, key=lambda u: tan[u])[:5] if mat[u] and u != hon],
            pattern=rtype,
            horses=[dict(umaban=u, name=names[u], odds=tan[u], pop=pop[u], q=round(q[u], 4), p=round(p[u], 4),
                         p_top3=round(t3[u], 4), index=score[u], style=rec[u].get("脚質"), jockey_wr=rec[u].get("騎手勝率%"),
                         waku=rec[u].get("枠"), material=mat[u]) for u in sorted(tan)],
            p_order=order, ph_order=sorted(ph, key=lambda u: -ph[u])))

    rows.sort(key=lambda r: (-(r["hon_clean"]), -r["lift_hyp"]))
    print(f"■ {a.date} 全{len(rows)}レース  ◎に材料なし・相手に材料あり の順（仮lift 1.25で期待値1.0）")
    print(f"{'場R':<7}{'レース':<16}{'頭':>3} {'型':<3}{'◎':>3}{'人気':>3}{'ｵｯｽﾞ':>6}{'K1':>7}{'仮lift':>7}  材料のある上位人気")
    for r in rows:
        H = {h["umaban"]: h for h in r["horses"]}
        h = H[r["hon"]]
        fl = " ".join(f"{u}{H[u]['name'][:5]}({'/'.join(H[u]['material'])})" for u in r["flagged_top5"])
        tag = "" if r["hon_clean"] else " ※◎に材料"
        print(f"{r['venue']}{r['R']:>2}R {r['title'][:14]:<16}{r['n']:>3} {r['pattern']:<3}{r['hon']:>3}{h['pop']:>3}{h['odds']:>6.1f}"
              f"{r['lift_k1']:>7.3f}{r['lift_hyp']:>7.3f}  {fl}{tag}")

    # ── 上位レースの印と買い目 ────────────────────────────────────────
    pick = [r for r in rows if r["hon_clean"] and not r["grade"] and r["flagged_top5"]]
    young = 0
    chosen = []
    for r in pick:                                     # 若馬戦（新馬・未勝利）は1日2レースまで
        if r["young"]:
            if young >= 2:
                continue
            young += 1
        chosen.append(r)
        if len(chosen) >= a.top:
            break
    out_races, spec = [], {"compiled": a.date, "stage": "前日版（予想オッズ）", "budget": a.budget, "races": {}}
    for r in chosen:
        H = {h["umaban"]: h for h in r["horses"]}
        # 相手は「候補まで掛けた確率」の順。材料は確率を数%〜2割下げるだけなので、外すのではなく順位を下げる
        hon = r["hon"]
        aite = [u for u in r["ph_order"] if u != hon][:4]
        rtype = race_type({h["umaban"]: h["odds"] for h in r["horses"]})
        view, bets = build_bets(rtype, hon, aite)
        name = f"{r['venue']}{r['R']}R {r['title']}"
        spec["races"][name] = dict(view=view, marks={"◎": hon, "○": aite[0], "▲": aite[1],
                                          "△": [u for u in aite[2:4] if any(u in x["combo"] for x in bets)], "🔥": None},
                                   caution=r["flagged_top5"], bets=bets)
        out_races.append(dict(name=name, horses=[dict(h) for h in r["horses"]]))
    D = BASE / a.date / "research"
    D.mkdir(parents=True, exist_ok=True)
    (D / "flat_preview.json").write_text(json.dumps(dict(date=a.date, keshi=KESHI, candidates_hypothetical=CAND,
                                                         races=rows, chosen=[f"{r['venue']}{r['R']}R" for r in chosen]),
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存: {D / 'flat_preview.json'}")
    for r in chosen:
        H = {h["umaban"]: h for h in r["horses"]}
        print(f"\n● {r['venue']}{r['R']}R {r['title']} {r['course']} {r['n']}頭")
        for u in r["p_order"][:7]:
            h = H[u]
            print(f"   {u:>2} {h['name']:<12}{h['pop']:>2}人気{h['odds']:>6.1f}倍 勝{h['p']*100:>5.1f}% 3着内{h['p_top3']*100:>5.1f}% "
                  f"指数{h['index']:>5.1f} {h['style'] or '?'} {'消:' + '/'.join(h['material']) if h['material'] else ''}")
    kaime_stage(dict(races=out_races, odds_note="発売前の予想オッズ"), spec, D / f"sns_kaime_flat_{a.date}.json")


if __name__ == "__main__":
    main()
