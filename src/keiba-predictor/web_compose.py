# -*- coding: utf-8 -*-
"""web_compose.py — 1レースの買い目を「標準の構成」で組み、的中の見込み・場面ごとの受け皿・実オッズの期待値を計算して出す（2026-11-14 新設）

土台の検証（docs/keiba_weekend_review_20261114_sat.md §8〜10・SKILL §2）:
  bet_type_by_race_test.py（券種）／bet_portfolio_study.py（部品と場面）／bet_form_study.py（軸流し・BOX・フォーメーション・マルチ）
決め方（検証で残ったものだけ）:
  ・単勝◎ ＝ ◎1着の受け皿（払戻率80%・一番早く落ち着く）
  ・馬連 ◎-○・◎-▲（＋◎-穴）＝ ◎2着までの受け皿。総流し・BOX・ヒモ足しは回収率が下がるので広げない
  ・3連複 フォーメーション ◎-○▲-印全部 を 1点100円＝ ◎3着までを高配当で受ける（1点に厚くするのと回収率は同じで、当たる頻度が約3.6倍・落ち着くのが約4倍早い）。
     本線の ◎-○-▲ だけ上乗せ。1頭軸の総流し・BOX・ヒモ足し・3連単マルチは使わない
  ・ワイド ◎-○・◎-▲（＋◎-穴）＝ ◎3着のときの押さえ。△（割安でない人気馬）とのワイド・馬連は回収率が低いので買わない（△は3連複の3列目だけ）
  ・馬単・3連単は使わない（単勝と同じ場面にしか当たらない・落ち着かない）
  ・◎抜きの保険（馬連○-▲）は --hoken を付けたときだけ1点・予算の1割
印: web_picks.marks_of ＋ 穴（6番人気以下・勝つ確率2%以上・印なしで最も割安な1頭。--ana 馬番 で指定／--keep 馬番… で△として残す馬を足す）
  python web_compose.py --date 20261115 --race 京都11 [--budget 10000] [--keep 6] [--ana 10] [--hoken] [--no-odds]
出力: 買い目（100円単位）、◎が1着／2着／3着／着外のとき何%を拾えるか、どれかが当たる確率、券ごとの的中確率と（オッズが取れれば）期待値、当たっても損になる割合。
"""
import argparse
import itertools
import json
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import web_frontier as F
import web_live as WL
import web_picks as WP

SHARE = {"単勝◎": .25, "馬連◎-○": .20, "馬連◎-▲": .15, "馬連◎-穴": .05, "ワイド◎-○": .10, "ワイド◎-▲": .08, "ワイド◎-穴": .05, "3連複": .12}


def r100(x):
    return int(round(x / 100.0)) * 100


def compose(race, budget=10000, keep=(), ana=None, hoken=False, use_odds=True):
    hs, marks = WP.marks_of(race)
    by = {h["uma"]: h for h in hs}
    M = {m: [h["uma"] for mm, h in marks if mm == m] for m in "◎○▲△"}
    H = M["◎"][0]; o = (M["○"] or [None])[0]; t = (M["▲"] or [None])[0]
    D = M["△"] + [u for u in keep if u not in [H, o, t] + M["△"]]
    used = {H, o, t} | set(D)
    if ana is None:
        c = [h for h in hs if h["uma"] not in used and h["pop"] >= 6 and h["p_model"] >= .02]
        ana = max(c, key=lambda h: h["p_model"] / h["p_market"])["uma"] if c else None
    aite = [x for x in [o, t] + D + ([ana] if ana else []) if x is not None]
    core = [x for x in (o, t) if x is not None]
    T = []                                                    # (券種, 組, 金額, 役割)
    def put(typ, comb, yen, role):
        if yen >= 100 and all(c is not None for c in comb):
            T.append([typ, tuple(comb) if typ == "単勝" else tuple(sorted(comb)), r100(yen), role])
    put("単勝", (H,), budget * SHARE["単勝◎"], "◎1着")
    put("馬連", (H, o), budget * SHARE["馬連◎-○"], "◎2着まで"); put("馬連", (H, t), budget * SHARE["馬連◎-▲"], "◎2着まで")
    put("ワイド", (H, o), budget * SHARE["ワイド◎-○"], "◎3着まで"); put("ワイド", (H, t), budget * SHARE["ワイド◎-▲"], "◎3着まで")
    if ana:
        put("馬連", (H, ana), budget * SHARE["馬連◎-穴"], "穴の押さえ"); put("ワイド", (H, ana), budget * SHARE["ワイド◎-穴"], "穴の押さえ")
    tri = list(dict.fromkeys(tuple(sorted((H, x, y))) for x in core for y in aite if y != x))
    for c in tri:
        put("3連複", c, 100, "◎3着まで（高配当）")
    if hoken and len(core) == 2:
        put("馬連", (o, t), budget * .10, "◎抜きの保険")
    # 余りは 3連複 ◎-○-▲ → 単勝 の順に寄せる。超えたら単勝から削る
    rest = budget - sum(x[2] for x in T)
    main_tri = tuple(sorted((H, o, t))) if len(core) == 2 else None
    for x in T:
        if rest > 0 and x[0] == "3連複" and x[1] == main_tri:
            add = min(rest, r100(budget * SHARE["3連複"]) - 100 * len(tri) + 0) if r100(budget * SHARE["3連複"]) > 100 * len(tri) else 0
            x[2] += max(add, 0); rest -= max(add, 0)
    T[0][2] += rest
    # ── 確率（モデル・全頭 Harville）──
    uma = [h["uma"] for h in race["horses"]]; p = np.array([h["p_model"] for h in race["horses"]], float); p /= p.sum()
    q = np.array([h["p_market"] for h in race["horses"]], float); q /= q.sum()
    Tn = C.tensor(p); ix = {u: i for i, u in enumerate(uma)}; n = len(uma)
    hi = ix[H]
    tot = sum(x[2] for x in T)
    def hit(x, a, b, c):
        typ, cb = x[0], [ix[u] for u in x[1]]
        if typ == "単勝":
            return a == cb[0]
        if typ == "馬連":
            return {a, b} == set(cb)
        if typ == "ワイド":
            return set(cb) <= {a, b, c}
        return set(cb) == {a, b, c}
    odds = {}
    if use_odds:
        try:
            po = F.pair_odds(race["rid"]); to = F.trio_odds(race["rid"])
            for x in T:
                if x[0] == "単勝":
                    odds[(x[0], x[1])] = by[x[1][0]]["odds"]
                elif x[0] in ("馬連", "ワイド"):
                    odds[(x[0], x[1])] = po[x[0]].get(x[1])
                else:
                    odds[(x[0], x[1])] = to.get(x[1])
        except Exception as e:
            print("（組み合わせオッズは取れず:", str(e)[:60], "）")
    pos = np.zeros(4); cov = np.zeros(4); anyhit = 0.0; gami = 0.0; pt = np.zeros(len(T)); ev_ret = 0.0
    for a in range(n):
        for b in range(n):
            if b == a:
                continue
            for c in range(n):
                if c in (a, b):
                    continue
                pr = Tn[a, b, c]
                if pr <= 0:
                    continue
                k = 0 if a == hi else 1 if b == hi else 2 if c == hi else 3
                pos[k] += pr
                hs_ = [hit(x, a, b, c) for x in T]
                if any(hs_):
                    cov[k] += pr; anyhit += pr
                for j, h_ in enumerate(hs_):
                    if h_:
                        pt[j] += pr
                if odds:
                    ret = sum(x[2] * (odds.get((x[0], x[1])) or 0) for x, h_ in zip(T, hs_) if h_)
                    ev_ret += pr * ret
                    if any(hs_) and ret < tot:
                        gami += pr
    return dict(H=H, o=o, t=t, D=D, ana=ana, tickets=T, total=tot, pos=pos, cov=cov, anyhit=anyhit, pt=pt, odds=odds, ev=ev_ret / tot if odds else None,
                gami=gami / anyhit if odds and anyhit else None, by=by)


CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"


def fmt_post(r):
    """買い目の表記（v3・2026-11-14）: 合計を先に → 券種ごとのブロック → 流しは「軸 ― 相手」、フォーメーションは「1頭目／2頭目／3頭目」の3行 →
    同額は「各◯円」、金額が違う組は相手ごとに書く → 各ブロックの最後に役割を1行。全角スペースの桁揃えはしない（スマホで崩れる）。"""
    c = lambda u: CIRC[u - 1]
    T = r["tickets"]; H = r["H"]
    L = [f"💰 買い目 合計{len(T)}点・{r['total']:,}円", ""]
    tan = [x for x in T if x[0] == "単勝"]
    if tan:
        L += [f"【単勝】◎{c(H)} {tan[0][2]:,}円", "・◎が勝てば的中", ""]
    for typ, role in (("馬連", "・◎が2着以内のときの本線"), ("ワイド", "・◎が3着以内のときの押さえ")):
        xs = [x for x in T if x[0] == typ and H in x[1]]
        if xs:
            aite = [(next(u for u in x[1] if u != H), x[2]) for x in xs]
            L.append(f"【{typ}】軸 ◎{c(H)} ― 相手 {''.join(c(u) for u, _ in aite)}（{len(aite)}点・{sum(y for _, y in aite):,}円）")
            if len({y for _, y in aite}) == 1:
                L.append(f"各{aite[0][1]:,}円")
            else:
                L.append("／".join(f"{c(u)} {y:,}円" for u, y in aite))
            L += [role, ""]
        ex = [x for x in T if x[0] == typ and H not in x[1]]
        for x in ex:
            L += [f"【{typ}】{'-'.join(c(u) for u in x[1])} {x[2]:,}円", "・◎が来ないときの保険", ""]
    tri = [x for x in T if x[0] == "3連複"]
    if tri:
        col2 = [u for u in (r["o"], r["t"]) if u]
        col3 = []
        for x in tri:
            for u in x[1]:
                if u != H and u not in col3:
                    col3.append(u)
        col3 = [u for u in [r["o"], r["t"]] + r["D"] + [r["ana"]] if u in col3]
        base = min(x[2] for x in tri); big = [x for x in tri if x[2] > base]
        L.append(f"【3連複フォーメーション】{len(tri)}点・{sum(x[2] for x in tri):,}円")
        L += [f"1頭目 ◎{c(H)}", f"2頭目 {''.join(c(u) for u in col2)}", f"3頭目 {''.join(c(u) for u in col3)}"]
        L.append(f"各{base:,}円" + ("".join(f"（{'-'.join(c(u) for u in x[1])}だけ{x[2]:,}円）" for x in big)))
        L += ["・◎が3着以内なら高配当を狙う", ""]
    pos, cov = r["pos"], r["cov"]
    L.append(f"どれかが当たる確率 約{r['anyhit']*100:.0f}%")
    L.append("◎が" + "・".join(f"{lab}なら{cov[i]/max(pos[i],1e-9)*100:.0f}%" for i, lab in enumerate(("1着", "2着", "3着"))) + "を拾える形")
    return chr(10).join(L)



def show(k, race, r):
    by = r["by"]; nm = lambda u: f"{u}{by[u]['name'][:8]}"
    print(f"■ {k} {race['title']} {race['dist']} {race['n']}頭")
    print("  印: ◎" + nm(r["H"]) + (" ○" + nm(r["o"]) if r["o"] else "") + (" ▲" + nm(r["t"]) if r["t"] else "") + "".join(" △" + nm(d) for d in r["D"]) + (" 穴" + nm(r["ana"]) if r["ana"] else ""))
    for (typ, cb, yen, role), p_ in zip(r["tickets"], r["pt"]):
        o_ = r["odds"].get((typ, cb)) if r["odds"] else None
        print(f"   {typ:4} {'-'.join(map(str, cb)):9} {yen:6,}円  当たる{p_*100:5.1f}%" + (f"  オッズ{o_:7.1f}  期待値{p_*o_:5.2f}" if o_ else "") + f"  〔{role}〕")
    pos, cov = r["pos"], r["cov"]
    print(f"  合計 {r['total']:,}円 ／ どれかが当たる {r['anyhit']*100:.1f}%" + (f" ／ 期待回収率 {r['ev']:.2f} ／ 当たっても損 {r['gami']*100:.0f}%" if r["ev"] else ""))
    print("  場面ごと: " + " ｜ ".join(f"◎{lab} {pos[i]*100:.1f}%→拾える{cov[i]/max(pos[i],1e-9)*100:.0f}%" for i, lab in enumerate(("1着", "2着", "3着", "着外"))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--race", nargs="+", required=True)
    ap.add_argument("--budget", type=int, default=10000); ap.add_argument("--keep", nargs="*", type=int, default=[])
    ap.add_argument("--ana", type=int); ap.add_argument("--hoken", action="store_true"); ap.add_argument("--no-odds", action="store_true")
    ap.add_argument("--post", action="store_true", help="投稿用の買い目の表記（v3）も出す")
    a = ap.parse_args()
    d = json.load(open(WL.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))
    print("オッズ取得:", d.get("made_at"))
    out = {}
    for k in a.race:
        r = compose(d["races"][k], a.budget, a.keep, a.ana, a.hoken, not a.no_odds)
        show(k, d["races"][k], r)
        if a.post:
            print(chr(10) + fmt_post(r) + chr(10))
        out[k] = dict(tickets=[[t, list(c), y, ro] for t, c, y, ro in r["tickets"]], total=r["total"], anyhit=round(r["anyhit"], 4),
                      pos=[round(float(x), 4) for x in r["pos"]], cov=[round(float(x), 4) for x in r["cov"]], ev=r["ev"], ana=r["ana"])
    json.dump(out, open(WL.OUT / f"{a.date}_web_compose.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
