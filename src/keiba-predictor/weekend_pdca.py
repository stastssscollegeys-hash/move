# -*- coding: utf-8 -*-
"""
weekend_pdca.py — 土日の全レースを JRA-VAN（JV速報）の結果で振り返る（2026-10-05新規）
================================================================================
Check: ①公開した印（レース前に作った版）の成績と1番人気との比較 ②買い目（E2台帳・参考）の収支 ③土日の馬場の特徴
使う予想: 土曜＝cards_{土}.json（前夜作成）／日曜＝直前最終版（cards_{日}.json の残り6R）＋昼の平場投稿案（docx）。
         日曜朝の7Rは作り直しで版が残っていないため対象外（以後は版を残す: cards_{日付}_{時刻}.json）。
出力: {日曜}/{日曜}_週末PDCA.md ／ research/weekend_pdca_{日曜}.json
使い方: python weekend_pdca.py --sat 20261003 --sun 20261004
"""
from __future__ import annotations
import argparse, collections, json, re, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import day_review as DR
import bet_engine as BE
import combo_backtest as C

BASE = Path.home() / "Desktop" / "競馬予想レポート"
CIRC = {ch: i + 1 for i, ch in enumerate("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱")}


def nums(s):
    return [CIRC[ch] for ch in s if ch in CIRC]


def from_cards(path, only=None):
    out = {}
    for c in json.loads(Path(path).read_text(encoding="utf-8"))["cards"]:
        k = (c["venue"], c["R"])
        if only and k not in only:
            continue
        bets = [dict(type=b["type"], combo=b["combo"], stake=b["stake"], kind="標準" if c["ref_bets"] else "E2") for b in (c["ref_bets"] or c["bets"])]
        out[k] = dict(marks={int(u): m for u, m in c["marks"].items()}, bets=bets, src=Path(path).name)
    return out


def from_flat_docx(path):
    import docx
    out = {}
    for t in docx.Document(path).tables:
        if len(t.rows) != 1 or len(t.columns) != 1:
            continue
        x = t.cell(0, 0).text
        m = re.match(r"🏇【(京都|東京|中山|阪神|新潟|福島|中京|小倉|札幌|函館)(\d+)R", x)
        if not m or (m.group(1), int(m.group(2))) in out:
            continue
        marks, bets = {}, []
        for ln in x.split("\n"):
            mm = re.match(r"^([◎○▲△🔥]) ?([①-⑱])", ln)
            if mm:
                marks[nums(mm.group(2))[0]] = mm.group(1)
            bb = re.match(r"^【(単勝|複勝|馬連|ワイド|馬単|3連複|3連単)】([①-⑱\-→]+) ([\d,]+)円", ln)
            if bb:
                bets.append(dict(type=bb.group(1), combo=nums(bb.group(2)), stake=int(bb.group(3).replace(",", "")), kind="E2" if "（参考）" not in x else "参考"))
        out[(m.group(1), int(m.group(2)))] = dict(marks=marks, bets=bets, src=Path(path).name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sat", required=True)
    ap.add_argument("--sun", required=True)
    a = ap.parse_args()
    days = (a.sat, a.sun)
    rows, pays = {}, {}
    for d in days:
        rs, py = DR.load_day(d)
        for r in rs:
            if r["着順int"]:
                rows.setdefault((d, r["競馬場"], r["R"]), []).append(r)
        for k, v in py.items():
            pays[(d,) + k] = v
    # 予想の版
    preds = {}
    for k, v in from_cards(BASE / a.sat / "research" / f"cards_{a.sat}.json").items():
        preds[(a.sat,) + k] = v
    flat = BASE / a.sun / f"{a.sun}_平場_予想とSNS投稿案.docx"
    if flat.exists():
        for k, v in from_flat_docx(flat).items():
            preds[(a.sun,) + k] = v
    for k, v in from_cards(BASE / a.sun / "research" / f"cards_{a.sun}.json").items():
        preds[(a.sun,) + k] = v                                         # 直前最終版で上書き
    for d in days:                                                    # 版が残っていれば、各レースを含む最後の版（＝発走前の最終版）を使う
        for f in sorted((BASE / d / "research" / "cards_versions").glob(f"cards_{d}_*.json")):
            for k, v in from_cards(f).items():
                preds[(d,) + k] = v
    L = [f"# 週末PDCA {a.sat}・{a.sun}（JRA-VANの成績で照合）", ""]
    # ── ① 印の成績 ──────────────────────────────────────────────
    n, win, top3 = collections.Counter(), collections.Counter(), collections.Counter()
    fav_n = fav_t3 = fav_w = same = 0
    per_race = []
    for k, p in sorted(preds.items()):
        hs = rows.get(k)
        if not hs:
            continue
        fin = {h["馬番"]: h["着順int"] for h in hs}
        fav = min(hs, key=lambda h: h["人気"] or 99)
        fav_n += 1; fav_t3 += fav["着順int"] <= 3; fav_w += fav["着順int"] == 1
        hon = next((u for u, m in p["marks"].items() if m == "◎"), None)
        same += hon == fav["馬番"]
        for u, m in p["marks"].items():
            if u in fin:
                n[m] += 1; win[m] += fin[u] == 1; top3[m] += fin[u] <= 3
        w = next(h for h in hs if h["着順int"] == 1)
        per_race.append(dict(day=k[0], venue=k[1], R=k[2], hon=hon, hon_fin=fin.get(hon), hon_pop=next((h["人気"] for h in hs if h["馬番"] == hon), None),
                             win_pop=w["人気"], win_mark=p["marks"].get(w["馬番"], ""), src=p["src"]))
    L += [f"## 1. 印の成績（レース前の版・{fav_n}レース）", "", "| 印 | 頭数 | 勝ち | 3着内 | 3着内率 |", "|---|---|---|---|---|"]
    for m in "◎○▲△🔥":
        if n[m]:
            L.append(f"| {m} | {n[m]} | {win[m]} | {top3[m]} | {top3[m]/n[m]*100:.0f}% |")
    L += ["", f"- 比較: 1番人気は {fav_n}頭で 勝ち{fav_w}・3着内{fav_t3}（{fav_t3/fav_n*100:.0f}%）。◎が1番人気と同じ馬だったのは {same}/{fav_n}レース",
          f"- 勝ち馬に印があったレース: {sum(1 for x in per_race if x['win_mark'])}/{len(per_race)}（勝ち馬の人気の中央値 {statistics.median(x['win_pop'] for x in per_race):.0f}番人気）", ""]
    # ── ② 買い目の収支 ────────────────────────────────────────────
    st, rt = collections.defaultdict(float), collections.defaultdict(float)
    hits = []
    for k, p in preds.items():
        py = pays.get(k)
        if not py or k not in rows:
            continue
        for b in p["bets"]:
            key = tuple(b["combo"]) if b["type"] in ("馬単", "3連単") else tuple(sorted(b["combo"]))
            got = py.get(b["type"], {}).get(key, 0) * b["stake"] / 100.0
            st[b["kind"]] += b["stake"]; rt[b["kind"]] += got
            if got:
                hits.append(f"{k[0][4:]} {k[1]}{k[2]}R {b['type']}{'-'.join(map(str, b['combo']))} {b['stake']:,}円→{int(got):,}円")
    L += ["## 2. 買い目の収支（実際には買っていない・参考）", ""]
    for kd in ("E2", "参考"):
        if st[kd]:
            L.append(f"- {kd}: 賭け金{int(st[kd]):,}円 → 払戻{int(rt[kd]):,}円（回収率{rt[kd]/st[kd]*100:.0f}%）")
    L += [f"- 的中: " + ("／".join(hits) if hits else "なし"), ""]
    led = json.loads((BASE / "daily_pdca" / "db" / "ev_ledger.json").read_text(encoding="utf-8"))
    sl, rl = 0.0, 0.0
    for x in led:
        k = (x["date"], x["venue"], x["R"])
        py = pays.get(k)
        if not py:
            continue
        key = tuple(x["combo"]) if x["type"] in ("馬単", "3連単") else tuple(sorted(x["combo"]))
        x["payout"] = py.get(x["type"], {}).get(key, 0) * x["stake"] / 100.0
        x["settled"] = True
        sl += x["stake"]; rl += x["payout"]
    (BASE / "daily_pdca" / "db" / "ev_ledger.json").write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
    L += [f"- 前向き台帳（E2.0・発走前に登録した分）: {len(led)}点 賭け金{int(sl):,}円 → 払戻{int(rl):,}円" + (f"（回収率{rl/sl*100:.0f}%）" if sl else ""), ""]
    # ── ③ 馬場の特徴（2日分）──────────────────────────────────────
    L += ["## 3. 馬場の特徴（土日）", ""]
    for d in days:
        f = BASE / d / "research" / f"day_review_{d}.json"
        if not f.exists():
            continue
        v = json.loads(f.read_text(encoding="utf-8"))["venues"]
        for key, x in v.items():
            st_ = " ".join(f"{s}{y['ratio']:.2f}" for s, y in x["style"].items() if y)
            wk = " ".join(f"{s}{y['ratio']:.2f}" for s, y in x["waku"].items() if y)
            L.append(f"- {d[4:6]}/{d[6:]} {key}（{x['races']}R・{'/'.join(x['baba'])}）時計{x['time_vs_normal'] or 0:+.2f}秒 ペース{x['pace_vs_normal'] or 0:+.2f} ｜脚質（逃げ＝最初のコーナー2番手以内） {st_} ｜枠 {wk}")
    L.append("")
    (BASE / a.sun / "research" / f"weekend_pdca_{a.sun}.json").write_text(json.dumps(dict(marks={m: dict(n=n[m], win=win[m], top3=top3[m]) for m in n},
        fav=dict(n=fav_n, win=fav_w, top3=fav_t3, same=same), bets={k: dict(stake=st[k], ret=rt[k]) for k in st}, ledger=dict(stake=sl, ret=rl), races=per_race),
        ensure_ascii=False, indent=1), encoding="utf-8")
    out = BASE / a.sun / f"{a.sun}_週末PDCA.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
