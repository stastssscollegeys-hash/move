# -*- coding: utf-8 -*-
"""
week_preview_data.py — 重賞1週間前プレビュー（SKILL §3b）の材料を、手元の10年履歴（JRA-VAN由来）から一括で出す（2026-10-14新規）
==========================================================================================================================
race_history.py は netkeiba の特集ページを読むが、特集IDの追記が要り、ページの混入にも注意が要る。
history_target（2016〜・JRA-VAN）にはレース名・人気・脚質・枠・払戻（payouts_{年}.json）が揃っているので、それで数える。
  A レースの型（過去10回）: 勝ち馬の人気・1番人気の成績・1〜3番人気の勝ち・3連単の中央値と10万円超・脚質と枠の3着内率・開催場
  B 登録馬ごと（netkeiba 出馬表から馬名・想定騎手）: 直近5走（日付・レース・コース・着順/頭数・人気・通過・上がり順位・着差・馬体重・騎手）・間隔
  C 想定騎手の今年の成績（騎乗数・勝率・3着内率）。名前の照合が1人に決まらないときは出さない（同名の別人と混同しやすい）
使い方: python week_preview_data.py --race 秋華賞 --race-id 202608040711 --date 20261018 [--years 10] > 出力.md
"""
from __future__ import annotations
import argparse, collections, json, re, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import predict_day as P

E.SOURCE = P.HIST


def entries(race_id: str):
    """netkeiba 出馬表（登録段階でも出る）→ [(馬名, 想定騎手, 厩舎)]"""
    import urllib.request
    req = urllib.request.Request(f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}", headers={"User-Agent": "Mozilla/5.0"})
    b = urllib.request.urlopen(req, timeout=30).read()
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        s = b.decode("euc-jp", "ignore")
    cl = lambda m: " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split()) if m else ""
    out = []
    for m in re.finditer(r'<tr class="HorseList.*?</tr>', s, re.S):
        r = m.group(0)
        out.append((cl(re.search(r"HorseName.*?<a[^>]*>(.*?)</a>", r, re.S)), cl(re.search(r'class="Jockey">(.*?)</td>', r, re.S)),
                    cl(re.search(r'class="Trainer">(.*?)</td>', r, re.S))))
    return [x for x in out if x[0]]


def fin(r):
    return r.get("着順int")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", required=True, help="履歴のレース名（完全一致）。例: 秋華賞 / 富士ステークス")
    ap.add_argument("--race-id", required=True, help="netkeiba の今年の race_id（登録馬と想定騎手を取る）")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--date", required=True, help="今年のレース日 YYYYMMDD（前走からの間隔）")
    a = ap.parse_args()
    rows = [r for r in E.load_rows()]
    hist_dir = Path(P.HIST)
    # ── A レースの型 ──
    past = collections.defaultdict(list)
    for r in rows:
        if r.get("レース名") == a.race:
            past[r["date"]].append(r)
    dates = sorted(past)[-a.years:]
    print(f"# {a.race} 1週間前プレビューの材料（{dates[0][:4]}〜{dates[-1][:4]}・{len(dates)}回・JRA-VAN履歴）\n")
    print("## A レースの型\n")
    pays = {}
    for y in {d[:4] for d in dates}:
        f = hist_dir / f"payouts_{y}.json"
        if f.exists():
            pays.update(json.loads(f.read_text(encoding="utf-8")))
    wpop, fav, top3win, p3, venues = [], [], 0, [], collections.Counter()
    sty = collections.defaultdict(lambda: [0, 0]); wak = collections.defaultdict(lambda: [0, 0])
    print("| 年 | 場 | 頭数 | 勝ち馬（人気） | 2着（人気） | 3着（人気） | 1番人気 | 3連単 |\n|---|---|---|---|---|---|---|---|")
    for d in dates:
        hs = [h for h in past[d] if fin(h)]
        hs.sort(key=fin)
        venues[hs[0]["競馬場"]] += 1
        top = hs[:3]
        f1 = min(hs, key=lambda h: int(h["人気"] or 99))
        wpop.append(int(top[0]["人気"])); fav.append(fin(f1)); top3win += int(top[0]["人気"]) <= 3
        k = f"{d}|{hs[0]['競馬場']}|{hs[0]['R']}"
        t3 = pays.get(k, {}).get("3連単", {})
        tp = max(t3.values()) * 1 if t3 else None          # 同着は高いほう
        if tp:
            p3.append(tp)
        for h in hs:
            n = int(h.get("頭数") or len(hs))
            if h.get("脚質"):
                s = sty[h["脚質"]]; s[0] += 1; s[1] += fin(h) <= 3
            if h.get("枠"):
                b = "内(1-3枠)" if h["枠"] <= 3 else "中(4-6枠)" if h["枠"] <= 6 else "外(7-8枠)"
                w = wak[b]; w[0] += 1; w[1] += fin(h) <= 3
        print(f"| {d[:4]} | {hs[0]['競馬場']} | {len(hs)} | " + " | ".join(f"{h['馬名']}（{h['人気']}）" for h in top)
              + f" | {fin(f1)}着 | " + (f"{tp:,}円" if tp else "-") + " |")
    n = len(dates)
    print(f"\n- 開催場: " + "・".join(f"{v}{c}回" for v, c in venues.most_common()))
    print(f"- 勝ち馬の人気: {sorted(wpop)}／1〜3番人気の勝ち {top3win}/{n}")
    print(f"- 1番人気: {sum(1 for x in fav if x == 1)}勝・3着内 {sum(1 for x in fav if x <= 3)}/{n}")
    if p3:
        print(f"- 3連単: 中央値 {int(statistics.median(p3)):,}円・10万円超 {sum(1 for x in p3 if x >= 100000)}回・最高 {max(p3):,}円（{len(p3)}回分）")
    print("- 脚質（3着内率）: " + "・".join(f"{k} {v[1]}/{v[0]}={v[1] / v[0] * 100:.0f}%" for k, v in sorted(sty.items(), key=lambda x: -x[1][0])))
    print("- 枠（3着内率）: " + "・".join(f"{k} {v[1]}/{v[0]}={v[1] / v[0] * 100:.0f}%" for k, v in sorted(wak.items())))

    # ── B・C 登録馬 ──
    ent = entries(a.race_id)
    by_h = collections.defaultdict(list)
    for r in rows:
        by_h[r["馬名"]].append(r)
    this_year = [r for r in rows if r["date"] >= "20260101" and fin(r)]
    jk_all = collections.Counter(r["騎手"] for r in this_year)
    print(f"\n## B 登録馬 {len(ent)}頭（想定騎手は netkeiba・登録段階）\n")
    for name, jk, tr in ent:
        rs = sorted(by_h.get(name, []), key=lambda r: r["date"])
        last = rs[-1] if rs else None
        sa = last.get("性齢") if last else ""
        print(f"### {name}　{sa}　想定 {jk or '未定'}　{tr}")
        cand = [k for k in jk_all if jk and (k == jk or k.startswith(jk))]          # 前方一致を優先（「幸」が「内田博幸」に当たらないように）
        if not cand:
            cand = [k for k in jk_all if jk and jk.replace(".", "") in k.replace(".", "")]
        if len(cand) == 1:
            js = [r for r in this_year if r["騎手"] == cand[0]]
            w = sum(1 for r in js if fin(r) == 1); t3 = sum(1 for r in js if fin(r) <= 3)
            print(f"- 騎手 {cand[0]}: 今年 {len(js)}騎乗・勝率 {w / len(js) * 100:.1f}%・3着内 {t3 / len(js) * 100:.1f}%")
        elif jk:
            print(f"- 騎手 {jk}: 履歴の名前と1人に決まらない（候補 {cand[:4]}）→ 成績は載せない")
        if not rs:
            print("- 🔴 JRAの履歴に出走なし（海外・地方・新馬未出走の可能性。Web検索で確認）\n")
            continue
        wins = [r for r in rs if fin(r) == 1]
        print(f"- 通算（JRA・2016〜）: {len(rs)}戦{len(wins)}勝・3着内 {sum(1 for r in rs if fin(r) and fin(r) <= 3)}回／父 {last.get('父')}・母父 {last.get('母父')}")
        for r in rs[-5:][::-1]:
            print(f"  - {r['date'][2:4]}/{r['date'][4:6]}/{r['date'][6:]} {r['競馬場']} {r.get('レース名') or r.get('条件')} {r['距離']} {r.get('馬場状態') or ''}"
                  f" → {r.get('着順')}着/{r.get('頭数')}頭（{r.get('人気')}番人気）通過{r.get('コーナー通過') or '-'} 上がり{r.get('後3F') or '-'}({r.get('後3F順位') or '-'}位)"
                  f" 着差{r.get('着差') or '-'} {r.get('馬体重') or ''} {r.get('騎手')}")
        gap = (E._day(a.date) - E._day(last["date"])).days
        print(f"- 前走から {gap}日\n")


if __name__ == "__main__":
    main()
