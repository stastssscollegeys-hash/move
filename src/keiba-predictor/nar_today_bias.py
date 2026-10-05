# -*- coding: utf-8 -*-
"""
nar_today_bias.py — 地方競馬の「当日の実測」を集計する（2026-09-30新規）
==============================================================================
ユーザー指示「今日の船橋の情報（ペース・タイム・トラックバイアス・勝ち馬データ）を入れて」に対応。
JRAには odds_snapshot / weekend_full_review があるが、地方競馬（NAR）には当日集計の道具が無く、
毎回Webを手で読んでいた。NARの結果ページから機械的に集計する。

取得元: nar.netkeiba.com/race/result.html?race_id=YYYY{場}{MMDD}{R}  ※**UTF-8**（JRA側のeuc-jpと違う）
出すもの:
  ・各レースの距離・馬場・勝ち時計・ペース・勝ち馬の脚質と通過順・枠・人気
  ・当日の脚質別／枠別の3着内率（＝トラックバイアス）
  ・同距離のレースがあれば勝ち時計の比較（馬場の速さの目安）

使い方: python nar_today_bias.py --date 20260930 --jo 43 --upto 10
        （jo: 船橋=43 / 大井=44 / 川崎=45 / 浦和=42 / 門別=30 など netkeiba の場コード）
"""
from __future__ import annotations
import argparse, collections, json, re, sys, time, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/153.0 Safari/537.36",
       "Accept-Language": "ja,en;q=0.9", "Referer": "https://nar.netkeiba.com/"}


def fetch(url, retry=3):
    for i in range(retry):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25) as r:
                return r.read().decode("utf-8", "replace")     # NARはUTF-8
        except Exception as e:
            if i == retry - 1:
                print(f"[WARN] {url} {e}")
                return ""
            time.sleep(2)
    return ""


def style_of(cpos, n: int) -> str:
    """最終コーナーの通過位置から脚質を判定（JRA側 pace_style_audit と同じ4分類）"""
    if not cpos or n < 2:
        return None
    r = (cpos - 1) / (n - 1)
    return "逃げ" if cpos == 1 else "先行" if r < 0.34 else "差し" if r < 0.67 else "追込"


def parse(html: str):
    """結果ページから レース情報・着順表・コーナー通過順 を取り出す。
    NARの結果ページは
      ・着順表(14列) = 着順/枠/馬番/馬名/性齢/斤量/騎手/タイム/着差/人気/単勝/後3F/厩舎/馬体重
        → **通過順は入っていない**
      ・「コーナー通過順位」が別セクション（例: 5,10,12,(1,3),9,7,(6,8)-4）
      ・「ラップタイム」「ペース: H」も別セクション
      ・馬場は「馬場:不」のように1文字表記
    という作りなので、それぞれ別に拾う。
    """
    flat = re.sub(r"<[^>]+>", "\n", html)
    flat = re.sub(r"&nbsp;", " ", flat)
    one = re.sub(r"\s+", " ", flat)

    info = {}
    m = re.search(r"(ダ|芝)\s*(\d{3,4})m", one)
    if m:
        info["surface"] = "ダート" if m.group(1) == "ダ" else "芝"
        info["dist"] = int(m.group(2))
    m = re.search(r"馬場\s*:\s*(良|稍|重|不)", one)
    if m:
        info["baba"] = {"良": "良", "稍": "稍重", "重": "重", "不": "不良"}[m.group(1)]
    m = re.search(r"天候\s*:\s*(\S{1,2})", one)
    if m:
        info["weather"] = m.group(1)
    m = re.search(r"ペース\s*:\s*([HMS])", one)
    if m:
        info["pace"] = m.group(1)
    # ラップタイム（200m毎）: 「ラップタイム」以降に 12.5 12.0 … と並ぶ
    i = one.find("ラップタイム")
    if i >= 0:
        laps = re.findall(r"(?<![\d.:])(\d{1,2}\.\d)(?![\d.])", one[i:i + 700])
        if laps:
            info["lap"] = laps[:12]

    # コーナー通過順位 → 最終コーナーの並びから 馬番→位置 を作る
    pos = {}
    j = one.find("コーナー通過順位")
    if j >= 0:
        seg = one[j:j + 900]
        corners = re.findall(r"[234]\s*コーナー\s*([0-9,()\- ]+)", seg)
        if corners:
            last = corners[-1]
            rank_i = 0
            # "5,(10,12),1,(3,9)-6" のような並びを左から順に位置づけ
            for grp in re.findall(r"\(([^)]*)\)|(\d+)", last):
                nums = [int(x) for x in re.findall(r"\d+", grp[0] or grp[1] or "")]
                if not nums:
                    continue
                rank_i += 1
                for u in nums:
                    pos.setdefault(u, rank_i)

    horses = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", td)).strip()
               for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(tds) < 12 or not re.fullmatch(r"\d+", tds[0] or ""):
            continue
        try:
            uma = int(tds[2])
        except ValueError:
            continue
        horses.append({"rank": int(tds[0]),
                       "waku": int(tds[1]) if re.fullmatch(r"\d+", tds[1]) else None,
                       "uma": uma, "name": tds[3],
                       "time": tds[7] or None, "margin": tds[8] or None,
                       "pop": int(tds[9]) if re.fullmatch(r"\d+", tds[9] or "") else None,
                       "odds": tds[10] or None,
                       "last3f": tds[11] or None,
                       "cpos": pos.get(uma)})
    return info, horses


ap = argparse.ArgumentParser()
ap.add_argument("--date", required=True)
ap.add_argument("--jo", required=True)
ap.add_argument("--upto", type=int, default=11)
a = ap.parse_args()
md = a.date[4:]

races = []
for r in range(1, a.upto + 1):
    rid = f"{a.date[:4]}{a.jo}{md}{r:02d}"
    html = fetch(f"https://nar.netkeiba.com/race/result.html?race_id={rid}")
    if not html:
        continue
    info, hs = parse(html)
    if not hs:
        print(f"  {r:>2}R 結果まだ／取得できず")
        continue
    win = next((h for h in hs if h["rank"] == 1), None)
    n = len(hs)
    for h in hs:
        h["style"] = style_of(h["cpos"], n)
    races.append({"R": r, **info, "n": n, "horses": hs, "win": win})
    print(f"  {r:>2}R {info.get('surface','?')}{info.get('dist','?')}m {info.get('baba','?')} "
          f"{n}頭 勝ち時計{win['time'] if win else '-'} ペース{info.get('pace','-')} "
          f"勝ち馬[{win['uma'] if win else '?'}]{win['name'][:8] if win else ''} "
          f"{win['style'] if win else '?'}(4角{win['cpos'] if win else '?'}番手) 上り{win['last3f'] if win else '-'} "
          f"{win['pop'] if win else '?'}人気")
    time.sleep(0.8)

if not races:
    sys.exit("\n結果が取れませんでした")

print(f"\n■ 本日の脚質別 3着内率（{len(races)}レース・{sum(r['n'] for r in races)}頭）")
agg = collections.defaultdict(lambda: [0, 0])
for r in races:
    for h in r["horses"]:
        if h["style"]:
            agg[h["style"]][0] += 1
            agg[h["style"]][1] += 1 if h["rank"] <= 3 else 0
for s in ("逃げ", "先行", "差し", "追込"):
    n, t = agg[s]
    if n:
        print(f"  {s}  {t}/{n} = {t/n*100:5.1f}%")
front = sum(agg[s][1] for s in ("逃げ", "先行")), sum(agg[s][0] for s in ("逃げ", "先行"))
back = sum(agg[s][1] for s in ("差し", "追込")), sum(agg[s][0] for s in ("差し", "追込"))
if front[1] and back[1]:
    print(f"  前(逃+先) {front[0]/front[1]*100:.1f}%  vs  後(差+追) {back[0]/back[1]*100:.1f}%"
          f"  → 差 {front[0]/front[1]*100-back[0]/back[1]*100:+.1f}pt")

print("\n■ 本日の枠別 3着内率")
wk = collections.defaultdict(lambda: [0, 0])
for r in races:
    for h in r["horses"]:
        if h["waku"]:
            wk[h["waku"]][0] += 1
            wk[h["waku"]][1] += 1 if h["rank"] <= 3 else 0
print("  " + "  ".join(f"{w}枠{wk[w][1]}/{wk[w][0]}" for w in sorted(wk)))

print("\n■ 勝ち馬の人気")
pops = [r["win"]["pop"] for r in races if r["win"] and r["win"]["pop"]]
if pops:
    print(f"  {pops}  → 1番人気の勝率 {sum(1 for p in pops if p==1)}/{len(pops)}")

print("\n■ 同距離の勝ち時計（馬場の速さの目安）")
bd = collections.defaultdict(list)
for r in races:
    if r.get("dist") and r["win"] and r["win"]["time"]:
        bd[r["dist"]].append((r["R"], r["win"]["time"]))
for d in sorted(bd):
    print(f"  {d}m: " + " / ".join(f"{R}R {t}" for R, t in bd[d]))

out = Path.home() / "Desktop" / "競馬予想レポート" / a.date / "research"
out.mkdir(parents=True, exist_ok=True)
(out / f"nar_today_{a.jo}.json").write_text(
    json.dumps({"date": a.date, "jo": a.jo, "races": races}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n保存: {out / f'nar_today_{a.jo}.json'}")
