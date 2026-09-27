# -*- coding: utf-8 -*-
"""
pdca_rounds.py — PDCAを100ラウンド回す（2026-09-25）
====================================================
メモリのルール「PDCAは100回回す。各ラウンドは前のラウンドの発見を引き継ぐ」に対応する実装。

⚠ 100個の仮説を試せば、何もなくても5個前後は「p<0.05」に見える（多重比較）。
　 過去に300帯スキャンの候補がhold-outで全滅した原因がこれ。したがって各ラウンドで必ず2つの関門を通す。
   関門1: **市場人気で条件付ける**（そうしないと「強い馬は人気」の再発見になる）
   関門2: **前半で見つけて後半で確かめる**（日付で2分割。両方で同じ符号かつ後半もp<0.05のものだけ残す）

各ラウンドの中身:
  仮説「条件Xの馬は、同じ人気帯の平均と比べて3着内率が高い（低い）」
  指標 lift = 実測3着内数 − 期待3着内数（期待は人気帯別の全体平均から算出）
  z = lift / sqrt(Σ p(1-p))

出力: daily_pdca/db/pdca_rounds.json（台帳）＋ 画面にサマリー
使い方: python pdca_rounds.py [--rounds 100]
"""
from __future__ import annotations
import argparse, json, math, re, sys, io
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
LEDGER = DB / "pdca_rounds.json"
MIN_N = 150          # この頭数に満たない仮説は判定しない
BANDS = [(1, 1), (2, 2), (3, 3), (4, 5), (6, 9), (10, 99)]


def fin_of(r):
    v = r.get("着順int")
    if v:
        try:
            return int(float(v))
        except (TypeError, ValueError):
            pass
    m = re.match(r"\s*(\d+)", str(r.get("着順") or ""))
    return int(m.group(1)) if m else None


def band(p):
    try:
        p = int(float(p))
    except (TypeError, ValueError):
        return None
    for lo, hi in BANDS:
        if lo <= p <= hi:
            return f"{lo}-{hi}"
    return None


def norm_dist(d):
    m = re.match(r"^([芝ダ障])\D*(\d{3,4})", str(d or ""))
    return f"{m.group(1)}{m.group(2)}" if m else ""


def weight_diff(r):
    m = re.search(r"\(([+-]?\d+)\)", str(r.get("馬体重") or ""))
    return int(m.group(1)) if m else None


_JK_SHORT: list[str] = []


def norm_jockey(name: str | None) -> str:
    """騎手名の表記ゆれを吸収する。
    累積DBは旧期間がフルネーム（丹内祐次）、新期間が略称（丹内）で入っている
    （旧期間は2026-09-25にnetkeibaから補完したため）。略称側に寄せる。"""
    if not name:
        return ""
    cands = [s for s in _JK_SHORT if name.startswith(s)]
    return max(cands, key=len) if cands else name


def klass(name):
    for c in ("新馬", "未勝利", "1勝", "2勝", "3勝"):
        if c in str(name):
            return c
    return "オープン以上"


def build_hypotheses(rows) -> list[tuple[str, callable]]:
    """仮説を自動生成する（フィールド×値）。
    🔴 **レース前に分かる項目だけ**を使う。累積DBの「脚質」「ペース」「着差」「後3F」「独自指数」は
    そのレースを走った結果から作られるので、使うと「逃げた馬は3着内が多い」という当たり前の再発見になる
    （2026-09-25の1回目の実行で実際に脚質3件だけが残り、これに気づいた）。"""
    H = []
    for w in range(1, 9):
        H.append((f"枠={w}", lambda r, w=w: r.get("枠") == w))
    for v in ("中山", "阪神", "東京", "京都", "中京", "新潟", "福島", "小倉", "札幌", "函館"):
        H.append((f"競馬場={v}", lambda r, v=v: r.get("競馬場") == v))
    for d in ("ダ1200", "ダ1400", "ダ1800", "芝1200", "芝1600", "芝2000", "芝2200", "芝2400"):
        H.append((f"距離={d}", lambda r, d=d: norm_dist(r.get("距離")) == d))
    for b in ("良", "稍重", "重", "不良"):
        H.append((f"馬場={b}", lambda r, b=b: r.get("馬場状態") == b))
    for t in ("晴", "曇", "雨", "小雨"):
        H.append((f"天候={t}", lambda r, t=t: r.get("天候") == t))
    for s, lab in (("牡", "牡"), ("牝", "牝"), ("セ", "セン")):
        H.append((f"性別={lab}", lambda r, s=s: str(r.get("性齢") or "").startswith(s)))
    for age in (2, 3, 4, 5):
        H.append((f"馬齢={age}歳" + ("以上" if age == 5 else ""),
                  lambda r, age=age: (m := re.search(r"(\d+)", str(r.get("性齢") or ""))) and
                  (int(m.group(1)) >= 5 if age == 5 else int(m.group(1)) == age)))
    for c in ("新馬", "未勝利", "1勝", "2勝", "3勝", "オープン以上"):
        H.append((f"クラス={c}", lambda r, c=c: klass(r.get("レース名")) == c))
    for lo, hi, lab in ((10, 999, "+10kg以上"), (-999, -10, "-10kg以下"), (-2, 2, "±2kg以内")):
        H.append((f"馬体重増減={lab}", lambda r, lo=lo, hi=hi: (wd := weight_diff(r)) is not None and lo <= wd <= hi))
    for lo, hi, lab in ((57.0, 99, "57kg以上"), (0, 53.9, "54kg未満")):
        H.append((f"斤量={lab}", lambda r, lo=lo, hi=hi: (k := r.get("斤量_kg")) and lo <= float(k) <= hi))
    # 中日数（2026-09-27 db_repair_fields.py でDB内の前走日から生成。前走がDBに無い馬は None＝対象外）
    for lo, hi, lab in ((1, 7, "連闘(〜7日)"), (8, 14, "中1週"), (15, 35, "中2〜4週"),
                        (36, 90, "中5週〜3ヶ月"), (91, 180, "休み明け(3〜6ヶ月)"), (181, 9999, "長期休養明け(6ヶ月〜)")):
        H.append((f"中日数={lab}", lambda r, lo=lo, hi=hi: isinstance(r.get("中日数"), int) and lo <= r["中日数"] <= hi))
    # 上位種牡馬（出走数の多い順）
    sires = defaultdict(int)
    for r in rows:
        if r.get("父"):
            sires[r["父"]] += 1
    for s, _ in sorted(sires.items(), key=lambda kv: -kv[1])[:20]:
        H.append((f"父={s}", lambda r, s=s: r.get("父") == s))
    # レース前に分かる統計由来の指標のみ（F04騎手・F05厩舎はティア統計、F14は馬場適性）
    for f, th, lab in (("F04_騎手", 70, "騎手評価70以上"), ("F05_厩舎", 70, "厩舎評価70以上"),
                       ("F14_馬場", 70, "馬場適性70以上"), ("F08_距離", 70, "距離適性70以上"),
                       ("F10_斤量", 70, "斤量有利70以上"), ("F12_年齢", 70, "年齢曲線70以上")):
        H.append((lab, lambda r, f=f, th=th: (v := r.get(f)) is not None and float(v) >= th))
    jk = defaultdict(int)
    for r in rows:
        if r.get("騎手"):
            jk[norm_jockey(r["騎手"])] += 1
    for j, _ in sorted(jk.items(), key=lambda kv: -kv[1])[:12]:
        H.append((f"騎手={j}", lambda r, j=j: norm_jockey(r.get("騎手")) == j))
    return H


def _count(rows, field) -> dict:
    c = defaultdict(int)
    for r in rows:
        if r.get(field):
            c[r[field]] += 1
    return c


def build_layer2(rows, survivors) -> list[tuple[str, callable]]:
    """第2層: 前のラウンドで残った条件に、別の軸を掛け合わせて深掘りする
    （メモリのルール「各ラウンドは前のラウンドの発見を引き継ぐ」に対応）。"""
    base = {name: cond for name, cond in build_hypotheses(rows)}
    out = []
    seconds = [("中山", lambda r: r.get("競馬場") == "中山"), ("阪神", lambda r: r.get("競馬場") == "阪神"),
               ("ダート", lambda r: norm_dist(r.get("距離")).startswith("ダ")),
               ("芝", lambda r: norm_dist(r.get("距離")).startswith("芝")),
               ("道悪", lambda r: r.get("馬場状態") in ("稍重", "重", "不良")),
               ("未勝利", lambda r: klass(r.get("レース名")) == "未勝利"),
               ("1勝", lambda r: klass(r.get("レース名")) == "1勝"),
               ("人気薄(6番人気以下)", lambda r: (p := r.get("人気")) and float(p) >= 6)]
    for sname in survivors:
        c1 = base.get(sname)
        if not c1:
            continue
        for lab, c2 in seconds:
            out.append((f"{sname} × {lab}", lambda r, c1=c1, c2=c2: c1(r) and c2(r)))
    return out


def evaluate(rows, cond) -> dict | None:
    """人気帯で条件付けた 3着内の超過（lift）とz値。"""
    base = defaultdict(lambda: [0, 0])          # band -> [n, top3]
    for r in rows:
        b, f = band(r.get("人気")), fin_of(r)
        if b and f:
            base[b][0] += 1
            base[b][1] += f <= 3
    p_band = {b: (t / n if n else 0) for b, (n, t) in base.items()}
    n = obs = exp = var = 0
    for r in rows:
        b, f = band(r.get("人気")), fin_of(r)
        if not (b and f) or not cond(r):
            continue
        p = p_band[b]
        n += 1; obs += f <= 3; exp += p; var += p * (1 - p)
    if n < MIN_N or var <= 0:
        return None
    z = (obs - exp) / math.sqrt(var)
    return {"n": n, "obs": obs, "exp": round(exp, 1), "lift_pt": round((obs - exp) / n * 100, 2), "z": round(z, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=100)
    a = ap.parse_args()
    rows = [r for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
            if fin_of(r) and band(r.get("人気"))]
    # 略称（新期間の表記）を辞書にして、フルネーム側を寄せる
    _JK_SHORT.extend(sorted({r["騎手"] for r in rows if r.get("騎手") and len(r["騎手"]) <= 3},
                            key=len, reverse=True))
    dates = sorted({r["date"] for r in rows})
    cut = dates[len(dates) // 2]
    first = [r for r in rows if r["date"] < cut]
    second = [r for r in rows if r["date"] >= cut]
    print(f"■ PDCA {a.rounds}ラウンド（全{len(rows):,}頭 / {len(dates)}日）")
    print(f"  前半 {dates[0]}〜{cut}（{len(first):,}頭） → 発見用")
    print(f"  後半 {cut}〜{dates[-1]}（{len(second):,}頭） → 確認用")
    print(f"  関門1: 人気帯で条件付け ／ 関門2: 前半と後半で同符号かつ後半 |z|>=1.96\n")

    def run(H, results, start=1):
        """🔴 累積DBは前半（〜2026-05-16）が項目の少ない旧形式で、レース名・斤量・馬体重・騎手・性齢が丸ごと無い。
        固定の日付で二分割すると、それらを使う仮説は前半が空になって判定できない。
        そこで**その仮説が使える行だけ**を取り出し、その中の日付中央で二分割する。"""
        for i, (name, cond) in enumerate(H, start):
            usable = [r for r in rows if cond(r) is not None]
            hit = [r for r in rows if cond(r)]
            if len(hit) < MIN_N:
                print(f"[{i:>3}] {name:<26} 対象{len(hit)}頭 → 判定できない（{MIN_N}頭未満）")
                continue
            ds = sorted({r["date"] for r in hit})
            mid = ds[len(ds) // 2]
            allr = evaluate(rows, cond)
            f1 = evaluate([r for r in rows if r["date"] < mid], cond)
            f2 = evaluate([r for r in rows if r["date"] >= mid], cond)
            if not (allr and f1 and f2):
                print(f"[{i:>3}] {name:<26} 期間を分けると判定できない（前半{f1['n'] if f1 else 0}頭/後半{f2['n'] if f2 else 0}頭）")
                continue
            survive = (f1["lift_pt"] * f2["lift_pt"] > 0) and abs(f2["z"]) >= 1.96
            results.append({"round": i, "hypothesis": name, "split": mid, "all": allr,
                            "first": f1, "second": f2, "survive": survive})
            print(f"[{i:>3}] {name:<26} n={allr['n']:>5} 超過{allr['lift_pt']:+5.2f}pt z={allr['z']:+5.2f} "
                  f"｜前半{f1['lift_pt']:+5.2f} 後半{f2['lift_pt']:+5.2f} {'★残った' if survive else ''}")
        return results

    results = []
    H1 = build_hypotheses(rows)
    print(f"── 第1層: 単独条件 {len(H1)}件 ──")
    run(H1[:a.rounds], results)
    surv1 = [r["hypothesis"] for r in results if r["survive"]]
    if len(results) < a.rounds and surv1:
        H2 = build_layer2(rows, surv1)[:a.rounds - len(results)]
        print(f"\n── 第2層: 第1層で残った{len(surv1)}件に別の軸を掛ける {len(H2)}件 ──")
        run(H2, results, start=len(results) + 1)

    surv = [r for r in results if r["survive"]]
    sig_all = [r for r in results if abs(r["all"]["z"]) >= 1.96]
    print(f"\n■ 結果: {len(results)}ラウンド判定 / 全体でp<0.05は{len(sig_all)}件 "
          f"（偶然でも約{len(results)*0.05:.0f}件は出る）/ **両関門を通ったのは{len(surv)}件**")
    for r in sorted(surv, key=lambda x: -abs(x["second"]["z"])):
        d = "高い" if r["second"]["lift_pt"] > 0 else "低い"
        print(f"  ★ {r['hypothesis']:<22} 同じ人気帯より3着内率が{d}"
              f"（全体{r['all']['lift_pt']:+.2f}pt・後半z={r['second']['z']:+.2f}・n={r['all']['n']:,}）")
    LEDGER.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n台帳: {LEDGER}")
    print("※ ここで残ったものも「買う理由」ではなく候補。実運用に入れる前に前向き台帳で追跡すること。")


if __name__ == "__main__":
    main()
