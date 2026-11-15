"""webmode_plan.py — JRA-VANが無い日の「見立て確率 × 取れている実オッズ」での買い目設計（2026-11-06 新設）

使い方:  python webmode_plan.py race.json
race.json:
  name     レース名
  uma      [馬番...]
  names    {馬番: 馬名}
  win      {馬番: 単勝オッズ}                     （実オッズ・前売りでも可）
  umaren   {"2-9": オッズ, ...}                    （無ければ市場確率からの推定オッズ）
  wide     {"2-9": [下限, 上限], ...}              （下限で評価＝保守的）
  hint     {馬番: 見立ての勝つ確率}                （外部の指数など。一部の馬だけでも可・無い馬は市場確率で補う）
  blend    見立ての重み（0〜1）。市場が強い（過去検証で外部予想は市場を超えない）ので既定は 0.3

出力: 印・見立て確率と市場確率の比・買い目（型は kaime_compose が選ぶ）・券種ごとの期待値。
確率の出所は「市場 0.7 ＋ 外部の指数 0.3」の見立て。モデル（ev_engine）の確率ではない＝100%超の根拠にしない。
"""
import json
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import bet_engine as B
import kaime_compose as KC


def load(path):
    return json.load(open(path, encoding="utf-8"))


def run(r):
    uma = [int(u) for u in r["uma"]]
    win = {int(k): float(v) for k, v in r["win"].items()}
    names = {int(k): v for k, v in r.get("names", {}).items()}
    q = np.array([1.0 / win[u] for u in uma]); q = q / q.sum()
    blend = float(r.get("blend", 0.3))
    hint = {int(k): float(v) for k, v in (r.get("hint") or {}).items()}
    h = np.array([hint.get(u, np.nan) for u in uma])
    miss = np.isnan(h)
    if (~miss).any():
        left = max(1.0 - np.nansum(h), 1e-6)                   # 指数が無い馬には、残りの確率を市場確率の比で配る
        h[miss] = left * q[miss] / q[miss].sum()
        h = h / h.sum()
        p = (1 - blend) * q + blend * h
    else:
        p = q.copy()
    p = p / p.sum()
    order = sorted(uma, key=lambda u: win[u])
    pop = {u: i + 1 for i, u in enumerate(order)}
    horses = [dict(uma=u, p_model=float(p[i]), p_market=float(q[i]), ratio=float(p[i] / q[i]), pop=pop[u]) for i, u in enumerate(uma)]
    # 印（predict_day.marks_and_bets と同じ規則）
    val = sorted(horses, key=lambda x: -x["ratio"])
    marks = {}
    hon = [x for x in val if x["p_model"] >= 0.08] or horses[:1]
    marks[hon[0]["uma"]] = "◎"
    for mk, fl in (("○", .05), ("▲", .05), ("△", .03), ("△", .03)):
        c = [x for x in val if x["uma"] not in marks and x["p_model"] >= fl] or [x for x in horses if x["uma"] not in marks]
        if c:
            marks[c[0]["uma"]] = mk
    ana = [x for x in val if x["uma"] not in marks and x["pop"] >= 6 and x["p_model"] >= 0.02 and x["ratio"] >= 1.0]   # 見立てが市場より低い馬は🔥にしない
    if ana:
        marks[ana[0]["uma"]] = "🔥"
    um = {}
    for k, v in marks.items():
        um.setdefault(v, []).append(k)
    M = {"◎": um["◎"][0], "○": um["○"][0], "▲": um["▲"][0]}
    if len(um.get("△", [])) > 0: M["△1"] = um["△"][0]
    if len(um.get("△", [])) > 1: M["△2"] = um["△"][1]
    if "🔥" in um: M["🔥"] = um["🔥"][0]
    ctx = KC.make_ctx(p, q, uma, M, pop)
    tm, tq = B.tables(p, uma), B.tables(q, uma)
    keyed = {t: dict(zip(ks, pq)) for t, (ks, pq) in tq.items()}
    pmap = {t: dict(zip(ks, pr)) for t, (ks, pr) in tm.items()}

    def est(t, combo):
        k = (combo[0],) if t in ("単勝", "複勝") else (tuple(combo) if t in ("馬単", "3連単") else tuple(sorted(combo)))
        pq = keyed.get(t, {}).get(k)
        return B.TAKE.get(t, .8) / pq if pq and pq > 1e-9 else None

    def real(t, combo):
        k = "-".join(str(x) for x in sorted(combo))
        if t == "単勝": return win.get(combo[0])
        if t == "馬連":
            v = (r.get("umaren") or {}).get(k)
            return float(v) if v else None
        if t == "ワイド":
            v = (r.get("wide") or {}).get(k)
            return float(v[0]) if v else None
        return None

    def odds_fn(t, combo):
        return real(t, combo) or est(t, combo)

    def p_fn(t, combo):
        if t == "単勝":
            return float(p[uma.index(combo[0])])
        k = tuple(combo) if t in ("馬単", "3連単") else tuple(sorted(combo))
        v = pmap.get(t, {}).get(k)
        return float(v) if v is not None else None

    extra = [x["uma"] for x in sorted(horses, key=lambda x: -x["p_model"]) if x["uma"] not in marks][:3]
    comp = KC.compose(M, ctx, odds_fn, None, None, p_fn=p_fn, extra=extra, ev_odds_fn=odds_fn)
    for u in comp.get("meta", {}).get("widened", []):
        marks[u] = "△"
    return dict(horses=horses, marks=marks, ctx=ctx, comp=comp, odds_fn=odds_fn, p_fn=p_fn, real=real, names=names, win=win)


def report(r):
    o = run(r)
    nm = lambda u: "%d%s" % (u, o["names"].get(u, ""))
    print("■", r.get("name"))
    print("馬番 馬名 人気 単勝 市場確率 見立て確率 比(見立て/市場) 単勝期待値 印")
    for x in sorted(o["horses"], key=lambda x: x["pop"]):
        u = x["uma"]
        print("%2d %-10s %2d人気 %5.1f  %5.1f%%  %5.1f%%  %.2f  %.2f  %s" % (
            u, o["names"].get(u, ""), x["pop"], o["win"][u], x["p_market"] * 100, x["p_model"] * 100, x["ratio"],
            x["p_model"] * o["win"][u], o["marks"].get(u, "")))
    c = o["comp"]
    print("型:", c["pattern"]["id"], c["pattern"]["name"], "｜", c["pattern"]["why"])
    print("レースの型:", o["ctx"]["kind"], "q1=%.2f" % o["ctx"]["q1"], "／ 他の候補型:", c.get("others"))
    meta = c.get("meta") or {}
    print("期待回収率 e=%s 合計=%s円 %s" % (meta.get("e"), meta.get("total"), meta.get("note", "")))
    tot = 0
    for t, cb, st in c["plan"]:
        od = o["odds_fn"](t, cb); pr = o["p_fn"](t, cb)
        src = "実" if o["real"](t, cb) else "推定"
        print("  %s %s %5d円  オッズ%s(%s) 的中%.1f%% 期待値%.2f" % (t, "-".join(map(str, cb)), st, ("%.1f" % od) if od else "-", src, (pr or 0) * 100, (pr or 0) * (od or 0)))
        tot += st
    print("  合計", tot, "円 ／ ガミ判定:", c.get("gami"), meta.get("no_gami"))
    return o


if __name__ == "__main__":
    report(load(sys.argv[1]))
