# -*- coding: utf-8 -*-
"""
draw_final.py — 枠順確定後の重賞を1本で再評価する（2026-10-02新規・汎用）
==========================================================================
入力: {日付フォルダ}/research/index_input.json   （枠・馬番・騎手・斤量・単勝オッズ入り）
      {日付フォルダ}/research/index_ranking.json （calc_index_preview.py の枠順込み指数）
出力: {日付フォルダ}/research/draw_final.json

やること（SKILL v4.0 の部品だけを使う。新しい補正は足さない）:
  1. 確率  = 単勝オッズ → prob_core.market_probs → 両関門を通った消し(KESHI) → λ-Harville
             ※枠順は確率に掛けない。文脈層（枠・脚質）は context_audit の監査を1つも通っていないため
  2. 枠の実測 = 同じ競馬場・同じコースの過去走を「人気で条件付けて」枠別に 実測3着内/期待3着内 を出す
             （生の枠別3着内率は人気の偏りを拾うだけなので使わない）
  3. 並び  = 想定脚質（蓄積DBの直近5走多数決）を馬番順に並べ、逃げ・先行の位置関係を出す
  4. 型    = kaime_patterns.classify（オッズの形だけで判定）
  5. 買い方候補 = kaime_select（単勝〜3連複の全ファミリー・推定配当・Σ(1/配当)≦1）

オッズが発売前の予想オッズのときは index_input.json の odds_note に書いておく（出力にそのまま引き継ぐ）。
使い方: python draw_final.py --dir 20261004 [--budget 10000]
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from prob_core import market_probs, adjust, top3_scenarios, ticket_probs, KESHI
from context_layer import ContextDB, enabled_layers
from kaime_patterns import classify, DEFAULT_STRUCTURE
from kaime_select import build_candidates, score_candidate

BASE = Path.home() / "Desktop" / "競馬予想レポート"
WAKU_NEUTRAL = 65.0          # calc_index_preview が枠順前に置く中立値


def _fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "")
    return int(s) if s.isdigit() else None


def waku_table(rows, venue, course):
    """同場・同コースの枠別 実測3着内 / 人気から期待される3着内。
    期待値は同じDB全体の人気別3着内率（人気が同じなら枠が違っても同じだけ来るはず、という帰無仮説）。"""
    pop_all = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        f = _fin(r)
        try:
            p = int(float(r.get("人気")))
        except (TypeError, ValueError):
            continue
        if f:
            pop_all[p][0] += 1
            pop_all[p][1] += f <= 3
    rate = {p: v[1] / v[0] for p, v in pop_all.items() if v[0] >= 50}
    agg = collections.defaultdict(lambda: [0, 0, 0.0])
    races = set()
    for r in rows:
        if r.get("競馬場") != venue or str(r.get("距離") or "").replace("m", "") != course.replace("m", ""):
            continue
        f = _fin(r)
        try:
            p, w = int(float(r.get("人気"))), int(float(r.get("枠")))
        except (TypeError, ValueError):
            continue
        if not f or p not in rate:
            continue
        races.add((r["date"], r["R"]))
        a = agg[w]
        a[0] += 1
        a[1] += f <= 3
        a[2] += rate[p]
    out = {}
    for w in sorted(agg):
        n, obs, exp = agg[w]
        out[str(w)] = dict(n=n, top3=obs, expected=round(exp, 1), raw_rate=round(obs / n, 3),
                           ratio=round(obs / exp, 2) if exp else None)
    return dict(races=len(races), by_waku=out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--snapshot-day", metavar="YYYYMMDD",
                    help="odds_snapshot.py の最新スナップショットから実オッズ（単勝）を読んで予想オッズを置き換える")
    a = ap.parse_args()
    R = BASE / a.dir / "research"
    inp = json.loads((R / "index_input.json").read_text(encoding="utf-8"))
    if a.snapshot_day:
        from odds_snapshot import latest_snapshots   # 取得時刻で最新を選ぶ
        latest = latest_snapshots(a.snapshot_day)
        for race in inp["races"]:
            files = [latest[race["race_id"]]] if race.get("race_id") in latest else []
            if not files:
                print(f"⚠ {race['name']}: スナップショットなし（予想オッズのまま）")
                continue
            snap = json.loads(files[-1].read_text(encoding="utf-8"))
            tan = {int(k): float(v[0]) for k, v in snap["odds"].get("単勝", {}).items() if v and v[0]}
            names = {h["umaban"]: h["horse_name"] for h in snap["horses"].values()}
            for h in race["horses"]:
                if names.get(h["umaban"]) != h["name"]:          # 馬番と馬名がずれていたら使わない
                    sys.exit(f"❌ {race['name']} {h['umaban']}番: 出馬表={h['name']} / オッズ側={names.get(h['umaban'])}")
                h["yoso_odds"] = tan.get(h["umaban"])               # 取消馬は None になり確率計算から外れる
                h["weight"] = snap["horses"].get(f"{h['umaban']:02d}", {}).get("weight", "")
            status = {m.get("status") for m in snap.get("odds_meta", {}).values()}
            inp["odds_note"] = f"単勝オッズは {snap.get('fetched_at')} 取得のスナップショット（status={'/'.join(sorted(x for x in status if x))}）"
            print(f"{race['name']}: {files[-1].name} の単勝オッズに置き換え")
    rank = {r["race"]: r for r in json.loads((R / "index_ranking.json").read_text(encoding="utf-8"))["races"]}
    cdb = ContextDB()
    rows = json.loads((BASE / "daily_pdca" / "db" / "race_results.json").read_text(encoding="utf-8"))
    out = dict(dir=a.dir, draw_confirmed=inp.get("draw_confirmed"), odds_note=inp.get("odds_note"),
               keshi=KESHI, context_layers_enabled=list(enabled_layers()), races=[])

    for race in inp["races"]:
        nm = race["name"]
        course = f"{race['surface']}{race['distance']}"
        idx = {h["name"]: h for h in rank[nm]["horses"]}
        no_odds = [h["name"] for h in race["horses"] if not h.get("yoso_odds")]   # 実オッズに無い馬＝出走取消
        hs = [h for h in race["horses"] if h.get("yoso_odds")]
        if no_odds:
            print(f"⚠ {nm}: オッズが無い馬を除外（取消の可能性）: {no_odds}")
        tan = {h["umaban"]: h["yoso_odds"] for h in hs}
        name = {h["umaban"]: h["name"] for h in hs}
        score = {h["umaban"]: idx[h["name"]]["index"] for h in hs}
        import re as _re
        def _wt(h):
            m = _re.search(r"\(([+-]?\d+)\)", str(h.get("weight") or ""))
            return bool(m) and int(m.group(1)) <= -10
        flags = {h["umaban"]: {"kin70": idx[h["name"]]["factors"]["F10_斤量"] >= 70, "wt_m10": _wt(h)} for h in hs}

        q = market_probs(tan)
        p = adjust(q, flags)
        tk = ticket_probs(top3_scenarios(p), p)             # 全頭λ-Harville（prob_calib_audit で実測に最も合った）
        t3 = {u: tk["複勝"].get((u,), 0.0) for u in p}
        porder = sorted(p, key=lambda u: -p[u])
        pop_of = {u: i + 1 for i, u in enumerate(sorted(tan, key=lambda u: tan[u]))}

        date8 = a.dir
        horses = []
        for h in sorted(hs, key=lambda x: x["umaban"]):
            u, ix = h["umaban"], idx[h["name"]]
            F = ix["factors"]
            n = len(hs)
            f07_neutral = F["F07_馬番"] - (1.0 - (u - 1) / max(n - 1, 1) - 0.5) * \
                {"東京": 25.0, "京都": 35.0, "中山": 30.0, "阪神": 28.0}.get(race["venue"], 15.0)
            # 指数のうち枠・馬番だけで動いた点数（重み: 枠0.09 / 馬番内外0.05）
            draw_delta = round((F["F06_枠"] - WAKU_NEUTRAL) * 0.09 + (F["F07_馬番"] - f07_neutral) * 0.05, 2)
            horses.append(dict(
                waku=h["waku"], umaban=u, name=h["name"], sexage=f"{h['sex']}{h['age']}", kin=h["kin"],
                jockey=h["jockey"], trainer=h.get("trainer", ""),
                odds=h.get("yoso_odds"), pop=pop_of.get(u),
                index=ix["index"], index_rank=ix["rank"], prev_index=ix.get("prev_index"), prev_rank=ix.get("prev_rank"),
                draw_delta=draw_delta, runs=ix["runs"],
                style=cdb.style_forecast(h["name"], date8),
                q=round(q.get(u, 0), 4), p=round(p.get(u, 0), 4), p_top3=round(t3.get(u, 0), 4),
                p_rank=porder.index(u) + 1 if u in porder else None,
                keshi=[k for k, v in flags[u].items() if v]))

        pats, ctx = classify(score, tan)
        cands, p1, _, hon_idx, ana = build_candidates(score, tan, name)
        scored = sorted((score_candidate(c, a.budget) for c in cands), key=lambda s: -s["adj"])
        cand_out = [dict(name=s["cand"].name, kind=s["cand"].kind, ok=s["ok"], ng=s["ng"],
                         ev=round(s["ev"], 3), prior=s["prior"], adj=round(s["adj"], 3),
                         hit=round(s["hit"], 3), over=round(s["over"], 3),
                         points=[dict(t=x["t"], combo=x["combo"], est=x["est"], p=round(x["p"], 4),
                                      p_src=x["p_src"], amt=x["amt"]) for x in s["points"]]) for s in scored]

        wt = waku_table(rows, race["venue"], course)
        out["races"].append(dict(
            name=nm, grade=race["grade"], venue=race["venue"], course=course + "m", n=len(hs),
            race_id=race.get("race_id"), scratched_from_predraw=race.get("scratched_from_predraw", []) + no_odds,
            horses=horses, p_order=porder, index_top=hon_idx, ana_by_index=ana,
            pattern=dict(id=pats[0]["id"], name=pats[0]["name"], desc=pats[0]["desc"],
                         default=DEFAULT_STRUCTURE[pats[0]["id"]], all=[x["id"] for x in pats]),
            waku_measured=wt, candidates=cand_out,
            quinella_top={"-".join(map(str, k)): round(v, 4) for k, v in
                          sorted(tk["馬連"].items(), key=lambda kv: -kv[1])[:8]}))

        print(f"\n■ {nm}（{race['venue']} {course}m・{len(hs)}頭）  型 {pats[0]['id']} {pats[0]['name']} → 既定 {DEFAULT_STRUCTURE[pats[0]['id']]}")
        print(f"{'枠':>2}{'番':>3} {'馬名':<12}{'脚質':<4}{'人気':>3}{'ｵｯｽﾞ':>7}{'q%':>6}{'p%':>6}{'3着内%':>7}{'指数':>6}{'順':>3}{'前順':>4}{'枠分':>6} 消し")
        for x in horses:
            print(f"{x['waku']:>2}{x['umaban']:>3} {x['name']:<12}{(x['style'] or '?'):<4}{x['pop']:>3}{x['odds']:>7.1f}"
                  f"{x['q']*100:>6.1f}{x['p']*100:>6.1f}{x['p_top3']*100:>7.1f}{x['index']:>6.1f}{x['index_rank']:>3}"
                  f"{str(x['prev_rank'] or '-'):>4}{x['draw_delta']:>+6.2f} {','.join(x['keshi'])}")
        print(f"  確率順: {[f'{u}{name[u]}' for u in porder[:6]]}")
        print(f"  枠の実測（{race['venue']}{course}・{wt['races']}R／人気で条件付け 実測÷期待）: "
              + " ".join(f"{w}枠{v['ratio']}({v['top3']}/{v['expected']})" for w, v in wt["by_waku"].items()))
        for s in cand_out:
            print(f"  {'○' if s['ok'] else '×'} {s['name']:<10} 期待値{s['ev']:.2f} 的中{s['hit']*100:4.1f}% Σ{s['over']:.2f} {s['ng']}")

    dst = R / "draw_final.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存: {dst}")

    mk = R / "draw_marks.json"
    if mk.exists():
        kaime_stage(out, json.loads(mk.read_text(encoding="utf-8")), R / f"sns_kaime_{a.dir}.json")


def cap_amount(pts, budget, cap=0.30):
    """1点上限（予算の30%）を超えた分を、残りの点へ推定配当に反比例で配り直す（100円単位）"""
    lim = int(budget * cap // 100 * 100)
    for _ in range(len(pts)):
        over = [x for x in pts if x["amt"] > lim]
        if not over:
            return
        free = [x for x in pts if x["amt"] < lim]
        if not free:
            return
        extra = sum(x["amt"] - lim for x in over)
        for x in over:
            x["amt"] = lim
        w = [1 / x["est"] for x in free]
        add = [int(extra * wi / sum(w) // 100 * 100) for wi in w]
        add[add.index(max(add))] += extra - sum(add)
        for x, v in zip(free, add):
            x["amt"] += v


def kaime_stage(out, M, dst):
    """印（draw_marks.json）に沿った買い目を金額まで決めて検査する。
    ファイル名は sns_kaime_*.json（rule_forward_ledger が読む kaime_*.json と混ざらないようにする）。
    検査: 100円単位／合計＝予算／Σ(1/推定配当)≦1.0／本線は推定4.0倍以上／全点が1頭に依存しない／△🔥が1回は入る"""
    from payout_estimator import estimate
    from kaime_select import allocate
    res = dict(compiled=M.get("compiled"), stage=M.get("stage"), odds_note=out.get("odds_note"),
               note="SNS提示用。前向き台帳（K1・R1）は当日朝の実オッズで別に登録する", races={})
    for race in out["races"]:
        spec = M["races"].get(race["name"])
        if not spec:
            continue
        H = {h["umaban"]: h for h in race["horses"]}
        O = {u: h["odds"] for u, h in H.items()}
        p = {u: h["p"] for u, h in H.items()}
        sp = sum(p.values()) or 1.0
        p = {u: v / sp for u, v in p.items()}
        tk = ticket_probs(top3_scenarios(p), p)
        pts = []
        gone = [u for x in spec["bets"] for u in x["combo"] if u not in H]
        if gone:
            sys.exit(f"❌ {race['name']}: 買い目に出走しない馬番 {sorted(set(gone))} が入っています。draw_marks.json を直してください")
        for b in spec["bets"]:
            c, t = b["combo"], b["t"]
            est = O[c[0]] if t == "単勝" else estimate(t, [O[x] for x in c])
            pr = tk[t].get(tuple(c) if t in ("馬単", "単勝") else tuple(sorted(c)), 0.0)
            pts.append(dict(t=t, combo=c, role=b.get("role", ""), est=round(est, 1), p=round(pr, 4)))
        allocate(pts, M.get("budget", 10000))
        cap_amount(pts, M.get("budget", 10000))
        budget = sum(x["amt"] for x in pts)
        over = sum(1 / x["est"] for x in pts)
        honsen = max(pts, key=lambda x: x["amt"])
        mk = spec["marks"]
        marked = [mk["◎"], mk["○"], mk["▲"], *mk["△"]] + ([mk["🔥"]] if mk.get("🔥") else [])
        used = {u for x in pts for u in x["combo"]}
        common = set.intersection(*[set(x["combo"]) for x in pts])
        checks = {"100円単位": all(x["amt"] % 100 == 0 and x["amt"] >= 100 for x in pts),
                  "合計＝予算": budget == M.get("budget", 10000),
                  "Σ(1/推定配当)≦1.0": over <= 1.0,
                  "本線は推定4.0倍以上": honsen["est"] >= 4.0,
                  "全点が1頭に依存しない": not common,
                  "印を付けた馬が1回は入る": all(u in used for u in marked),
                  "1点上限30%": max(x["amt"] for x in pts) <= budget * 0.30}
        for x in pts:
            x["back"] = int(x["amt"] * x["est"] // 100 * 100)
        # どれか1点以上当たる確率（ワイドは同時に当たるので足し算にせず、着順シナリオで数える）
        sc = top3_scenarios(p)
        def _hit(a, b, c3):
            for x in pts:
                cc, t = x["combo"], x["t"]
                if (t == "単勝" and cc[0] == a) or (t == "馬連" and set(cc) == {a, b}) or (t == "馬単" and cc == [a, b])                         or (t == "ワイド" and set(cc) <= {a, b, c3}) or (t == "3連複" and set(cc) == {a, b, c3}):
                    return True
            return False
        hit_any = sum(pr for (a, b, c3), pr in sc.items() if _hit(a, b, c3))
        ev = sum(x["p"] * x["amt"] * x["est"] for x in pts) / budget if budget else 0
        res["races"][race["name"]] = dict(view=spec["view"], marks=mk, caution=spec.get("caution", []),
                                          name={str(u): h["name"] for u, h in H.items()},
                                          points=pts, budget=budget, over=round(over, 3), checks=checks,
                                          hit_any=round(hit_any, 4), ev_est=round(ev, 3))
        print(f"\n■ {race['name']} 買い目（{spec['view']}）")
        for x in pts:
            print(f"  {x['t']:<4}{'-'.join(map(str, x['combo'])):<8}{x['amt']:>6,}円  推定{x['est']:>5.1f}倍 → {x['back']:>7,}円"
                  f"  的中率{x['p']*100:>5.1f}%  {x['role']}")
        print(f"  合計{budget:,}円 / {len(pts)}点  Σ(1/配当)={over:.2f}  どれか当たる確率{hit_any*100:.0f}%  推定の期待回収{ev*100:.0f}%  "
              + " ".join(f"{'✅' if v else '❌'}{k}" for k, v in checks.items()))
    dst.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存: {dst}")


if __name__ == "__main__":
    main()
