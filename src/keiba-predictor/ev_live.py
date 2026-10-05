# -*- coding: utf-8 -*-
"""
ev_live.py — 回収率エンジンを、これから走るレースに当てる（前向き台帳つき・2026-10-02新規）
===========================================================================================
2019〜2026年の年ごとの前向き検証（combo_backtest.py）で、**馬連・ワイドを「モデル確率／市場確率 ≧ 1.3」の組だけ買う**と
回収率が116〜117%（95%区間の下限102〜103%・馬連は8年すべて100%超）になった。これを未来のレースで確かめる。

流れ
  1. 履歴   : db/history_target（TARGET・〜2026-09-13）＋ JV-Link で直接読んだ最新の成績（C:/keiba_db/jv_raw）
  2. 出走表 : jv_raw の SE（区分1/2）＋ RA。オッズは netkeiba のスナップショット（odds_snapshot.py）の単勝
  3. モデル : 履歴の全レースで学習（正則化0.01）。ev_engine と同じ特徴量
  4. 候補   : 馬連・ワイドで 比≧1.30 かつ 市場確率が下限以上（馬連0.03・ワイド0.08）の組。実オッズが出ていれば 期待値＝確率×オッズ も記録
  5. 台帳   : db/ev_ledger.json に記録（実際には買わない）。精算は fetch_payouts.py → ev_live.py --settle

⚠ 検証は **確定オッズ** で作った市場確率を使っている。発売中のオッズで選ぶと市場確率がずれる。
   台帳には取得時刻を残す。締切に近いほど検証に近い条件になる（発走30分前以降を推奨）。
使い方
  python ev_live.py --date 20261003 [--register]        # 候補を出す（--register で台帳に記録）
  python ev_live.py --settle                            # 払戻（db/payouts.json）で精算
  python ev_live.py --report                            # 台帳の累計
"""
from __future__ import annotations
import argparse, collections, datetime, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import combo_backtest as C
import target_import as T
import odds_snapshot as O

BASE_DIR = Path.home() / "Desktop" / "競馬予想レポート"
DB = BASE_DIR / "daily_pdca" / "db"
HIST = DB / "history_target"
RAW = Path("C:/keiba_db/jv_raw/RACE")
LEDGER = DB / "ev_ledger.json"
MODEL = DB / "ev_model_live.json"
RULE = "E2.1"                      # 事前登録: 馬連・ワイド・馬単・比≧1.30・実オッズの期待値≧0.9（発売前は問わない）・型ごとの目標倍率（2026-10-05・調教入りエンジン）。変えたら版を上げる
EV_FLOOR = 0.9
RATIO = 1.30
MINQ = {"馬連": 0.03, "ワイド": 0.08, "馬単": 0.02}
TYPES = ("馬連", "ワイド", "馬単")
BUDGET = 10000                     # 1レースの仮想予算（台帳用・実際には買わない）
TARGET = {"堅い": 2.5, "普通": 4.0, "荒れ": 8.0}


def jv_results_and_entries(date: str):
    """jv_raw から (最新の成績行, 当日の出走表行)。成績は TARGET の最終日より後だけ"""
    ras, ses_res, ses_ent = {}, {}, {}
    for f in sorted(list(RAW.glob("RA_*.txt")) + list((RAW.parent / "RT").glob("RA_*.txt")) + list((RAW.parent / "RT" / "entry").glob("RA_*.txt"))):
        b = f.read_bytes()
        for i in range(0, len(b) - 1271, 1272):
            x = T.parse_ra(b[i:i + 1272])
            if x and x["R"]:
                k = (x["date"], x["venue"], x["R"])
                if k not in ras or x["made"] >= ras[k]["made"]:
                    ras[k] = x
    for f in sorted(list(RAW.glob("SE_*.txt")) + list((RAW.parent / "RT").glob("SE_*.txt")) + list((RAW.parent / "RT" / "entry").glob("SE_*.txt"))):
        b = f.read_bytes()
        for i in range(0, len(b) - 554, 555):
            r = b[i:i + 555]
            x = T.parse_se(r)
            if x and x["R"] and x["uma"]:
                k = (x["date"], x["venue"], x["R"], x["uma"])
                if k not in ses_res or x["made"] >= ses_res[k]["made"]:
                    ses_res[k] = x
            if T.seg(r, 12, 4) + T.seg(r, 16, 4) == date:
                e = T.parse_se(r, entry=True)
                if e and e["R"] and e["uma"]:
                    k = (e["date"], e["venue"], e["R"], e["uma"])
                    if k not in ses_ent or (e["flag"], e["made"]) >= (ses_ent[k]["flag"], ses_ent[k]["made"]):
                        ses_ent[k] = e
    last = max((p.stem for p in HIST.glob("results_*.json")), default="results_2016")
    res_rows = T.build_rows(ras, ses_res)
    ent_rows = T.build_rows(ras, ses_ent, entry=True)
    wh = load_wh(date)
    for r in ent_rows:                                     # 当日発表の馬体重（JV速報 0B11）を出走表に入れる
        w = wh.get((r["競馬場"], r["R"], r["馬番"]))
        if w:
            r["馬体重"] = w
    return res_rows, ent_rows


def load_wh(date: str):
    """jv_rt.ps1 -Spec 0B11 -OutDir RT/wh の WH レコード → {(場, R, 馬番): "484(+4)"}。体重未発表・増減不明は除く"""
    f = RAW.parent / "RT" / "wh" / f"WH_{date}.txt"
    out = {}
    if not f.exists():
        return out
    for r in f.read_bytes().split(b"\r\n"):
        if len(r) < 80 or r[:2] != b"WH":
            continue
        venue = T.VENUE.get(r[19:21].decode("ascii", "ignore"))
        R = int(r[25:27] or 0)
        for i in range(18):
            e = r[35 + i * 45:35 + (i + 1) * 45]
            if len(e) < 45:
                break
            uma, wt, sg, df = e[:2].decode("ascii", "ignore"), e[38:41].decode("ascii", "ignore"), e[41:42].decode("ascii", "ignore"), e[42:45].decode("ascii", "ignore")
            if uma.strip().isdigit() and wt.strip().isdigit() and df.strip().isdigit() and df.strip() != "999":
                out[(venue, R, int(uma))] = f"{int(wt)}({'-' if sg == '-' else '+'}{int(df)})"
    return out


def snapshot_odds(date: str):
    """{(場, R): ({馬番: 単勝オッズ}, {馬名}, snapshot dict)}"""
    out = {}
    for rid, path in O.latest_snapshots(date).items():
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        tan = {}
        for k, v in d["odds"].get("単勝", {}).items():
            try:
                tan[int(k)] = float(v[0])
            except (TypeError, ValueError, IndexError):
                pass
        names = {h["umaban"]: h["horse_name"] for h in d["horses"].values()}
        out[(d["venue"], int(d["R"]))] = (tan, names, d)
    return out


def train_all():
    """履歴の全レースで学習。結果は日付つきで保存し、同じ履歴なら使い回す"""
    E.SOURCE = HIST
    hist_rows = E.load_rows()
    last = max(r["date"] for r in hist_rows)
    res_rows, _ = jv_results_and_entries("00000000")
    extra = [r for r in res_rows if r["date"] > last]
    return hist_rows, extra, last


def run(date: str, register: bool, only=None):
    hist_rows, extra, last = train_all()
    res_rows, ent_rows = jv_results_and_entries(date)
    extra = [r for r in res_rows if r["date"] > last]
    print(f"■ 履歴 {len({(r['date'], r['競馬場'], r['R']) for r in hist_rows}):,}レース（〜{last}）＋ JV-Link の最新成績 {len({(r['date'], r['競馬場'], r['R']) for r in extra}):,}レース")
    snap = snapshot_odds(date)
    live = []
    skipped = []
    for r in ent_rows:
        if r["date"] != date:
            continue
        tan, names, d = snap.get((r["競馬場"], r["R"]), ({}, {}, None))
        o = tan.get(r["馬番"])
        if not o or o >= 900 or names.get(r["馬番"], "").replace(" ", "") != r["馬名"].replace(" ", ""):
            skipped.append((r["競馬場"], r["R"], r["馬番"], r["馬名"]))
            continue
        r = dict(r, 単勝オッズ=o, _live=True)
        live.append(r)
    if skipped:
        print(f"  オッズが無い／馬名が合わない馬 {len(skipped)}頭（取消・除外の可能性）を除外")
    E.SOURCE = HIST

    # build は SOURCE の履歴＋extra＋live を時系列に処理する
    orig = E.load_rows
    E.load_rows = lambda: orig() + extra
    races, _ = E.build(extra_rows=live)
    E.load_rows = orig
    train = [r for r in races if r["part"] != "live"]
    liv = [r for r in races if r["part"] == "live"]
    print(f"  学習 {len(train):,}レース ／ 当日 {len(liv)}レース")
    beta, w = E.fit(E.pack(train), 0.01)

    cands = []
    race_out = {}
    for r in liv:
        p = E.probs(r, beta, w)
        q = r["q"]
        uma = r["uma"]
        _tan, _names, _d = snap[(r["key"][1], r["key"][2])]
        race_out[f"{r['key'][1]}{r['key'][2]}"] = dict(
            venue=r["key"][1], R=r["key"][2], title=(_d.get("title") or "")[:30], race_id=_d["race_id"], n=len(uma),
            horses=[dict(uma=int(u), name=_names[u], odds=_tan[u], p_model=round(float(pi), 4), p_market=round(float(qi), 4),
                         pop=1 + sum(1 for x in uma if _tan[x] < _tan[u])) for u, pi, qi in zip(uma, p, q)])
        cm, cq = C.combos(p, uma), C.combos(q, uma)
        key = (r["key"][1], r["key"][2])
        tan, names, d = snap[key]
        for t in TYPES:
            tab = d["odds"].get(t) or {}
            for c in cm[t]:
                if cq[t][c] < MINQ[t]:
                    continue
                ratio = cm[t][c] / cq[t][c]
                if ratio < RATIO:
                    continue
                k = "".join(f"{x:02d}" for x in c)
                v = tab.get(k)
                odds = float(v[0]) if v and v[0] not in (None, "") else None
                cands.append(dict(race_id=d["race_id"], venue=key[0], R=key[1], title=(d.get("title") or "")[:24], type=t, combo=list(c),
                                  names=[names[x] for x in c], p_model=round(cm[t][c], 5), p_market=round(cq[t][c], 5), ratio=round(ratio, 3),
                                  odds_now=odds, ev_now=round(cm[t][c] * odds, 3) if odds else None, snap_at=d.get("fetched_at")))
    cands = [c for c in cands if c["ev_now"] is None or c["ev_now"] >= EV_FLOOR]     # E2.1: 実オッズで期待値0.9未満は外す
    # 型ごとの目標倍率で配分（実オッズがあれば実オッズ、なければ 払戻率÷市場確率）
    import bet_engine as BE
    by_race = collections.defaultdict(list)
    for c in cands:
        by_race[(c["venue"], c["R"])].append(c)
    kinds = {(r["key"][1], r["key"][2]): BE.race_kind(r["q"]) for r in liv}
    final = []
    for rk, cs in by_race.items():
        T = TARGET[kinds[rk]]
        cs = sorted(cs, key=lambda c: -c["ratio"])
        for c in cs:
            c["use_odds"] = c["odds_now"] or (BE.TAKE[c["type"]] / c["p_market"])
        chosen, S = [], 0.0
        for c in cs:
            if chosen and S + 1.0 / c["use_odds"] > 1.0 / T * 1.15:
                continue
            chosen.append(c); S += 1.0 / c["use_odds"]
            if S >= 1.0 / T or len(chosen) >= 12:
                break
        w = np.array([1.0 / c["use_odds"] for c in chosen])
        amt = np.minimum(np.floor(BUDGET * w / w.sum() / 100.0) * 100.0, BUDGET * 0.30)      # 1点は予算の30%まで
        for c, a in zip(chosen, amt):
            if a >= 100:
                c["stake"], c["kind"] = int(a), kinds[rk]
                final.append(c)
    cands = final
    cands.sort(key=lambda x: (x["venue"], x["R"], x["type"], -x["ratio"]))
    print(f"\n■ {date} 候補（{RULE}: {'・'.join(TYPES)}で 比≧{RATIO}）  {len(cands)}点 / {len({(c['venue'], c['R']) for c in cands})}レース")
    for c in cands:
        print(f"  {c['venue']}{c['R']:>2}R {c['type']:<4} {'-'.join(map(str, c['combo'])):<7} {'・'.join(n[:5] for n in c['names']):<20} 比{c['ratio']:.2f}"
              f"  確率{c['p_model']*100:5.1f}%（市場{c['p_market']*100:5.1f}%）  オッズ{c['odds_now'] if c['odds_now'] else '未発売':>6}  期待値{c['ev_now'] if c['ev_now'] else '-'}  {c['kind']}・{c['stake']:,}円")
    for c in cands:
        race_out[f"{c['venue']}{c['R']}"].setdefault("bets", []).append({k: c[k] for k in ("type", "combo", "names", "ratio", "p_model", "p_market", "odds_now", "ev_now", "stake", "kind")})
    for ro in race_out.values():
        ro.setdefault("bets", [])
        ro["kind"] = BE.race_kind(np.array([h["p_market"] for h in ro["horses"]]))
    out = Path(DB / "ev_live"); out.mkdir(exist_ok=True)
    (BASE_DIR / date / "research").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / date / "research" / f"ev_live_{date}.json").write_text(json.dumps(dict(date=date, rule=RULE, made_at=datetime.datetime.now().isoformat(timespec="minutes"), races=race_out), ensure_ascii=False, indent=1), encoding="utf-8")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    (out / f"{date}_{stamp}.json").write_text(json.dumps(dict(date=date, rule=RULE, made_at=stamp, n_train=len(train), cands=cands), ensure_ascii=False, indent=1), encoding="utf-8")
    if register:
        led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
        have = {(x["race_id"], x["type"], tuple(x["combo"])) for x in led}
        done_races = {x["race_id"] for x in led}
        n = 0
        for c in cands:
            if (c["race_id"], c["type"], tuple(c["combo"])) in have:
                continue
            if only is not None and (f"{c['venue']}{c['R']}" not in only or c["race_id"] in done_races):
                continue                                   # 自動運転: 発走前の指定レースだけ・1レース1回
            led.append(dict(c, rule=RULE, date=date, registered_at=datetime.datetime.now().isoformat(timespec="minutes"), settled=False, payout=None))
            n += 1
        LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n台帳に {n} 点を追加（累計 {len(led)} 点）→ {LEDGER}")


def settle():
    """払戻は JV速報の HR（RT/HR_日付.txt。jv_rt.ps1 -Spec 0B12 で取得）で精算する（2026-10-05 netkeiba から切り替え）"""
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    pays = {}
    for d in {x["date"] for x in led if not x["settled"]}:
        f = RAW.parent / "RT" / f"HR_{d}.txt"
        if f.exists():
            b = f.read_bytes()
            for i in range(0, len(b) - 718, 719):
                h = T.parse_hr(b[i:i + 719])
                if h:
                    pays[(d, h["venue"], h["R"])] = h["pay"]
    n = 0
    for x in led:
        if x["settled"]:
            continue
        p = pays.get((x["date"], x["venue"], x["R"]))
        if not p:
            continue
        key = tuple(x["combo"]) if x["type"] in ("馬単", "3連単") else tuple(sorted(x["combo"]))
        x["payout"], x["settled"] = p.get(x["type"], {}).get(key, 0) * x["stake"] / 100.0, True
        n += 1
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"精算 {n}点")


def report():
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    done = [x for x in led if x["settled"]]
    print(f"■ {RULE} 前向き台帳  登録 {len(led)}点 / 精算済み {len(done)}点")

    def line(label, v):
        if not v:
            return
        st, rt = float(sum(x["stake"] for x in v)), float(sum(x["payout"] for x in v))
        races = collections.defaultdict(lambda: [0.0, 0.0])
        for x in v:
            races[x["race_id"]][0] += x["stake"]; races[x["race_id"]][1] += x["payout"]
        lo, hi = C.ci([a for a, b in races.values()], [b for a, b in races.values()])
        print(f"  {label:<10} {len(races):>4}レース {len(v):>4}点  賭け{int(st):>8,}円  回収率 {rt/st*100:6.1f}% ［{lo*100:.0f}〜{hi*100:.0f}%］ 的中点 {sum(1 for x in v if x['payout'])}")
    line("全体", done)
    for t in TYPES:
        line(t, [x for x in done if x["type"] == t])
    for k in ("堅い", "普通", "荒れ"):
        line(k, [x for x in done if x.get("kind") == k])
    print("  採用: 300レース以上で、レース単位の95%区間の下限が100%超（事前登録）。それまで実際には買わない")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--races", default="", help="登録するレース（例: 東京11,京都11）。指定すると、まだ台帳にないレースだけを1回登録")
    ap.add_argument("--settle", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.settle:
        settle()
    elif a.report:
        report()
    elif a.date:
        run(a.date, a.register, set(a.races.split(",")) if a.races else None)
    else:
        ap.print_help()
