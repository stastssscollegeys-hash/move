# -*- coding: utf-8 -*-
"""
postmortem_all.py — このスキル（v5.1）で事前予想を出して結果を見た全レースを、1レースずつ振り返る（2026-11-01新規・ユーザー指示）
===============================================================================================================
ユーザー指示: 的中したレースは何が良くて当たったのか（その馬を評価した理由・買い目の根拠）、外れたレースは事前予想とのずれ（印か買い目か展開か）を、
一つずつ分析して次につなげる。今日だけでなく、事前予想→結果を見たレース全部で。
・対象: カード（cards_{日付}.json・cards_versions）が残る 2026-10-03 以降の全日。事前予想は各レースの「発走5分前までの最後の版」（発走時刻は JV の RA）
  版が無い日は cards_{日付}.json（作成時刻が発走前のもの）を使う
・成績・払戻: JV速報（RT の RA/SE/HR）。買い目は版に残っている ref_bets（標準）／bets（E2）。実際には買っていない（参考）
・外れの分類（レースごとに1つ）:
    A 印の見落とし : 勝ち馬に印が無い（勝ち馬の人気・割安さ順位も記録）
    B 軸が来ない   : 勝ち馬に印はあるが◎が3着内に入らない（◎の着順・人気）
    C 形が合わない : ◎は3着内に来たが、買い目の形（券種・組み合わせ）が当たらなかった
    D 印の上位が決着 : 買い目に入っていた馬だけで決着したのに取りこぼした（3着内の3頭が全部、買い目の馬）
  的中は、的中した券種と、当たった馬の印・人気・評価理由（カードの reasons）を残す
・出力: docs/keiba_postmortem_all.md（集計）と、Desktop の 20261101/research/postmortem_all.json（1レースずつ）
使い方: python postmortem_all.py
"""
from __future__ import annotations
import collections, datetime, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import day_review as DR
import target_import as T

BASE = Path.home() / "Desktop" / "競馬予想レポート"
RT = Path("C:/keiba_db/jv_raw/RT")
DATES = ["20261003", "20261004", "20261011", "20261012", "20261017", "20261018", "20261024", "20261025", "20261031", "20261101"]


def post_times(d):
    out = {}
    for f in (RT / "entry" / f"RA_{d}.txt", RT / f"RA_{d}.txt"):
        if not f.exists():
            continue
        b = f.read_bytes()
        for i in range(0, len(b) - 1271, 1272):
            r = b[i:i + 1272]
            x = T.parse_ra(r)
            if not x or x["date"] != d or not x["R"]:
                continue
            hm = r[873:877].decode("ascii", "ignore")
            if hm.isdigit() and (x["venue"], x["R"]) not in out:
                out[(x["venue"], x["R"])] = datetime.datetime.strptime(d + hm, "%Y%m%d%H%M")
    return out


def pre_race_cards(d):
    """{(場,R): カード}。各レースの発走5分前までの最後の版。版が無ければ cards_{d}.json"""
    pt = post_times(d)
    cards = {}
    base = BASE / d / "research" / f"cards_{d}.json"
    if base.exists():
        for c in json.loads(base.read_text(encoding="utf-8"))["cards"]:
            cards[(c["venue"], int(c["R"]))] = (c, "最終版")
    vers = sorted((BASE / d / "research" / "cards_versions").glob(f"cards_{d}_*.json"))
    best = {}
    for f in vers:
        hm = f.stem.split("_")[-1]
        t = datetime.datetime.strptime(d + hm, "%Y%m%d%H%M")
        for c in json.loads(f.read_text(encoding="utf-8"))["cards"]:
            k = (c["venue"], int(c["R"]))
            if k in pt and t <= pt[k] - datetime.timedelta(minutes=5):
                best[k] = (c, f"版{hm}")
    cards.update(best)
    return cards


def pay_of(pp, t, combo):
    key = tuple(combo) if t in ("馬単", "3連単") else tuple(sorted(combo))
    v = pp.get(t, {})
    if t in ("単勝", "複勝"):
        return v.get(combo[0], v.get(str(combo[0]), 0))
    return v.get(key, v.get("-".join(map(str, key)), 0))


def main():
    races = []
    for d in DATES:
        try:
            rows, pay = DR.load_day(d)
        except FileNotFoundError:
            print(d, "成績なし"); continue
        by = collections.defaultdict(list)
        for r in rows:
            if r["着順int"]:
                by[(r["競馬場"], r["R"])].append(r)
        cards = pre_race_cards(d)
        for k, (c, src) in sorted(cards.items()):
            hs = by.get(k)
            if not hs or not c["marks"]:
                continue
            H = {int(h["uma"]): h for h in c["horses"]}
            fin = {h["馬番"]: h["着順int"] for h in hs}
            pop = {h["馬番"]: h["人気"] for h in hs}
            order = sorted(fin, key=lambda u: fin[u])
            top3 = order[:3]
            marks = {int(u): m for u, m in c["marks"].items()}
            hon = next((u for u, m in marks.items() if m == "◎"), None)
            bets = c["bets"] or c["ref_bets"]
            kind = "E2" if c["bets"] else "標準"
            pp = pay.get(k, {})
            stake = sum(b["stake"] for b in bets)
            ret = hits = 0
            hit_types = []
            for b in bets:
                got = pay_of(pp, b["type"], b["combo"]) * b["stake"] / 100.0
                if got > 0:
                    hits += 1; hit_types.append(f"{b['type']}{'-'.join(map(str, b['combo']))}")
                ret += got
            win = order[0]
            bet_horses = {u for b in bets for u in b["combo"]}
            # 外れ（収支マイナス）の分類
            cause = ""
            if ret < stake:
                if win not in marks:
                    cause = "A 印の見落とし"
                elif hon is None or fin.get(hon, 99) > 3:
                    cause = "B 軸が来ない"
                elif set(top3) <= bet_horses:
                    cause = "D 印の上位が決着"
                else:
                    cause = "C 形が合わない"
            rk = {h["uma"]: i for i, h in enumerate(sorted(c["horses"], key=lambda h: -h["ratio"]), 1)} if c["horses"] else {}
            rs_ = {}
            for u, m in marks.items():
                if u in H and u in fin:
                    cats = set()
                    for t in (H[u].get("reasons_all") or H[u].get("reasons") or []):
                        t = str(t)
                        cats.add(t.split(":")[0].split("：")[0][:14] if ":" in t or "：" in t else t[:10])
                    rs_[str(u)] = dict(mark=m, fin=fin[u], pop=pop.get(u), cats=sorted(cats))
            races.append(dict(reasons=rs_, 
                date=d, venue=k[0], R=k[1], name=re.split(r" 出馬表|\|", c.get("name") or "")[0].strip()[:20], grade=c.get("grade"), n=len(hs), src=src, kind=kind,
                pattern=(bets[0].get("pattern") if bets else None) or "旧標準(V1.1)",
                shobu=bool(c.get("shobu")), marks={str(u): m for u, m in marks.items()}, top3=top3, top3_pop=[pop.get(u) for u in top3],
                top3_mark=[marks.get(u, "") for u in top3], win_ratio_rank=rk.get(win), hon=hon, hon_fin=fin.get(hon), hon_pop=pop.get(hon),
                stake=stake, ret=ret, hit_types=hit_types, cause=cause,
                win_reason=(H[win]["reasons"][:3] if win in H and win in marks else None)))
    out = BASE / "20261101" / "research" / "postmortem_all.json"
    out.write_text(json.dumps(races, ensure_ascii=False, indent=1), encoding="utf-8")
    report(races)


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "-"


def report(rs):
    n = len(rs)
    st, rt = sum(r["stake"] for r in rs), sum(r["ret"] for r in rs)
    L = ["# 事前予想→結果の全レース振り返り（v5.1・2026-10-03〜11-01）", "",
         f"対象 {n}レース／{len(set(r['date'] for r in rs))}日。事前予想=各レースの発走5分前までの最後の版。買い目は参考（標準）とE2の合算（実際には買っていない）。",
         f"買い目の合計: {int(st):,}円 → {int(rt):,}円（回収率 {rt / st * 100:.1f}%）", ""]
    # ── 的中 ──
    hit = [r for r in rs if r["ret"] >= r["stake"]]
    ok_any = [r for r in rs if r["hit_types"]]
    L += [f"## 1. 的中・収支プラスのレース（{len(hit)}/{n} = {pct(len(hit), n)}）／何か当たった {len(ok_any)}（{pct(len(ok_any), n)}）", ""]
    ha = collections.Counter(); hb = collections.Counter()
    for r in hit:
        ha[r["pattern"]] += 1
        hb["勝ち馬が◎" if r["top3_mark"][0] == "◎" else ("勝ち馬が○▲" if r["top3_mark"][0] in "○▲" else ("勝ち馬が△🔥" if r["top3_mark"][0] else "印なし"))] += 1
    L += ["- 型別: " + " ／ ".join(f"{k} {v}" for k, v in ha.most_common()), "- 勝ち馬の印: " + " ／ ".join(f"{k} {v}" for k, v in hb.most_common()), ""]
    L += ["| 日付 | レース | 型 | 勝ち馬の印・人気 | 当たった券種 | 賭け→払戻 |", "|---|---|---|---|---|---|"]
    for r in sorted(hit, key=lambda r: -(r["ret"] - r["stake"]))[:15]:
        L.append(f"| {r['date']} | {r['venue']}{r['R']}R {r['name']} | {r['pattern']} | {r['top3_mark'][0] or '印なし'}・{r['top3_pop'][0]}人気 | {'、'.join(r['hit_types'][:3])} | {int(r['stake']):,}→{int(r['ret']):,} |")
    L.append("")
    # ── 外れの分類 ──
    miss = [r for r in rs if r["cause"]]
    cc = collections.Counter(r["cause"] for r in miss)
    L += [f"## 2. 外れ（収支マイナス）の分類（{len(miss)}レース）", "", "| 原因 | レース数 | 割合 | 平均の勝ち馬人気 | ◎の平均着順 |", "|---|---|---|---|---|"]
    for k in ("A 印の見落とし", "B 軸が来ない", "C 形が合わない", "D 印の上位が決着"):
        sub = [r for r in miss if r["cause"] == k]
        if sub:
            wp = [r["top3_pop"][0] for r in sub if r["top3_pop"][0]]
            hf = [r["hon_fin"] for r in sub if r["hon_fin"]]
            L.append(f"| {k} | {len(sub)} | {pct(len(sub), len(miss))} | {sum(wp) / len(wp):.1f} | {sum(hf) / len(hf):.1f} |")
    L.append("")
    a = [r for r in miss if r["cause"].startswith("A")]
    if a:
        rr = [r["win_ratio_rank"] for r in a if r["win_ratio_rank"]]
        L.append(f"- A（印の見落とし）の勝ち馬: 人気の中央値 {sorted(r['top3_pop'][0] for r in a if r['top3_pop'][0])[len(a) // 2]}番人気、割安さ順位の中央値 {sorted(rr)[len(rr) // 2] if rr else '-'}位")
    # ── 型別の成績 ──
    L += ["", "## 3. 買い目の型別の成績", "", "| 型 | レース | 賭け | 払戻 | 回収率 | 何か当たる | 収支プラス |", "|---|---|---|---|---|---|---|"]
    bp = collections.defaultdict(list)
    for r in rs:
        bp[r["pattern"]].append(r)
    for k, v in sorted(bp.items(), key=lambda kv: -len(kv[1])):
        s, t = sum(r["stake"] for r in v), sum(r["ret"] for r in v)
        L.append(f"| {k} | {len(v)} | {int(s):,} | {int(t):,} | {t / s * 100:.0f}% | {pct(sum(1 for r in v if r['hit_types']), len(v))} | {pct(sum(1 for r in v if r['ret'] >= r['stake']), len(v))} |")
    # ── ◎の成績・勝ち馬の印 ──
    L += ["", "## 4. 印の見直しの材料", ""]
    w_mark = collections.Counter(("◎" if r["top3_mark"][0] == "◎" else r["top3_mark"][0] or "印なし") for r in rs)
    L.append("- 勝ち馬の印: " + " ／ ".join(f"{k} {v}（{pct(v, n)}）" for k, v in w_mark.most_common()))
    hf = collections.Counter(min(r["hon_fin"], 6) if r["hon_fin"] else 0 for r in rs)
    L.append("- ◎の着順: " + " ／ ".join(f"{('6着以下' if k == 6 else str(k) + '着')} {v}（{pct(v, n)}）" for k, v in sorted(hf.items()) if k))
    pc = collections.Counter(min(r["hon_pop"], 7) for r in rs if r["hon_pop"])
    L.append("- ◎の人気: " + " ／ ".join(f"{('7番人気以下' if k == 7 else str(k) + '番人気')} {v}" for k, v in sorted(pc.items())))
    L += ["", "## 5. 評価の理由（カードの根拠）別に見た、印の馬の3着内率", "", "印のついた全馬(◎○▲△🔥)のうち、その理由が付いていた馬の3着内率と、付いていなかった馬の3着内率。理由の付きやすさの差は人気の差も含む", "",
          "| 理由の種類 | 付いた馬 | 3着内率 | 付かない馬の3着内率 | 差 |", "|---|---|---|---|---|"]
    allh = [v for r in rs for v in r["reasons"].values()]
    base3 = sum(1 for v in allh if v["fin"] <= 3) / len(allh)
    cnt = collections.Counter(c for v in allh for c in v["cats"])
    for cat, k in cnt.most_common(14):
        w = [v for v in allh if cat in v["cats"]]; wo = [v for v in allh if cat not in v["cats"]]
        a1 = sum(1 for v in w if v["fin"] <= 3) / len(w); a2 = sum(1 for v in wo if v["fin"] <= 3) / max(1, len(wo))
        L.append(f"| {cat} | {len(w)} | {a1 * 100:.0f}% | {a2 * 100:.0f}% | {(a1 - a2) * 100:+.0f}pt |")
    L.append("")
    L.append(f"（印のついた全馬 {len(allh)}頭の3着内率 {base3 * 100:.0f}%）")
    L.append("")
    L.append("（1レースずつの詳細は 20261101/research/postmortem_all.json）")
    Path(__file__).resolve().parents[2].joinpath("docs", "keiba_postmortem_all.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
