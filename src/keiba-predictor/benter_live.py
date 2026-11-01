# -*- coding: utf-8 -*-
"""
benter_live.py — 「市場＋木（ずれ）」の単勝ルール B1 を当日のレースに当てる（2026-10-21 事前登録）
==================================================================================================
根拠（benter.py・docs/keiba_benter.md）: 20年分の年ごとの前向き検証で、市場の確率を出発点に「市場とのずれ」だけを木のモデルで学ぶと
  対数尤度が市場より +0.0112（17年すべて改善）。発走前のオッズで買う馬を選び、確定オッズで払い戻すと（2023/1〜2026/10・12,414R）
    30分前 119.5%［103.6〜138.0］／10分前 116.1%［100.5〜134.1］／5分前 115.9%［100.7〜133.7］・4年とも100%超
  ただし作り方は2023〜26を含む20年の結果を見て選んだ → ここからの前向き台帳で確かめる。それまで実際には買わない

ルール B1（動かさない。変えるなら版を上げる）
  ・券種: 単勝だけ ・選ぶ時点: 自動運転の登録時（発走35〜30分前）の単勝オッズ
  ・確率: p ∝ exp( 市場の重み×ln(そのときの市場の確率) ＋ 木の重み×木の点数 )。重みと木は _cache/benter_live.pkl（benter.py --fit-live）
  ・買う馬: p×オッズ ≧ 1.0 の全部に100円ずつ（上限1万円＝100頭分なので実質かからない）
  ・採用: 300レース以上で、レース単位の95%区間の下限が100%超（ほかの台帳と同じ）
  ・10分前・5分前の版: 登録時に木の点数を残し（db/ledger_b1_races.json）、後で時系列オッズ（0B41）から計算し直して並べる

当日の特徴量は朝に作る（ev_live.py の通常実行）。朝の時点で空の列は、登録の直前にここで入れ直す:
  ・馬体重（発走の約1時間前に発表・JV 0B11）: 増減・470kgとの差・439kg以下・一番軽い・ダート×体重・好走時の体重との離れ・休み明け×減り・中5週×増・牝馬×増減
  ・当日のトラックバイアス: その日・その場・同じ芝ダで、もう終わったレース（3R以上・内枠8頭以上）から
"""
from __future__ import annotations
import datetime, json, re
from pathlib import Path

import numpy as np

import ev_engine as E

RULE_B1 = "B1"
EV_B1 = 1.0
STAKE = 100
CAP = 10_000
_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        import benter
        _MODEL = benter.load_live() or False
    return _MODEL or None


def day_bias(res_rows, date, exp3):
    """その日の終わったレース → {(場, 芝ダ): [(R, 内枠の上振れ[...], 前の上振れ[...])]}"""
    races = {}
    for r in res_rows:
        if r.get("date") != date:
            continue
        races.setdefault((r["競馬場"], int(float(r["R"]))), []).append(r)
    out = {}
    for (v, R), hs in sorted(races.items()):
        fs = [E.fin(h) for h in hs]
        os_ = [E.num(h.get("単勝オッズ")) for h in hs]
        if not all(fs) or not all(os_):
            continue                                       # まだ終わっていない・取消の扱いが不明なレースは使わない
        ins, frs = [], []
        for h, f, o in zip(hs, fs, os_):
            rk = min(14, 1 + sum(1 for y in os_ if y < o))
            rres = float(f <= 3) - exp3.get(rk, 0.2)
            if h.get("枠") and int(h["枠"]) <= 3:
                ins.append(rres)
            if h.get("脚質") in ("逃げ", "先行"):
                frs.append(rres)
        out.setdefault((v, E.surf(hs[0].get("距離"))), []).append((R, ins, frs))
    return out


def refresh(Xf, aux, key, uma_all, wh, sf, bias):
    """朝の全特徴量（頭数×F_ALL）に、馬体重と当日のトラックバイアスを入れ直したコピー"""
    IX = E.IX
    X = np.array(Xf, dtype=float, copy=True)
    bws = {}
    for i, u in enumerate(uma_all):
        w = wh.get((key[1], key[2], int(u)))
        if not w:
            continue
        x = X[i]
        mb = re.match(r"(\d+)", w)
        md = re.search(r"\(([+-]?\d+)\)", w)
        if md:
            d = int(md.group(1))
            x[IX["馬体重 増減（10kg単位）"]] = max(-2.0, min(2.0, d / 10.0))
            x[IX["馬体重 10kg以上減"]], x[IX["馬体重 10kg以上増"]] = float(d <= -10), float(d >= 10)
            gap = aux[i][0]
            if gap is not None and gap >= 91:
                x[IX["休み明け×体重の減り（10kg単位）"]] = max(0.0, min(3.0, -d / 10.0))
            if gap is not None and gap <= 35:
                x[IX["中5週以内×12kg以上増"]] = float(d >= 12)
            if x[IX["牝馬"]] == 1.0:
                x[IX["牝馬×増減の大きさ（10kg単位）"]] = min(3.0, abs(d) / 10.0)
        if mb:
            bw = int(mb.group(1))
            bws[i] = bw
            x[IX["馬体重（470kgとの差・40kg単位）"]] = max(-2.0, min(2.0, (bw - 470) / 40.0))
            x[IX["馬体重 439kg以下"]] = float(bw <= 439)
            if sf == "ダ":
                x[IX["ダート×馬体重（470kgとの差）"]] = max(-2.0, min(2.0, (bw - 470) / 40.0))
            if aux[i][1]:
                x[IX["好走時の体重との離れ（10kg単位）"]] = min(3.0, abs(bw - aux[i][1]) / 10.0)
    n = len(uma_all)
    if len(bws) == n and n >= 8:
        m = min(bws.values())
        for i, bw in bws.items():
            X[i, IX["レースで一番軽い"]] = float(bw == m)
    done = [b for b in bias.get((key[1], sf), []) if b[0] < key[2]]
    ins = [x for b in done for x in b[1]]
    frs = [x for b in done for x in b[2]]
    return X, done, ins, frs


def apply_bias(X, waku, done, ins, frs):
    IX = E.IX
    if len(done) >= 3 and len(ins) >= 8:
        Wd = sum(ins) / len(ins)
        for i, wk in enumerate(waku):
            if wk:
                X[i, IX["当日の内枠有利度×内枠"]] = Wd * 10.0 * float(wk <= 3)
                X[i, IX["当日の内枠有利度×外枠"]] = Wd * 10.0 * float(wk >= 6)
    if len(done) >= 3 and len(frs) >= 8:
        Bd = sum(frs) / len(frs)
        X[:, IX["当日の前残り度×前で運ぶ割合"]] = Bd * 10.0 * (X[:, IX["前で運ぶ割合（直近5走）"]] + 0.4)
    return X


def score(cache_races, snap, wh, res_rows, date, exp3, names_of=None):
    """戻り: [{key, race_id, title, uma, odds, p, s_res, picks:[...], filled:(体重の発表頭数, 頭数), bias_races}]"""
    m = model()
    if m is None:
        print("  B1: _cache/benter_live.pkl が無いので計算しません（python benter.py --fit-live）")
        return []
    bias = day_bias(res_rows, date, exp3)
    out = []
    for c in cache_races:
        if c.get("Xf") is None:
            continue
        tan, nm, d = snap.get((c["key"][1], c["key"][2]), ({}, {}, None))
        X, done, ins, frs = refresh(c["Xf"], c["aux"], c["key"], c["uma"], wh, c["sf"], bias)
        X = apply_bias(X, c.get("waku") or [None] * len(c["uma"]), done, ins, frs)
        s_all = m.score_res(X)
        keep = [i for i, u in enumerate(c["uma"]) if tan.get(u) and tan[u] < 900]
        if len(keep) < 5 or d is None:
            continue
        uma = [int(c["uma"][i]) for i in keep]
        odds = np.array([tan[c["uma"][i]] for i in keep], float)
        s = s_all[keep] - s_all[keep].mean()
        p = m.probs(s, odds)
        picks = [dict(uma=u, name=nm.get(u, ""), odds=float(o), p=round(float(pi), 4), ev=round(float(pi * o), 3))
                 for u, o, pi in zip(uma, odds, p) if pi * o >= EV_B1]
        out.append(dict(key=c["key"], race_id=d["race_id"], title=(d.get("title") or "")[:24], snap_at=d.get("fetched_at"), uma=uma,
                        odds=[float(x) for x in odds], p=[round(float(x), 4) for x in p], s_res=[round(float(x), 4) for x in s],
                        w=[float(x) for x in m.w_res], picks=picks,
                        filled=(sum(1 for u in c["uma"] if (c["key"][1], c["key"][2], int(u)) in wh), len(c["uma"])), bias_races=len(done)))
    return out


def show(rs):
    if not rs:
        return
    n = sum(len(r["picks"]) for r in rs)
    print(f"\n■ B1（市場＋木の単勝・確率×オッズ≧{EV_B1}）候補 {n}点 / {len(rs)}レース中")
    for r in rs:
        for x in r["picks"]:
            print(f"  {r['key'][1]}{r['key'][2]:>2}R 単勝 {x['uma']:>2} {x['name'][:8]:<8} オッズ{x['odds']:>6.1f}  確率{x['p']*100:5.1f}%  期待値{x['ev']:.2f}"
                  f"  （馬体重 {r['filled'][0]}/{r['filled'][1]}頭・当日の終わったレース {r['bias_races']}）")


def register(rs, date, only, ledger: Path, races_log: Path):
    led = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    rl = json.loads(races_log.read_text(encoding="utf-8")) if races_log.exists() else []
    done = {x["race_id"] for x in rl}
    now = datetime.datetime.now().isoformat(timespec="minutes")
    m = 0
    for r in rs:
        rk = f"{r['key'][1]}{r['key'][2]}"
        if r["race_id"] in done or (only is not None and rk not in only):
            continue                                       # 1レース1回（最初に登録した時点のオッズで決める）
        rl.append(dict(rule=RULE_B1, date=date, venue=r["key"][1], R=r["key"][2], race_id=r["race_id"], registered_at=now, snap_at=r["snap_at"],
                       uma=r["uma"], odds=r["odds"], s_res=r["s_res"], w=r["w"], filled=r["filled"], bias_races=r["bias_races"]))
        stake = STAKE if len(r["picks"]) * STAKE <= CAP else CAP // len(r["picks"]) // 100 * 100
        for x in r["picks"]:
            led.append(dict(rule=RULE_B1, date=date, race_id=r["race_id"], venue=r["key"][1], R=r["key"][2], title=r["title"], type="単勝",
                            combo=[x["uma"]], names=[x["name"]], p_model=x["p"], odds_now=x["odds"], ev_now=x["ev"], stake=stake,
                            model="benter_live " + str(getattr(model(), "last", "")), registered_at=now, snap_at=r["snap_at"], settled=False, payout=None))
            m += 1
    ledger.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
    races_log.write_text(json.dumps(rl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"B1 台帳に {m} 点を追加（累計 {len(led)} 点・登録レース {len(rl)}）→ {ledger}")


# ── 後から: 10分前・5分前のオッズで選んでいたら（時系列オッズ 0B41・登録時の木の点数を使う） ─────────
TS_B1 = Path("C:/keiba_db/jv_raw/TS_b1")
PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
HERE = Path(__file__).resolve().parent


def _db():
    import ev_live as L
    return L


def jv_key(x):
    """netkeiba の race_id（年4・場2・回2・日2・R2）→ JV のレースキー（日付8・場2・回2・日2・R2）"""
    rid = str(x["race_id"])
    return x["date"] + rid[4:12] if len(rid) == 12 and rid.isdigit() else None


def fetch_ts(dates):
    """登録済みのレースの時系列オッズを JV（0B41）から取る。32bit PowerShell の jv/jv_ts.ps1 を使う"""
    import subprocess
    L = _db()
    rl = json.loads(L.LEDGER_B1_RACES.read_text(encoding="utf-8")) if L.LEDGER_B1_RACES.exists() else []
    keys = sorted({jv_key(x) for x in rl if x["date"] in dates and jv_key(x)})
    keys = [k for k in keys if not (TS_B1 / f"{k}.txt").exists()]
    if not keys:
        print("取るレースがありません（未登録か取得済み）")
        return
    TS_B1.mkdir(parents=True, exist_ok=True)
    kf = TS_B1.parent / "ts_keys_b1.txt"
    kf.write_text("\n".join(keys), encoding="ascii")
    r = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "jv" / "jv_ts.ps1"),
                        "-KeyFile", str(kf), "-Spec", "0B41", "-OutDir", str(TS_B1)], capture_output=True, text=True, errors="replace", timeout=1800)
    print((r.stdout or "").strip().splitlines()[-1:] or r.returncode)


def _post(date):
    """{(場, R): 'MMDDHHMM'}（当日の RA と 発走時刻の変更 TC から）"""
    import target_import as T
    import jv_odds as J
    raw, out = Path("C:/keiba_db/jv_raw"), {}
    for f in [raw / "RT" / "entry" / f"RA_{date}.txt", raw / "RT" / f"RA_{date}.txt", raw / "RACE" / f"RA_{date[:4]}.txt"]:
        if f.exists():
            b = f.read_bytes()
            for i in range(0, len(b) - 1271, 1272):
                r = b[i:i + 1272]
                x = T.parse_ra(r)
                hm = r[873:877].decode("ascii", "ignore")
                if x and x["date"] == date and x["R"] and hm.isdigit():
                    out.setdefault((x["venue"], x["R"]), date[4:] + hm)
    tc = raw / "RT" / "info" / f"TC_{date}.txt"
    if tc.exists():
        for ln in tc.read_bytes().decode("ascii", "ignore").splitlines():
            if ln[:2] == "TC" and len(ln) >= 43 and ln[11:19] == date and ln[35:39].isdigit():
                out[(J.VENUE.get(ln[19:21]), int(ln[25:27]))] = date[4:] + ln[35:39]
    return out


def _snaps(f):
    import jv_odds as J
    t = f.read_bytes().decode("ascii", "ignore")
    s = []
    for i in range(0, len(t), 962):
        rec = t[i:i + 962]
        if rec.startswith("O1"):
            tan = J.parse_record("O1", rec)["単勝"]
            if tan:
                s.append((rec[27:35], {k[0]: v for k, v in tan.items()}))
    return sorted(s, key=lambda z: z[0])


def late_report():
    """登録時（35〜30分前）と 10分前・5分前 で選んでいたらの回収率を、同じレースで並べる。払戻は JV の HR"""
    import datetime as dt
    import target_import as T
    L = _db()
    rl = json.loads(L.LEDGER_B1_RACES.read_text(encoding="utf-8")) if L.LEDGER_B1_RACES.exists() else []
    pays, posts = {}, {}
    for d in {x["date"] for x in rl}:
        f = Path("C:/keiba_db/jv_raw/RT") / f"HR_{d}.txt"
        if f.exists():
            b = f.read_bytes()
            for i in range(0, len(b) - 718, 719):
                h = T.parse_hr(b[i:i + 719])
                if h:
                    pays[(d, h["venue"], h["R"])] = h["pay"].get("単勝", {})
        posts[d] = _post(d)
    res = {k: [0.0, 0.0, 0] for k in ("登録時", "10分前", "5分前")}
    per = {k: [] for k in res}
    for x in rl:
        pay = pays.get((x["date"], x["venue"], x["R"]))
        if pay is None:
            continue
        cand = {"登録時": dict(zip(x["uma"], x["odds"]))}
        k = jv_key(x)
        post = posts[x["date"]].get((x["venue"], x["R"]))
        if k and post and (TS_B1 / f"{k}.txt").exists():
            P = dt.datetime.strptime("2000" + post, "%Y%m%d%H%M")
            sn = _snaps(TS_B1 / f"{k}.txt")
            for lab, m in (("10分前", 10), ("5分前", 5)):
                od = None
                for t, o in sn:
                    if dt.datetime.strptime("2000" + t, "%Y%m%d%H%M") <= P - dt.timedelta(minutes=m):
                        od = o
                if od:
                    cand[lab] = {u: od.get(u) for u in x["uma"]}
        s = np.array(x["s_res"], float)
        for lab, om in cand.items():
            o = np.array([om.get(u) or np.nan for u in x["uma"]], float)
            if np.isnan(o).any() or (o <= 0).any():
                continue
            q = (1 / o) / (1 / o).sum()
            u = x["w"][0] * np.log(q) + x["w"][1] * s
            p = np.exp(u - u.max()); p /= p.sum()
            sel = [int(uu) for uu, pi, oi in zip(x["uma"], p, o) if pi * oi >= EV_B1]
            st = STAKE * len(sel)
            rt = sum(pay.get((uu,), 0) * STAKE / 100.0 for uu in sel)
            res[lab][0] += st; res[lab][1] += rt; res[lab][2] += 1
            per[lab].append((st, rt))
    print("■ B1 選ぶ時点の比較（同じ木の点数・払戻は確定）")
    for lab, (st, rt, n) in res.items():
        if not n:
            print(f"  {lab:<5} データなし" + ("（python benter_live.py --fetch-ts 日付 で時系列オッズを取る）" if lab != "登録時" else ""))
            continue
        a = np.array(per[lab])
        import benter
        roi, lo, hi = benter.roi_ci(a[:, 0], a[:, 1]) if st else (None, None, None)
        print(f"  {lab:<5} {n:>4}レース {int(st/STAKE):>4}点  回収率 {(roi or 0)*100:6.1f}%" + (f" ［{lo*100:.0f}〜{hi*100:.0f}%］" if roi is not None else ""))


if __name__ == "__main__":
    import argparse, sys
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-ts", nargs="+", metavar="YYYYMMDD", help="登録済みレースの時系列オッズ（0B41）を取る")
    ap.add_argument("--late", action="store_true", help="登録時・10分前・5分前で選んでいたらの回収率")
    a = ap.parse_args()
    if a.fetch_ts:
        fetch_ts(set(a.fetch_ts))
    if a.late:
        late_report()
