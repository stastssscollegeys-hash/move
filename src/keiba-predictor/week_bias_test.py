# -*- coding: utf-8 -*-
"""
week_bias_test.py — 先週のトラックバイアスは今週に続くか（開催替わり・柵替え・馬場の変化で分けて）を10年で測る（2026-10-07新規）
==============================================================================================================
ユーザー指摘: トラックバイアスは 先週の状況・競馬場が変わるタイミング・週末から週末までの天気と馬場状態 で変わる。
            指数の比較だけでなく、先週の状態と今週への変化を見て最終予想を作るべき。
測り方（リークなし）:
  ・週末ごと（土日月）× 競馬場 × 芝ダ で、前の週末の「内枠（1〜3枠）」と「前で運んだ馬（逃げ・先行）」の 3着内 − 人気からの期待（1頭あたり）を出す
  ・次に同じ競馬場・同じ芝ダで行われた週末（9日以内）で、レース前に分かる「内枠の馬」「前で運ぶ型の馬」の 3着内 − 期待 を、前週の偏りの向きで比べる
  ・区分: 同じ開催・同じ柵（A/B/C…） ／ 同じ開催で柵替え ／ 開催替わり ／ 今週の馬場が前週より悪化（良→稍重以下）・回復
データ: history_target（結果）、TARGET の SR（回・日目・柵の位置。RA の 710 バイト目）
出力: docs/keiba_week_bias.md ／ db/week_bias.json
"""
from __future__ import annotations
import collections, datetime, glob, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import predict_day as P
import target_import as T

E.SOURCE = P.HIST


def meta():
    """(日付, 場, R) → (回, 日目, 柵)"""
    out = {}
    for y in range(2016, 2027):
        for f in glob.glob(f"C:/TFJV/SE_DATA/{y}/SR*.DAT"):
            for r in T.records(Path(f), 1272):
                x = T.parse_ra(r)
                if x and x["R"]:
                    out[(x["date"], x["venue"], x["R"])] = (T.seg(r, 22, 2), T.seg(r, 24, 2), r[709:710].decode("ascii", "ignore").strip())
    return out


def wkey(d):
    dt = datetime.date(int(d[:4]), int(d[4:6]), int(d[6:]))
    return (dt - datetime.timedelta(days=(dt.weekday() - 4) % 7)).isoformat()   # その週の金曜（土日月を1つの週末に）


def main():
    M = meta()
    rows = [r for r in E.load_rows() if r.get("着順int") and r.get("人気")]
    pr = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        p = min(int(r["人気"]), 14); pr[p][0] += 1; pr[p][1] += r["着順int"] <= 3
    EXP = {p: v[1] / v[0] for p, v in pr.items()}
    by_h = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: (r["date"], r["R"])):
        by_h[r.get("horse_id") or r["馬名"]].append(r)
    pre = {}
    for rs in by_h.values():
        for i, r in enumerate(rs):
            past = [x for x in rs[max(0, i - 5):i] if x.get("脚質")]
            if len(past) >= 2:
                sh = sum(x["脚質"] in ("逃げ", "先行") for x in past) / len(past)
                pre[id(r)] = "前" if sh >= 0.6 else "後" if sh <= 0.2 else "中"
    wk = collections.defaultdict(list)
    for r in rows:
        wk[(r["競馬場"], r["距離"][:1], wkey(r["date"]))].append(r)
    stat = {}
    for k, rs in wk.items():
        inn = [r for r in rs if r.get("枠") and r["枠"] <= 3]
        fr = [r for r in rs if r.get("脚質") in ("逃げ", "先行")]
        if len(inn) < 30 or len(fr) < 30:
            continue
        babas = collections.Counter(r["馬場状態"] for r in rs)
        m = [M.get((r["date"], r["競馬場"], r["R"])) for r in rs]
        m = [x for x in m if x]
        stat[k] = dict(W=sum((r["着順int"] <= 3) - EXP[min(int(r["人気"]), 14)] for r in inn) / len(inn),
                       B=sum((r["着順int"] <= 3) - EXP[min(int(r["人気"]), 14)] for r in fr) / len(fr),
                       bad=sum(v for b, v in babas.items() if b and b != "良") / max(1, sum(babas.values())),
                       kai=collections.Counter(x[0] for x in m).most_common(1)[0][0] if m else "",
                       rail=collections.Counter(x[2] for x in m).most_common(1)[0][0] if m else "",
                       last_day=max(x[1] for x in m) if m else "")
    obs = []
    keys = sorted(stat)
    for (v, sf, w) in keys:
        nxt = (datetime.date.fromisoformat(w) + datetime.timedelta(days=7)).isoformat()
        cur, nx = stat[(v, sf, w)], stat.get((v, sf, nxt))
        if not nx:
            continue
        if cur["kai"] != nx["kai"]:
            cond = "開催替わり"
        elif sf == "芝" and cur["rail"] and nx["rail"] and cur["rail"] != nx["rail"]:
            cond = "同じ開催・柵替え"
        else:
            cond = "同じ開催・同じ柵"
        bc = "馬場が悪化" if nx["bad"] - cur["bad"] >= 0.5 else "馬場が回復" if cur["bad"] - nx["bad"] >= 0.5 else "馬場は同程度"
        for r in wk[(v, sf, nxt)]:
            e = EXP[min(int(r["人気"]), 14)]
            obs.append(dict(cond=cond, baba=bc, sf=sf, Wp=cur["W"], Bp=cur["B"], inner=bool(r.get("枠") and r["枠"] <= 3), style=pre.get(id(r)),
                            res=(r["着順int"] <= 3) - e, e=e, year=r["date"][:4]))
    print(f"■ 前週→今週の組 {len({(o['cond'], o['Wp']) for o in obs}):,}／ 判定の頭数 {len(obs):,}")
    out = {}

    def tab(label, sel, keyf, cuts):
        res = []
        for lo, hi, lab in cuts:
            sub = [o for o in obs if sel(o) and lo <= keyf(o) < hi]
            if len(sub) < 300:
                continue
            ex = sum(o["e"] for o in sub); rs = sum(o["res"] for o in sub); var = sum(o["e"] * (1 - o["e"]) for o in sub)
            res.append(dict(band=lab, n=len(sub), ratio=round((ex + rs) / ex, 3), z=round(rs / math.sqrt(var), 2)))
            print(f"  {label:<26}{lab:<14}{len(sub):>7,}頭  実際/期待 {(ex + rs) / ex:5.3f}  z={rs / math.sqrt(var):+5.2f}")
        return res
    CW = [(-9, -0.04, "前週は内が不利"), (-0.04, 0.04, "前週ふつう"), (0.04, 9, "前週は内が有利")]
    CB = [(-9, -0.04, "前週は前が止まる"), (-0.04, 0.04, "前週ふつう"), (0.04, 9, "前週は前残り")]
    for cond in ("同じ開催・同じ柵", "同じ開催・柵替え", "開催替わり"):
        for sf in ("芝", "ダ"):
            print(f"■ {cond}・{sf}")
            out[f"{cond}|{sf}|内枠"] = tab("内枠の馬 × 前週の内枠有利度", lambda o, c=cond, s=sf: o["cond"] == c and o["sf"] == s and o["inner"], lambda o: o["Wp"], CW)
            out[f"{cond}|{sf}|前"] = tab("前で運ぶ型 × 前週の前残り度", lambda o, c=cond, s=sf: o["cond"] == c and o["sf"] == s and o["style"] == "前", lambda o: o["Bp"], CB)
    for bc in ("馬場は同程度", "馬場が悪化", "馬場が回復"):
        print(f"■ 同じ開催・同じ柵 × {bc}（芝ダ合計）")
        out[f"馬場|{bc}|内枠"] = tab("内枠の馬 × 前週の内枠有利度", lambda o, b=bc: o["cond"] == "同じ開催・同じ柵" and o["baba"] == b and o["inner"], lambda o: o["Wp"], CW)
        out[f"馬場|{bc}|前"] = tab("前で運ぶ型 × 前週の前残り度", lambda o, b=bc: o["cond"] == "同じ開催・同じ柵" and o["baba"] == b and o["style"] == "前", lambda o: o["Bp"], CB)
    (P.BASE / "daily_pdca" / "db" / "week_bias.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
