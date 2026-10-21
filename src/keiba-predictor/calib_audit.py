"""確率エンジンの「条件別の当たり具合」点検（前向き確率 _cache/walk_probs.pkl を使う）

条件（間隔・前走・距離変化・人気・クラス など）ごとに、
  実際の勝ち数 ÷ モデルの勝つ確率の合計（A/E）と、同じく市場の A/E を並べる。
モデルの A/E が 1 から外れていて、年をまたいで同じ向きなら「その条件の扱いが足りない」ヒント。
ヒントは在サンプルの発見なので、採用は ev_engine の前向き検証（--walk / fresh_test）を通してから。

使い方:
  python calib_audit.py                    # 全条件の表（docs/keiba_calib_audit.md に保存）
  python calib_audit.py --min 300          # 頭数がこれ未満の区分は出さない
前提: python strategy_tournament.py --build で _cache/walk_probs.pkl を作っておく
"""
import argparse, collections, json, math, pickle, re, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.stdout.reconfigure(encoding="utf-8")
CACHE = HERE / "_cache" / "walk_probs.pkl"


def load_hist():
    import predict_day as P
    rows = []
    for f in sorted(Path(P.HIST).glob("results_*.json")):
        rows += json.loads(f.read_text(encoding="utf-8"))
    return rows


def dist_m(s):
    m = re.search(r"(\d{3,4})", str(s or ""))
    return int(m.group(1)) if m else 0


def cls_of(c):
    c = str(c or "")
    if "新馬" in c: return "新馬"
    if "未勝利" in c: return "未勝利"
    if "1勝" in c: return "1勝"
    if "2勝" in c: return "2勝"
    if "3勝" in c: return "3勝"
    if c[:2] == "G1": return "G1"
    if c[:2] in ("G2", "G3"): return "G2G3"
    return "OP"


def build_features(hist):
    """(date, 場, R, 馬番) → 条件の辞書。前走は horse_id ごとに日付順で引く"""
    by_h = collections.defaultdict(list)
    for r in hist:
        if r.get("horse_id"):
            by_h[r["horse_id"]].append(r)
    feat = {}
    for hid, runs in by_h.items():
        runs.sort(key=lambda r: r["date"])
        for i, r in enumerate(runs):
            prev = runs[i - 1] if i else None
            d = dist_m(r["距離"]); surf = str(r["距離"])[:1]
            f = {}
            f["クラス"] = cls_of(r.get("条件"))
            f["芝ダ"] = surf
            f["距離帯"] = surf + ("〜1400" if d <= 1400 else "1500〜1800" if d <= 1800 else "1900〜2400" if d <= 2400 else "2500〜")
            f["頭数"] = "〜10頭" if (r.get("頭数") or 0) <= 10 else "11〜15頭" if r["頭数"] <= 15 else "16頭〜"
            age = int(re.sub(r"\D", "", str(r.get("性齢")) or "0") or 0)
            f["年齢"] = f"{min(age, 6)}歳" + ("以上" if age >= 6 else "")
            f["性"] = str(r.get("性齢") or "?")[:1]
            f["競馬場"] = r["競馬場"]
            if prev is None:
                f["間隔"] = "初出走"
            else:
                import datetime as dt
                gap = (dt.datetime.strptime(r["date"], "%Y%m%d") - dt.datetime.strptime(prev["date"], "%Y%m%d")).days
                f["間隔"] = ("〜14日" if gap <= 14 else "15〜35日" if gap <= 35 else "36〜70日" if gap <= 70
                            else "71〜150日" if gap <= 150 else "151〜300日" if gap <= 300 else "301日〜")
                pf = prev.get("着順int") or 99
                pc = cls_of(prev.get("条件"))
                f["前走着順"] = "1着" if pf == 1 else "2〜3着" if pf <= 3 else "4〜5着" if pf <= 5 else "6〜9着" if pf <= 9 else "10着〜"
                f["前走クラス"] = pc
                f["昇級"] = "昇級" if pf == 1 and pc not in ("G1", "G2G3", "OP") and f["クラス"] != pc else "同級以下"
                if gap > 150:
                    f["長休み明け×前走格"] = ("重賞" if pc in ("G1", "G2G3") else "OP" if pc == "OP" else "条件戦") + \
                                            ("・3着内" if pf <= 3 else "・4着以下")
                pd_ = dist_m(prev["距離"])
                dd = d - pd_
                f["距離変化"] = ("延長400m超" if dd > 400 else "延長200〜400" if dd >= 200 else "短縮400m超" if dd < -400
                               else "短縮200〜400" if dd <= -200 else "同程度")
                f["芝ダ替わり"] = "替わり" if str(prev["距離"])[:1] != surf else "同じ"
                f["乗り替わり"] = "乗り替わり" if prev.get("騎手") != r.get("騎手") else "同じ騎手"
                w = re.search(r"\(([+-]?\d+)\)", str(r.get("馬体重") or ""))
                if w:
                    wv = int(w.group(1))
                    f["馬体重増減"] = "−10kg以下" if wv <= -10 else "−4〜−8" if wv <= -4 else "+10kg以上" if wv >= 10 else "+4〜+8" if wv >= 4 else "±2以内"
                past_d = [dist_m(x["距離"]) for x in runs[:i] if str(x["距離"])[:1] == surf]
                f["距離経験"] = "初めての長さ（最長+200m超）" if past_d and d > max(past_d) + 200 else "経験あり"
            feat[(r["date"], r["競馬場"], int(float(r["R"])), int(r["馬番"]))] = f
    return feat


def main(A):
    races = pickle.loads(CACHE.read_bytes())
    feat = build_features(load_hist())
    # 区分ごと: 頭数, 勝ち, Σp, Σq, 年別[勝ち, Σp, Σq], 単勝払戻(100円×頭数)
    acc = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, collections.defaultdict(lambda: [0, 0.0, 0.0])])
    pop_acc = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, collections.defaultdict(lambda: [0, 0.0, 0.0])])
    miss = 0
    for r in races:
        y = r["key"][0][:4]
        order = np.argsort(-np.asarray(r["q"]))
        rank = {int(i): k + 1 for k, i in enumerate(order)}
        for j, u in enumerate(r["uma"]):
            f = feat.get((r["key"][0], r["key"][1], int(r["key"][2]), int(u)))
            if f is None:
                miss += 1
                continue
            win = 1 if r["fins"][j] == 1 else 0
            p, q = float(r["p"][j]), float(r["q"][j])
            pop = rank[j]
            f = dict(f, 人気=("1番人気" if pop == 1 else "2〜3番人気" if pop <= 3 else "4〜6番人気" if pop <= 6 else "7〜9番人気" if pop <= 9 else "10番人気〜"))
            for k, v in f.items():
                a = acc[(k, v)]
                a[0] += 1; a[1] += win; a[2] += p; a[3] += q
                b = a[4][y]; b[0] += win; b[1] += p; b[2] += q
    L = []
    pr = L.append
    pr("# 確率エンジンの条件別の当たり具合（前向き確率・2019〜）\n")
    pr(f"レース {len(races):,}（特徴が引けなかった馬 {miss:,}頭）。A/E＝実際の勝ち÷確率の合計。1より大きい＝その条件の馬を低く見すぎ。")
    pr("「年」＝モデルのA/Eが1から同じ向きに外れた年の数／年の数。**モデルのA/Eが市場より1から遠い区分**が、エンジンの直しどころの候補。\n")
    pr("| 条件 | 区分 | 頭数 | 勝ち | モデル A/E | 市場 A/E | 年（同じ向き） | 判定 |")
    pr("|---|---|---:|---:|---:|---:|---|---|")
    hints = []
    for (k, v), a in sorted(acc.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n, w, sp, sq, yr = a
        if n < A.min or sp <= 0:
            continue
        aem, aeq = w / sp, w / sq
        # 2項近似の標準誤差（ポアソン）
        se = math.sqrt(max(sp, 1e-9)) / sp
        z = (aem - 1) / se
        same = sum(1 for b in yr.values() if b[1] > 0 and (b[0] / b[1] - 1) * (aem - 1) > 0)
        flag = ""
        if abs(z) >= 2.5 and same >= max(5, int(0.75 * len(yr))) and abs(aem - 1) > abs(aeq - 1):
            flag = "🔴直しどころ候補"
            hints.append((k, v, n, w, aem, aeq, same, len(yr), z))
        elif abs(z) >= 2:
            flag = "注意"
        pr(f"| {k} | {v} | {n:,} | {w:,} | {aem:.3f} | {aeq:.3f} | {same}/{len(yr)} | {flag} |")
    pr("\n## 直しどころ候補（|z|≥2.5・4分の3以上の年で同じ向き・市場より外れが大きい）\n")
    for k, v, n, w, aem, aeq, same, ny, z in sorted(hints, key=lambda h: -abs(h[8])):
        pr(f"- {k}＝{v}: {n:,}頭・勝ち{w:,}／モデル A/E {aem:.3f}（市場 {aeq:.3f}）・{same}/{ny}年・z={z:+.1f}")
    if not hints:
        pr("- なし")
    text = "\n".join(L)
    out = HERE.parents[1] / "docs" / "keiba_calib_audit.md"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n保存: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=300)
    main(ap.parse_args())
