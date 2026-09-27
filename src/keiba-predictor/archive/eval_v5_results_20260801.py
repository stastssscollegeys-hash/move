# -*- coding: utf-8 -*-
"""
eval_v5_results_20260801.py — 8/1(土) v5買い目・自信度予想の答え合わせPDCA

事前予想（自信度7以上・v5の46パターン機械評価買い目）を再構成し、
実際の着順（累積DB）・払戻（netkeiba）と照合して回収率を検証する。
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

TARGET_DATE = "20260801"
JSON_PATH = r"C:\Users\User\Desktop\競馬予想レポート\20260801\週末ビッグデータ_20260801-0802_records.json"
ODDS_PATH = str(SRC / "odds_20260802_g3.json")
DB_PATH = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'race_results.json'

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "ja",
})


def fetch_payouts(race_id):
    """netkeiba結果ページから払戻を取得。{券種: [(組み合わせ文字列, 払戻円), ...]}"""
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
            for div_or_ul in result_td.find_all(["ul", "div"], recursive=False) or [result_td]:
                txt = div_or_ul.get_text("-", strip=True)
                if txt:
                    combos.append(txt)
            if not combos:
                combos = [result_td.get_text("-", strip=True)]
            pay_texts = re.findall(r"([\d,]+)円", payout_td.get_text())
            pays = [int(p.replace(",", "")) for p in pay_texts]
            # combos と pays の対応（複勝・ワイドは複数行）
            if len(combos) == 1 and len(pays) > 1:
                # Resultの中の区切り再分割を試みる
                raw = combos[0]
                nums = re.findall(r"\d+", raw)
                if btype in ("複勝",) and len(pays) >= 2:
                    combos = nums[:len(pays)]
                elif btype in ("ワイド",) and len(pays) >= 2 and len(nums) >= 2 * len(pays):
                    combos = [f"{nums[2*i]}-{nums[2*i+1]}" for i in range(len(pays))]
            for c, p in zip(combos, pays):
                payouts[btype].append((c, p))
    return payouts


def norm_combo(nums):
    return "-".join(str(n) for n in sorted(int(x) for x in nums))


def main():
    # ── 事前予想の再構成 ─────────────────────────────
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

    # ── 実結果（累積DB） ─────────────────────────────
    with open(DB_PATH, encoding='utf-8') as f:
        db = json.load(f)
    results = defaultdict(dict)   # (競馬場,R) -> {馬番int: record}
    for e in db:
        if e.get('date') != TARGET_DATE:
            continue
        try:
            umaban = int(float(e.get('馬番', 0)))
        except (TypeError, ValueError):
            continue
        results[(e['競馬場'], int(e['R']))][umaban] = e

    # ── race_id マッピング ────────────────────────────
    api = SmartRCAPI()
    rid_map = {}
    try:
        for r in api.fetch_races(TARGET_DATE):
            rid = rcode_to_netkeiba_id(r['rcode'])
            venue_cd = rid[4:6]
            VEN = {"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京",
                   "06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
            rid_map[(VEN.get(venue_cd,'?'), int(r.get('rno', 0)))] = rid
    finally:
        api.close()

    # ── 検証 ─────────────────────────────────────────
    print(f"{'='*100}")
    print(f"8/1(土) v5買い目 答え合わせPDCA")
    print(f"{'='*100}")

    total_inv = 0
    total_ret = 0
    race_reports = []

    for k in keys:
        recs = races[k]
        top = recs[0]
        c, tags = conf[k]
        budget = BUDGET_BY_CONF[c]
        odds_key = f"{k[0]}_{k[1]}_{k[2]}"
        name, desc, res, ranking, p, q = choose_pattern(recs, budget, real_odds.get(odds_key))

        res_map = results.get((k[1], k[2]), {})
        finish = sorted(
            [(int(e['着順int']), ub, e['馬名'], e.get('単勝オッズ', 0), e.get('人気', 0))
             for ub, e in res_map.items() if e.get('着順int', 99) < 90],
            key=lambda x: x[0])
        top3 = finish[:3]
        top3_str = " / ".join(f"{o}着 {ub}番{nm}({od}倍{int(nk)}人気)" for o, ub, nm, od, nk in top3)

        marks = [r for r in recs if r['AI印']]
        mark_str = "　".join(f"{r['AI印']}{r['馬番']}{r['馬名']}" for r in marks)
        h_rec = next(r for r in recs if r['AI印'] == '◎')
        h_fin = next((o for o, ub, nm, od, nk in finish if ub == int(h_rec['馬番'])), None)

        print(f"\n■ {k[1]}{k[2]}R {top['レース名']} 自信度{c}/10")
        print(f"  予想印: {mark_str}")
        print(f"  結果:   {top3_str}")
        print(f"  ◎{h_rec['馬名']}: {h_fin}着")

        if name is None:
            winner_marked = any(int(m['馬番']) == top3[0][1] for m in marks[:3]) if top3 else False
            print(f"  買い目: 見送り（EV基準未達）")
            race_reports.append((k, c, '見送り', 0, 0, h_fin, top3))
            continue

        # 払戻取得
        rid = rid_map.get((k[1], k[2]))
        payouts = fetch_payouts(rid) if rid else {}

        top3_nums = [ub for _, ub, *_ in top3]
        inv = res['total']
        ret = 0
        print(f"  買い目: {name}（投資{inv:,}円）")
        for btype, idxs, amount, est_odds in res['bets']:
            nums = [int(recs[i]['馬番']) for i in idxs]
            hit = False
            pay_per100 = 0
            if btype == '単勝':
                hit = (len(top3_nums) > 0 and nums[0] == top3_nums[0])
                key_s = str(nums[0])
                cand = [p for cmb, p in payouts.get('単勝', []) if re.sub(r'\D','',cmb) == key_s]
                pay_per100 = cand[0] if (hit and cand) else 0
            elif btype == '馬連':
                hit = (len(top3_nums) >= 2 and set(nums) == set(top3_nums[:2]))
                cand = [p for cmb, p in payouts.get('馬連', [])]
                pay_per100 = cand[0] if (hit and cand) else 0
            elif btype == '馬単':
                hit = (len(top3_nums) >= 2 and nums == top3_nums[:2])
                cand = [p for cmb, p in payouts.get('馬単', [])]
                pay_per100 = cand[0] if (hit and cand) else 0
            elif btype == 'ワイド':
                hit = set(nums) <= set(top3_nums)
                pay_per100 = 0
                if hit:
                    want = norm_combo(nums)
                    for cmb, pv in payouts.get('ワイド', []):
                        cn = re.findall(r'\d+', cmb)
                        if len(cn) >= 2 and norm_combo(cn[:2]) == want:
                            pay_per100 = pv
                            break
            elif btype == '3連複':
                hit = (len(top3_nums) >= 3 and set(nums) == set(top3_nums[:3]))
                cand = [p for cmb, p in payouts.get('3連複', [])]
                pay_per100 = cand[0] if (hit and cand) else 0
            elif btype == '3連単':
                hit = (len(top3_nums) >= 3 and nums == top3_nums[:3])
                cand = [p for cmb, p in payouts.get('3連単', [])]
                pay_per100 = cand[0] if (hit and cand) else 0

            this_ret = int(pay_per100 * amount / 100) if hit and pay_per100 else 0
            ret += this_ret
            sep = '→' if btype in ('馬単', '3連単') else '-'
            mark = '✅' if hit else '　'
            pay_note = f" → 払戻{this_ret:,}円({pay_per100}円)" if this_ret else ("（的中も払戻取得失敗）" if hit else "")
            print(f"   {mark} {btype} {sep.join(map(str,nums))} {amount:,}円{pay_note}")

        rr = ret / inv * 100 if inv else 0
        print(f"  ⇒ 投資{inv:,}円 / 回収{ret:,}円 / 回収率{rr:.0f}%")
        total_inv += inv
        total_ret += ret
        race_reports.append((k, c, name, inv, ret, h_fin, top3))

    print(f"\n{'='*100}")
    print(f"【8/1(土) トータル】投資{total_inv:,}円 / 回収{total_ret:,}円 / "
          f"回収率{total_ret/total_inv*100 if total_inv else 0:.1f}%")

    # 自信度別成績
    print(f"\n【自信度別】")
    by_conf = defaultdict(lambda: [0, 0, 0, 0])  # races, hon_win, inv, ret
    for k, c, nm, inv, ret, h_fin, top3 in race_reports:
        s = by_conf[c]
        s[0] += 1
        if h_fin == 1: s[1] += 1
        s[2] += inv; s[3] += ret
    for c in sorted(by_conf, reverse=True):
        s = by_conf[c]
        rr = s[3]/s[2]*100 if s[2] else 0
        print(f"  自信度{c}: {s[0]}R ◎勝利{s[1]} 投資{s[2]:,}円 回収{s[3]:,}円 ({rr:.0f}%)")

    # JSON保存（PDCAレポート用）
    out = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260801\v5買い目_答え合わせ_20260801.json")
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
