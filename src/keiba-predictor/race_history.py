# -*- coding: utf-8 -*-
"""
race_history.py — 対象重賞の過去傾向を自前で集計し、型（S/H）を決める
==========================================================================
なぜ必要か
----------
2026-09-09に週末リサーチを回したところ、**「人気別成績」「3連単配当水準」という
型判定の核心データが、外部サイトからは取れなかった**。
netkeibaの該当部分は有料プレミアム、競馬ラボ・SPAIAは403、うましる等のブログは
レースによって載っていたり載っていなかったりする。

そこで **netkeibaの過去レース結果ページを直接読んで自分で数える**。
外部の集計に依存しないので、どの重賞でも同じ物差しで測れる。

同時に、その**レース自体の脚質・枠傾向**も出す。
汎用の「中山芝2200mのコース傾向」より、**同じ条件で行われた過去10回の
セントライト記念そのもの**のほうが予想には効く（頭数・メンバー質・ペースが近い）。

⚠ 実装時に踏んだ罠（再発防止）
--------------------------------
1. 特集ページには**当年の無関係なレース**（京都新聞杯・木曽川特別など）が
   多数混ざる。年ごとに1件だけ拾わないと、別レース9件を集計して
   **もっともらしい嘘の数字**（1番人気の複勝率100%等）が出る。
2. netkeibaの払戻表記は **「三連単」「三連複」（漢数字）**。
   '3連単' で照合していたため、配当が1件も取れていなかった。

使い方
------
    python race_history.py セントライト記念
    python race_history.py ローズS --years 10
    python race_history.py --list          # 対応レース一覧
"""
from __future__ import annotations
import argparse, re, sys, io
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bs4 import BeautifulSoup
from fetch_payouts import session, get

# netkeiba特集ページのID。新しい重賞を足すときはここに追記する
# （race.netkeiba.com/special/index.html?id=XXXX のタイトルで確認できる）
SPECIAL = {
    "ローズS": "0094",
    "セントライト記念": "0095",
    "オールカマー": "0096",
    "神戸新聞杯": "0097",
    "チャレンジC": "0126",
    "毎日王冠": "0101",       # 2026-09-27 追加（東京 芝1800 G2・10/4）
    "京都大賞典": "0102",     # 2026-09-27 追加（京都 芝2400 G2・10/4）
}

# 型判定のしきい値（v6.3）。3連単中央値と上位人気の信頼度で決める
S_TOP3_WIN = 0.65        # 1〜3番人気が勝つ割合がこれ以上ならS寄り
S_MEDIAN_PAY = 30_000    # 3連単中央値がこれ未満ならS寄り
H_MEDIAN_PAY = 80_000    # これ以上ならH寄り


def past_ids(sid: str, s, years: int) -> list[str]:
    h = get(s, f"https://race.netkeiba.com/special/index.html?id={sid}", "utf-8")
    if not h:
        return []
    ids = sorted(set(re.findall(r"race/(\d{12})", h)) | set(re.findall(r"race_id=(\d{12})", h)))
    # ⚠罠1: 当年の無関係レースを排除し、年ごとに1件だけにする
    by_year: dict[str, str] = {}
    cur = str(__import__("datetime").date.today().year)
    for i in ids:
        y = i[:4]
        if y.isdigit() and y < cur:
            by_year.setdefault(y, i)
    return [by_year[y] for y in sorted(by_year)][-years:]


def style_of(passing: str) -> str:
    """通過順から脚質を決める（4コーナー位置と頭数比で判定）"""
    nums = [int(x) for x in re.findall(r"\d+", passing or "") if x.isdigit()]
    if not nums:
        return "?"
    first, last = nums[0], nums[-1]
    if first <= 2:
        return "逃げ"
    if first <= 4:
        return "先行"
    return "差し" if last <= 8 else "追込"


def parse(html: str) -> dict | None:
    so = BeautifulSoup(html, "html.parser")
    t = so.select_one("table.race_table_01")
    if not t:
        return None
    rows_ = t.select("tr")
    head = [x.get_text(strip=True) for x in rows_[0].select("th,td")]

    def col(*n):
        for i, h in enumerate(head):
            if any(x in h for x in n):
                return i
        return None

    ir, ip, io_ = col("着順"), col("人気"), col("単勝")
    iw, ipass = col("枠番"), col("通過")
    if ir is None or ip is None:
        return None

    horses = []
    for tr in rows_[1:]:
        td = tr.select("td")
        if len(td) <= max(x for x in (ir, ip) if x is not None):
            continue
        rk = td[ir].get_text(strip=True)
        if not rk.isdigit():
            continue
        try:
            horses.append({
                "rank": int(rk), "pop": int(td[ip].get_text(strip=True)),
                "odds": float(td[io_].get_text(strip=True)) if io_ is not None else 0.0,
                "waku": int(td[iw].get_text(strip=True)) if iw is not None
                        and td[iw].get_text(strip=True).isdigit() else 0,
                "style": style_of(td[ipass].get_text(strip=True)) if ipass is not None else "?",
            })
        except (ValueError, IndexError):
            continue

    pay = {}
    for tb in so.select("table.pay_table_01"):
        for tr in tb.select("tr"):
            th, td = tr.select_one("th"), tr.select("td")
            if not th or len(td) < 2:
                continue
            m = re.search(r"([\d,]+)", td[1].get_text(" ", strip=True))
            if m:
                pay[th.get_text(strip=True)] = int(m.group(1).replace(",", ""))
    return {"horses": horses, "pay": pay, "n": len(horses)}


def ids_by_pattern(s, name: str, pattern: str, years: int) -> list[str]:
    """特集ページが使えないレース用（2026-09-25追加）。
    race_id は「年＋場コード＋回＋日＋R」で毎年ほぼ同じ並びになるので、年だけ差し替えて当てる。
    ⚠ 必ずページのタイトルにレース名が入っているかを確かめてから採用する
    （確かめないと別レースを集計して、もっともらしい嘘の数字が出る＝2026-09-09の罠1）。"""
    import datetime
    cur = datetime.date.today().year
    out = []
    for y in range(cur - 1, cur - years - 3, -1):
        rid = pattern.format(year=y)
        h = get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
        if not h:
            continue
        m = re.search(r"<title>(.*?)</title>", h, re.S)
        title = (m.group(1) if m else "").strip()
        key = name.replace("S", "").replace("ステークス", "")
        if key and key in title:
            out.append(rid)
        if len(out) >= years:
            break
    return sorted(out)


def main(name: str, years: int, pattern: str | None = None) -> None:
    s = session()
    if pattern:
        ids = ids_by_pattern(s, name, pattern, years)
        print(f"（レースIDの直接指定で {len(ids)}件を確認）")
    elif name not in SPECIAL:
        print(f"未登録のレースです。SPECIAL に特集IDを追記するか --race-id-pattern を使ってください。")
        print(f"対応: {', '.join(SPECIAL)}")
        return
    else:
        ids = past_ids(SPECIAL[name], s, years)
    print(f"═══ {name} 過去{len(ids)}回の自前集計 ═══\n")

    pop = defaultdict(lambda: {"n": 0, "w": 0, "t3": 0, "ret": 0.0})
    sty = defaultdict(lambda: {"n": 0, "t3": 0})
    wak = defaultdict(lambda: {"n": 0, "t3": 0})
    tan3, fuku3, wins, fields = [], [], [], []

    for rid in ids:
        h = get(s, f"https://db.netkeiba.com/race/{rid}/", "euc-jp")
        if not h:
            continue
        d = parse(h)
        if not d or not d["horses"]:
            continue
        fields.append(d["n"])
        for x in d["horses"]:
            p = pop[min(x["pop"], 10)]
            p["n"] += 1
            if x["rank"] == 1:
                p["w"] += 1
                p["ret"] += x["odds"] * 100
                wins.append(x["pop"])
            if x["rank"] <= 3:
                p["t3"] += 1
            if x["style"] != "?":
                a = sty[x["style"]]; a["n"] += 1; a["t3"] += 1 if x["rank"] <= 3 else 0
            if x["waku"]:
                b = wak[x["waku"]]; b["n"] += 1; b["t3"] += 1 if x["rank"] <= 3 else 0
        # ⚠罠2: netkeibaは「三連単」（漢数字）
        for k, v in d["pay"].items():
            if "三連単" in k or "3連単" in k:
                tan3.append(v)
            elif "三連複" in k or "3連複" in k:
                fuku3.append(v)
        print(f"  {rid[:4]}年 {d['n']:>2}頭  勝ち馬"
              f"{[x['pop'] for x in d['horses'] if x['rank']==1]}人気"
              f"  3連単{d['pay'].get('三連単', '—'):>9,}円" if d["pay"].get("三連単")
              else f"  {rid[:4]}年 {d['n']:>2}頭")

    if not wins:
        print("  結果を取得できませんでした。")
        return

    print(f"\n■ 人気別（{len(fields)}回・{sum(fields)}頭）")
    print(f"{'人気':>4}{'頭数':>6}{'勝率':>8}{'複勝率':>9}{'単勝回収':>9}")
    print("─" * 38)
    for k in sorted(pop):
        v = pop[k]
        if v["n"] < 3:
            continue
        print(f"{('10〜' if k >= 10 else k):>4}{v['n']:>6}{v['w']/v['n']*100:>7.1f}%"
              f"{v['t3']/v['n']*100:>8.1f}%{v['ret']/(v['n']*100)*100:>8.0f}%")

    if sty:
        print(f"\n■ 脚質別3着内率（このレース自体の過去{len(fields)}回）")
        for k, v in sorted(sty.items(), key=lambda x: -x[1]["n"]):
            if v["n"] >= 5:
                print(f"  {k:<4}{v['t3']/v['n']*100:>6.1f}%  ({v['n']}頭)")

    if wak:
        print(f"\n■ 枠別3着内率")
        line = "  " + " ".join(f"{k}枠{v['t3']/v['n']*100:.0f}%" for k, v in sorted(wak.items())
                               if v["n"] >= 5)
        print(line)

    if tan3:
        tan3.sort(); fuku3.sort()
        med = tan3[len(tan3)//2]
        big = sum(1 for x in tan3 if x >= 100_000)
        print(f"\n■ 配当水準")
        print(f"  3連単 中央値 {med:,}円 / 最低 {tan3[0]:,} / 最高 {tan3[-1]:,}")
        if fuku3:
            print(f"  3連複 中央値 {fuku3[len(fuku3)//2]:,}円")
        print(f"  3連単10万円超: {big}/{len(tan3)}回 ({big/len(tan3)*100:.0f}%)")
    else:
        med = 0

    top3 = sum(1 for w in wins if w <= 3) / len(wins)
    print(f"\n■ 勝ち馬の人気: {sorted(wins)}   1〜3番人気が勝った割合 {top3*100:.0f}%")

    print(f"\n■ 型判定（v6.3）")
    if top3 >= S_TOP3_WIN and med and med < S_MEDIAN_PAY:
        print("  → **S型（的中率重視）**。上位人気が堅く配当も跳ねない。")
        print("     本線=馬単◎→○・3連複◎○▲の8〜15倍帯 ／ 4〜6点 ／ 1点上限30%")
    elif med >= H_MEDIAN_PAY or top3 < 0.5:
        print("  → **H型（高配当）**。上位人気が信用できず配当が大きい。")
        print("     本線=3連複の穴絡み20〜50倍帯 ／ 6〜10点 ／ 1点上限25%")
    else:
        print("  → 中間。個別材料で決める（配当中央値が大きいならH寄りに倒す）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("race", nargs="?", help="レース名（SPECIALに登録済みのもの）")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--race-id-pattern", help="例: {year}06040911（特集ページが無いレース用・年だけ差し替える）")
    a = ap.parse_args()
    if a.list or not a.race:
        print("対応レース: " + ", ".join(SPECIAL))
    else:
        main(a.race, a.years, a.race_id_pattern)
