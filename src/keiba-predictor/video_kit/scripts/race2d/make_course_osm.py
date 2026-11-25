# -*- coding: utf-8 -*-
"""競馬場のコースの形を、OpenStreetMap（地図のデータ・無料・出どころの表示が条件）から取って保存する（2026-11-20）
使い方: python make_course_osm.py <名前> <緯度> <経度> --dirt-lap 1899 --turf-lap 2083 [--turf-out-lap 2223] [--radius 900]
  内回り・外回りのある場は --turf-lap に内回り、--turf-out-lap に外回りの1周（輪の名前＝芝・芝外）
  2026-11-20 いちばん大きい建物（スタンドの見当）の位置も取る＝build_frames.py がゴール前の直線を自動で決める（home_side が auto のとき）
  例: python make_course_osm.py 東京 35.6625 139.4855 --dirt-lap 1899 --turf-lap 2083
出力: courses/<名前>.json（メートルの座標・北が上。芝とダートの輪＝1周の長さが公式に近い閉じた線を選ぶ。残りの閉じた輪は障害など）
地図データ © OpenStreetMap contributors（ODbL）。動画には出どころを小さく表示する（Race2D.tsx）
"""
import json, math, sys, argparse, time
from pathlib import Path

EPS = ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter",
       "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def fetch(lat, lon, r):
    """curl で取る（Mac の python の SSL では窓口に届かないことがあった・2026-11-20）"""
    import subprocess
    q = f'[out:json][timeout:120];(way(around:{r},{lat},{lon})["leisure"="track"];way(around:{r},{lat},{lon})["building"~"grandstand|stadium|yes"]["building:levels"];way(around:{r},{lat},{lon})["building"="grandstand"];relation(around:{r},{lat},{lon})["leisure"="track"];);out geom;'
    for k, ep in enumerate(EPS * 2):
        t = subprocess.run(["curl", "-s", "-m", "120", "-A", "race2d-course-shape/0.1", "--data-urlencode", f"data={q}", ep],
                           capture_output=True, text=True).stdout
        if t.lstrip().startswith("{"):
            return json.loads(t)
        print(f"   {ep} だめ（{t.strip()[:40] or '応答なし'}）")
        time.sleep(5 * (k + 1))            # 混んでいたら少し待って次へ
    sys.exit("地図のデータが取れませんでした（窓口が混んでいます。時間をおいて再実行するか、取れた JSON を --json で渡す）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name"); ap.add_argument("lat", type=float); ap.add_argument("lon", type=float)
    ap.add_argument("--dirt-lap", type=float); ap.add_argument("--turf-lap", type=float); ap.add_argument("--turf-out-lap", type=float)
    ap.add_argument("--radius", type=int, default=900)
    ap.add_argument("--json", help="Overpass の取得結果（JSON）を渡すと、取りに行かずにそれを使う")
    ap.add_argument("--save-raw", help="取ってきた Overpass の結果（JSON）をここに保存する（あとで --json で使い直せる）")
    a = ap.parse_args()
    d = json.loads(Path(a.json).read_text(encoding="utf-8")) if a.json else fetch(a.lat, a.lon, a.radius)
    if a.save_raw and not a.json: Path(a.save_raw).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    k = math.cos(math.radians(a.lat))
    loops, others, blds = [], [], []
    # 2026-11-20 コースが「面」（multipolygon の relation）で入っている場がある（京都など）→ 面の境目の線（outer・inner）も1本の線として候補にする
    els = []
    for e in d["elements"]:
        if e.get("type") == "relation":
            for m in e.get("members", []):
                if m.get("type") == "way" and m.get("geometry"):
                    els.append(dict(type="way", id=f"r{e['id']}_{m.get('ref')}", tags={"leisure": "track", "_role": m.get("role")}, geometry=m["geometry"]))
        else:
            els.append(e)
    for e in els:
        g = e.get("geometry") or []
        tg = e.get("tags", {})
        if tg.get("building") and len(g) >= 4:           # 建物：面積の大きいものをスタンドの見当にする
            P = [((p["lon"] - a.lon) * 111320 * k, (p["lat"] - a.lat) * 110540) for p in g]
            A = abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))) / 2
            blds.append((A, [round(sum(x for x, _ in P) / len(P), 1), round(sum(y for _, y in P) / len(P), 1)], tg.get("building")))
            continue
        if tg.get("leisure") != "track": continue
        if len(g) < 3 or tg.get("area") == "yes": continue      # パドックなどの面は使わない
        pts = [[round((p["lon"] - a.lon) * 111320 * k, 2), round((p["lat"] - a.lat) * 110540, 2)] for p in g]
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        (loops if L > 1000 and pts[0] == pts[-1] else others).append(dict(id=e["id"], len=round(L), pts=pts))
    # 2026-11-20 地図では1周が何本かの線に分かれていることがある（新潟のダート・芝外など）→ 端どうしをつないで輪にする
    #   つなぐ先が2つ以上あるとき（内回りと外回りの分かれ目）は、曲がり方のいちばん小さい線を選ぶ。1周の長さで選ぶので、余分な輪ができても困らない
    opn = [o for o in others if o["pts"][0] != o["pts"][-1] and len(o["pts"]) >= 2]
    ang = lambda p, q: math.atan2(q[1] - p[1], q[0] - p[0])
    for st in opn:
        chain, ids, ok = list(st["pts"]), {st["id"]}, False
        for _ in range(40):
            end, h0 = chain[-1], ang(chain[-2], chain[-1])
            cands = []
            for o in opn:
                if o["id"] in ids: continue
                for pts in (o["pts"], o["pts"][::-1]):
                    if math.dist(pts[0], end) < 1.0:
                        dh = abs((ang(pts[0], pts[1]) - h0 + math.pi) % (2 * math.pi) - math.pi)
                        cands.append((dh, o["id"], pts))
            if not cands: break
            dh, oid, pts = min(cands)
            chain += pts[1:]; ids.add(oid)
            if math.dist(chain[-1], chain[0]) < 1.0: ok = True; break
        if ok:
            L = sum(math.dist(chain[i], chain[i + 1]) for i in range(len(chain) - 1))
            if L > 1000: loops.append(dict(id="+".join(str(i) for i in sorted(ids)), len=round(L), pts=chain))
    out = dict(name=a.name, center=[a.lat, a.lon], credit="地図データ © OpenStreetMap contributors", loops={}, pockets=[o["pts"] for o in others if o["pts"][0] == o["pts"][-1]])
    used = set()
    for kind, lap in (("ダート", a.dirt_lap), ("芝", a.turf_lap), ("芝外", a.turf_out_lap)):
        if not lap: continue
        best = min((l for l in loops if l["id"] not in used), key=lambda l: abs(l["len"] - lap), default=None)
        if best and abs(best["len"] - lap) < lap * 0.05:
            out["loops"][kind] = best["pts"]; used.add(best["id"])
            print(f"   {kind}: 線 {best['id']}  1周 {best['len']}m（公式 {lap:.0f}m）")
        else:
            print(f"   {kind}: 公式の1周に近い輪が見つかりません")
    for l in loops:
        if l["id"] not in used:
            out["loops"].setdefault("その他", []).append(l["pts"]); print(f"   その他の輪: 線 {l['id']}  1周 {l['len']}m")
    # スタンド＝選んだコースの輪から 250m 以内の建物のうち、いちばん大きいもの（遠くの大きな建物を選ばない・2026-11-20 福島で 800m 先の建物を選んだ）
    ring = [q for k2, v in out["loops"].items() if k2 != "その他" for q in v[::4]]
    near = lambda b: min((math.dist(b[1], q) for q in ring), default=1e9) <= 250
    gs = [b for b in blds if b[2] == "grandstand" and near(b)] or [b for b in blds if near(b)]
    if gs:
        st = max(gs, key=lambda b: b[0])
        out["stand"] = st[1]
        print(f"   スタンドの見当: 建物 {st[2]}・面積 {st[0]:.0f}㎡・位置 {st[1]}")
    p = Path(__file__).resolve().parent / "courses" / f"{a.name}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"✅ {p}  引き込み線などの小さな形 {len(out['pockets'])}個")


if __name__ == "__main__":
    main()
