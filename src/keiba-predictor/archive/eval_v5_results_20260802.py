# -*- coding: utf-8 -*-
"""
eval_v5_results_20260802.py — 8/2(日) 買い目答え合わせPDCA

検証対象:
  A. 重賞2本の多層買い目（当日最終版・馬体重反映後の確定買い目をハードコード）
  B. 平場（自信度7以上・訂正版）のv5.2機械選択買い目（choose_patternで再構成）
実着順（累積DB）× netkeiba払戻で回収率を算出する。
"""
import sys, json, re, time
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from collections import defaultdict
import requests
from bs4 import BeautifulSoup

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / 'scripts'))
sys.path.insert(0, str(SRC / 'scraper'))

from gen_weekend_confidence_report import calc_confidence
from gen_kaime_v5 import choose_pattern, BUDGET_BY_CONF
from convert_netkeiba_to_features import rcode_to_netkeiba_id
from smartrc_api import SmartRCAPI

TARGET_DATE = "20260802"
JSON_PATH = r"C:\Users\User\Desktop\競馬予想レポート\20260801\週末ビッグデータ_20260801-0802_records.json"
ODDS_PATH = str(SRC / "odds_20260802_g3.json")
DB_PATH = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'race_results.json'

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "ja",
})

# ── 重賞の確定買い目（当日最終版・馬体重反映後）───────────
G3_BETS = {
    ('札幌', 11): {   # クイーンS 15,000円 11点
        'label': 'クイーンS(G3) 多層11点',
        'bets': [
            ('ワイド', (10, 7), 2000), ('ワイド', (10, 1), 2000),
            ('馬連', (10, 7), 2000), ('馬連', (10, 1), 1500),
            ('馬連', (10, 2), 800), ('馬連', (10, 3), 700),
            ('単勝', (10,), 2000),
            ('3連複', (10, 7, 1), 1200), ('3連複', (10, 7, 2), 900), ('3連複', (10, 7, 3), 900),
            ('馬連', (7, 1), 1000),
        ],
    },
    ('新潟', 7): {    # アイビスSD 10,000円 12点（馬体重反映でワイド2点差し替え済み）
        'label': 'アイビスSD(G3) 多層12点',
        'bets': [
            ('ワイド', (16, 6), 1200),
            ('ワイド', (16, 9), 1000), ('ワイド', (16, 10), 800), ('ワイド', (16, 17), 700),
            ('馬連', (16, 9), 1500), ('馬連', (16, 6), 1500),
            ('3連複', (16, 9, 6), 900), ('3連複', (16, 9, 10), 600),
            ('3連複', (16, 6, 17), 500), ('3連複', (16, 9, 13), 400),
            ('3連複', (9, 6, 10), 500), ('馬連', (9, 6), 400),
        ],
    },
}


def fetch_payouts(race_id):
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    time.sleep(1.5)
    r = SESSION.get(url, timeout=15)
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    payouts = defaultdict(list)
    for table in soup.select("table.Payout_Detail_Table"):
        for tr in table.select("tr"):
            th = tr.find("th")
            if not th:
                continue
            btype = th.get_text(strip=True)
            result_td = tr.select_one("td.Result")
            payout_td = tr.select_one("td.Payout")
            if not result_td or not payout_td:
                continue
            combos = []
            for el in result_td.find_all(["ul", "div"], recursive=False) or [result_td]:
                txt = el.get_text("-", strip=True)
                if txt:
                    combos.append(txt)
            if not combos:
                combos = [result_td.get_text("-", strip=True)]
            pays = [int(p.replace(",", "")) for p in re.findall(r"([\d,]+)円", payout_td.get_text())]
            if len(combos) == 1 and len(pays) > 1:
                nums = re.findall(r"\d+", combos[0])
                if btype == '複勝' and len(pays) >= 2:
                    combos = nums[:len(pays)]
                elif btype == 'ワイド' and len(pays) >= 2 and len(nums) >= 2 * len(pays):
                    combos = [f"{nums[2*i]}-{nums[2*i+1]}" for i in range(len(pays))]
            for c, p in zip(combos, pays):
                payouts[btype].append((c, p))
    return payouts


def norm_combo(nums):
    return "-".join(str(n) for n in sorted(int(x) for x in nums))


def settle_bets(bets, top3_nums, payouts):
    """bets=[(券種, nums, amount)] → (invest, ret, lines)"""
    inv = ret = 0
    lines = []
    for btype, nums, amount in bets:
        nums = [int(n) for n in nums]
        inv += amount
        hit = False
        pay100 = 0
        if btype == '単勝':
            hit = bool(top3_nums) and nums[0] == top3_nums[0]
            if hit:
                cand = [p for c, p in payouts.get('単勝', []) if re.sub(r'\D', '', c) == str(nums[0])]
                pay100 = cand[0] if cand else 0
        elif btype == '馬連':
            hit = len(top3_nums) >= 2 and set(nums) == set(top3_nums[:2])
            if hit:
                cand = [p for c, p in payouts.get('馬連', [])]
                pay100 = cand[0] if cand else 0
        elif btype == '馬単':
            hit = len(top3_nums) >= 2 and nums == top3_nums[:2]
            if hit:
                cand = [p for c, p in payouts.get('馬単', [])]
                pay100 = cand[0] if cand else 0
        elif btype == 'ワイド':
            hit = set(nums) <= set(top3_nums)
            if hit:
                want = norm_combo(nums)
                for c, p in payouts.get('ワイド', []):
                    cn = re.findall(r'\d+', c)
                    if len(cn) >= 2 and norm_combo(cn[:2]) == want:
                        pay100 = p
                        break
        elif btype == '3連複':
            hit = len(top3_nums) >= 3 and set(nums) == set(top3_nums[:3])
            if hit:
                cand = [p for c, p in payouts.get('3連複', [])]
                pay100 = cand[0] if cand else 0
        elif btype == '3連単':
            hit = len(top3_nums) >= 3 and nums == top3_nums[:3]
            if hit:
                cand = [p for c, p in payouts.get('3連単', [])]
                pay100 = cand[0] if cand else 0
        this_ret = int(pay100 * amount / 100) if hit and pay100 else 0
        ret += this_ret
        sep = '→' if btype in ('馬単', '3連単') else '-'
        mark = '✅' if hit else '　'
        note = f" → 払戻{this_ret:,}円({pay100}円)" if this_ret else ("（的中も払戻取得失敗）" if hit else "")
        lines.append(f"   {mark} {btype} {sep.join(map(str, nums))} {amount:,}円{note}")
    return inv, ret, lines


def main():
    # 予想データ
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    with open(ODDS_PATH, encoding='utf-8') as f:
        real_odds = json.load(f)
    races = defaultdict(list)
    for r in data['records']:
        races[(r['date'], r['競馬場'], r['R'])].append(r)
    for k in races:
        races[k].sort(key=lambda x: x['AI予測順位'])
    conf = {k: calc_confidence(v) for k, v in races.items()}
    keys = sorted([k for k in races if k[0] == TARGET_DATE and conf[k][0] >= 7],
                  key=lambda k: (-conf[k][0], k[1], k[2]))

    # 実結果
    with open(DB_PATH, encoding='utf-8') as f:
        db = json.load(f)
    results = defaultdict(dict)
    for e in db:
        if e.get('date') != TARGET_DATE:
            continue
        try:
            ub = int(float(e.get('馬番', 0)))
        except (TypeError, ValueError):
            continue
        results[(e['競馬場'], int(e['R']))][ub] = e

    # race_idマップ
    api = SmartRCAPI()
    rid_map = {}
    try:
        VEN = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
               "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}
        for r in api.fetch_races(TARGET_DATE):
            rid = rcode_to_netkeiba_id(r['rcode'])
            rid_map[(VEN.get(rid[4:6], '?'), int(r.get('rno', 0)))] = rid
    finally:
        api.close()

    print(f"{'='*100}")
    print(f"8/2(日) 買い目答え合わせPDCA（重賞多層 + 平場v5.2）")
    print(f"{'='*100}")

    total_inv = total_ret = 0
    race_reports = []

    for k in keys:
        recs = races[k]
        top = recs[0]
        c, _ = conf[k]
        res_map = results.get((k[1], k[2]), {})
        finish = sorted(
            [(int(e['着順int']), ub, e['馬名'], e.get('単勝オッズ', 0), e.get('人気', 0))
             for ub, e in res_map.items() if e.get('着順int', 99) < 90],
            key=lambda x: x[0])
        top3 = finish[:3]
        top3_nums = [ub for _, ub, *_ in top3]
        top3_str = " / ".join(f"{o}着 {ub}番{nm}({od}倍{int(nk)}人気)" for o, ub, nm, od, nk in top3)
        marks = [r for r in recs if r['AI印']]
        h_rec = next(r for r in recs if r['AI印'] == '◎')
        h_fin = next((o for o, ub, nm, od, nk in finish if ub == int(h_rec['馬番'])), None)

        grade = f"[{top['グレード']}]" if top['グレード'] else ""
        print(f"\n■ {k[1]}{k[2]}R {top['レース名']}{grade} 自信度{c}/10")
        print(f"  予想印: " + "　".join(f"{r['AI印']}{r['馬番']}{r['馬名']}" for r in marks))
        print(f"  結果:   {top3_str}")
        print(f"  ◎{h_rec['馬名']}: {h_fin}着")

        g3 = G3_BETS.get((k[1], k[2]))
        if g3:
            rid = rid_map.get((k[1], k[2]))
            payouts = fetch_payouts(rid) if rid else {}
            inv, ret, lines = settle_bets(g3['bets'], top3_nums, payouts)
            print(f"  買い目: {g3['label']}（投資{inv:,}円）")
            for ln in lines:
                print(ln)
            rr = ret / inv * 100 if inv else 0
            print(f"  ⇒ 投資{inv:,}円 / 回収{ret:,}円 / 回収率{rr:.0f}%")
            total_inv += inv; total_ret += ret
            race_reports.append((k, c, g3['label'], inv, ret, h_fin, top3))
            continue

        budget = BUDGET_BY_CONF[c]
        odds_key = f"{k[0]}_{k[1]}_{k[2]}"
        name, desc, res, ranking, p, q = choose_pattern(recs, budget, real_odds.get(odds_key))
        if name is None:
            print(f"  買い目: 見送り（EV基準未達）")
            race_reports.append((k, c, '見送り', 0, 0, h_fin, top3))
            continue
        rid = rid_map.get((k[1], k[2]))
        payouts = fetch_payouts(rid) if rid else {}
        bets = [(btype, [int(recs[i]['馬番']) for i in idxs], amount)
                for btype, idxs, amount, _ in res['bets']]
        inv, ret, lines = settle_bets(bets, top3_nums, payouts)
        print(f"  買い目: {name}（投資{inv:,}円）")
        for ln in lines:
            print(ln)
        rr = ret / inv * 100 if inv else 0
        print(f"  ⇒ 投資{inv:,}円 / 回収{ret:,}円 / 回収率{rr:.0f}%")
        total_inv += inv; total_ret += ret
        race_reports.append((k, c, name, inv, ret, h_fin, top3))

    print(f"\n{'='*100}")
    print(f"【8/2(日) トータル】投資{total_inv:,}円 / 回収{total_ret:,}円 / "
          f"回収率{total_ret/total_inv*100 if total_inv else 0:.1f}%")

    out = Path(rf"C:\Users\User\Desktop\競馬予想レポート\{TARGET_DATE}\v5買い目_答え合わせ_{TARGET_DATE}.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'total_inv': total_inv, 'total_ret': total_ret,
            'races': [
                {'race': f"{k[1]}{k[2]}R", 'conf': c, 'pattern': nm,
                 'inv': inv, 'ret': ret, 'honmei_finish': h_fin,
                 'top3': [[o, ub, nmn] for o, ub, nmn, *_ in top3]}
                for k, c, nm, inv, ret, h_fin, top3 in race_reports
            ],
        }, f, ensure_ascii=False, indent=1)
    print(f"\n[保存] {out}")


if __name__ == '__main__':
    main()
