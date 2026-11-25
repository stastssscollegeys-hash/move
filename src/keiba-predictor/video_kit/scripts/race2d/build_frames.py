# -*- coding: utf-8 -*-
"""race2d の JSON（from_jvlink.py などの出力）から、動画の毎フレームの馬の位置・カメラ・順位を作る（2026-11-19）
使い方: python build_frames.py <race2d.json> <出力 frames.json> [--w 1080 --h 1652 --fps 30]

決め方（データどおりの所と推定の所）:
  先頭の進み方   … ラップ（先頭の馬の200mごと）＝データどおり
  各馬の遅れ（秒）… 残り600m＝走破タイム−上がり3F の差、ゴール＝走破タイムの差＝データどおり
                    3コーナー＝3角の順位に、残り600m の遅れの並びを当てはめる（推定）
                    スタート〜3コーナーの手前＝0 から3コーナーの遅れへなめらかにつなぐ（推定）
  内か外か       … データに無い。すぐ前（約1.2馬身以内）に馬がいるときだけ外へずらす（推定）
  動画の時間     … 残り600m までは速回し（既定10倍）、そこからゴールまでは5倍、勝った馬のゴールの直後で止めて2秒
"""
import json, math, sys, argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEN = 2.4            # 1馬身（m）
LANE = 3.0           # 横の1列の幅（m）。図で丸が重ならない幅（本物の馬の幅より広め）
START_RUN = 100      # スタートからこの距離（m）はゲートの並びのまま走らせる（2026-11-20・重なりの多くがスタート直後だった）
INWARD_UNTIL = 500   # 直線の入口からこの距離（m）より手前だけ、内へ寄ってよい（3〜4コーナーで内へ潜らせない・2026-11-20）
PATH_HOLD = 2.0      # 内へ1頭分寄ったあと、次に寄るまで待つ秒（レースの時間）。ふらつき止め（2026-11-20）
LAT_V = 4.0          # 横に動く速さの上限（m/秒・レースの時間）。2026-11-20 これが無くて馬が1コマ最大1.8m 横に滑っていた。2.5・4・6 を比べて、横滑りと重なりがどちらも前より減る 4（福島記念：重なり 688→554）
RAIL = 1.6           # 内ラチから1列目の中心まで（m）
STYLE_JA = {1: "逃げ", 2: "先行", 3: "差し", 4: "追込"}


def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


class Course:
    """直線2本＋半円2つ。右の直線を上へ走ってゴール（左回り）。u＝ゴールまでの残り距離"""
    def __init__(self, c):
        self.dir = -1 if c.get("turn") == "right" else 1   # 2026-11-20 右回りは左右を映した形（x→−x）
        self.L = c["straight"]; self.home = c["home"]; self.w = c["track_w"]
        self.R = (c["lap"] - 2 * self.L) / (2 * math.pi)
        self.fin_y = self.home
        self.arc = math.pi * self.R

    def at(self, u, lane=0.0):
        """残り u（m）・内ラチからの距離 lane（m）→ (x, y, 進む向きの角度)。右回りは左回りの形を左右に映す"""
        x, y, h = self._at(u, lane)
        return (x, y, h) if self.dir > 0 else (-x, y, math.pi - h)

    def _at(self, u, lane=0.0):
        R, L, d = self.R, self.L, RAIL + lane
        if u < 0:                                  # ゴールの先（右の直線をさらに上へ）
            return (R + d, self.fin_y - u, math.pi / 2)
        if u <= self.home:                         # 最後の直線
            return (R + d, self.fin_y - u, math.pi / 2)
        u2 = u - self.home
        if u2 <= self.arc:                         # 3〜4コーナー（下の半円）。中心 (0,0)
            a = 2 * math.pi - u2 / R               # ゴール側から戻る
            return ((R + d) * math.cos(a), (R + d) * math.sin(a), a + math.pi / 2)
        u3 = u2 - self.arc
        # 向こう正面（左の直線・下へ走る）。長い距離は上へまっすぐ延ばす（引き込み線）
        return (-(R + d), u3, -math.pi / 2)

    def corner_name(self, u):
        if u <= 0: return "ゴール"
        if u <= self.home: return "最後の直線"
        if self.straight_only: return "直線"
        u2 = u - self.home
        if u2 <= self.arc / 2: return "4コーナー"
        if u2 <= self.arc: return "3コーナー"
        return "向こう正面"

    def rails(self, lane, u_max):
        pts, u = [], -60.0
        while u <= u_max:
            x, y, _ = self.at(u, lane); pts.append([round(x, 1), round(y, 1)]); u += 6
        return pts


def synth_shape(venue, cs):
    """地図にコースの線が無い・足りない競馬場（2026-11-20 函館）：courses.json の公式の1周から、直線2本と半円2つの輪を作る
    同じ競馬場の輪は中心をそろえ、直線の長さも同じ（＝内側から ダート→芝→芝外 と入れ子になる）。ゴール前の直線は北（上）"""
    cfgs = {k: v for k, v in cs.items() if not k.startswith("_") and v.get("shape") == venue}
    S = max(v["home"] for v in cfgs.values()) + 40
    loops = {}
    for v in cfgs.values():
        R = max(30.0, (v["lap"] - 2 * S) / (2 * math.pi)); pts = []
        for k in range(400):
            t = k / 400 * v["lap"]                          # 反時計回り：北の直線（右→左）→ 西の半円 → 南の直線 → 東の半円
            arc = math.pi * R
            if t < S: pts.append([S / 2 - t, R])
            elif t < S + arc: a = math.pi / 2 + (t - S) / R; pts.append([-S / 2 + R * math.cos(a), R * math.sin(a)])
            elif t < 2 * S + arc: pts.append([-S / 2 + (t - S - arc), -R])
            else: a = -math.pi / 2 + (t - 2 * S - arc) / R; pts.append([S / 2 + R * math.cos(a), R * math.sin(a)])
        loops[v["loop"]] = pts
    return dict(name=venue, credit="", loops=loops, synthetic=True)


def load_shape(cfg, cs):
    """形のデータ：地図（courses/<場>.json）にその輪があれば地図、無ければ公式の1周から作った形（synth_shape）"""
    f = HERE / "courses" / f"{cfg['shape']}.json"
    g = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    need = {v["loop"] for k, v in cs.items() if not k.startswith("_") and v.get("shape") == cfg["shape"]}
    have = {k: v for k, v in (g or {}).get("loops", {}).items() if k != "その他"}
    if g and need <= set(have):
        return g
    if g and have:
        # 2026-11-20 一部の輪だけ地図にある（京都の外回りなど）：足りない輪は、1周の長さがいちばん近い実物の輪を使う
        #   ShapeCourse._prep が公式の1周に合わせて大きさを変える（中心＝競馬場の中心）＝実物の形の特徴を残したまま入れ子になる
        laps = {v["loop"]: v["lap"] for k, v in cs.items() if not k.startswith("_") and v.get("shape") == cfg["shape"]}
        g = dict(g); g["loops"] = dict(g["loops"]); g["derived"] = []
        for lp in sorted(need - set(have)):
            src = min(have, key=lambda k: abs(laps.get(k, 0) - laps[lp]))
            g["loops"][lp] = have[src]; g["derived"].append(f"{lp}←{src}")
        return g
    return synth_shape(cfg["shape"], cs)


class ShapeCourse:
    """実物の形（courses/<競馬場>.json・OpenStreetMap）。輪の線＝内ラチとみなす。左回り。u＝ゴールまでの残り距離（m）
    ゴール前の直線＝輪の中のまっすぐな所のうち home_side（north など）にあるもの。その始まり（4コーナーの出口）から home m でゴール
    引き込み線（chute の距離）＝向こう正面の直線を、そのまま後ろへ延ばした線（本物の角度とは少しずれる）
    画面の向き：縦（tall）＝ゴール前の直線が上へ向かう／横＝左から右へ（スタンドから見た向き）"""
    STEP = 1.0

    def __init__(self, c, D, tall, g):
        self.credit = g.get("credit", "")
        self.home, self.w, self.lap = c["home"], c["track_w"], c["lap"]
        self.dir = -1 if c.get("turn") == "right" else 1                # 2026-11-20 右回り（時計回り）に対応。外ラチ側＝左回りは進む向きの右・右回りは左
        self.chute = D in c.get("chute", [])
        self.straight_only = bool(c.get("straight_only"))                # 2026-11-20 新潟の直線1000m：ゴール前の直線を後ろへまっすぐ延ばす
        pts = self._prep(g["loops"][c["loop"]], c["lap"], self.dir)
        self.P = pts; N = self.N = len(pts)
        hd = [math.atan2(pts[(i + 1) % N][1] - pts[i - 1][1], pts[(i + 1) % N][0] - pts[i - 1][0]) for i in range(N)]
        self.hd = hd
        def turn(i, w=12):
            d = hd[(i + w) % N] - hd[i - w]
            return abs((d + math.pi) % (2 * math.pi) - math.pi)
        straight = [turn(i) < math.radians(2.5) for i in range(N)]
        runs, i0 = [], None                     # まっすぐな所のまとまり（輪の切れ目をまたぐものもつなぐ）
        k0 = next(i for i in range(N) if not straight[i])
        for j in range(N + 1):
            i = (k0 + j) % N
            if straight[i] and i0 is None: i0 = i
            if (not straight[i] or j == N) and i0 is not None:
                runs.append((i0, (i - 1) % N)); i0 = None
        rl = lambda r: (r[1] - r[0]) % N + 1
        runs = [r for r in runs if rl(r) > 150]
        side = c.get("home_side", "auto" if g.get("stand") else "north")
        if side == "auto" and not g.get("stand"): side = "north"          # 作った形（synth_shape）はゴール前の直線が北
        if side == "auto":      # 2026-11-20 ゴール前の直線＝スタンド（地図のいちばん大きい建物）にいちばん近い直線
            sx, sy = g["stand"][0] * self._sc, g["stand"][1] * self._sc
            mid = lambda r: pts[(r[0] + rl(r) // 2) % N]
            home_run = min(runs, key=lambda r: math.dist(mid(r), (sx, sy)))
            back_run = max(runs, key=lambda r: math.dist(mid(r), (sx, sy)))
        key = {"north": lambda r: pts[(r[0] + rl(r) // 2) % N][1], "south": lambda r: -pts[(r[0] + rl(r) // 2) % N][1],
               "east": lambda r: pts[(r[0] + rl(r) // 2) % N][0], "west": lambda r: -pts[(r[0] + rl(r) // 2) % N][0]}.get(side)
        if side != "auto":
            home_run = max(runs, key=key); back_run = min(runs, key=key)
        self.fi = (home_run[0] + int(self.home / self.STEP)) % N        # ゴール
        self.u_curve_end = self.home                                     # 4コーナーの出口
        self.u_back_end = ((self.fi - back_run[1]) % N) * self.STEP      # 向こう正面の終わり（3コーナーの入口）
        self.u_back_start = ((self.fi - back_run[0]) % N) * self.STEP    # 向こう正面の始まり
        hx, hy = math.cos(hd[home_run[0] + 5]), math.sin(hd[home_run[0] + 5])
        want = math.pi / 2 if tall else (0.0 if self.dir > 0 else math.pi)   # 横＝スタンドから見た向き（左回りは左→右・右回りは右→左）
        self.rot = want - math.atan2(hy, hx)

    def _prep(self, raw, lap, d=1):
        if raw[0] == raw[-1]: raw = raw[:-1]
        A = sum(raw[i][0] * raw[(i + 1) % len(raw)][1] - raw[(i + 1) % len(raw)][0] * raw[i][1] for i in range(len(raw)))
        if A * d < 0: raw = raw[::-1]                                    # 左回り＝反時計回り・右回り＝時計回りにそろえる
        L = sum(math.dist(raw[i], raw[(i + 1) % len(raw)]) for i in range(len(raw)))
        sc = lap / L                                                     # 公式の1周にそろえる
        self._sc = sc
        raw = [[x * sc, y * sc] for x, y in raw]
        out, n = [], int(lap / self.STEP)
        seg = [math.dist(raw[i], raw[(i + 1) % len(raw)]) for i in range(len(raw))]
        i, acc = 0, 0.0
        for k in range(n):
            t = k * lap / n
            while acc + seg[i] < t: acc += seg[i]; i = (i + 1) % len(raw)
            f = (t - acc) / seg[i] if seg[i] else 0
            a, b = raw[i], raw[(i + 1) % len(raw)]
            out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f])
        for _ in range(3):                                               # 地図の線の角ばりをならす
            out = [[sum(out[(i + j) % n][0] for j in range(-7, 8)) / 15, sum(out[(i + j) % n][1] for j in range(-7, 8)) / 15] for i in range(n)]
        # 2026-11-20 角ばった線（札幌のダート）はならすと 1.8% 縮んだ → 0.5% を超えて縮んだら公式の1周に合わせ直す（東京は 0.1% なので今までどおり）
        L2 = sum(math.dist(out[i], out[(i + 1) % n]) for i in range(n))
        if abs(L2 - lap) > lap * 0.005:
            k2 = lap / L2; out = [[x * k2, y * k2] for x, y in out]; self._sc = getattr(self, "_sc", 1.0) * k2
        return out

    def _r(self, x, y):
        c, s = math.cos(self.rot), math.sin(self.rot)
        return (x * c - y * s, x * s + y * c)

    def at(self, u, lane=0.0):
        d = RAIL + lane
        if self.straight_only and u > self.home:                         # 直線のコース：4コーナーの出口から後ろへまっすぐ
            i = (self.fi - int(self.home / self.STEP)) % self.N
            h = self.hd[(i + 3) % self.N]; e = u - self.home
            x, y = self.P[i][0] - math.cos(h) * e, self.P[i][1] - math.sin(h) * e
            nx, ny = self.dir * math.sin(h), -self.dir * math.cos(h)
            X, Y = self._r(x + nx * d, y + ny * d)
            return (X, Y, h + self.rot)
        if self.chute and u > self.u_back_start:                         # 引き込み線
            i = (self.fi - int(self.u_back_start / self.STEP)) % self.N
            h = self.hd[(i + 3) % self.N]; e = u - self.u_back_start
            x, y = self.P[i][0] - math.cos(h) * e, self.P[i][1] - math.sin(h) * e
        else:
            fidx = self.fi - u / self.STEP
            i = int(math.floor(fidx)); f = fidx - i
            a, b = self.P[i % self.N], self.P[(i + 1) % self.N]
            x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            h = self.hd[i % self.N]
        nx, ny = self.dir * math.sin(h), -self.dir * math.cos(h)         # 外ラチ側（左回り＝進む向きの右・右回り＝左）
        X, Y = self._r(x + nx * d, y + ny * d)
        return (X, Y, h + self.rot)

    def corner_name(self, u):
        if u <= 0: return "ゴール"
        if u <= self.home: return "最後の直線"
        if u <= self.u_back_end:
            return "4コーナー" if u <= (self.home + self.u_back_end) / 2 else "3コーナー"
        if u <= self.u_back_start or self.chute: return "向こう正面"
        return "2コーナー"

    def ring(self, lane, step=6):
        """1周の線（描く用）"""
        out = []
        for k in range(0, self.N, step):
            h = self.hd[k]; x, y = self.P[k]
            nx, ny = self.dir * math.sin(h), -self.dir * math.cos(h)
            X, Y = self._r(x + nx * lane, y + ny * lane); out.append([round(X, 1), round(Y, 1)])
        return out

    def other_ring(self, raw, lane, lap, step=6):
        tmp = ShapeCourse.__new__(ShapeCourse); tmp.STEP = 1.0
        P = tmp._prep(raw, lap, self.dir); N = len(P); out = []
        for k in range(0, N, step):
            a, b = P[k - 1], P[(k + 1) % N]; h = math.atan2(b[1] - a[1], b[0] - a[0])
            X, Y = self._r(P[k][0] + self.dir * math.sin(h) * lane, P[k][1] - self.dir * math.cos(h) * lane); out.append([round(X, 1), round(Y, 1)])
        return out

    def shapes(self, D, g, c_all):
        """描く形：芝の帯・ダートの帯・内馬場・引き込み線"""
        sh = {}
        for kind, cfg in c_all.items():
            if not kind.startswith(g["name"] + "_") or cfg.get("shape") != g["name"]: continue
            loop = g["loops"].get(cfg["loop"])
            if not loop: continue
            sh[cfg["loop"]] = [self.other_ring(loop, -1.0, cfg["lap"]), self.other_ring(loop, cfg["track_w"], cfg["lap"])]
        if self.straight_only:      # 直線のコースの延ばした所（芝の帯）
            a1 = self.at(self.home - 20, -1.0); a2 = self.at(D + 40, -1.0)
            b2 = self.at(D + 40, self.w); b1 = self.at(self.home - 20, self.w)
            sh["芝直線"] = [[round(p[0], 1), round(p[1], 1)] for p in (a1, a2, b2, b1)]
        if self.chute:
            a1 = self.at(self.u_back_start - 20, -1.0); a2 = self.at(D + 40, -1.0)
            b2 = self.at(D + 40, self.w); b1 = self.at(self.u_back_start - 20, self.w)
            sh["chute"] = [[round(p[0], 1), round(p[1], 1)] for p in (a1, a2, b2, b1)]
        return sh


def interp(x, xs, ys):
    if x <= xs[0]: return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1]) if xs[i] > xs[i - 1] else 1
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1652)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--note", default="", help="画面の下の注記（予想の着順のとき）。印を出す前の版は「独自指数の評価・脚質…」などに差し替える")
    ap.add_argument("--fast", type=float, default=10.0); ap.add_argument("--slow", type=float, default=5.0)
    # 2026-11-20 ユーザー「最後の展開がどうやって最終画面に変わったか分からない」「最後まで丁寧に展開を入れられないのかな」
    #   → 予想の着順（mode＝prediction）だけ、残り --final-m からは --final 倍（既定1.5倍）に落とし、カメラは印の馬を追う
    ap.add_argument("--final", type=float, default=1.5); ap.add_argument("--final-m", type=float, default=300.0)
    a = ap.parse_args(); NOTE_ARG = a.note
    data = json.loads(Path(a.src).read_text(encoding="utf-8"))
    race, horses = data["race"], data["horses"]
    D = race["distance"]
    cs = json.loads((HERE / "courses.json").read_text(encoding="utf-8"))
    if race["course"] not in cs:
        sys.exit(f"courses.json に {race['course']} がありません（コースの形を足してください）")
    cfg = cs[race["course"]]
    shape_g = None
    if cfg.get("shape"):
        shape_g = load_shape(cfg, cs)
        C = ShapeCourse(cfg, D, a.h > a.w, shape_g)
    else:
        C = Course(cfg)                                   # 形のデータが無い競馬場は、直線2本と半円2つで描く

    # 先頭の進み方 τ(s)：s＝スタートからの距離
    laps = race["laps"]; n = len(laps)
    seg = [D - 200 * (n - 1)] + [200] * (n - 1)
    S, Tt = [0.0], [0.0]
    for l, t in zip(seg, laps):
        S.append(S[-1] + l); Tt.append(Tt[-1] + t)
    tau = lambda s: interp(s, S, Tt)
    lead_T = Tt[-1]

    s3, s6 = D - min(830, D * 0.6), D - 600
    forecast = data.get("mode") == "forecast"
    if forecast:
        # 展開予想：脚質の順（逃げ→先行→差し→追い込み・同じ脚質は内の馬番から）に並べ、同じ脚質の中は1馬身、脚質が替わると2.5馬身あける
        #   3コーナーの隊列をそのまま、4コーナーで少し詰める（0.75倍）。直線の入口で止める（結果は描かない）
        v = 200 / (sum(laps) / len(laps))
        rows = sorted(horses, key=lambda h: (h.get("style") or 3, h["umaban"]))
        g, prev = 0.0, None
        for k, h in enumerate(rows):
            st = h.get("style") or 3
            if k: g += LEN * (1.0 if st == prev else 2.5)
            prev = st
            h["g3"] = g / v; h["g6"] = g * 0.75 / v; h["gF"] = h["g6"]
            h["time"] = lead_T + h["gF"]; h["last3f"] = None
        live = rows
    else:
        live = [h for h in horses if h.get("time")]
    for h in live if not forecast else []:
        h["g6"] = (h["time"] - h["last3f"]) - tau(s6) if h.get("last3f") else h["time"] - lead_T
        h["gF"] = h["time"] - lead_T
    # 3コーナー：3角（無ければ4角）の順位に、残り600m の遅れの並びを当てはめる。同じ順位（併走）は平均
    g6s = sorted(h["g6"] for h in live)
    key = lambda h: (h["corners"].get("3c") or h["corners"].get("4c") or 99, h["g6"])
    order3 = [] if forecast else sorted(live, key=key)
    i = 0
    while i < len(order3):
        j = i
        r = order3[i]["corners"].get("3c") or order3[i]["corners"].get("4c")
        while j + 1 < len(order3) and (order3[j + 1]["corners"].get("3c") or order3[j + 1]["corners"].get("4c")) == r and r:
            j += 1
        v = sum(g6s[i:j + 1]) / (j - i + 1)
        for k in range(i, j + 1): order3[k]["g3"] = v
        i = j + 1
    base = min(h["g3"] for h in live)
    for h in live: h["g3"] -= base           # 3コーナーの先頭は遅れ0
    early = min(400.0, s3 * 0.7)

    def gap(h, s):
        if s <= s3: return h["g3"] * smooth(s / early)
        if s <= s6: return h["g3"] + (h["g6"] - h["g3"]) * (s - s3) / (s6 - s3)
        return h["g6"] + (h["gF"] - h["g6"]) * min(1.0, (s - s6) / 600)

    grid = [x * 2.0 for x in range(int(D / 2) + 1)]
    for h in live:
        h["_ts"] = [tau(s) + gap(h, s) for s in grid]
        for k in range(1, len(h["_ts"])):     # 前に進むだけ（時間は増えるだけ）にそろえる
            if h["_ts"][k] <= h["_ts"][k - 1]: h["_ts"][k] = h["_ts"][k - 1] + 1e-3
        h["_v"] = 200 / laps[-1]              # ゴールのあとの速さ

    def pos_s(h, t):
        if t <= 0: return 0.0
        if t >= h["_ts"][-1]: return D + (t - h["_ts"][-1]) * h["_v"] * 0.8
        return interp(t, h["_ts"], grid)

    # 動画の時間 → レースの時間
    t6 = tau(s6); t_end = lead_T + 0.25                 # 勝った馬がゴールした直後で、レースの時間ごと止める（ゴールの瞬間の差のまま）
    if forecast:
        t_end = tau(D - C.home) + 0.5                  # 先頭が直線に入ったところまで
    intro, outro = 1.0, 2.0
    pred_mode = data.get("mode") == "prediction"
    marked = set((data.get("prediction") or {}).get("order") or []) | {h["umaban"] for h in live if h.get("mark")}
    tF = t_end
    if pred_mode and a.final > 0 and a.final_m > 0:
        tF = max(t6, min(t_end, tau(D - a.final_m)))        # 先頭が残り final_m に来たレースの時間（ここから --final 倍）
    v1 = t6 / a.fast; v2 = (tF - t6) / a.slow; v3 = (t_end - tF) / a.final if tF < t_end else 0.0
    total = intro + v1 + v2 + v3 + outro
    nf = int(total * a.fps)

    def race_t(vt):
        if vt <= intro: return 0.0
        vt -= intro
        if vt <= v1: return vt * a.fast
        vt -= v1
        if vt <= v2: return t6 + vt * a.slow
        vt -= v2
        if vt <= v3: return tF + vt * a.final
        return t_end                                                       # 止めたまま（終わったレース＝ゴールの瞬間／予想＝直線の入口）

    W, H = a.w, a.h
    # 図を描く範囲 [左, 上, 幅, 高さ]。縦（ショート）＝上の帯の下に順位と全体図の段、その下がコース。下の2割は字幕と2人のアイコンが重なるので使わない
    #   横（本編）＝左に順位・右に全体図、真ん中がコース
    if H > W:
        top = H * 0.11 + W * 0.36; view = [0, top, W, H * 0.80 - top]
    else:
        top = H * 0.13; view = [W * 0.27, top, W * 0.46, H * 0.80 - top]
    GATE = 1.45 / LANE                                              # ゲートの1枠の幅（約1.45m）を列の数に直した値
    lanes = {h["umaban"]: (h["umaban"] - 1) * GATE for h in live}   # スタートは馬番順にゲートに並ぶ
    MAXL = max(1, int((C.w - RAIL - 1.5) / LANE))                        # 外へ出せるいちばん外の列（コースの幅から。外の柵の外へ出さない・2026-11-20）
    path = {h["umaban"]: min(MAXL, round((h["umaban"] - 1) * GATE)) for h in live}   # 馬ごとの進路（何列目）。保つのが基本
    moved_at = {h["umaban"]: 0.0 for h in live}                          # 進路を最後に変えたレースの時間
    fanned = {h["umaban"]: False for h in live}                          # 直線の手前で外へ出したか
    cam = None
    frames = []
    t_prev = 0.0
    for f in range(nf):
        t = race_t(f / a.fps)
        dt = max(0.0, t - t_prev); t_prev = t
        ss = {h["umaban"]: pos_s(h, t) for h in live}
        order = sorted(live, key=lambda h: (-ss[h["umaban"]], h["umaban"]))
        # 横の位置：前から順に、約1.2馬身以内に馬がいる列は避けて、いちばん内の空いた列へ
        placed, target = [], {}
        for h in order:
            s = ss[h["umaban"]]
            if t <= 0:
                target[h["umaban"]] = (h["umaban"] - 1) * GATE; continue
            # 進路の決め方（2026-11-20）
            #   ① ユーザー「急に移動したり最後の方バグってるところない?」→ 毎コマ「いちばん内の空き」を選び直していて、1コマ最大1.8m 横に滑っていた
            #   ② ユーザー「馬がこんなに内側に行ったり外側に行ったりするのかな?」→ ①の直しでも、近くの空きを毎コマ選び直していて内外にふらついた
            #   → 実際のレースのように【進路を保つ】のを基本にし、横に動くのは次の3つだけ:
            #     ・真ん前（同じ列で1馬身半以内）が詰まった → 外へ1頭分（抜きにいく）
            #     ・直線の手前（残り home+80m）で、差し・追い込みの馬は外へ1頭分出す（1回だけ）
            #     ・3コーナーより前（直線の入口から INWARD_UNTIL m より手前）で、内の列が前も横も長く空いていて、前に動いてから PATH_HOLD 秒たった → 内へ1頭分（ゆっくり寄る）
            #       3〜4コーナーと直線では内へ戻さない（差し・追い込みは外へ出していく。内へ潜ってから外へ出し直す形になっていた・13番 6→2→5列目）
            k = h["umaban"]
            u = D - s
            if s < START_RUN:                                               # 最初の START_RUN m はゲートの並びのまま（隣の2頭を同じ列に丸めて重ねない）
                g = (k - 1) * GATE
                path[k] = min(MAXL, round(g)); placed.append((s, g)); target[k] = g; continue
            L = path[k]
            side_busy = lambda c: c < 0 or c > MAXL or any(abs(s - ps) < LEN * 1.4 and abs(c - pl) < 1 for ps, pl in placed)
            # 自分から列を移るとき（外へ出す・内へ寄る）は、後ろの馬（前のコマの列）も見る。前が詰まって逃げるときは前の馬だけ
            #   （2026-11-20 13番が直線の手前で外へ出した列に、後ろから16番が来ていて、0.5馬身後ろで体が重なったまま走った。
            #     逃げるときまで後ろを見ると、逃げ場が無くなって重なりがかえって増えた＝25→68）
            move_busy = lambda c: side_busy(c) or any(j != k and 0 < s - ss[j] < LEN * 2.5 and abs(c - lanes[j]) < 1 for j in lanes)
            ahead_busy = lambda c, m: any(0 <= ps - s < LEN * m and abs(c - pl) < 1 for ps, pl in placed)
            held = t - moved_at[k] >= PATH_HOLD
            if ahead_busy(L, 1.5) or side_busy(L):
                c = L + 1
                while side_busy(c) or ahead_busy(c, 1.5):
                    c += 1
                    if c > L + 3 or c > MAXL: c = None; break
                if c is None:                                               # 外が詰まっていれば内を突く（重なったまま走らせない）
                    c = next((d for d in (L - 1, L - 2, L - 3) if d >= 0 and not side_busy(d) and not ahead_busy(d, 1.5)), L)
                L = min(c, MAXL)
            elif (h.get("style") or 3) >= 3 and not fanned[k] and u <= C.home + 80:
                fanned[k] = True
                if not move_busy(L + 1) and not ahead_busy(L + 1, 1.5): L += 1
            elif held and u > C.home + INWARD_UNTIL and L > 0 and not move_busy(L - 1) and not ahead_busy(L - 1, 4):
                L -= 1
            if L != path[k]: path[k] = L; moved_at[k] = t
            placed.append((s, L)); target[k] = float(L)
        cap = LAT_V * dt / LANE
        for k in lanes:
            if t <= 0: lanes[k] = target[k]; continue
            lanes[k] += max(-cap, min(cap, (target[k] - lanes[k]) * 0.18))
        pts = {}
        for h in live:
            x, y, _ = C.at(D - ss[h["umaban"]], lanes[h["umaban"]] * LANE)
            pts[h["umaban"]] = (x, y)
        # カメラ：先頭から順に、先頭との差が45m以内の馬を画面に入れる（ばらけたら前の集団を追う）
        lead_s = ss[order[0]["umaban"]]
        grp = [pts[h["umaban"]] for h in order if lead_s - ss[h["umaban"]] < 45] or [pts[order[0]["umaban"]]]
        if pred_mode and marked and t >= tF - 1e-6:        # 最後の直線（予想）は、印の馬と先頭だけを追う＝誰が抜いたかが見える大きさ
            grp = [pts[h["umaban"]] for h in order if h["umaban"] in marked or h is order[0]]
        xs, ys = [p[0] for p in grp], [p[1] for p in grp]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        bw, bh = max(xs) - min(xs) + 22, max(ys) - min(ys) + 22
        sc = min(view[2] * 0.92 / bw, view[3] * 0.92 / bh, view[2] / 30)   # いちばん寄っても横 30m
        sc = max(sc, view[2] / 110)
        # 速回しでもカメラが置いていかれないよう、先頭の馬からのずれだけをなめらかにする
        lx, ly = pts[order[0]["umaban"]]
        if cam is None: rel = [cx - lx, cy - ly]; zs = sc
        else:
            rel = [rel[0] + (cx - lx - rel[0]) * 0.15, rel[1] + (cy - ly - rel[1]) * 0.15]; zs = zs + (sc - zs) * 0.06
        cam = [lx + rel[0], ly + rel[1], zs]
        u_lead = D - lead_s
        phase = "スタート" if t <= 0 else ("ゴール" if u_lead <= 0 else C.corner_name(u_lead))
        if forecast and t >= t_end - 1e-6: phase = "直線へ"
        if phase == "ゴール" and not forecast and all(h.get("finish") for h in live):
            order = sorted(live, key=lambda h: h["finish"])            # ゴールのあとは公式の着順（同じタイムの馬は位置では決まらない）
        if 0 < u_lead <= 600 and phase in ("4コーナー", "3コーナー"): phase = "残り600m"
        frames.append(dict(
            p=[[round(pts[h["umaban"]][0], 2), round(pts[h["umaban"]][1], 2)] for h in live],
            cam=[round(cam[0], 2), round(cam[1], 2), round(cam[2], 3)],
            rank=[h["umaban"] for h in order],
            gap=[round(max(0.0, (lead_s - ss[h["umaban"]]) / LEN), 1) for h in order[:5]],
            lead=[round(x, 1) for x in pts[order[0]["umaban"]]],
            phase=phase, rem=max(0, round(u_lead)),
            rs=round(0.55 + 0.45 * smooth(lead_s / 150), 2)))            # 丸の大きさ（スタート直後はゲートの幅に合わせて小さく）

    u_max = D + 40
    half1 = sum(laps[: n // 2]) if n % 2 == 0 else None
    pace = None
    if half1:
        half2 = lead_T - half1
        diff = half2 - half1
        pace = dict(first=round(half1, 1), second=round(half2, 1),
                    label="ハイペース" if diff >= 1.0 else ("スローペース" if diff <= -1.0 else "平均ペース"))
    marks = []
    for u, label in ((0, "ゴール"), (200, "残り200m"), (400, "残り400m"), (600, "残り600m")):
        x1, y1, _ = C.at(u, -1.0); x2, y2, _ = C.at(u, C.w)
        marks.append(dict(u=u, label=label, a=[round(x1, 1), round(y1, 1)], b=[round(x2, 1), round(y2, 1)]))
    out = dict(
        fps=a.fps, w=W, h=H, frames=len(frames), lane=LANE, view=[round(v) for v in view],
        race=race, pace=pace,
        mode="forecast" if forecast else ("prediction" if data.get("mode") == "prediction" else "result"), forecast=data.get("forecast"),
        final_m=(a.final_m if pred_mode and tF < t_end else None),
        horses=[dict(umaban=h["umaban"], waku=h["waku"], name=h["name"], finish=h.get("finish"),
                     style=STYLE_JA.get(h.get("style") or 0), mark=h.get("mark")) for h in live],
        track=dict(w=C.w, R=round(getattr(C, "R", 0), 1), L=getattr(C, "L", 0), turn="right" if C.dir < 0 else "left",
                   shapes=C.shapes(D, shape_g, cs) if shape_g else None, credit=getattr(C, "credit", ""),
                   # 3D 用：ゴール前の直線の外のスタンドの線（ゴールの先100m〜4コーナーの出口）／ハロン棒（内ラチ）
                   stand=[[round(q[0], 1), round(q[1], 1)] for q in (C.at(u, C.w + 48)[:2] for u in range(-120, int(C.home) + 1, 20))],
                   poles=[dict(u=u, p=[round(q, 1) for q in C.at(u, -1.6)[:2]]) for u in (200, 400, 600, 800, 1000) if u < D],
                   full=dict(start=list(C.at(D, 0)[:2])),
                   marks=marks),
        frame=frames,
        note=("AIの脚質の判定（前走の通過順位）から組んだ予想の隊列です" if forecast else
              (NOTE_ARG or "アスメシの印・脚質・前走の上がりから組んだ着順の予想です（タイムは推定）") if data.get("mode") == "prediction" else
              "3コーナーまでの位置・内外は推定。残り600m とゴールの差はデータどおり"))
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✅ {a.out}  {len(frames)}フレーム（{total:.1f}秒）  ペース {pace['label'] if pace else '—'}  "
          f"先頭の時計 {lead_T:.1f}秒  コース＝{('直線2本と半円2つ（地図に線が無い・公式の1周から）' if shape_g.get('synthetic') else '実物の形（地図）' + ('・足りない輪は近い輪から ' + '・'.join(shape_g['derived']) if shape_g.get('derived') else '')) if shape_g else '直線2本と半円2つ'}")
    if forecast:
        print("   予想の隊列:", " → ".join(f"{h['umaban']}{STYLE_JA.get(h.get('style') or 3)}" for h in live)); return
    fin = sorted(live, key=lambda h: h["gF"])[:3]
    print("   ゴールの差（データ）:", "、".join(f"{h['umaban']}番 {h['name']} {h['gF']:+.1f}秒" for h in fin))


if __name__ == "__main__":
    main()
