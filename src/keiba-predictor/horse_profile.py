# -*- coding: utf-8 -*-
"""
horse_profile.py — 馬のデータを10年分まとめる（馬ごとの得意条件／どんな馬がどんなレースで走るか）（2026-10-14新規）
=====================================================================================================================
1) 馬カード（全馬）: 通算成績と、条件ごと（芝ダ・距離帯・競馬場・回り・馬場・頭数・クラス・季節・間隔・ペース・枠・自分の脚質）の
   着別成績と「人気から期待される3着内の数」との差。差がプラス＝その条件では人気以上に走ってきた（得意）。
   期待値は 人気×頭数帯 ごとの全体の3着内率（人気の偏りを除く）。
2) 型の分析: レース前に分かる馬の特徴（前走着順・間隔・距離の変化・芝ダ変更・クラスの上下・キャリア・年齢・性別・
   前走の脚質・前走の上がり順位・同じ条件での3着内経験・馬体重・道悪実績・乗り替わり）× レースの型（芝ダ×距離帯×クラス群・馬場）で、
   人気から期待される3着内との比と単勝回収率。前半（〜2022）と後半（2023〜）の両方で同じ向きのものだけ「安定」。
⚠ 脚質（付け直し版 course_profile.style_of）・ペースは結果由来。馬カードでは「その馬が過去にどう走ったか」として使う（レース前に分かる過去の値）。
出力: daily_pdca/db/horse_profile.json（2025年以降に走った馬）／ _cache/horse_profile_all.pkl（全馬）／
      docs/keiba_horse_types.md（型の分析）／ 競馬予想レポート/馬の型まとめ.md
使い方:
  python horse_profile.py                        # 全部作り直す（2〜3分）
  python horse_profile.py --horse エンネ モンローウォーク
"""
from __future__ import annotations
import argparse, collections, json, math, pickle, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from course_profile import style_of, pace_of, meters

BASE = Path.home() / "Desktop" / "競馬予想レポート"
SRC = BASE / "daily_pdca" / "db" / "history_target"
OUT_JSON = BASE / "daily_pdca" / "db" / "horse_profile.json"
OUT_ALL = Path(__file__).resolve().parent / "_cache" / "horse_profile_all.pkl"
OUT_MD = Path(__file__).resolve().parents[2] / "docs" / "keiba_horse_types.md"
SPLIT = "20230101"
LEFT = {"東京", "中京", "新潟"}


def band(m):
    return "〜1300" if m <= 1300 else "1400〜1600" if m <= 1600 else "1700〜2200" if m <= 2200 else "2300〜"


def nband(n):
    return "〜10頭" if n <= 10 else "11〜14頭" if n <= 14 else "15頭〜"


def cls_of(c):
    c = str(c or "")
    return ("新馬" if "新馬" in c else "未勝利" if "未勝利" in c else "1勝" if "1勝" in c else "2勝" if "2勝" in c else "3勝" if "3勝" in c
            else "重賞" if c[:2] in ("G1", "G2", "G3") else "OP")


CLS_RANK = {"新馬": 0, "未勝利": 0, "1勝": 1, "2勝": 2, "3勝": 3, "OP": 4, "重賞": 5}


def season(d):
    m = int(d[4:6])
    return "春(3-5月)" if 3 <= m <= 5 else "夏(6-8月)" if 6 <= m <= 8 else "秋(9-11月)" if 9 <= m <= 11 else "冬(12-2月)"


def gap_band(g):
    return None if g is None else "連闘〜中2週" if g <= 21 else "中3〜5週" if g <= 42 else "6〜12週" if g <= 91 else "13週〜（休み明け）"


def baba3(b):
    return "良" if b == "良" else "稍重" if b == "稍重" else "重・不良" if b in ("重", "不良") else None


# ── 読み込み・レースごとの情報 ─────────────────────────────────────
def load():
    rows = []
    for f in sorted(SRC.glob("results_*.json")):
        rows += [r for r in json.loads(f.read_text(encoding="utf-8"))
                 if not str(r.get("距離") or "").startswith("障") and r.get("着順int") and r.get("人気")]
    races = collections.defaultdict(list)
    for r in rows:
        races[(r["date"], r["競馬場"], int(float(r["R"])))].append(r)
    # 人気×頭数帯 の3着内率・勝率（期待値）
    tab = collections.defaultdict(lambda: [0, 0, 0])
    for k, hs in races.items():
        nb = nband(len(hs))
        for h in hs:
            t = tab[(min(int(h["人気"]), 14), nb)]
            t[0] += 1; t[1] += h["着順int"] <= 3; t[2] += h["着順int"] == 1
    EXP3 = {k: v[1] / v[0] for k, v in tab.items()}
    out = []
    for k, hs in sorted(races.items()):
        n = len(hs)
        h0 = hs[0]
        m = meters(h0["距離"])
        rc = dict(date=k[0], venue=k[1], surf=str(h0["距離"])[:1], m=m, band=band(m), cls=cls_of(h0.get("条件")),
                  baba=baba3(h0.get("馬場状態")), n=n, pace=pace_of(h0.get("前3F_レース"), h0.get("後3F_レース")),
                  turn="左" if k[1] in LEFT else "右", season=season(k[0]))
        ups = sorted(h.get("後3F") for h in hs if h.get("後3F"))
        for h in hs:
            up = h.get("後3F")
            urank = (1 + sum(1 for x in ups if x < up)) if up else None
            w = h.get("枠")
            mm = re.search(r"^(\d+)\(([+-]?\d+)\)", str(h.get("馬体重") or ""))
            out.append(dict(rc, hid=h.get("horse_id") or h.get("馬名"), name=h.get("馬名") or "", f=h["着順int"], pop=int(h["人気"]),
                            odds=float(h.get("単勝オッズ") or 0), exp3=EXP3[(min(int(h["人気"]), 14), nband(n))],
                            style=style_of(h.get("コーナー通過"), n), urank=urank,
                            waku="内(1-3枠)" if w and w <= 3 else "中(4-5枠)" if w and w <= 5 else "外(6-8枠)" if w else None,
                            sexage=str(h.get("性齢") or ""), sire=h.get("父") or "", bms=h.get("母父") or "", jockey=h.get("騎手") or "",
                            trainer=h.get("厩舎") or "", kin=h.get("斤量_kg"), bw=int(mm.group(1)) if mm else None,
                            bwd=int(mm.group(2)) if mm else None))
    return out


# ── 1) 馬カード ──────────────────────────────────────────────────
DIMS = [("surf", "芝ダ"), ("sband", "芝ダ×距離帯"), ("venue", "競馬場"), ("turn", "回り"), ("baba", "馬場"), ("nb", "頭数"),
        ("cls", "クラス"), ("season", "季節"), ("gapb", "間隔"), ("pace", "ペース"), ("waku", "枠"), ("style", "自分の脚質")]


def horse_cards(runs):
    by = collections.defaultdict(list)
    for r in runs:
        by[r["hid"]].append(r)
    cards = {}
    for hid, rs in by.items():
        rs.sort(key=lambda r: r["date"])
        prev = None
        for r in rs:
            r["gap"] = None
            if prev:
                from datetime import date
                d1 = date(int(prev["date"][:4]), int(prev["date"][4:6]), int(prev["date"][6:]))
                d2 = date(int(r["date"][:4]), int(r["date"][4:6]), int(r["date"][6:]))
                r["gap"] = (d2 - d1).days
            r["prev"] = prev
            prev = r
        cells = {lab: collections.defaultdict(lambda: [0, 0, 0, 0, 0.0]) for _, lab in DIMS}    # 1着,2着,3着,着外,期待3着内
        for r in rs:
            r["sband"] = f"{r['surf']}{r['band']}"
            r["nb"] = nband(r["n"])
            r["gapb"] = gap_band(r["gap"])
            for key, lab in DIMS:
                v = r.get(key)
                if not v:
                    continue
                c = cells[lab][v]
                c[min(r["f"], 4) - 1 if r["f"] <= 3 else 3] += 1
                c[4] += r["exp3"]
        last = rs[-1]
        sa = last["sexage"]
        fr = [r["style"] for r in rs[-5:] if r["style"]]
        cards[hid] = dict(
            name=last["name"], sex=sa[:1], birth=int(last["date"][:4]) - int(sa[1:]) if sa[1:].isdigit() else None,
            sire=last["sire"], bms=last["bms"], trainer=last["trainer"], jockey=last["jockey"],
            runs=len(rs), rec=[sum(r["f"] == 1 for r in rs), sum(r["f"] == 2 for r in rs), sum(r["f"] == 3 for r in rs), sum(r["f"] > 3 for r in rs)],
            exp3=round(sum(r["exp3"] for r in rs), 2), first=rs[0]["date"], last=last["date"], last_cls=last["cls"],
            style5=dict(collections.Counter(fr)), up_top3=sum(1 for r in rs if r["urank"] and r["urank"] <= 3),
            bw=[r["bw"] for r in rs if r["bw"]][-5:],
            cells={lab: {k: [*v[:4], round(v[4], 2)] for k, v in d.items()} for lab, d in cells.items()},
            recent=[dict(date=r["date"], venue=r["venue"], d=f"{r['surf']}{r['m']}", cls=r["cls"], baba=r["baba"], n=r["n"], f=r["f"],
                         pop=r["pop"], style=r["style"], urank=r["urank"], pace=r["pace"]) for r in rs[-6:]])
    return cards, by


def strength(c):
    """条件のセル [1着,2着,3着,着外,期待3着内] → (走数, 3着内, 期待, 差)"""
    n = sum(c[:4])
    t3 = sum(c[:3])
    return n, t3, c[4], t3 - c[4]


def card_text(h):
    rec = "-".join(str(x) for x in h["rec"])
    t3 = sum(h["rec"][:3])
    L = [f"### {h['name']}（{h['sex']}・{h['birth']}年生・父 {h['sire']}・母父 {h['bms']}・{h['trainer']}）",
         f"通算 {h['runs']}戦 {rec}（3着内 {t3}回・人気からの期待 {h['exp3']:.1f}回 → {t3 - h['exp3']:+.1f}）／{h['first']}〜{h['last']}・直近のクラス {h['last_cls']}",
         f"直近5走の脚質 {h['style5']}／上がり3位以内 {h['up_top3']}回／馬体重 {h['bw']}"]
    good, bad = [], []
    for lab, d in h["cells"].items():
        for k, c in d.items():
            n, t3_, e, df = strength(c)
            if n >= 2:
                s = f"{lab}={k}: {n}戦{'-'.join(str(x) for x in c[:4])}（{df:+.1f}）"
                (good if df >= 0.8 else bad if df <= -0.8 else []).append((df, s))
    if good:
        L.append("- **得意（人気より3着内が多い）**: " + "／".join(s for _, s in sorted(good, reverse=True)[:8]))
    if bad:
        L.append("- **苦手（人気より3着内が少ない）**: " + "／".join(s for _, s in sorted(bad)[:8]))
    L.append("- 直近: " + "／".join(f"{r['date'][2:]} {r['venue']}{r['d']} {r['cls']} {r['baba'] or ''} {r['f']}着({r['pop']}人気・{r['style'] or '-'}・上がり{r['urank'] or '-'}位・{r['pace'] or '-'})" for r in h["recent"][-4:]))
    return "\n".join(L)


# ── 2) 型の分析 ───────────────────────────────────────────────────
def horse_type_feats(r):
    """レース前に分かる特徴（前走までの情報だけ）"""
    p = r["prev"]
    f = {}
    sa = r["sexage"]
    f["年齢"] = (sa[1:] + "歳") if sa[1:].isdigit() and int(sa[1:]) <= 6 else "7歳以上" if sa[1:].isdigit() else None
    f["性別"] = {"牡": "牡", "牝": "牝", "セ": "セン"}.get(sa[:1])
    f["キャリア"] = None
    f["馬体重"] = None if not r["bw"] else "〜439kg" if r["bw"] < 440 else "440〜479kg" if r["bw"] < 480 else "480〜519kg" if r["bw"] < 520 else "520kg〜"
    if not p:
        f["前走"] = "初出走"
        return f
    f["前走着順"] = "1着" if p["f"] == 1 else "2〜3着" if p["f"] <= 3 else "4〜5着" if p["f"] <= 5 else "6〜9着" if p["f"] <= 9 else "10着以下"
    f["前走人気と着順"] = ("人気より上" if p["f"] < p["pop"] - 2 else "人気より下" if p["f"] > p["pop"] + 2 else "人気どおり")
    f["間隔"] = gap_band(r["gap"])
    if p["surf"] != r["surf"]:
        f["距離・芝ダ"] = "芝ダ変更"
    else:
        dd = r["m"] - p["m"]
        f["距離・芝ダ"] = "延長(+200m以上)" if dd >= 200 else "短縮(-200m以上)" if dd <= -200 else "同距離前後"
    cr, pr = CLS_RANK[r["cls"]], CLS_RANK[p["cls"]]
    f["クラス"] = "昇級" if cr > pr else "降級" if cr < pr else "同クラス"
    f["前走の脚質"] = p["style"] or None
    f["前走の上がり"] = None if not p["urank"] else "1位" if p["urank"] == 1 else "2〜3位" if p["urank"] <= 3 else "4位以下"
    f["乗り替わり"] = "乗り替わり" if p["jockey"] and r["jockey"] and p["jockey"] != r["jockey"] else "同じ騎手"
    return f


def type_analysis(by):
    # 履歴の要約（同条件の3着内経験・道悪実績・キャリア）を走るたびに更新
    recs = []
    for hid, rs in by.items():
        seen_band, seen_heavy, k = set(), False, 0
        for r in rs:
            f = horse_type_feats(r)
            f["キャリア"] = "1〜3戦" if k <= 3 else "4〜10戦" if k <= 10 else "11〜20戦" if k <= 20 else "21戦〜"
            if k > 0:
                f["同じ芝ダ×距離帯での3着内"] = "あり" if r["sband"] in seen_band else "なし"
            if r["baba"] == "重・不良" and k > 0:
                f["道悪での3着内（今回 重・不良）"] = "あり" if seen_heavy else "なし"
            recs.append((r, f))
            k += 1
            if r["f"] <= 3:
                seen_band.add(r["sband"])
                if r["baba"] == "重・不良":
                    seen_heavy = True
    # レースの型
    def rtype(r):
        cg = "新馬・未勝利" if r["cls"] in ("新馬", "未勝利") else "1〜2勝" if r["cls"] in ("1勝", "2勝") else "3勝・OP・重賞"
        return f"{r['surf']}{r['band']}・{cg}"
    acc = collections.defaultdict(lambda: [[0, 0, 0.0, 0.0, 0.0], [0, 0, 0.0, 0.0, 0.0]])    # 期間 → n, 3着内, 期待, 単勝払戻, 勝ち
    for r, f in recs:
        per = 0 if r["date"] < SPLIT else 1
        for scope in ("全レース", rtype(r)):
            for dim, v in f.items():
                if v is None:
                    continue
                a = acc[(scope, dim, v)][per]
                a[0] += 1; a[1] += r["f"] <= 3; a[2] += r["exp3"]; a[3] += r["odds"] * 100 if r["f"] == 1 else 0; a[4] += r["f"] == 1
    return acc


def summarize(acc, min_n=800):
    out = collections.defaultdict(list)
    for (scope, dim, v), (a, b) in acc.items():
        n, t3, e, pay = a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3]
        if n < min_n or e <= 0:
            continue
        var = e * (1 - min(0.99, e / n))
        z = (t3 - e) / math.sqrt(var) if var > 0 else 0
        ra = a[1] / a[2] if a[2] else None
        rb = b[1] / b[2] if b[2] else None
        stable = bool(ra and rb and a[0] >= 200 and b[0] >= 200 and (ra - 1) * (rb - 1) > 0 and abs(z) >= 3)
        out[scope].append(dict(dim=dim, v=v, n=n, ratio=t3 / e, z=z, roi=pay / n, ra=ra, rb=rb, roia=a[3] / a[0] if a[0] else None,
                               roib=b[3] / b[0] if b[0] else None, win=(a[4] + b[4]) / n, stable=stable))
    return out


def build():
    runs = load()
    cards, by = horse_cards(runs)
    OUT_ALL.parent.mkdir(exist_ok=True)
    OUT_ALL.write_bytes(pickle.dumps(cards))
    active = {k: v for k, v in cards.items() if v["last"] >= "20250101"}
    OUT_JSON.write_text(json.dumps(active, ensure_ascii=False), encoding="utf-8")
    print(f"馬 {len(cards):,}頭（うち2025年以降に出走 {len(active):,}頭）・{len(runs):,}走")
    acc = type_analysis(by)
    S = summarize(acc)
    md = [f"# どんなレースで、どんな馬が走るか（{runs[0]['date']}〜{runs[-1]['date']}・{len(runs):,}走・{len(cards):,}頭）\n",
          "指標: **比** = 3着内の実数 ÷ 人気（×頭数帯）から期待される3着内の数（1.00＝人気どおり、1.10＝人気より1割多く3着内）。"
          "**単回** = その条件の馬の単勝を全部100円ずつ買ったときの回収率（市場平均は約80%）。",
          f"**安定** = 前半（〜2022）と後半（2023〜）の両方で同じ向き、かつ |z|≧3。安定でないものは偶然の可能性が高い。800走以上のみ。",
          "特徴はすべて**レース前に分かる値**（前走までの成績・今回の条件）。ただし ev_engine の確率にはこの多くがすでに入っていて、"
          "市場もかなり織り込んでいる。**単回が80%前後なら市場が正しく織り込み済み、明らかに高い・低いものだけが「市場の穴」の候補。**\n"]
    order = ["全レース"] + sorted(k for k in S if k != "全レース")
    for scope in order:
        xs = [x for x in S[scope] if x["stable"]]
        if not xs:
            continue
        md.append(f"\n## {scope}\n")
        md.append("| 特徴 | 値 | 走数 | 比 | 前半→後半 | 勝率 | 単回 | 単回 前半→後半 |")
        md.append("|---|---|---:|---:|---|---:|---:|---|")
        for x in sorted(xs, key=lambda x: -abs(x["z"]))[:14 if scope == "全レース" else 8]:
            md.append(f"| {x['dim']} | {x['v']} | {x['n']:,} | **{x['ratio']:.2f}** | {x['ra']:.2f}→{x['rb']:.2f} | {x['win'] * 100:.1f}% | {x['roi']:.0f}% | "
                      f"{x['roia']:.0f}→{x['roib']:.0f}% |")
    # 単勝回収率で市場の穴の候補（全期間90%以上・両期間とも85%以上・2,000走以上）
    md.append("\n## 市場の穴の候補（単勝回収率が両期間とも高い型）\n")
    md.append("| 範囲 | 特徴 | 値 | 走数 | 単回 | 前半→後半 | 比 |")
    md.append("|---|---|---|---:|---:|---|---:|")
    cand = [(s, x) for s, xs in S.items() for x in xs if x["n"] >= 2000 and x["roi"] >= 90 and x["roia"] >= 85 and x["roib"] >= 85]
    for s, x in sorted(cand, key=lambda t: -t[1]["roi"])[:25]:
        md.append(f"| {s} | {x['dim']} | {x['v']} | {x['n']:,} | **{x['roi']:.0f}%** | {x['roia']:.0f}→{x['roib']:.0f}% | {x['ratio']:.2f} |")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    pickle.dump(S, open(Path(__file__).resolve().parent / "_cache" / "horse_types.pkl", "wb"))
    print(f"保存: {OUT_JSON}\n保存: {OUT_ALL}\n保存: {OUT_MD}")


def show(names):
    try:
        J = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        J = {}
    pool = list(J.values())
    for nm in names:
        hit = [h for h in pool if h["name"] == nm]
        if not hit and OUT_ALL.exists():
            hit = [h for h in pickle.loads(OUT_ALL.read_bytes()).values() if h["name"] == nm]
        if not hit:
            print(f"見つからない: {nm}\n")
            continue
        for h in hit:
            print(card_text(h) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horse", nargs="+")
    a = ap.parse_args()
    if a.horse:
        show(a.horse)
    else:
        build()
