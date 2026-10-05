# -*- coding: utf-8 -*-
"""
engine_fix_audit.py — 旧エンジンの指数に残る2つの問題を「直したら成績が変わるか」で測る（2026-10-02）
================================================================================================
問題1  F02タイム指数: ±200mの過去走の最速時計を「今回距離×61秒/km＋3秒」と比べている。
        芝の時計はこの基準より常に速いので100点に張り付き、別距離の時計も補正なしで比べている。
問題2  F06枠バイアス表・F07馬番内外: 競馬場ごとの固定表（54〜76点）。実測と合わないコースがある。

旧エンジン（総合指数＝独自指数55%＋ML能力45%）は前向き検証中なので、直す価値があるかを先に測る。
評価に使うのは **レース前に作られた records だけ**（index_audit_leakfree と同じ素性判定）。

  V0 現行
  V1 F02 を作り直したタイム指数に差し替え（基準タイム＝そのレースより前の同条件の中央値。馬の値＝直近3走の最良）
  V2 F06・F07 を中立（全馬同点）にする
  V3 V1＋V2
を作り、①◎（総合指数1位）の 1着率・3着内率・単勝回収 ②同じレースでの差（ブートストラップ）
③各因子が「同じ人気の馬」より走るか（実測÷期待）を出す。
使い方: python engine_fix_audit.py
"""
from __future__ import annotations
import collections, datetime, json, math, random, statistics, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
DB = BASE / "daily_pdca" / "db"
sys.path.insert(0, str(BASE / "daily_pdca"))
from config import WEIGHTS

KEY = {"F01_後3F": "後3F能力", "F02_タイム": "タイム指数", "F03_着差": "着差スコア", "F04_騎手": "騎手",
       "F05_厩舎": "厩舎", "F06_枠": "枠バイアス", "F07_馬番": "馬番内外", "F08_距離": "距離適性",
       "F09_体重": "馬体重変化", "F10_斤量": "斤量", "F11_性別": "性別", "F12_年齢": "年齢",
       "F13_クラス": "クラス", "F14_馬場": "馬場適性", "F15_EV": "EV", "F16_乖離": "人気乖離", "F17_頭数": "頭数影響"}


def sec(t):
    s = str(t or "")
    try:
        if ":" in s:
            m, r = s.split(":", 1)
            return int(m) * 60 + float(r)
        return float(s)
    except ValueError:
        return None


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "").strip()
    return int(s) if s.isdigit() else None


def cond(r):
    d = str(r.get("距離") or "")
    return ("芝" if d.startswith("芝") else "ダ", "".join(c for c in d if c.isdigit()),
            "良" if str(r.get("馬場状態") or "良")[:1] == "良" else "道悪")


# ── 蓄積DB ──────────────────────────────────────────────────────────
rows = [r for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8")) if not str(r.get("距離") or "").startswith("障")]
by_race = collections.defaultdict(dict)
by_horse = collections.defaultdict(list)
pop_rate = collections.defaultdict(lambda: [0, 0])
for r in rows:
    f = fin(r)
    try:
        by_race[(r["date"], r["競馬場"], int(float(r["R"])))][int(float(r["馬番"]))] = r
        p = int(float(r["人気"]))
    except (TypeError, ValueError, KeyError):
        continue
    if f:
        pop_rate[p][0] += 1
        pop_rate[p][1] += f <= 3
    t = sec(r.get("タイム"))
    if r.get("馬名") and t and f:
        by_horse[r["馬名"]].append((r["date"], cond(r), t))
EXP = {p: v[1] / v[0] for p, v in pop_rate.items() if v[0] >= 50}
for v in by_horse.values():
    v.sort()

_base_cache = {}


def baselines(date):
    """その日より前のレースだけで作る基準タイム（条件ごとの中央値。件数が少なければ馬場を無視）"""
    if date not in _base_cache:
        full, loose = collections.defaultdict(list), collections.defaultdict(list)
        for r in rows:
            t = sec(r.get("タイム"))
            if r["date"] < date and t and fin(r):
                c = cond(r)
                full[c].append(t)
                loose[c[:2]].append(t)
        _base_cache[date] = ({k: statistics.median(v) for k, v in full.items() if len(v) >= 30},
                             {k: statistics.median(v) for k, v in loose.items() if len(v) >= 30})
    return _base_cache[date]


def new_f02(name, date, surface):
    """作り直したタイム指数: 同じ芝ダの直近3走について（基準−時計）/基準 を取り、最良の値。1%速い＝+12.5点"""
    full, loose = baselines(date)
    figs = []
    for d, c, t in [x for x in by_horse.get(name, []) if x[0] < date and x[1][0] == surface][-3:]:
        b = full.get(c) or loose.get(c[:2])
        if b:
            figs.append((b - t) / b * 100.0)
    return min(100.0, max(0.0, 50.0 + max(figs) * 12.5)) if figs else 50.0


# ── レース前records ─────────────────────────────────────────────────
pre = {}
for f in sorted(BASE.glob("**/週末ビッグデータ_*_records.json")):
    try:
        rs = json.load(open(f, encoding="utf-8")).get("records", [])
    except Exception:
        continue
    if not rs:
        continue
    last = max(r["date"] for r in rs)
    if datetime.datetime.fromtimestamp(f.stat().st_mtime).date() > datetime.date(int(last[:4]), int(last[4:6]), int(last[6:8])):
        continue
    for r in rs:
        pre.setdefault((r["date"], r["競馬場"], int(r["R"])), {})[int(float(r["馬番"]))] = r

races, err = [], []
for k, horses in sorted(pre.items()):
    res = by_race.get(k)
    if not res or len(horses) < 8:
        continue
    surface = "芝" if str(next(iter(horses.values())).get("距離", "")).startswith("芝") else "ダ"
    js = []
    for u, p in horses.items():
        q = res.get(u)
        if not q or not fin(q) or q.get("馬名") != p.get("馬名"):
            continue
        try:
            F = {f: float(p[f]) for f in KEY}
            dok = sum(F[f] * WEIGHTS[KEY[f]] for f in KEY)
            err.append(abs(dok - float(p["独自指数"])))
            ml = min(100.0, float(p["ML能力%"]) * 2.5)
            n02 = new_f02(p["馬名"], k[0], surface)
            mid07 = F["F07_馬番"]                     # 中立値はレース内の平均にする（下で入れる）
            js.append(dict(F=F, ml=ml, n02=n02, sogo=float(p["総合指数"]), pop=int(float(q["人気"])), odds=float(q["単勝オッズ"]), fin=fin(q),
                           surface=surface))
        except (TypeError, ValueError, KeyError):
            continue
    if len(js) < 8:
        continue
    m06 = sum(h["F"]["F06_枠"] for h in js) / len(js)
    m07 = sum(h["F"]["F07_馬番"] for h in js) / len(js)
    for h in js:
        def total(over):
            # 保存されている総合指数（本番の値そのもの）に、差し替えた因子の差分だけを足す。
            # 独自指数には因子の加重和のほかに後段の補正が乗っているため、加重和から作り直すと本番の◎とずれる
            return h["sogo"] + 0.55 * sum((v - h["F"][f]) * WEIGHTS[KEY[f]] for f, v in over.items())
        h["V0"] = total({})
        h["V1"] = total({"F02_タイム": h["n02"]})
        h["V2"] = total({"F06_枠": m06, "F07_馬番": m07})
        h["V3"] = total({"F02_タイム": h["n02"], "F06_枠": m06, "F07_馬番": m07})
    races.append(js)

N = len(races)
print(f"■ レース前records {N}レース / {sum(len(r) for r in races):,}頭  （独自指数の再現誤差 中央値 {statistics.median(err):.2f}点）")

# ── 現行F02の中身 ───────────────────────────────────────────────────
print("\n■ 現行のF02タイム指数は何点が付いているか")
for s in ("芝", "ダ"):
    v = [h["F"]["F02_タイム"] for r in races for h in r if h["surface"] == s]
    print(f"  {s}: 100点 {sum(1 for x in v if x >= 99.9)/len(v)*100:4.1f}% ／ 50点（該当走なし） {sum(1 for x in v if abs(x-50) < 0.05)/len(v)*100:4.1f}%"
          f" ／ 0点 {sum(1 for x in v if x <= 0.05)/len(v)*100:4.1f}% ／ その他 {sum(1 for x in v if 0.05 < x < 99.9 and abs(x-50) >= 0.05)/len(v)*100:4.1f}%  (n={len(v):,})")
v = [h["n02"] for r in races for h in r]
print(f"  作り直した指数: 50点（過去走なし） {sum(1 for x in v if abs(x-50) < 1e-9)/len(v)*100:.1f}% ／ 0か100に張り付き {sum(1 for x in v if x in (0.0, 100.0))/len(v)*100:.1f}%"
      f" ／ 四分位 {sorted(v)[len(v)//4]:.0f}〜{sorted(v)[len(v)*3//4]:.0f}点")


def pick(r, key):
    return max(r, key=lambda h: h[key])


def stat(ps):
    n = len(ps)
    return (sum(1 for h in ps if h["fin"] == 1) / n * 100, sum(1 for h in ps if h["fin"] <= 3) / n * 100,
            sum(h["odds"] for h in ps if h["fin"] == 1) / n * 100, sum(h["pop"] for h in ps) / n)


print("\n■ ① ◎（総合指数1位）の成績")
print(f"{'版':<26}{'1着率':>7}{'3着内':>8}{'単勝回収':>9}{'平均人気':>8}{'◎が変わる':>10}")
LAB = {"V0": "V0 現行", "V1": "V1 タイム指数を作り直す", "V2": "V2 枠・馬番を中立にする", "V3": "V3 両方"}
base = [pick(r, "V0") for r in races]
for v in LAB:
    ps = [pick(r, v) for r in races]
    w, p3, roi, ap = stat(ps)
    print(f"{LAB[v]:<22}{w:>7.1f}%{p3:>7.1f}%{roi:>8.1f}%{ap:>8.2f}{sum(1 for a, b in zip(base, ps) if a is not b):>8}R")
w, p3, roi, ap = stat([min(r, key=lambda h: h["pop"]) for r in races])
print(f"{'（参考）市場1番人気':<20}{w:>7.1f}%{p3:>7.1f}%{roi:>8.1f}%{ap:>8.2f}")

print("\n■ ② 現行との差（同じレースで比較・95%区間）")
rng = random.Random(1)
for v in ("V1", "V2", "V3"):
    ps = [pick(r, v) for r in races]
    d3 = [(b.get("fin") <= 3) - (a.get("fin") <= 3) for a, b in zip(base, ps)]
    dr = [(b["odds"] if b["fin"] == 1 else 0) - (a["odds"] if a["fin"] == 1 else 0) for a, b in zip(base, ps)]
    out = []
    for d in (d3, dr):
        xs = sorted(sum(d[rng.randrange(N)] for _ in range(N)) / N * 100 for _ in range(4000))
        out.append((sum(d) / N * 100, xs[100], xs[3900]))
    print(f"  {LAB[v]:<22} 3着内 {out[0][0]:+5.1f}pt［{out[0][1]:+5.1f}, {out[0][2]:+5.1f}］  単勝回収 {out[1][0]:+6.1f}pt［{out[1][1]:+6.1f}, {out[1][2]:+6.1f}］")

print("\n■ ③ 因子そのものは「同じ人気の馬」より走るか（レース内で上位1/3の馬・実測÷期待）")


def factor_test(label, val):
    obs = exp = n = 0
    halves = [[0, 0.0], [0, 0.0]]
    for i, r in enumerate(races):
        vs = sorted((val(h) for h in r), reverse=True)
        if vs[0] == vs[-1]:
            continue
        cut = vs[max(0, len(r) // 3 - 1)]
        for h in r:
            if val(h) >= cut and val(h) > vs[-1] and h["pop"] in EXP:
                n += 1
                obs += h["fin"] <= 3
                exp += EXP[h["pop"]]
                halves[i >= N // 2][0] += h["fin"] <= 3
                halves[i >= N // 2][1] += EXP[h["pop"]]
    var = exp * (1 - exp / n) if n else 1
    z = (obs - exp) / math.sqrt(var) if var > 0 else 0
    print(f"  {label:<22} n={n:>5,}  3着内 実測{obs:>5} / 期待{exp:>7.1f} ＝ {obs/exp:.3f}倍  z={z:+.2f}"
          f"  （前半 {halves[0][0]/halves[0][1]:.3f}倍 ／ 後半 {halves[1][0]/halves[1][1]:.3f}倍）")


factor_test("現行F02タイム指数", lambda h: h["F"]["F02_タイム"])
factor_test("作り直したタイム指数", lambda h: h["n02"])
factor_test("現行F06枠バイアス表", lambda h: h["F"]["F06_枠"])
factor_test("現行F07馬番内外", lambda h: h["F"]["F07_馬番"])
print("  ※ |z|が2未満、または前半と後半で向きが変わるものは「市場に無い情報を持っていない」")
