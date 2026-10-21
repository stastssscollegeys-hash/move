# -*- coding: utf-8 -*-
"""
predict_day.py — 1日ぶんの予想カード（平場も重賞も同じ手順）を作る（2026-10-03新規・標準手順）
===========================================================================================
ユーザー指示（2026-10-03）: レースを予想するときは、
  ① 馬のデータ（過去10年分）を遡って分析する
  ② そのレースの傾向（競馬場・距離・どんな馬が走るか・脚質・年齢・性別・斤量・前走からの流れ）をつかむ
  ③ 馬とレースの特徴を合わせて予想し、印と買い目を期待値で決める
  平場も重賞も同じ手順で行う。
実装
  ① 履歴   : TARGET＋JV-Link の10年ぶん（db/history_target ＋ jv_raw の最新成績）から、出走馬ごとに 通算・直近5走・同コース実績・父の成績
  ② 傾向   : 同じコース（競馬場×芝ダ×距離）の10年ぶんを、人気から外した比（3着内の実測÷期待）で 脚質・枠・年齢・性別・斤量
             重賞は同じレース名の過去10回（race_profile）、平場は同条件（コース×クラス）の10年
  ③ 予想   : ev_live.py の確率（ev_engine＝市場確率＋①②を特徴量にした条件付きロジット）。印は確率の順、買い目は ev_live のE2.0
             候補が無いレースは「見送り」。SNS用に 参考買い目（比≧1.15）も別枠で出す
出力: {日付}/research/cards_{日付}.json ／ {日付}/{日付}_予想カード_エンジン版.docx ／ 重賞は X・Threads の下書き
使い方: python ev_live.py --date 20261004   # 先に確率を作る（発走30分前以降に回し直す）
        python predict_day.py --date 20261004
"""
from __future__ import annotations
import argparse, collections, datetime, json, math, re, statistics, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import ev_live as L
import bet_engine as B
import combo_backtest as C

BASE = Path.home() / "Desktop" / "競馬予想レポート"
HIST = BASE / "daily_pdca" / "db" / "history_target"
import os as _os
if _os.environ.get("REPLAY"):                      # 再生テストの出力は _replay/ に分ける（本番の日付フォルダを上書きしない）
    BASE = BASE / "_replay"
BAN = ["netkeiba", "SPAIA", "うましる", "競馬ラボ", "重賞ナビ", "PDCA", "EV", "インフルエンサー", "両関門", "Harville", "lift", "合算"]
MARKS = ["◎", "○", "▲", "△", "△"]


def norm(name):
    return re.sub(r"第\d+回|\(.*?\)|（.*?）|\s", "", str(name or ""))


def band(m):
    return "短距離" if m <= 1300 else "マイル" if m <= 1600 else "中距離" if m <= 2200 else "長距離"


def load_rows():
    E.SOURCE = HIST
    rows = E.load_rows()
    if L.REPLAY:
        rows = [r for r in rows if r["date"] < L.REPLAY]
    last = max(r["date"] for r in rows)
    res, _ = L.jv_results_and_entries("00000000")
    return rows + [r for r in res if r["date"] > last]


class Tends:
    """人気を除いた比（3着内の実測÷期待）を、条件ごとに引く"""

    def __init__(self, rows):
        pr = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            if r.get("着順int") and r.get("人気"):
                p = min(int(r["人気"]), 14)
                pr[p][0] += 1; pr[p][1] += r["着順int"] <= 3
        self.exp = {p: v[1] / v[0] for p, v in pr.items()}
        self.rows = [r for r in rows if r.get("着順int") and r.get("人気")]
        self.by_course = collections.defaultdict(list)
        self.by_band = collections.defaultdict(list)
        for r in self.rows:
            d = r["距離"]
            self.by_course[(r["競馬場"], d)].append(r)
            self.by_band[(d[:1], band(int("".join(c for c in d if c.isdigit()))))].append(r)
        self.cache = {}

    def ratio(self, sub, keyf, key):
        hit = exp = n = 0
        var = 0.0
        for r in sub:
            if keyf(r) == key:
                e = self.exp[min(int(r["人気"]), 14)]
                n += 1; hit += r["着順int"] <= 3; exp += e; var += e * (1 - e)
        if n == 0 or exp == 0:
            return None
        return dict(n=n, ratio=hit / exp, z=(hit - exp) / math.sqrt(var) if var > 0 else 0.0)


def style_of_row(r):
    return r.get("脚質") or "?"


# 元データの「脚質」の「逃げ」は最初のコーナー2番手以内（1番手だけではない）。文章ではこの言い方にする（2026-10-19）
STYLE_WORD = {"逃げ": "最初のコーナーで2番手以内", "先行": "先行", "差し": "差し", "追込": "追込"}


def waku_of_row(r):
    w = r.get("枠")
    return "?" if not w else "内" if w <= 3 else "中" if w <= 5 else "外"


def age_of_row(r):
    sa = str(r.get("性齢") or "")
    return sa[1:] if len(sa) > 1 else "?"


def marks_and_bets(horses, ro, venue):
    """印・注意馬・公開の買い目（標準形V1＋妙味の馬連）。朝の通常実行と、オッズだけ入れ替える軽い更新の両方で使う"""
    # 印（2026-10-07 価値順に変更・mark_scheme_test.py）: 人気どおりの確率順より、モデル÷市場（＝人気に対する割安さ）の順が
    #   10年の全券種で良かった（◎単勝 81.5→91.4%、◎-○馬連 82.7→97.6%、8年すべてで改善）。ただし勝つ確率の下限を置く
    #   ◎: 勝つ確率8%以上で最も割安 ／ ○▲: 5%以上で割安な順 ／ △: 3%以上で割安な順（後ろから型×20倍以上は除く）
    #   🔥: 6番人気以下・2%以上で最も割安（後ろから型×20倍以上は除く）
    def long_closer(hh):
        return hh.get("style") == "後ろから" and (hh.get("odds") or 0) >= 20
    val = sorted(horses, key=lambda hh: -hh["ratio"])
    marks = {}
    hon = [hh for hh in val if hh["p_model"] >= 0.08] or horses[:1]
    marks[hon[0]["uma"]] = "◎"
    for mk, floor in (("○", 0.05), ("▲", 0.05), ("△", 0.03), ("△", 0.03)):
        c = [hh for hh in val if hh["uma"] not in marks and hh["p_model"] >= floor and not (mk == "△" and long_closer(hh))]
        if not c:
            c = [hh for hh in horses if hh["uma"] not in marks]
        if c:
            marks[c[0]["uma"]] = mk
    ana = [hh for hh in val if hh["uma"] not in marks and hh["pop"] >= 6 and hh["p_model"] >= 0.02 and not long_closer(hh)]
    if ana:
        marks[ana[0]["uma"]] = "🔥"
    caution = [hh["uma"] for hh in horses if hh["pop"] <= 3 and hh["ratio"] <= 0.85 and hh["uma"] not in marks]
    # 買い目: 公開用は標準形 V1.1（2026-10-10〜。下に説明）。台帳のE2.1は別に記録（bets）
    #   単勝◎2,000 ／ 馬連◎-○3,000 ／ ワイド◎-🔥3,000 ／ 3連複◎○🔥1,000 ／ 3連複◎○▲1,000（🔥がいなければ ワイド◎-▲・3連複◎○▲2,000）
    bets = ro["bets"]
    # 2026-10-10 標準形 V1.1（bet_structure_test.py・2019〜2026/9 の24,927R・実際の払戻）: 3連複2点をやめ、ワイド◎流し（相手5頭×1,000）に。
    #   回収率は同じ（V1 93.0% → 92.9%・区間の幅は狭く）で、何か当たる 31.9→48.1%、「印は当たったのに馬券は外れ」62.5→41.7%。
    #   ユーザー指摘「印は当たっているのに馬券が当たらない」「中穴に印が集まったレースで3連複1点1,000円は重い」への対応。旧V1は下の V1_PLAN に残す
    um = {}
    for k, v in marks.items():
        um.setdefault(v, []).append(int(k))
    h_ = (um.get("◎") or [None])[0]
    o_ = (um.get("○") or [None])[0]
    aite = [x for lab in ("○", "▲", "🔥", "△") for x in um.get(lab, [])]   # 上限超えで削るのは後ろ（△）から
    plan = [("単勝", [h_], 2000), ("馬連", [h_, o_], 3000)] + [("ワイド", [h_, x], 1000) for x in aite]
    # V1_PLAN（〜2026-10-10）: 単勝◎2,000 ／ 馬連◎-○3,000 ／ ワイド◎-🔥3,000 ／ 3連複◎○🔥1,000 ／ 3連複◎○▲1,000（🔥なし: ワイド◎-▲3,000・3連複◎○▲2,000）
    psort = sorted(horses, key=lambda x: x["uma"])
    pv = np.array([hh["p_model"] for hh in psort]); qv = np.array([hh["p_market"] for hh in psort])
    pv, qv = pv / pv.sum(), qv / qv.sum()
    ub = [hh["uma"] for hh in psort]
    tm, tq = B.tables(pv, ub), B.tables(qv, ub)
    snap = SNAP.get((venue, ro["R"]))
    ref = []
    for t, combo, amt in plan:
        if None in combo:
            continue
        k = tuple(combo) if t in ("単勝",) else tuple(sorted(combo))
        if t == "単勝":
            pm_ = next(hh["p_model"] for hh in horses if hh["uma"] == combo[0]); pq_ = next(hh["p_market"] for hh in horses if hh["uma"] == combo[0])
        else:
            keys, prob = tm[t]; pq_ = tq[t][1][keys.index(k)]; pm_ = prob[keys.index(k)]
        b = dict(type=t, combo=list(k), stake=amt, odds_est=round(B.TAKE.get(t, 0.8) / pq_, 1), p_model=round(float(pm_), 4))
        v = ((snap[2]["odds"].get(t) or {}) if snap else {}).get("".join(f"{x:02d}" for x in k))
        try:
            b["odds_now"] = float(v[0]) if v and v[0] not in (None, "") else None
        except (TypeError, ValueError):
            b["odds_now"] = None
        ref.append(b)
    # 妙味の馬連（2026-10-07・umaren_real_test.py）: 市場との比≧1.3 の馬連。3年の実オッズで117.3%［101.8〜133.0］、年別100%以上。
    #   出たレースだけ「勝負レース」。1点1,000円・最大2点（標準形V1とは別枠で足す）
    km, prm = tm["馬連"]; prq = tq["馬連"][1]
    value_q = sorted(((float(x / y), k) for k, x, y in zip(km, prm, prq) if y >= 0.03 and x / y >= 1.3), reverse=True)[:2]
    for r_, k in value_q:
        b = dict(type="馬連", combo=list(k), stake=1000, odds_est=round(B.TAKE["馬連"] / prq[km.index(k)], 1), p_model=round(float(prm[km.index(k)]), 4), value=True, ratio=round(r_, 2))
        v = ((snap[2]["odds"].get("馬連") or {}) if snap else {}).get("".join(f"{x:02d}" for x in k))
        try:
            b["odds_now"] = float(v[0]) if v and v[0] not in (None, "") else None
        except (TypeError, ValueError):
            b["odds_now"] = None
        ref.append(b)
    over = sum(b["stake"] for b in ref) - 10000         # 1レース上限1万円: 妙味の馬連の分は ワイド（印の軽い相手から）を減らして空ける
    for b in [x for x in ref if x["type"] in ("3連複", "ワイド") and not x.get("value")][::-1]:
        if over <= 0:
            break
        cut = min(over, b["stake"])
        b["stake"] -= cut
        over -= cut
    ref = [b for b in ref if b["stake"] >= 100]
    return marks, caution, bets, ref, value_q


BABA_CODE = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}


def going_now(date, venue, sf):
    """JV の天候馬場状態（WE。0B14 → RT/info/WE_{日付}.txt）から、その日・その場・芝ダの最新の馬場発表を返す（2026-10-08）
       前日発表（発表時刻00000000・前日作成）も入るので、金曜・土曜の夜の予想でも週の間の雨を反映できる。
       WE: WE 区分1 作成日8 日付8 場2 回2 日目2 発表8 変更識別1 天候1 芝1 ダ1 （変更前の3字）"""
    import jv_odds as J
    f = Path("C:/keiba_db/jv_raw/RT/info") / f"WE_{date}.txt"
    if not f.exists():
        return None
    best = None
    for ln in f.read_bytes().decode("ascii", "ignore").splitlines():
        if ln[:2] != "WE" or len(ln) < 37 or ln[11:19] != date or J.VENUE.get(ln[19:21]) != venue:
            continue
        code = ln[35] if sf == "芝" else ln[36]
        if code in BABA_CODE:
            k = (ln[3:11], ln[25:33])
            if best is None or k >= best[0]:
                best = (k, BABA_CODE[code])
    return best[1] if best else None


def week_bias_note(date, venue, dist, e):
    """先週の馬場の偏りが今週も続くか（2026-10-07 week_bias_test.py の10年の結果に基づく説明文）
       芝・同じ開催・同じ柵・馬場が同程度 → 先週の内外の偏りが続く（0.94↔1.06倍）／柵替え → リセット・内枠がやや有利（1.04倍）
       開催替わり・馬場の変化 → 先週の傾向は当てにしない／ダート → 先週の偏りは続かない"""
    import race_meta as RM
    d0 = datetime.date(int(date[:4]), int(date[4:6]), int(date[6:]))
    prev = []
    for k in range(5, 10):
        dd = (d0 - datetime.timedelta(days=k)).strftime("%Y%m%d")
        f = BASE / dd / "research" / f"day_review_{dd}.json"
        if f.exists():
            v = json.loads(f.read_text(encoding="utf-8"))["venues"].get(f"{venue}{dist[:1]}")
            if v:
                prev.append((dd, v))
    if not prev:
        return None
    if dist[:1] != "芝":
        return f"先週の{venue}ダート: 10年の検証ではダートの偏りは翌週に続かないので、今週は持ち越さない"
    M = getattr(week_bias_note, "_M", None) or RM.load()
    week_bias_note._M = M
    cur = M.get((date, venue, e["R"]))
    prv = [M.get((dd, venue, r)) for dd, _ in prev for r in range(1, 13)]
    prv = [x for x in prv if x]
    inn = [v["waku"].get("内") for _, v in prev if v.get("waku") and v["waku"].get("内")]
    n = sum(x["n"] for x in inn)
    ratio = sum(x["ratio"] * x["n"] for x in inn) / n if n else None
    babas = [b for _, v in prev for b, c in v.get("baba", {}).items() for _ in range(c)]
    bad_prev = sum(1 for b in babas if b != "良") / max(1, len(babas))
    now_baba = going_now(date, venue, "芝") or str(e.get("馬場状態") or "良")
    bad_now = float(now_baba != "良")
    pk = collections.Counter(x[0] for x in prv).most_common(1)[0][0] if prv else ""
    prl = collections.Counter(x[2] for x in prv if x[2]).most_common(1)[0][0] if any(x[2] for x in prv) else ""
    head = f"先週の{venue}芝（{'・'.join(dd[4:6] + '/' + dd[6:] for dd, _ in prev)}）"
    lean = None if ratio is None else ("内枠有利" if ratio >= 1.1 else "内枠不利" if ratio <= 0.9 else "内外の差は小さい")
    if cur and pk and cur[0] != pk:
        return f"{head}は{lean or '—'}。今週から開催替わりなので、先週の傾向は持ち越さない"
    if cur and prl and cur[2] and prl != cur[2]:
        return f"{head}は{lean or '—'}。今週は柵替え（{prl}→{cur[2]}コース）で偏りはリセット。替わった週は内枠がやや有利（10年で1.04倍）"
    if abs(bad_now - bad_prev) >= 0.5:
        return f"{head}は{lean or '—'}。週の間に馬場が{'悪化' if bad_now > bad_prev else '回復'}した（今週の発表は{now_baba}）ので、先週の傾向は当てにしない"
    if lean in ("内枠有利", "内枠不利"):
        return f"{head}は{lean}（人気から期待される3着内の{ratio:.2f}倍）。同じ開催・同じ柵・馬場も同程度なので、今週も続きやすい（10年で{'1.06' if lean == '内枠有利' else '0.94'}倍）"
    return f"{head}は内外の差が小さい。同じ柵・同じ馬場状態なので、大きな偏りは想定しない"


def save_cards(date, cards):
    out = BASE / date / "research" / f"cards_{date}.json"
    if not cards:                                   # 発走前のレースが無い（終わった日など）なら、前の版を上書きしない
        print("■ 予想できるレースがありません（既存のカードは残します）")
        raise SystemExit(0)
    body = json.dumps(dict(date=date, made_at=datetime.datetime.now().isoformat(timespec="minutes"), rule=L.RULE, cards=cards), ensure_ascii=False, indent=1)
    out.write_text(body, encoding="utf-8")
    ver = BASE / date / "research" / "cards_versions"                # 版を残す（振り返りで「レース前の最後の版」を使う。2026-10-05）
    ver.mkdir(exist_ok=True)
    (ver / f"cards_{date}_{datetime.datetime.now():%H%M}.json").write_text(body, encoding="utf-8")
    return cards


def quick_update(date):
    """オッズだけ入れ替える軽い更新: 朝の予想カードを読み、ev_live（--quick）の新しい確率・オッズで印と買い目を作り直す"""
    global SNAP
    cf = BASE / date / "research" / f"cards_{date}.json"
    ef = BASE / date / "research" / f"ev_live_{date}.json"
    if not cf.exists() or not ef.exists():
        print("■ 朝の予想カードか ev_live の結果が無いので、通常の作成を行います")
        return build_cards(date)
    SNAP = L.snapshot_odds(date)
    cards = json.loads(cf.read_text(encoding="utf-8"))["cards"]
    ev = json.loads(ef.read_text(encoding="utf-8"))["races"]
    out = []
    for c in cards:
        ro = ev.get(f"{c['venue']}{c['R']}")
        if not ro:
            continue                                    # 発走済み・取消などで今回の計算に無いレースは載せない
        new = {h["uma"]: h for h in ro["horses"]}
        hs = []
        for h in c["horses"]:
            n_ = new.get(h["uma"])
            if not n_:
                continue                                # 出走取消
            h = dict(h, p_model=n_["p_model"], p_market=n_["p_market"], odds=n_["odds"], pop=n_["pop"], ratio=round(n_["p_model"] / n_["p_market"], 2))
            hs.append(h)
        hs.sort(key=lambda h: -h["p_model"])
        for i, h in enumerate(hs, 1):
            h["rank"] = i
        ro2 = dict(ro, bets=ro.get("bets", []), kind=ro.get("kind", c["kind"]))
        marks, caution, bets, ref, value_q = marks_and_bets(hs, ro2, c["venue"])
        out.append(dict(c, horses=hs, n=len(hs), kind=ro2["kind"], shobu=bool(value_q), marks={str(k): v for k, v in marks.items()}, caution=caution, bets=bets, ref_bets=ref))
    print(f"■ 軽い更新: {len(out)}レース（朝のカード {len(cards)}レース）")
    return save_cards(date, out)


def build_cards(date: str):
    ev = json.loads((BASE / date / "research" / f"ev_live_{date}.json").read_text(encoding="utf-8"))
    rows = load_rows()
    T = Tends(rows)
    res, ent = L.jv_results_and_entries(date)
    global SNAP
    SNAP = L.snapshot_odds(date)
    import chokyo as CKM, bisect
    CK = CKM.load()
    d14 = (datetime.date(int(date[:4]), int(date[4:6]), int(date[6:])) - datetime.timedelta(days=14)).strftime("%Y%m%d")

    def chokyo_note(hid):
        """直近14日でいちばん速かった調教（その日・そのトレセンの中央値との差）"""
        v = CK.get(str(hid or ""))
        if not v:
            return None, None
        ds = [x[0] for x in v]
        w = [x for x in v[bisect.bisect_left(ds, d14):bisect.bisect_left(ds, date)] if x[4] is not None]
        if not w:
            return None, None
        b = min(w, key=lambda x: x[4])
        km = "坂路4F" if b[1] == "坂路" else b[1].replace("ウッド", "ウッド")
        txt = f"{b[0][4:6]}/{b[0][6:]} {km} {b[2]:.1f}秒" + (f"・終い{b[3]:.1f}" if b[3] else "") + f"（その日の中央値より{abs(b[4]):.1f}秒{'速い' if b[4] < 0 else '遅い'}）"
        return txt, b[4]
    ent = [r for r in ent if r["date"] == date]
    by_horse = collections.defaultdict(list)
    for r in rows:
        by_horse[r.get("horse_id") or r["馬名"]].append(r)
    for v in by_horse.values():
        v.sort(key=lambda r: (r["date"], r["R"]))
    cards = []
    for key, ro in sorted(ev["races"].items(), key=lambda kv: (kv[1]["venue"], kv[1]["R"])):
        es = {r["馬番"]: r for r in ent if r["競馬場"] == ro["venue"] and r["R"] == ro["R"]}
        if not es:
            continue
        any_e = next(iter(es.values()))
        dist, venue = any_e["距離"], ro["venue"]
        m = int("".join(c for c in dist if c.isdigit()))
        graded = bool(re.search(r"G[123]|\(L\)", any_e.get("条件", "")))
        name = any_e.get("レース名") or ro["title"]
        # ② 傾向
        course_rows = T.by_course.get((venue, dist), [])
        lines = []
        for label, keyf, keys in (("脚質", style_of_row, ("逃げ", "先行", "差し", "追込")), ("枠", waku_of_row, ("内", "中", "外"))):
            for k in keys:
                x = T.ratio(course_rows, keyf, k)
                if x and x["n"] >= 400 and abs(x["z"]) >= 2.5:
                    lines.append((abs(x["z"]), f"{venue}{dist}では{label}「{STYLE_WORD.get(k, k)}」の馬は、人気から期待される3着内の{x['ratio']:.2f}倍（{x['n']:,}頭）"))
        bd = T.by_band.get((dist[:1], band(m)), [])
        for k in ("3", "4", "5", "6", "7"):
            x = T.ratio(bd, age_of_row, k if k != "7" else "7")
            if x and x["n"] >= 1500 and abs(x["z"]) >= 3.0:
                lines.append((abs(x["z"]), f"{dist[:1]}{band(m)}では{k}歳{'以上' if k == '7' else ''}は人気から期待される3着内の{x['ratio']:.2f}倍"))
        prof = None
        if graded:
            pf = BASE / date / "research" / f"race_profile_{norm(name)}.json"
            if not pf.exists():
                import subprocess
                subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "race_profile.py"), norm(name), "--dir", date], capture_output=True)
            if pf.exists():
                prof = json.loads(pf.read_text(encoding="utf-8"))
                p1 = prof["pop"].get("1")
                if p1:
                    lines.append((9, f"このレースの過去{len(prof['editions'])}回: 1番人気は{p1['n']}回中{p1['win']}勝・3着内{p1['top3']}回（{prof.get('kind', '')}）"))
        # 前日の馬場の特徴（day_review.py の出力）
        rv = sorted(BASE.glob("2*/research/day_review_*.json"))
        rv = [f for f in rv if f.stem[-8:] <= date]
        for f in rv[-2:]:
            dr = json.loads(f.read_text(encoding="utf-8"))
            vv = dr["venues"].get(f"{venue}{dist[:1]}")
            if vv:
                bits = []
                if vv.get("time_vs_normal") is not None:
                    tm = vv["time_vs_normal"]
                    bits.append("時計が出る馬場" if tm <= -0.4 else "時計がかかる馬場" if tm >= 0.4 else "時計は平均的")
                st = {k: x["ratio"] for k, x in vv["style"].items() if x}
                if st:
                    fr = (st.get("逃げ", 1) + st.get("先行", 1)) / 2
                    bk = (st.get("差し", 1) + st.get("追込", 1)) / 2
                    bits.append("前の馬が残りやすい" if fr - bk >= 0.5 else "差し・追い込みが届きやすい" if bk - fr >= 0.5 else "脚質の偏りは小さい")
                if vv.get("pace_vs_normal") is not None:
                    bits.append("流れは速め" if vv["pace_vs_normal"] >= 0.4 else "流れは遅め" if vv["pace_vs_normal"] <= -0.4 else "流れは平均的")
                gap = (datetime.date(int(date[:4]), int(date[4:6]), int(date[6:])) - datetime.date(int(dr["date"][:4]), int(dr["date"][4:6]), int(dr["date"][6:]))).days
                when = "今日ここまで" if gap == 0 else f"前日（{dr['date'][4:6]}/{dr['date'][6:]}）" if gap == 1 else f"{'先週' if gap <= 9 else ''}（{dr['date'][4:6]}/{dr['date'][6:]}）"   # 先週分を「前日」と書いていた（2026-10-10修正）
                lines.append((10.5 if dr["date"] == date else 10, f"{when}の{venue}{dist[:1]}（{vv['races']}レース）: " + "・".join(bits)))
        wb = week_bias_note(date, venue, dist, any_e)
        if wb:
            lines.append((11, wb))
        lines.sort(key=lambda x: -x[0])
        # ① 馬ごと
        hs = sorted(ro["horses"], key=lambda h: -h["p_model"])
        kin_avg = statistics.mean([e["斤量_kg"] for e in es.values() if e.get("斤量_kg")] or [55.0])
        horses = []
        for rank, h in enumerate(hs, 1):
            e = es.get(h["uma"])
            if not e:
                continue
            hist = [r for r in by_horse.get(e.get("horse_id") or e["馬名"], []) if r["date"] < date]
            last5 = hist[-5:][::-1]
            reasons = []
            lab = ""
            fr = [r for r in hist[-5:] if r.get("脚質")]
            if fr:
                share = sum(1 for r in fr if r["脚質"] in ("逃げ", "先行")) / len(fr)
                lab = "前で運ぶ" if share >= 0.6 else "後ろから" if share <= 0.2 else "中団"
                st = {"前で運ぶ": ("逃げ", "先行"), "後ろから": ("差し", "追込"), "中団": ("差し",)}[lab][0]
                x = T.ratio(course_rows, style_of_row, st)
                if x and x["n"] >= 400 and abs(x["ratio"] - 1) >= 0.08:
                    reasons.append((abs(x["ratio"] - 1), f"直近{len(fr)}走は「{lab}」型。{venue}{dist}では{STYLE_WORD[st]}の馬は{x['ratio']:.2f}倍"))
            wb = waku_of_row(e)
            x = T.ratio(course_rows, waku_of_row, wb) if wb != "?" else None
            if x and x["n"] >= 400 and abs(x["ratio"] - 1) >= 0.06:
                reasons.append((abs(x["ratio"] - 1) * 0.8, f"{e['枠']}枠（{wb}）はこのコースで{x['ratio']:.2f}倍"))
            kd = (e["斤量_kg"] or 0) - kin_avg
            if abs(kd) >= 1.5:
                reasons.append((0.1, f"斤量{e['斤量_kg']:g}kg（平均より{kd:+.1f}kg）"))
            same = [r for r in hist if r["競馬場"] == venue and r["距離"][:1] == dist[:1]]
            if len(same) >= 2:
                k3 = sum(1 for r in same if r["着順int"] and r["着順int"] <= 3)
                reasons.append((0.12 + k3 / len(same) * 0.1, f"{venue}の{dist[:1]}は{len(same)}戦{k3}回3着内"))
            sd = [r for r in hist if r["距離"][:1] == dist[:1] and abs(int("".join(c for c in r["距離"] if c.isdigit())) - m) <= 200]
            if len(sd) >= 2:
                k3 = sum(1 for r in sd if r["着順int"] and r["着順int"] <= 3)
                reasons.append((0.1 + k3 / len(sd) * 0.1, f"同じ距離帯（±200m）は{len(sd)}戦{k3}回3着内"))
            if last5:
                lp = last5[0]
                gap = (datetime.date(int(date[:4]), int(date[4:6]), int(date[6:])) - datetime.date(int(lp["date"][:4]), int(lp["date"][4:6]), int(lp["date"][6:]))).days
                dm = m - int("".join(c for c in lp["距離"] if c.isdigit()))
                note = f"前走{lp['レース名'][:12]}（{lp['着順']}着・{lp['人気']}番人気）から{gap}日"
                if lp["距離"][:1] != dist[:1]:
                    note += "・芝ダ変更"
                elif dm != 0:
                    note += f"・距離{dm:+d}m"
                reasons.append((0.15, note))
                if prof and lp["レース名"]:
                    rot = prof.get("rotation", {})
                    n_ = rot.get(norm(lp["レース名"]))
                    if n_:
                        reasons.append((0.5, f"前走の{norm(lp['レース名'])}は、このレースの過去3着内馬の前走で{n_}頭"))
            fa = e.get("父")
            if fa:
                sub = [r for r in T.rows if r.get("父") == fa and r["競馬場"] == venue and r["距離"][:1] == dist[:1]]
                if len(sub) >= 60:
                    ex = sum(T.exp[min(int(r["人気"]), 14)] for r in sub)
                    ob = sum(r["着順int"] <= 3 for r in sub)
                    if abs(ob / ex - 1) >= 0.12:
                        reasons.append((abs(ob / ex - 1) * 0.6, f"父{fa}は{venue}の{dist[:1]}で{ob / ex:.2f}倍（{len(sub)}頭）"))
            ck_txt, ck_diff = chokyo_note(e.get("horse_id"))
            if ck_txt and ck_diff is not None and ck_diff <= -1.5:
                reasons.append((0.3 + min(1.0, -ck_diff / 10), f"調教: {ck_txt}"))
            reasons.sort(key=lambda x: -x[0])
            extra = {"chokyo": ck_txt} if ck_txt else {}
            if graded:                                   # 重賞だけ: 騎手のこの競馬場・芝ダでの直近3年（人気をそろえた比）
                jr = [r for r in T.rows if r.get("騎手") == e["騎手"] and r["競馬場"] == venue and r["距離"][:1] == dist[:1] and r["date"] >= str(int(date[:4]) - 3) + date[4:]]
                if len(jr) >= 30:
                    ex = sum(T.exp[min(int(r["人気"]), 14)] for r in jr)
                    extra["jockey_course"] = f"{e['騎手']}騎手の{venue}{'芝' if dist[:1] == '芝' else 'ダート'}（直近3年{len(jr)}鞍）: 3着内{sum(r['着順int'] <= 3 for r in jr)}回＝人気から期待される数の{sum(r['着順int'] <= 3 for r in jr) / ex:.2f}倍"
            horses.append(dict(rank=rank, uma=h["uma"], name=h["name"], waku=e["枠"], sexage=e["性齢"], kin=e["斤量_kg"], jockey=e["騎手"], trainer=e["厩舎"],
                               p_model=h["p_model"], p_market=h["p_market"], ratio=round(h["p_model"] / h["p_market"], 2), odds=h["odds"], pop=h["pop"],
                               reasons=[r[1] for r in reasons[:3]], reasons_all=[r[1] for r in reasons], style=lab, sire=e.get("父") or "", weight=e.get("馬体重") or "", **extra,
                               last5=[f"{r['date'][4:6]}/{r['date'][6:]} {r['競馬場']}{r['距離']} {r['レース名'][:10]} {r['着順']}着/{r.get('頭数', '')}頭 {r['人気']}番人気 上がり{r.get('後3F') or '-'}" for r in last5],
                               career=f"{len(hist)}戦{sum(1 for r in hist if r['着順int'] == 1)}勝・3着内{sum(1 for r in hist if r['着順int'] and r['着順int'] <= 3)}回"))
        marks, caution, bets, ref, value_q = marks_and_bets(horses, ro, venue)
        cards.append(dict(key=key, venue=venue, R=ro["R"], name=name, grade=any_e.get("条件", ""), dist=dist, n=ro["n"], kind=ro["kind"], graded=graded, shobu=bool(value_q),
                          trends=[l[1] for l in lines[:6]], horses=horses, marks={str(k): v for k, v in marks.items()}, caution=caution, bets=bets, ref_bets=ref))
    return save_cards(date, cards)


def circ(n):
    return "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"[n - 1] if 1 <= n <= 18 else str(n)


def bet_lines(c):
    src = c["bets"] or c["ref_bets"]
    if not src:
        return ["見送り（期待値に見合う組み合わせがありません）"], False
    L_ = [f"💰 買い目 合計{len(src)}点・{sum(b['stake'] for b in src):,}円" + ("" if c["bets"] else "（参考）")]
    for b in src:
        od = b.get('odds_now') or b.get('odds_est')
        pm = b['p_model']
        ev = f"／的中{pm*100:.1f}%×{od:.1f}倍＝期待値{pm*od:.2f}" if od else ""
        L_.append(f"【{b['type']}】{'-'.join(circ(x) for x in b['combo'])} {b['stake']:,}円{ev}")
    tot = sum(b['stake'] * b['p_model'] * (b.get('odds_now') or b.get('odds_est') or 0) for b in src) / sum(b['stake'] for b in src)
    L_.append(f"全体の期待回収率（モデル確率×オッズ）: {tot*100:.0f}%（1.0＝100%を割ると買う根拠なし）")
    return L_, bool(c["bets"])


def sns_drafts(c, date):
    D = f"{date[:4]}年{int(date[4:6])}月{int(date[6:])}日（日）"
    head = f"🏇【{c['name']} G2】{D}\n━━ {c['venue']} {c['dist']} / {c['n']}頭 ━━"
    hs = {h["uma"]: h for h in c["horses"]}
    order = [h for h in c["horses"] if c["marks"].get(str(h["uma"]))]
    mk = [f"{c['marks'][str(h['uma'])]} {circ(h['uma'])}{h['name']}" for h in order]
    X = []
    X.append("\n".join([head, "", "ここ10年のデータと、今の馬の状態から出した予想印です。", "", "─────", "🎯 予想印", "─────"] + mk + ["", "根拠は1頭ずつスレッドで👇", "#競馬予想 #AI予想 #JRA"]))
    for h in order[:3]:
        body = [head, "", f"{c['marks'][str(h['uma'])]} {circ(h['uma'])}{h['name']}（{h['sexage']}・{h['kin']:g}kg・{h['jockey']}）", "",
                f"勝つ確率の見立ては{h['p_model']*100:.0f}%（人気が示す確率は{h['p_market']*100:.0f}%）", ""] + [f"・{x}" for x in h["reasons"]] + [f"・{h['career']}", "", "#競馬予想 #AI予想 #JRA"]
        X.append("\n".join(body))
    bl, is_e2 = bet_lines(c)
    X.append("\n".join([head, ""] + c["trends"][:4] and [head, "", "─────", "このレースの傾向", "─────"] + [f"・{x}" for x in c["trends"][:4]] + ["", "#競馬予想 #AI予想 #JRA"]))
    X.append("\n".join([head, ""] + bl + ["", "※発売前の予想オッズで組んでいます。当日朝に実際のオッズで組み直します。" if not is_e2 else "※前日の予想オッズでの買い目です。当日に組み直します。", "#競馬予想 #AI予想 #JRA"]))
    T_ = []
    T_.append("\n".join([head, "（1/3）予想印", ""] + mk + ["", "根拠は次の投稿から👇"]))
    top = order[0]
    T_.append("\n".join([head, f"（2/3）◎ {circ(top['uma'])}{top['name']}", ""] + [f"・{x}" for x in top["reasons"]] + [f"・{top['career']}"]))
    T_.append("\n".join([head, "（3/3）買い目", ""] + bl))
    return X, [t[:500] for t in T_]


def write_docx(cards, date):
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading(f"{date[:4]}年{int(date[4:6])}月{int(date[6:])}日 予想カード（エンジン版・平場も重賞も同じ手順）", 0)
    doc.add_paragraph("手順: ①馬の過去10年のデータ → ②レース（コース・距離）の傾向 → ③馬とレースを合わせた確率 → 印と買い目（期待値）。"
                      "確率は、人気（市場）を土台に、馬の過去走・コースの傾向・同じレースの過去10回を加えた統計モデルで出しています。")
    problems = []
    for c in cards:
        doc.add_heading(f"{c['venue']}{c['R']}R {c['name']}　{c['dist']} {c['n']}頭　（{c['kind']}型）", 1)
        doc.add_paragraph(c["grade"])
        doc.add_heading("このレース・コースの傾向（過去10年）", 3)
        for x in c["trends"] or ["特筆すべき傾向なし"]:
            doc.add_paragraph(f"・{x}")
        doc.add_heading("予想印", 3)
        tb = doc.add_table(rows=0, cols=8); tb.style = "Table Grid"
        for i, row in enumerate([["印", "馬", "馬名", "性齢・斤量・騎手", "勝つ確率", "人気の確率", "比", "決め手"]] +
                                [[c["marks"].get(str(h["uma"]), "注" if h["uma"] in c["caution"] else ""), f"{h['waku']}枠{circ(h['uma'])}", h["name"],
                                  f"{h['sexage']} {h['kin']:g}kg {h['jockey']}", f"{h['p_model']*100:.1f}%", f"{h['p_market']*100:.1f}%（{h['pop']}人気）", f"{h['ratio']:.2f}",
                                  " ／ ".join(h["reasons"][:2])] for h in c["horses"] if c["marks"].get(str(h["uma"])) or h["uma"] in c["caution"]]):
            cells = tb.add_row().cells
            for j, v in enumerate(row):
                cells[j].text = str(v)
        if c["caution"]:
            doc.add_paragraph("「注」: 人気は上位3番手以内だが、モデルの確率が人気より1.2割以上低い馬（買われ過ぎ）。")
        doc.add_heading("買い目", 3)
        bl, is_e2 = bet_lines(c)
        for x in bl:
            doc.add_paragraph(x)
        doc.add_heading("主な出走馬の過去（直近5走）", 3)
        for h in c["horses"][:6]:
            doc.add_paragraph(f"{circ(h['uma'])}{h['name']}　{h['career']}")
            for x in h["last5"]:
                doc.add_paragraph(f"　{x}")
        if c["graded"]:
            X, Tt = sns_drafts(c, date)
            doc.add_heading("X投稿案", 3)
            for i, x in enumerate(X, 1):
                doc.add_paragraph(f"【X{i}】{len(x)}字\n{x}")
                problems += [f"{c['name']} X{i}: 禁止語 {b}" for b in BAN if b in x]
            doc.add_heading("Threads投稿案（500字以内）", 3)
            for i, t in enumerate(Tt, 1):
                doc.add_paragraph(f"【Threads{i}】{len(t)}字\n{t}")
        doc.add_page_break()
    out = BASE / date / f"{date}_予想カード_エンジン版.docx"
    try:
        doc.save(out)
    except PermissionError:
        out = BASE / date / f"{date}_予想カード_エンジン版_new.docx"
        doc.save(out)
    return out, problems


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--quick", action="store_true", help="朝のカードを使い、オッズだけ入れ替えて印と買い目を作り直す（軽い）")
    a = ap.parse_args()
    cards = quick_update(a.date) if a.quick else build_cards(a.date)
    out, problems = write_docx(cards, a.date)
    print(f"■ {a.date} {len(cards)}レースのカード → {out}")
    for c in cards:
        mk = " ".join(f"{v}{circ(int(k))}" for k, v in sorted(c["marks"].items(), key=lambda kv: "◎○▲△🔥".index(kv[1]) if kv[1] in "◎○▲△🔥" else 9))
        print(f"  {c['venue']}{c['R']:>2}R {c['name'][:14]:<14} {mk}  買い目: {'E2 ' + str(len(c['bets'])) + '点' if c['bets'] else ('参考' + str(len(c['ref_bets'])) + '点' if c['ref_bets'] else '見送り')}")
    print("  禁止語検出:", problems or "なし")
