# -*- coding: utf-8 -*-
"""web_pattern_test.py — 買い目の型（web_compose.PATTERNS）を10年ぶんのレースに当てはめ、条件で枝分かれさせた「どの型にするか」の表（木）を作る（2026-11-26 新設）

きっかけ: 2026-11-26 ユーザー指示「毎回同じ買い目・形にする必要はない。期待値・印・独自指数で、どのパターンかを判断して買う。的中と回収率のバランスのいい形で」
          「◎だけでなく対抗・単穴・紐・穴の場合も含めて、いろんなパターンを」「もっとたくさん場合分けできるはず」「もっと型を増やして場合分けも増やして。レースごとに適切な買い方を」。
やること:
  1) 印は web_picks と同じ（◎＝割安さ1位・確率8%以上／○▲＝5%以上で割安な順／△＝1〜3番人気で印なし／穴＝6番人気以下・2%以上で最も割安）。
     型ごとに web_compose.tickets_for で1万円ぶんの買い目を並べ、実際の払戻（確定）で成績を出す。
  2) レースの条件は web_compose.DIMS（22個・発走前に分かるものだけ）。
  3) 木の作り方: 最初の枝は必ず「◎の割安さの帯」。そのあとは「分けたときに、区分ごとの最良の型の点（レース数で重みづけ）がいちばん上がる条件」で分ける。
     分けた先の区分が、前半（2019〜22）・後半（2023〜）とも「最小レース数」以上あり、点が MIN_GAIN 以上上がるときだけ分ける。深さは MAX_DEPTH まで。
  4) 型の点（つり合い）: 点＝「前半と後半の回収率の低いほう」＋ W_PLUS ×「収支がプラスになる率」。回収率（低いほう）がその区分でいちばん良い型より MAX_DROP 以上低い型は選ばない。
  5) 確かめ: 同じ作り方の木を「前半だけ」で作って、後半のレースに当てはめる（木を作るのに使っていないレースでの成績）。比べる相手＝いつも標準型 K3。
  6) 細かさは 2026-11-26 に72通り（型16／34・条件14／22・最小レース数3通り・引き継ぎの幅3通り・プラスの下限2通り）を後半で比べて決めた（db/web_pattern_explore_20261126.json）:
     ・区分を細かくするほど後半の回収率は下がる（約10区分 91〜93%・25区分以上 88〜90%。いつも K3 は 91.0%）
     ・型を34に増やしても回収率は同じだが、収支がプラスになる率は約24%→約33%に上がる（点数を絞った型が選べるため）
     → 型は全部から選ぶ・木に使う条件は14個・区分の最小は前半/後半それぞれ600レース・プラスになる率20%未満の型は選ばない
出力: db/web_pattern_table.json（web_compose.py が --pattern auto で引く）・db/web_pattern_results.json（葉の一覧と確かめの数字）
時間: 型が多いので、下ごしらえ（型ごとの払戻の計算）を _cache/web_pattern_prep.pkl にためる。1回で終わらなければ「続きあり」と出るので、もう一度実行する。
注意: 確定オッズ・JV版モデルの前向き予測で測っている。条件と型をたくさん見るので偶然が混ざる＝表は「いまの最善の見立て」。
  python web_pattern_test.py            # 下ごしらえ（続きから）→ 木
  python web_pattern_test.py --prep     # 下ごしらえだけ
"""
import collections, hashlib, json, pickle, sys, time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import web_compose as WC

W_PLUS, MAX_DROP, MIN_GAIN, MAX_DEPTH = 0.2, 5.0, 0.5, 8
MIN_N = 600                  # 区分の最小レース数（前半・後半それぞれ）。2026-11-26 に72通り比べて、粗い区分（約10）が後半でいちばん良かった
PLUS_FLOOR = 20.0            # 収支がプラスになる率がこれ未満の型は選ばない（当たるのが10回に1回のような型を、たまたまの高配当で選ばない）
TREE_DIMS = WC.DIMS[:14]     # 木に使う条件。22個ぜんぶ使うと、後半の成績が下がった（db/web_pattern_explore_20261126.json）
FIRST = "帯"                 # 最初の枝は必ず「◎の割安さの帯」（勝負のレース＝1.30以上を、ほかの条件に埋もれさせない）
PK = list(WC.PATTERNS)
PREP = Path(__file__).resolve().parent / "_cache" / "web_pattern_prep.pkl"
BUDGET_SEC = 430             # 下ごしらえを1回で進める時間（10分の制限の中で、保存までを終わらせる）


def meta():
    """(日付, 場, R) → (距離の文字, 条件, 馬場)"""
    m = {}
    for f in sorted(Path(E.SOURCE).glob("results_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            try:
                k = (str(r.get("date")), r.get("競馬場"), int(r.get("R")))
            except (TypeError, ValueError):
                continue
            if k not in m:
                m[k] = (r.get("距離") or "", r.get("条件") or "", r.get("馬場状態") or "良")
    return m


def marks(pr):
    p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), list(pr["uma"])
    p, q = p / p.sum(), q / q.sum(); n = len(uma); ratio = p / q
    pop = np.empty(n, int); pop[np.argsort(-q)] = np.arange(1, n + 1)
    c = [i for i in range(n) if p[i] >= .08] or [int(np.argmax(p))]
    hon = max(c, key=lambda i: ratio[i])
    rest = sorted([i for i in range(n) if i != hon and p[i] >= .05], key=lambda i: -ratio[i])[:2]
    used = {hon, *rest}; d = []
    for i in np.argsort(-q)[:3]:
        if int(i) not in used:
            d.append(int(i)); used.add(int(i))
    ca = [i for i in range(n) if i not in used and pop[i] >= 6 and p[i] >= .02]
    ana = max(ca, key=lambda i: ratio[i]) if ca else None
    U = lambda i: int(uma[i])
    return dict(H=U(hon), core=[U(i) for i in rest], D=[U(i) for i in d], ana=(U(ana) if ana is not None else None), ratio=float(ratio[hon]), pop=int(pop[hon]), n=n,
                o_ratio=(float(ratio[rest[0]]) if rest else 0.0), ana_ratio=(float(ratio[ana]) if ana is not None else 0.0), p_hon=float(p[hon]),
                p_o=(float(p[rest[0]]) if rest else 0.0), fav_q=float(q.max()), t_ratio=(float(ratio[rest[1]]) if len(rest) > 1 else 0.0),
                odds_hon=float(0.8 / q[hon]), pop_o=(int(pop[rest[0]]) if rest else 0), pop_t=(int(pop[rest[1]]) if len(rest) > 1 else 0),
                hon_is_p=bool(hon == int(np.argmax(p))), top3_p=float(np.sort(p)[-3:].sum()))


def prep():
    """型ごとの出資・払戻と、レースの条件を計算してためる。→ (feats, ST, RT, FR) か None（続きあり）"""
    sig = hashlib.md5((json.dumps(WC.PATTERNS, ensure_ascii=False, sort_keys=True) + "|".join(WC.DIMS) + "v3").encode()).hexdigest()
    st = dict(sig=sig, done=0, feats=[], ST=[], RT=[], FR=[])
    if PREP.exists():
        try:
            old = pickle.loads(PREP.read_bytes())
            if old.get("sig") == sig:
                st = old
        except Exception:
            pass
    preds = C.predictions()
    if st["done"] >= len(preds):
        return st["feats"], np.array(st["ST"], float), np.array(st["RT"], float), np.array(st["FR"], bool)
    pay, M = C.load_pay(), meta(); t0 = time.time()
    for i in range(st["done"], len(preds)):
        pr = preds[i]; st["done"] = i + 1
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if pp and pp.get("ワイド") and pp.get("単勝"):
            m = marks(pr)
            if len(m["core"]) >= 2:
                srt = lambda k: tuple(sorted(map(int, k.split("-")))); ordr = lambda k: tuple(map(int, k.split("-"))); one = lambda k: (int(k),)
                tbl = {"単勝": {one(k): y for k, y in pp["単勝"].items()}, "複勝": {one(k): y for k, y in pp.get("複勝", {}).items()},
                       "馬連": {srt(k): y for k, y in pp.get("馬連", {}).items()}, "ワイド": {srt(k): y for k, y in pp["ワイド"].items()},
                       "馬単": {ordr(k): y for k, y in pp.get("馬単", {}).items()}, "3連複": {srt(k): y for k, y in pp.get("3連複", {}).items()},
                       "3連単": {ordr(k): y for k, y in pp.get("3連単", {}).items()}}
                dist, cond, baba = M.get((pr["key"][0], pr["key"][1], int(pr["key"][2])), ("", "", "良"))
                st["feats"].append(WC.feats(m["ratio"], m["pop"], m["n"], m["o_ratio"], m["ana_ratio"], m["p_hon"], m["p_o"], m["fav_q"], m["t_ratio"], len(m["D"]), dist, cond, baba,
                                            odds_hon=m["odds_hon"], pop_o=m["pop_o"], pop_t=m["pop_t"], hon_is_p=m["hon_is_p"], has_ana=m["ana"] is not None, venue=pr["key"][1], top3_p=m["top3_p"]))
                a, b = [], []
                for k in PK:
                    T = WC.tickets_for(WC.PATTERNS[k][1], m["H"], m["core"][0], m["core"][1], m["D"], m["ana"], 10000)
                    a.append(sum(x[2] for x in T)); b.append(sum(tbl[x[0]].get(tuple(x[1]), 0) * x[2] / 100 for x in T))
                st["ST"].append(a); st["RT"].append(b); st["FR"].append(pr["key"][0] < "20230101")
        if time.time() - t0 > BUDGET_SEC:
            break
    PREP.parent.mkdir(exist_ok=True); PREP.write_bytes(pickle.dumps(st))
    if st["done"] < len(preds):
        print(f"下ごしらえ {st['done']:,}／{len(preds):,} レースまで。続きあり → もう一度実行してください"); return None
    return st["feats"], np.array(st["ST"], float), np.array(st["RT"], float), np.array(st["FR"], bool)


def best(idx, ST, RT, HALF):
    """レースの番号 idx で、型ごとの点を付ける。HALF＝2つの期の分け目（本番は前半/後半・確かめは前半の中をさらに半分）。→ (点, 良い順の型の番号, 成績)"""
    st, rt, h = ST[idx], RT[idx], HALF[idx][:, None]
    ra = (rt * h).sum(0) / np.maximum((st * h).sum(0), 1) * 100; rb = (rt * ~h).sum(0) / np.maximum((st * ~h).sum(0), 1) * 100
    low = np.minimum(ra, rb); plus = (rt >= st).mean(0) * 100
    sc = low + W_PLUS * plus
    fl = plus >= PLUS_FLOOR                                  # 先に「プラスになる率の下限」を通った型だけにして、その中でいちばん良い回収率から MAX_DROP 以内を残す
    if not fl.any():
        fl = np.ones_like(plus, bool)
    ok = fl & (low >= low[fl].max() - MAX_DROP)
    sc = np.where(ok, sc, -1e9)
    S = (len(idx), (rt > 0).mean(0) * 100, plus, rt.sum(0) / np.maximum(st.sum(0), 1) * 100, ra, rb)
    return float(sc.max()), np.argsort(-sc), S


def grow(idx, F, ST, RT, HALF, depth, used, min_n):
    sc, order, S = best(idx, ST, RT, HALF)
    row = lambda j: dict(pattern=PK[j], hit=round(float(S[1][j]), 1), plus=round(float(S[2][j]), 1), roi=round(float(S[3][j]), 1))
    j = int(order[0])
    node = dict(leaf=dict(n=int(S[0]), front=round(float(S[4][j]), 1), back=round(float(S[5][j]), 1), **row(j), next=[row(int(k)) for k in order[1:4]]))
    if depth >= MAX_DEPTH:
        return node
    cand = None
    for d in ([FIRST] if depth == 0 else TREE_DIMS):
        if d in used:
            continue
        col = F[d][idx]; vals = list(np.unique(col))
        if len(vals) < 2:
            continue
        parts = {v: idx[col == v] for v in vals}
        if any(min(HALF[ix].sum(), (~HALF[ix]).sum()) < min_n for ix in parts.values()):
            continue
        g = sum(best(ix, ST, RT, HALF)[0] * len(ix) for ix in parts.values()) / len(idx) - sc
        if (g >= MIN_GAIN or depth == 0) and (cand is None or g > cand[0]):
            cand = (g, d, parts)
    if cand:
        g, d, parts = cand
        node["dim"] = d; node["gain"] = round(float(g), 2)
        node["children"] = {str(v): grow(ix, F, ST, RT, HALF, depth + 1, used | {d}, min_n) for v, ix in parts.items()}
    return node


def walk(node, f):
    while node.get("dim") and f.get(node["dim"]) in node.get("children", {}):
        node = node["children"][f[node["dim"]]]
    return node["leaf"]


def leaves(node, path=()):
    if node.get("dim"):
        for v, ch in node["children"].items():
            yield from leaves(ch, path + (v,))
    else:
        yield path, node["leaf"]


def main():
    got = prep()
    if got is None or "--prep" in sys.argv:
        return
    feats, ST, RT, FR = got
    F = {d: np.array([f[d] for f in feats]) for d in WC.DIMS}
    allidx = np.arange(len(FR)); front, back = allidx[FR], allidx[~FR]
    print(f"レース {len(FR):,}（前半 {FR.sum():,}・後半 {(~FR).sum():,}）／型 {len(PK)}／木に使う条件 {len(TREE_DIMS)}（用意してある条件は {len(WC.DIMS)}）")

    # ── 確かめ: 前半（2019〜22）だけで木を作り、後半（2023〜）に当てはめる。前半の中をさらに2つの期に分けて、本番と同じ点の付け方をする ──
    H1 = np.zeros(len(FR), bool); H1[front[: len(front) // 2]] = True
    tf = grow(front, F, ST, RT, H1, 0, frozenset(), MIN_N // 2)
    def run(choice, ix=back):
        j = np.array([PK.index(choice[i]) for i in ix]); s_ = ST[ix, j]; r = RT[ix, j]
        return r.sum() / s_.sum() * 100, (r > 0).mean() * 100, (r >= s_).mean() * 100
    ch = {i: walk(tf, feats[i])["pattern"] for i in back}
    res = {"いつも標準型 K3": run({i: "K3" for i in back}), f"木で型を決める（前半で作った木・区分 {len(list(leaves(tf)))}）": run(ch)}
    print(f"\n■ 確かめ: 前半だけで木を作り、後半 {len(back):,} レースに当てはめた成績（木を作るのに使っていないレース）")
    for k, (roi, hit, plus) in res.items():
        print(f"  {k:40} 回収 {roi:5.1f}%・当たる {hit:4.1f}%・プラス {plus:4.1f}%")
    byb = {}
    for b in np.unique(F["帯"]):
        ix = np.array([i for i in back if F["帯"][i] == b]); byb[str(b)] = (run({i: "K3" for i in ix}, ix), run(ch, ix))
        print(f"    {b}（後半 {len(ix):,}R）: K3 回収{byb[str(b)][0][0]:5.1f}%・プラス{byb[str(b)][0][2]:4.1f}% ／ 木 回収{byb[str(b)][1][0]:5.1f}%・プラス{byb[str(b)][1][2]:4.1f}%")

    # ── 本番の木（前半・後半の両方を使う）──
    tree = grow(allidx, F, ST, RT, FR, 0, frozenset(), MIN_N)
    LV = list(leaves(tree))
    print(f"\n■ 型の表（木）: 区分 {len(LV)}")
    cnt = collections.Counter()
    for path, e in sorted(LV, key=lambda x: x[0]):
        cnt[e["pattern"]] += e["n"]
        print(f"  {e['n']:6,}R {e['pattern']:3} {WC.PATTERNS[e['pattern']][0][:12]:12} 当{e['hit']:3.0f}%・プ{e['plus']:3.0f}%・回{e['roi']:6.1f}%（{e['front']:5.1f}／{e['back']:5.1f}） ｜ {'・'.join(path)}")
        print("            次点: " + " ／ ".join(f"{x['pattern']} {WC.PATTERNS[x['pattern']][0][:10]}（当{x['hit']:.0f}%・プ{x['plus']:.0f}%・回{x['roi']:.0f}%）" for x in e["next"]))
    print("  型ごとのレースの割合: " + " ".join(f"{k} {v/len(FR)*100:.0f}%" for k, v in cnt.most_common()))

    # ── 帯ごとの、全部の型の成績（手で型を選ぶときの材料）──
    allp = {}
    for b in list(np.unique(F["帯"])):
        ix = allidx[F["帯"] == b]; _, order, S = best(ix, ST, RT, FR)
        allp[str(b)] = [dict(pattern=PK[j], hit=round(float(S[1][j]), 1), plus=round(float(S[2][j]), 1), roi=round(float(S[3][j]), 1), front=round(float(S[4][j]), 1), back=round(float(S[5][j]), 1)) for j in range(len(PK))]

    WC.TABLE.write_text(json.dumps(dict(made="20261126", rule=f"木: 最初の枝は帯。点＝前半・後半の回収率の低いほう＋{W_PLUS}×収支がプラスになる率（プラスになる率{PLUS_FLOOR:.0f}%未満の型は選ばない）。分けるのは前半・後半とも{MIN_N}レース以上・点が{MIN_GAIN}以上上がるとき",
                                     dims=TREE_DIMS, tree=tree), ensure_ascii=False, indent=1), encoding="utf-8")
    (E.DB / "web_pattern_results.json").write_text(json.dumps(dict(made="20261126", n=int(len(FR)), min_n=MIN_N, leaves=[dict(path=list(p), **e) for p, e in LV],
                                                                    check={k: dict(roi=v[0], hit=v[1], plus=v[2]) for k, v in res.items()},
                                                                    check_band={b: dict(k3=dict(roi=v[0][0], plus=v[0][2]), tree=dict(roi=v[1][0], plus=v[1][2])) for b, v in byb.items()}, by_band=allp), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n保存:", WC.TABLE)


if __name__ == "__main__":
    main()
