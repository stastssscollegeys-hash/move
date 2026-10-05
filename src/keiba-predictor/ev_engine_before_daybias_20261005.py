# -*- coding: utf-8 -*-
"""
ev_engine.py — 回収率を目的にした予想エンジン（2026-10-02新規・同日v2）
==================================================================
目的は的中率ではなく **長期の回収率が100%を超えること（当面の目標120%）**。
回収率＝Σ(的中確率×オッズ) なので、勝つには「市場のオッズが示す確率より正確な確率」が要る。
人気どおりに買えば的中率は上がるが、回収率は控除率（単勝80%）に固定される。

設計
  1. 確率モデル（条件付きロジット）
        その馬の強さ = β×ln(市場の確率) ＋ Σ 重み×特徴量　→ レース内でsoftmax
     市場の確率を土台に、市場が織り込み切れていない分だけを特徴量で動かす。
     特徴量はすべて **そのレースの日付より前に分かる情報** から作る（同日の他レースの結果も使わない）。
  2. データは時期で3つに分ける（混ぜない）
        学習 60% … 重みを決める
        調整 20% … 正則化の強さを決める
        判定 20% … 最後に1回だけ測る。ここの数字を見て作り直したら、その分だけ数字は信用できなくなる
     関門A: 判定区間で、市場だけの確率より対数尤度が良い（95%区間が0を超える）
     関門B: 判定区間で「モデルの確率×単勝オッズ ≧ 1.0」の馬だけ買った回収率の、95%区間の下限が100%超
     両方通ったときだけ active=True。通らないモデルで買っても回収率は控除率に戻るので **買わない**。
  3. 判定の後は前向き台帳で回収率を追う。的中率は判定に使わない。

データ: 既定は daily_pdca/db/history/（history_backfill.py が集めた年ごとのファイル）。無ければ蓄積DB。
使い方
  python ev_engine.py --fit [--source <フォルダ or JSON>]
  python ev_engine.py --report
"""
from __future__ import annotations
import argparse, collections, datetime, json, math, re, statistics, sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
MODEL = DB / "ev_model.json"
SOURCE = DB / "history" if any((DB / "history").glob("results_*.json")) else DB / "race_results.json"
SPLIT = (0.60, 0.80)      # 学習の終わり／調整の終わり（日付の割合）
K_ENT = 50.0              # 騎手・厩舎の累積を0へ寄せる強さ（出走数の単位）
K_HORSE = 5.0
TARGET_ROI = 1.20


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "").strip()
    return int(s) if s.isdigit() else None


def meters(d):
    n = "".join(c for c in str(d or "") if c.isdigit())
    return int(n) if n else None


def surf(d):
    return "芝" if str(d or "").startswith("芝") else "ダ"


def sec(t):
    s = str(t or "")
    try:
        if ":" in s:
            m, r = s.split(":", 1)
            return int(m) * 60 + float(r)
        return float(s)
    except ValueError:
        return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _day(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def race_class(r):
    """クラスを0〜7の段階にする（新馬0 未勝利1 1勝2 2勝3 3勝4 OP/L 5 G3 6 G2 6.5 G1 7）。分からなければ None"""
    t = f"{r.get('条件') or ''} {r.get('レース名') or ''}"
    if re.search(r"G1|GI\)|\(GI$|ＧⅠ", t) and not re.search(r"GII|GIII", t):
        return 7.0
    if "GIII" in t or "G3" in t:
        return 6.0
    if "GII" in t or "G2" in t:
        return 6.5
    if "新馬" in t:
        return 0.0
    if "未勝利" in t:
        return 1.0
    if "1勝" in t or "500万" in t:
        return 2.0
    if "2勝" in t or "1000万" in t:
        return 3.0
    if "3勝" in t or "1600万" in t:
        return 4.0
    if "オープン" in t or "(L)" in t or "(OP)" in t:
        return 5.0
    return None


F = [
    # 前走の内容
    "前走着順（0=1着〜1=最下位）", "前走で人気より上の着順", "前走の単勝オッズ（対数）", "前走データなし", "前走1着",
    "前走4角の位置（0=先頭〜1）", "前走 直線で上げた着順", "前走の上がり順位（0=最速〜1）", "前走の上がりデータなし",
    # 間隔・条件の変化
    "間隔2週以内", "間隔13週以上", "距離延長（400m単位）", "距離短縮（400m単位）", "芝ダ変更", "クラス上げ", "クラス下げ", "乗り替わり",
    # 当日
    "馬体重 増減（10kg単位）", "馬体重 10kg以上減", "馬体重 10kg以上増", "斤量（平均との差）", "牝馬", "3歳", "7歳以上",
    "馬番の内外（0=最内〜1=大外）",
    # 市場に対する実績の累積
    "騎手が市場評価より勝つ度合い", "厩舎が市場評価より勝つ度合い", "馬自身が市場評価より勝つ度合い", "キャリア出走数（対数）",
    "連対率（直近5走）", "前で運ぶ割合（直近5走）",
    "種牡馬が市場評価より勝つ度合い", "種牡馬×芝ダでの度合い", "種牡馬×距離帯での度合い", "母父が市場評価より勝つ度合い",
    "騎手×厩舎での度合い", "騎手×競馬場での度合い", "馬自身の同コースでの度合い",
    "先行争い（前で運ぶ馬の数）×自分の前傾", "単騎逃げ濃厚",
    "傾向 コース×脚質", "傾向 コース×枠", "傾向 馬場×脚質", "傾向 馬場×枠", "傾向 距離帯×年齢", "傾向 距離帯×性別",
    "傾向 コース×斤量帯", "傾向 クラス×年齢", "傾向 馬場×種牡馬", "傾向 コース×種牡馬",
    "前走のレースペース（ハイほど＋）", "前走ペース×前走で前にいた",
    "このレース 脚質", "このレース 枠", "このレース 年齢", "このレース 前走クラス", "このレース 人気帯", "このレース 斤量帯",
    # 時計
    "時計の指数（直近3走の最良）", "時計の指数（馬場差補正・直近3走の最良）", "時計の指数（馬場差補正・前走）",
    "時計の指数（馬場差補正・直近5走平均）", "同じ距離帯での最良指数", "時計データなし",
]
F_ALL = list(F)
IX = {name: i for i, name in enumerate(F_ALL)}
# 2026-10-02 実験して採用しなかった特徴量（年ごとの前向き検証で 対数尤度差 +0.00586 → +0.00572 と改善せず）。計算は残し、学習には使わない
EXTRA = ["騎手×厩舎での度合い", "騎手×競馬場での度合い", "馬自身の同コースでの度合い", "先行争い（前で運ぶ馬の数）×自分の前傾", "単騎逃げ濃厚"]
KEEP = [i for i, n in enumerate(F_ALL) if n not in EXTRA]
F = [F_ALL[i] for i in KEEP]


def load_rows():
    src = Path(SOURCE)
    files = sorted(src.glob("results_*.json")) if src.is_dir() else [src]
    rows = []
    for f in files:
        for _ in range(3):                       # 収集中のファイルは書き込みの瞬間に読めないことがある
            try:
                rows += [r for r in json.loads(f.read_text(encoding="utf-8")) if not str(r.get("距離") or "").startswith("障")]
                break
            except (json.JSONDecodeError, OSError):
                import time
                time.sleep(3)
    return rows


def build(extra_rows=None):
    """レースごとの (市場確率, 特徴量行列, 勝ち馬, オッズ) を時系列順に作る。
    extra_rows: まだ結果の出ていない出走表の行（_live=True・単勝オッズ入り）。学習・履歴には混ぜず、特徴量だけ作って part="live" で返す"""
    rows = load_rows() + list(extra_rows or [])
    races = collections.defaultdict(list)
    for r in rows:
        try:
            r["_u"], r["_o"] = int(float(r["馬番"])), float(r["単勝オッズ"])
        except (TypeError, ValueError, KeyError):
            continue
        r["_f"] = None if r.get("_live") else fin(r)
        if r["_o"] > 0:
            races[(r["date"], r["競馬場"], int(float(r["R"])))].append(r)
    keys = sorted(k for k, hs in races.items()
                  if len(hs) >= 6 and (hs[0].get("_live") or sum(1 for h in hs if h["_f"] == 1) == 1)
                  and 1.10 <= sum(1 / h["_o"] for h in hs) <= 1.45)
    dates = sorted({k[0] for k in keys if not races[k][0].get("_live")})
    live_dates = sorted({k[0] for k in keys if races[k][0].get("_live")})
    cut1, cut2 = dates[int(len(dates) * SPLIT[0])], dates[int(len(dates) * SPLIT[1])]

    tm = collections.defaultdict(list)           # 基準タイムは学習区間だけで作る
    for r in rows:
        t = sec(r.get("タイム"))
        if t and r["date"] < cut1 and fin(r):
            tm[(surf(r.get("距離")), meters(r.get("距離")))].append(t)
    std = {k: statistics.median(v) for k, v in tm.items() if len(v) >= 30}

    hist = collections.defaultdict(list)
    tend = collections.defaultdict(lambda: [0.0, 0.0])      # (傾向名, キー) → [Σ(勝ち−市場確率), 件数]。その日までの全レースから
    K_TEND = 80.0

    def stylecat(fr, has):
        return "?" if not has else "前" if fr >= 0.6 else "後" if fr <= 0.2 else "中"

    def wakuband(w):
        return "?" if not w else "内" if w <= 3 else "中" if w <= 5 else "外"

    def kinband(d):
        return "軽" if d <= -1.5 else "重" if d >= 1.5 else "並"

    GENERIC = re.compile(r"新馬|未勝利|\d勝クラス|\d+万|歳以上|歳|オープン$|^$")

    def racekey(name):
        n = re.sub(r"第\d+回|\(.*?\)|（.*?）|\s", "", str(name or ""))
        return None if (not n or GENERIC.search(n)) else n

    def tend_keys(h, venue, sf, mt, baba, cls_now, fr_, has_, kdiff, hk0):
        sa = str(h.get("性齢") or "")
        age = sa[1:] if len(sa) > 1 else "?"
        sex = sa[:1]
        bb = "良" if baba in ("良", "", None) else "道悪"      # 出走表の段階では馬場が未定→良として扱う
        sc, wb = stylecat(fr_, has_), wakuband(h.get("枠"))
        bd = band(mt)
        return {
            "傾向 コース×脚質": (venue, sf, mt, sc), "傾向 コース×枠": (venue, sf, mt, wb), "傾向 馬場×脚質": (sf, bb, sc),
            "傾向 馬場×枠": (sf, bb, wb), "傾向 距離帯×年齢": (sf, bd, age), "傾向 距離帯×性別": (sf, bd, sex),
            "傾向 コース×斤量帯": (venue, sf, kinband(kdiff)), "傾向 クラス×年齢": (cls_now, age),
            "傾向 馬場×種牡馬": (sf, bb, h.get("父")) if h.get("父") else None,
            "傾向 コース×種牡馬": (venue, sf, bd, h.get("父")) if h.get("父") else None,
            **race_keys(h, sc, wb, age, kinband(kdiff))}

    def race_keys(h, sc, wb, age, kb):
        rn = racekey(h.get("レース名"))
        if not rn:
            return {}
        orank = h.get("_orank", 0)
        ob = "1番人気" if orank == 1 else "2-3番人気" if orank <= 3 else "4-6番人気" if orank <= 6 else "7番人気以下"
        return {"このレース 脚質": (rn, sc), "このレース 枠": (rn, wb), "このレース 年齢": (rn, age), "このレース 前走クラス": (rn, h.get("_prevcls")),
                "このレース 人気帯": (rn, ob), "このレース 斤量帯": (rn, kb)}

    ent = {k: collections.defaultdict(lambda: [0.0, 0.0]) for k in ("騎手", "厩舎", "父", "父芝ダ", "父距離", "母父", "騎手厩舎", "騎手場", "馬コース")}

    def band(m):
        return "短" if m and m < 1400 else "中" if m and m < 1800 else "長" if m else ""
    horse_res = collections.defaultdict(lambda: [0.0, 0.0])
    by_date = collections.defaultdict(list)
    for k in keys:
        by_date[k[0]].append(k)

    out = []
    for d in dates + live_dates:
        pending = []
        for k in by_date[d]:
            hs = races[k]
            s = sum(1 / h["_o"] for h in hs)
            n = len(hs)
            kin = [num(h.get("斤量_kg")) for h in hs]
            kin_avg = statistics.mean([x for x in kin if x]) if any(kin) else None
            cls_now = race_class(hs[0])
            sf, mt = surf(hs[0].get("距離")), meters(hs[0].get("距離"))
            X, q = np.zeros((n, len(F_ALL))), []
            for i, (h, kg) in enumerate(zip(hs, kin)):
                qi = (1 / h["_o"]) / s
                q.append(qi)
                hk = h.get("horse_id") or h.get("馬名")
                past = hist.get(hk, [])
                p = past[-1] if past else None
                x = X[i]
                if p and p["fin"] and p["n"] > 1:
                    x[IX["前走着順（0=1着〜1=最下位）"]] = (p["fin"] - 1) / (p["n"] - 1) - 0.4
                    x[IX["前走1着"]] = float(p["fin"] == 1)
                    if p["pop"]:
                        x[IX["前走で人気より上の着順"]] = max(-1.0, min(1.0, (p["pop"] - p["fin"]) / 8.0))
                    x[IX["前走の単勝オッズ（対数）"]] = math.log(p["odds"]) - 2.5
                    if p["c4"]:
                        x[IX["前走4角の位置（0=先頭〜1）"]] = (p["c4"] - 1) / (p["n"] - 1) - 0.4
                        x[IX["前走 直線で上げた着順"]] = max(-1.0, min(1.0, (p["c4"] - p["fin"]) / 8.0))
                else:
                    x[IX["前走データなし"]] = 1.0
                if p and p["l3rank"] and p["n"] > 1:
                    x[IX["前走の上がり順位（0=最速〜1）"]] = (p["l3rank"] - 1) / (p["n"] - 1) - 0.4
                else:
                    x[IX["前走の上がりデータなし"]] = 1.0
                if p:
                    gap = (_day(d) - _day(p["date"])).days
                    x[IX["間隔2週以内"]], x[IX["間隔13週以上"]] = float(gap <= 14), float(gap >= 91)
                    if p["m"] and mt:
                        if p["surf"] != sf:
                            x[IX["芝ダ変更"]] = 1.0
                        else:
                            dd = (mt - p["m"]) / 400.0
                            x[IX["距離延長（400m単位）"]], x[IX["距離短縮（400m単位）"]] = max(0.0, min(2.0, dd)), max(0.0, min(2.0, -dd))
                    if cls_now is not None and p["cls"] is not None:
                        x[IX["クラス上げ"]], x[IX["クラス下げ"]] = float(cls_now > p["cls"]), float(cls_now < p["cls"])
                    if p["jockey"] and h.get("騎手") and p["jockey"] != h.get("騎手"):
                        x[IX["乗り替わり"]] = 1.0
                m = re.search(r"\(([+-]?\d+)\)", str(h.get("馬体重") or ""))
                if m:
                    w = int(m.group(1))
                    x[IX["馬体重 増減（10kg単位）"]] = max(-2.0, min(2.0, w / 10.0))
                    x[IX["馬体重 10kg以上減"]], x[IX["馬体重 10kg以上増"]] = float(w <= -10), float(w >= 10)
                if kg and kin_avg:
                    x[IX["斤量（平均との差）"]] = kg - kin_avg
                sa = str(h.get("性齢") or "")
                x[IX["牝馬"]] = float(sa.startswith("牝"))
                age = num(sa[1:]) if len(sa) > 1 else None
                if age:
                    x[IX["3歳"]], x[IX["7歳以上"]] = float(age == 3), float(age >= 7)
                x[IX["馬番の内外（0=最内〜1=大外）"]] = (h["_u"] - 1) / max(n - 1, 1) - 0.5
                for name, col in (("騎手", "騎手が市場評価より勝つ度合い"), ("厩舎", "厩舎が市場評価より勝つ度合い")):
                    e = ent[name].get(h.get(name))
                    if e:
                        x[IX[col]] = e[0] / (e[1] + K_ENT) * 10.0
                fa, bm = h.get("父"), h.get("母父")
                for key, name, col in (((fa), "父", "種牡馬が市場評価より勝つ度合い"), ((fa, sf), "父芝ダ", "種牡馬×芝ダでの度合い"),
                                       ((fa, band(mt)), "父距離", "種牡馬×距離帯での度合い"), ((bm), "母父", "母父が市場評価より勝つ度合い")):
                    if fa if name != "母父" else bm:
                        e2 = ent[name].get(key)
                        if e2:
                            x[IX[col]] = e2[0] / (e2[1] + K_ENT) * 10.0
                jk, tr, vn = h.get("騎手"), h.get("厩舎"), k[1]
                for key, name, col, ok in (((jk, tr), "騎手厩舎", "騎手×厩舎での度合い", jk and tr), ((jk, vn), "騎手場", "騎手×競馬場での度合い", jk),
                                           ((hk, vn, sf, band(mt)), "馬コース", "馬自身の同コースでの度合い", hk)):
                    if ok:
                        e4 = ent[name].get(key)
                        if e4:
                            x[IX[col]] = e4[0] / (e4[1] + (K_HORSE if name == "馬コース" else K_ENT)) * 10.0
                h["_orank"] = 1 + sum(1 for y in hs if y["_o"] < h["_o"])
                h["_prevcls"] = p["cls"] if p else None
                fr_h = (sum(1 for pp in past[-5:] if pp["style"] in ("逃げ", "先行")) / max(1, len([pp for pp in past[-5:] if pp["style"]])))
                has_h = any(pp["style"] for pp in past[-5:])
                tk = tend_keys(h, k[1], sf, mt, hs[0].get("馬場状態"), cls_now, fr_h, has_h, (kg - kin_avg) if (kg and kin_avg) else 0.0, hk)
                for name, key in tk.items():
                    if key is not None:
                        t0 = tend.get((name, key))
                        if t0:
                            x[IX[name]] = t0[0] / (t0[1] + K_TEND) * 10.0
                if p and p.get("pace") is not None:
                    pc = max(-3.0, min(3.0, -p["pace"] / 1.0))             # 前3F−後3F が小さい（前半が速い）ほど＋
                    x[IX["前走のレースペース（ハイほど＋）"]] = pc
                    if p["c4"] and p["n"] > 1:
                        x[IX["前走ペース×前走で前にいた"]] = pc * (0.5 - (p["c4"] - 1) / (p["n"] - 1))
                e = horse_res.get(hk)
                if e:
                    x[IX["馬自身が市場評価より勝つ度合い"]] = e[0] / (e[1] + K_HORSE) * 10.0
                x[IX["キャリア出走数（対数）"]] = math.log1p(len(past)) - 1.5
                last5 = past[-5:]
                if last5:
                    x[IX["連対率（直近5走）"]] = sum(1 for pp in last5 if pp["fin"] and pp["fin"] <= 2) / len(last5) - 0.25
                    st = [pp["style"] for pp in last5 if pp["style"]]
                    if st:
                        x[IX["前で運ぶ割合（直近5走）"]] = sum(1 for v in st if v in ("逃げ", "先行")) / len(st) - 0.4
                same = [pp for pp in past if pp["surf"] == sf]
                raw3 = [pp["raw"] for pp in same[-3:] if pp["raw"] is not None]
                adj3 = [pp["adj"] for pp in same[-3:] if pp["adj"] is not None]
                adj5 = [pp["adj"] for pp in same[-5:] if pp["adj"] is not None]
                if raw3:
                    x[IX["時計の指数（直近3走の最良）"]] = max(-4.0, min(4.0, max(raw3)))
                if adj3:
                    x[IX["時計の指数（馬場差補正・直近3走の最良）"]] = max(-4.0, min(4.0, max(adj3)))
                    x[IX["時計の指数（馬場差補正・直近5走平均）"]] = max(-4.0, min(4.0, sum(adj5) / len(adj5)))
                    if same[-1]["adj"] is not None:
                        x[IX["時計の指数（馬場差補正・前走）"]] = max(-4.0, min(4.0, same[-1]["adj"]))
                    near = [pp["adj"] for pp in same if pp["adj"] is not None and pp["m"] and mt and abs(pp["m"] - mt) <= 200]
                    if near:
                        x[IX["同じ距離帯での最良指数"]] = max(-4.0, min(4.0, max(near)))
                else:
                    x[IX["時計データなし"]] = 1.0
                pending.append((h, hk, qi, n, cls_now))
            fr = X[:, IX["前で運ぶ割合（直近5走）"]] + 0.4          # 前で運ぶ割合（0〜1）。過去走なしは0
            has = X[:, IX["前走データなし"]] == 0
            nf = int(((fr >= 0.6) & has).sum())
            X[:, IX["先行争い（前で運ぶ馬の数）×自分の前傾"]] = np.where(has, (nf - 2.5) / 2.0 * (fr - 0.4), 0.0)
            X[:, IX["単騎逃げ濃厚"]] = ((fr >= 0.6) & has & (nf == 1)).astype(float)
            out.append(dict(key=k, q=np.array(q), X=X[:, KEEP], win=-1 if hs[0].get("_live") else [h["_f"] == 1 for h in hs].index(True),
                            odds=np.array([h["_o"] for h in hs]), uma=[h["_u"] for h in hs],
                            part="live" if hs[0].get("_live") else "train" if d < cut1 else "valid" if d < cut2 else "test",
                            names=[h.get("馬名") for h in hs]))
        # ── その日が終わってから履歴を更新する（同日の結果を特徴量に混ぜない）──
        raws = collections.defaultdict(list)
        day_entries = []
        for h, hk, qi, n, cls_now in pending:
            f = h["_f"]
            for name in ("騎手", "厩舎"):
                if h.get(name) and f:
                    e = ent[name][h.get(name)]
                    e[0] += (1.0 if f == 1 else 0.0) - qi
                    e[1] += 1.0
            sf0, mt0 = surf(h.get("距離")), meters(h.get("距離"))
            fa, bm = h.get("父"), h.get("母父")
            if f:
                res = (1.0 if f == 1 else 0.0) - qi
                for key, name, ok in (((fa), "父", fa), ((fa, sf0), "父芝ダ", fa), ((fa, band(mt0)), "父距離", fa), ((bm), "母父", bm)):
                    if ok:
                        e3 = ent[name][key]
                        e3[0] += res
                        e3[1] += 1.0
            if f:
                frh = (sum(1 for pp in hist.get(hk, [])[-5:] if pp["style"] in ("逃げ", "先行")) / max(1, len([pp for pp in hist.get(hk, [])[-5:] if pp["style"]])))
                hasu = any(pp["style"] for pp in hist.get(hk, [])[-5:])
                kd = (h.get("斤量_kg") or 0) - (statistics.mean([y.get("斤量_kg") for y in races[(h["date"], h["競馬場"], int(float(h["R"])))] if y.get("斤量_kg")]) if any(y.get("斤量_kg") for y in races[(h["date"], h["競馬場"], int(float(h["R"])))]) else 0)
                tk2 = tend_keys(h, h.get("競馬場"), surf(h.get("距離")), meters(h.get("距離")), h.get("馬場状態"), cls_now, frh, hasu, kd, hk)
                resT = (1.0 if f == 1 else 0.0) - qi
                for name, key in tk2.items():
                    if key is not None:
                        t1 = tend[(name, key)]
                        t1[0] += resT
                        t1[1] += 1.0
            if f:
                res2 = (1.0 if f == 1 else 0.0) - qi
                for key, name, ok in (((h.get("騎手"), h.get("厩舎")), "騎手厩舎", h.get("騎手") and h.get("厩舎")), ((h.get("騎手"), h.get("競馬場")), "騎手場", h.get("騎手")),
                                       ((hk, h.get("競馬場"), sf0, band(mt0)), "馬コース", hk)):
                    if ok:
                        e5 = ent[name][key]
                        e5[0] += res2
                        e5[1] += 1.0
            if hk and f:
                e = horse_res[hk]
                e[0] += (1.0 if f == 1 else 0.0) - qi
                e[1] += 1.0
            sf, mt = surf(h.get("距離")), meters(h.get("距離"))
            t, b = sec(h.get("タイム")), std.get((sf, mt))
            raw = (b - t) / b * 100.0 if (t and b and f) else None
            c = [int(v) for v in re.findall(r"\d+", str(h.get("コーナー通過") or ""))]
            ent_h = dict(date=d, fin=f, n=n, pop=num(h.get("人気")), odds=h["_o"], m=mt, surf=sf, jockey=h.get("騎手"),
                         style=h.get("脚質"), l3rank=num(h.get("後3F順位")), c4=c[-1] if c else None, cls=cls_now, raw=raw, adj=None, live=bool(h.get("_live")),
                         pace=((h.get("前3F_レース") - h.get("後3F_レース")) if (h.get("前3F_レース") and h.get("後3F_レース")) else None))
            if raw is not None:
                raws[(h.get("競馬場"), sf)].append(raw)
            day_entries.append((hk, h.get("競馬場"), ent_h))
        variant = {k: statistics.median(v) for k, v in raws.items() if len(v) >= 20}     # その日その場の馬場差
        for hk, venue, e in day_entries:
            if e["raw"] is not None and (venue, e["surf"]) in variant:
                e["adj"] = e["raw"] - variant[(venue, e["surf"])]
            if hk and not e.get("live"):
                hist[hk].append(e)
    return out, (cut1, cut2)


# ── 条件付きロジット ─────────────────────────────────────────────────
def probs(race, beta, w):
    u = beta * np.log(race["q"]) + race["X"] @ w
    u -= u.max()
    e = np.exp(u)
    return e / e.sum()


def pack(races):
    R, H, K = len(races), max(len(r["q"]) for r in races), len(F)
    LQ, X, M, win = np.full((R, H), -1e9), np.zeros((R, H, K)), np.zeros((R, H), dtype=bool), np.zeros(R, dtype=int)
    for i, r in enumerate(races):
        n = len(r["q"])
        LQ[i, :n], X[i, :n], M[i, :n], win[i] = np.log(r["q"]), r["X"], True, r["win"]
    return LQ, X, M, win


def _P(packed, beta, w):
    LQ, X, M, win = packed
    U = np.where(M, beta * LQ + X @ w, -1e9)
    U -= U.max(axis=1, keepdims=True)
    E = np.exp(U) * M
    return E / E.sum(axis=1, keepdims=True)


def fit(packed, l2):
    from scipy.optimize import minimize
    LQ, X, M, win = packed
    R, k = len(win), len(F)
    idx = np.arange(R)
    LQm = np.where(M, LQ, 0.0)

    def negll(theta):
        beta, w = theta[0], theta[1:]
        P = _P(packed, beta, w)
        ll = np.log(np.maximum(P[idx, win], 1e-300)).sum() / R - 0.5 * l2 * (w @ w)
        gb = (LQm[idx, win] - (P * LQm).sum(axis=1)).sum() / R
        gw = (X[idx, win] - np.einsum("rh,rhk->rk", P, X)).sum(axis=0) / R - l2 * w
        return -ll, -np.concatenate([[gb], gw])

    res = minimize(negll, np.concatenate([[1.0], np.zeros(k)]), jac=True, method="L-BFGS-B", options={"maxiter": 800})
    return float(res.x[0]), res.x[1:]


def loglik(packed, beta, w):
    P = _P(packed, beta, w)
    return np.log(np.maximum(P[np.arange(len(packed[3])), packed[3]], 1e-300))


def boot_mean(x, n=4000, seed=1):
    rng = np.random.default_rng(seed)
    m = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def bet_sim(races, beta, w, thr, cap=None):
    """期待値（モデル確率×単勝オッズ）が thr 以上の馬に100円ずつ。cap を指定するとそのオッズ以下の馬だけ"""
    st, rt, nb, hit = [], [], 0, 0
    for r in races:
        p = probs(r, beta, w)
        ev = p * r["odds"]
        sel = np.where((ev >= thr) & ((r["odds"] <= cap) if cap else True))[0]
        st.append(100.0 * len(sel))
        rt.append(100.0 * r["odds"][r["win"]] if r["win"] in sel else 0.0)
        nb += len(sel)
        hit += int(r["win"] in sel)
    return np.array(st), np.array(rt), nb, hit


def roi_ci(st, rt, n=4000, seed=1):
    if st.sum() == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(st), size=(n, len(st)))
    s, r = st[idx].sum(axis=1), rt[idx].sum(axis=1)
    x = r[s > 0] / s[s > 0]
    return float(rt.sum() / st.sum()), float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def run_fit():
    races, (cut1, cut2) = build()
    tr = [r for r in races if r["part"] == "train"]
    va = [r for r in races if r["part"] == "valid"]
    te = [r for r in races if r["part"] == "test"]
    d0, d1 = races[0]["key"][0], races[-1]["key"][0]
    print(f"■ データ {len(races):,}レース（{d0}〜{d1}）  特徴量 {len(F)}個")
    print(f"   学習 {len(tr):,}（〜{cut1}の前日）／ 調整 {len(va):,}（〜{cut2}の前日）／ 判定 {len(te):,}（{cut2}〜）")
    ptr, pva, pte = pack(tr), pack(va), pack(te)
    zero = np.zeros(len(F))

    best = None
    for l2 in (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0):
        b, w = fit(ptr, l2)
        g = float((loglik(pva, b, w) - loglik(pva, 1.0, zero)).mean())
        print(f"   正則化 {l2:<6} 調整区間での市場との差 {g:+.5f}")
        if best is None or g > best[0]:
            best = (g, l2)
    l2 = best[1]
    beta, w = fit(pack(tr + va), l2)                 # 重みは学習＋調整で決め直し、判定区間は触らない
    print(f"   採用: 正則化 {l2} ／ β（市場確率の指数）= {beta:.3f}")

    d = loglik(pte, beta, w) - loglik(pte, 1.0, zero)
    lo, hi = boot_mean(d)
    gateA = lo > 0
    print(f"\n■ 関門A（判定区間 {len(te):,}レース・市場だけの確率との対数尤度の差）: {d.mean():+.5f}/レース  95%区間［{lo:+.5f}, {hi:+.5f}］ → {'通過' if gateA else '不通過'}")

    print("\n■ 特徴量の重み（＋は市場の評価より走る方向。大きさの順・上位15）")
    for i in np.argsort(-np.abs(w))[:15]:
        print(f"   {w[i]:+.3f}  {F[i]}")

    print(f"\n■ 関門B（判定区間・単勝を期待値しきい値以上だけ買う）")
    print(f"{'しきい値':>8}{'対象':>10}{'点数':>8}{'的中':>6}{'回収率':>9}{'95%区間':>18}")
    rows = []
    for cap, lab in ((None, "全部"), (30.0, "30倍以下"), (10.0, "10倍以下")):
        for thr in (0.0, 0.9, 1.0, 1.05, 1.1, 1.2):
            st, rt, nb, hit = bet_sim(te, beta, w, thr, cap)
            roi, rl, rh = roi_ci(st, rt)
            if roi is None:
                continue
            rows.append(dict(thr=thr, cap=cap, bets=nb, hit=hit, roi=round(roi, 4), lo=round(rl, 4), hi=round(rh, 4)))
            print(f"{thr:>8.2f}{lab:>10}{nb:>9,}{hit:>6}{roi*100:>8.1f}%   ［{rl*100:>5.1f}〜{rh*100:>5.1f}%］"
                  + ("  ←しきい値なし（控除率の水準）" if thr == 0.0 else ""))
    main_row = next((x for x in rows if x["thr"] == 1.0 and x["cap"] is None), None)
    gateB = bool(main_row and main_row["lo"] > 1.0)
    print(f"\n判定: 関門A {'通過' if gateA else '不通過'} ／ 関門B（しきい値1.0・全部で、区間の下限が100%超） {'通過' if gateB else '不通過'}")
    MODEL.write_text(json.dumps(dict(
        fitted=datetime.date.today().isoformat(), source=str(SOURCE), data_from=d0, data_to=d1,
        cut_train=cut1, cut_valid=cut2, n_train=len(tr), n_valid=len(va), n_test=len(te), l2=l2, beta=beta,
        features=F, weights=[float(x) for x in w], target_roi=TARGET_ROI,
        gateA=dict(ll_gain=float(d.mean()), ci=[lo, hi], passed=bool(gateA)),
        gateB=dict(rows=rows, passed=gateB), active=bool(gateA and gateB)), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存: {MODEL}（active={bool(gateA and gateB)}）")


def run_walk(l2=0.01, first=2019):
    """年ごとの前向き検証: その年より前の全レースで学習し、その年だけで測る。判定区間を1つに頼らず、毎年が未使用データになる。"""
    races, _ = build()
    packed_all = {}
    years = sorted({r["key"][0][:4] for r in races})
    zero = np.zeros(len(F))
    pooled = {k: ([], []) for k in ("1.0", "1.05", "1.1", "0.9")}
    pooled10 = {k: ([], []) for k in ("1.0", "1.05", "1.1", "0.9")}
    gains = []
    print(f"■ 年ごとの前向き検証（学習＝その年より前の全レース・正則化{l2}）  データ {len(races):,}レース")
    print(f"{'年':>5}{'学習R':>8}{'検証R':>7}{'対数尤度差':>11}{'  EV≧1.0(全)':>16}{'  EV≧1.05(10倍以下)':>22}")
    for y in years:
        if int(y) < first:
            continue
        tr = [r for r in races if r["key"][0][:4] < y]
        te = [r for r in races if r["key"][0][:4] == y]
        if len(tr) < 5000 or not te:
            continue
        beta, w = fit(pack(tr), l2)
        pte = pack(te)
        d = loglik(pte, beta, w) - loglik(pte, 1.0, zero)
        gains.append(d)
        cells = []
        for thr, cap, store in ((1.0, None, pooled), (1.05, 10.0, pooled10)):
            st, rt, nb, hit = bet_sim(te, beta, w, thr, cap)
            cells.append(f"{nb:>5}点 {rt.sum()/st.sum()*100 if st.sum() else 0:>6.1f}%")
        for key, thr in (("0.9", 0.9), ("1.0", 1.0), ("1.05", 1.05), ("1.1", 1.1)):
            st, rt, _, _ = bet_sim(te, beta, w, thr, None)
            pooled[key][0].append(st); pooled[key][1].append(rt)
            st, rt, _, _ = bet_sim(te, beta, w, thr, 10.0)
            pooled10[key][0].append(st); pooled10[key][1].append(rt)
        print(f"{y:>5}{len(tr):>8,}{len(te):>7,}{d.mean():>+11.5f}   {cells[0]:>14}   {cells[1]:>18}")
    g = np.concatenate(gains)
    lo, hi = boot_mean(g)
    print(f"\n  全年まとめ 対数尤度差 {g.mean():+.5f}/レース ［{lo:+.5f}, {hi:+.5f}］（{len(g):,}レース）")
    for lab, store in (("全部", pooled), ("10倍以下", pooled10)):
        for key in ("0.9", "1.0", "1.05", "1.1"):
            st, rt = np.concatenate(store[key][0]), np.concatenate(store[key][1])
            roi, rl, rh = roi_ci(st, rt)
            if roi:
                print(f"  EV≧{key:<5}（{lab}）{int(st.sum()/100):>7,}点  回収率 {roi*100:6.1f}%  ［{rl*100:5.1f}〜{rh*100:5.1f}%］")


def report():
    if not MODEL.exists():
        print("モデル未作成。python ev_engine.py --fit")
        return
    m = json.loads(MODEL.read_text(encoding="utf-8"))
    print(f"■ ev_model（{m['fitted']}・{m.get('data_from')}〜{m.get('data_to')}・学習{m['n_train']:,}／調整{m.get('n_valid', 0):,}／判定{m['n_test']:,}R）  目標回収率 {m['target_roi']*100:.0f}%")
    a = m["gateA"]
    print(f"  関門A: {a['ll_gain']:+.5f} ［{a['ci'][0]:+.5f}, {a['ci'][1]:+.5f}］ {'通過' if a['passed'] else '不通過'}")
    for r in m["gateB"]["rows"]:
        if r.get("cap") is None:
            print(f"  しきい値{r['thr']:.2f}: {r['bets']:,}点 回収率{r['roi']*100:.1f}% ［{r['lo']*100:.0f}〜{r['hi']*100:.0f}%］")
    print(f"  稼働: {'する' if m['active'] else 'しない（買い目は出さない）'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--walk", action="store_true", help="年ごとの前向き検証（その年より前で学習→その年で測る）")
    ap.add_argument("--source", help="学習に使うデータ（年ごとのファイルが入ったフォルダ、または1つのJSON）")
    a = ap.parse_args()
    if a.source:
        SOURCE = Path(a.source)
    if a.walk:
        run_walk()
    elif a.fit:
        run_fit()
    else:
        report()
