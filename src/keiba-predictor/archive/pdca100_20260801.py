# -*- coding: utf-8 -*-
"""
pdca100_20260801.py — 100回PDCAループ（累積DB 9,722レコード / 720レース）

1ラウンド=1仮説の検証。前計算可能な「クリーン因子」（当該レースの結果に依存しない
F04-F17のサブセット）だけで事前スコアを構成し、日付で学習/検証分割して評価する。

ラウンド構成:
  R001-040: クリーン因子の重みランダム探索（目的関数=rank1複勝率+単勝ROI）
  R041-060: 単勝オッズ帯別ROI検証（クリーンrank1）
  R061-075: 2頭軸（rank1×rank2）ワイド的中率のセグメント検証
  R076-090: セグメントフィルタ仮説（若馬戦/会場/頭数/距離/妙味人気帯）
  R091-100: 自信度プロキシ較正（スコア差→複勝率マップ・若馬キャップ）

出力: コンソール + JSON + Word要約
"""
import sys, json, random
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from collections import defaultdict

DB_PATH = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'race_results.json'
OUT_DIR = Path.home() / 'Desktop' / '競馬予想レポート' / '20260801'
random.seed(20260801)

CLEAN_FACTORS = ['F04_騎手', 'F05_厩舎', 'F06_枠', 'F07_馬番', 'F09_体重', 'F10_斤量',
                 'F11_性別', 'F12_年齢', 'F13_クラス', 'F14_馬場', 'F15_EV', 'F16_乖離', 'F17_頭数']


def load_races():
    with open(DB_PATH, encoding='utf-8') as f:
        db = json.load(f)
    races = defaultdict(list)
    for e in db:
        c = e.get('着順int', 99)
        if c >= 90:
            continue
        try:
            e['_odds'] = float(e.get('単勝オッズ') or 0)
            e['_ninki'] = int(float(e.get('人気') or 0))
        except (TypeError, ValueError):
            e['_odds'], e['_ninki'] = 0.0, 0
        races[(e['date'], e['競馬場'], int(e['R']))].append(e)
    # 6頭未満は除外
    return {k: v for k, v in races.items() if len(v) >= 6}


def clean_score(e, w):
    return sum(e.get(f, 50.0) * w[i] for i, f in enumerate(CLEAN_FACTORS))


def eval_weights(race_keys, races, w):
    """rank1の複勝率と単勝ROIを返す"""
    n = 0; top3 = 0; inv = 0; ret = 0
    for k in race_keys:
        horses = races[k]
        best = max(horses, key=lambda e: clean_score(e, w))
        n += 1
        if best['着順int'] <= 3:
            top3 += 1
        inv += 100
        if best['着順int'] == 1 and best['_odds'] > 0:
            ret += best['_odds'] * 100
    return (top3 / n if n else 0), (ret / inv if inv else 0), n


def objective(t3, roi):
    return 0.5 * t3 + 0.5 * min(roi, 2.0) / 2.0


def main():
    races = load_races()
    dates = sorted(set(k[0] for k in races))
    split = dates[int(len(dates) * 0.7)]
    train_keys = [k for k in races if k[0] <= split]
    valid_keys = [k for k in races if k[0] > split]
    print(f"累積DB: {len(races)}レース（学習{len(train_keys)} / 検証{len(valid_keys)}・分割日{split}）")

    rounds_log = []
    adopted = []

    def log_round(rid, phase, hypothesis, result, adopt, detail=""):
        rounds_log.append({'round': rid, 'phase': phase, 'hypothesis': hypothesis,
                           'result': result, 'adopt': adopt, 'detail': detail})
        mark = "✅採用" if adopt else "─棄却"
        if adopt or rid % 10 == 0:
            print(f"  R{rid:03d} [{phase}] {hypothesis[:44]:<44} {result[:42]:<42} {mark}")

    # ============================================================
    # Phase 1 (R001-040): 重みランダム探索
    # ============================================================
    print("\n[Phase1] クリーン因子 重み探索（R001-040）")
    base_w = [1.0 / len(CLEAN_FACTORS)] * len(CLEAN_FACTORS)
    t3, roi, _ = eval_weights(train_keys, races, base_w)
    vt3, vroi, _ = eval_weights(valid_keys, races, base_w)
    best_w, best_j = base_w[:], objective(t3, roi)
    log_round(0, 'P1', '均等重みベースライン',
              f"train複勝{t3*100:.1f}%/ROI{roi*100:.0f}% valid複勝{vt3*100:.1f}%", True)

    for rid in range(1, 41):
        w = [max(0.0, x * random.uniform(0.4, 1.8)) for x in best_w]
        s = sum(w) or 1
        w = [x / s for x in w]
        t3, roi, _ = eval_weights(train_keys, races, w)
        j = objective(t3, roi)
        adopt = False
        detail = ""
        if j > best_j + 1e-4:
            vt3_new, vroi_new, _ = eval_weights(valid_keys, races, w)
            if vt3_new >= vt3 - 0.02:
                best_w, best_j = w, j
                vt3, vroi = vt3_new, vroi_new
                adopt = True
                top_f = sorted(zip(CLEAN_FACTORS, w), key=lambda x: -x[1])[:3]
                detail = " / ".join(f"{f.split('_')[1]}{x:.2f}" for f, x in top_f)
        log_round(rid, 'P1', f"重み摂動#{rid}",
                  f"train J={j:.3f} 複勝{t3*100:.1f}% ROI{roi*100:.0f}%", adopt, detail)
    ft3, froi, _ = eval_weights(train_keys, races, best_w)
    print(f"  → 最終重み: train複勝{ft3*100:.1f}%/単勝ROI{froi*100:.0f}% valid複勝{vt3*100:.1f}%/ROI{vroi*100:.0f}%")
    top5_w = sorted(zip(CLEAN_FACTORS, best_w), key=lambda x: -x[1])[:5]
    print("  → 上位因子: " + " / ".join(f"{f}={x:.3f}" for f, x in top5_w))
    adopted.append(f"クリーン因子最適重み: 上位= " + ", ".join(f"{f.split('_')[1]}{x:.2f}" for f, x in top5_w))

    # 全レースにclean rank付与（以降のPhaseで使用）
    rank_map = {}
    for k, horses in races.items():
        order = sorted(horses, key=lambda e: -clean_score(e, best_w))
        rank_map[k] = order

    # ============================================================
    # Phase 2 (R041-060): 単勝オッズ帯検証
    # ============================================================
    print("\n[Phase2] クリーンrank1 単勝オッズ帯ROI（R041-060）")
    bands = [(1.0, 1.9), (1.9, 2.6), (2.6, 3.5), (3.5, 5.0), (5.0, 7.0), (7.0, 10.0),
             (10.0, 15.0), (15.0, 25.0), (25.0, 50.0), (50.0, 999.0)]
    rid = 41
    for lo, hi in bands:
        for split_name, keys in (('train', train_keys), ('valid', valid_keys)):
            if rid > 60:
                break
            n = inv = ret = wins = 0
            for k in keys:
                b = rank_map[k][0]
                if lo <= b['_odds'] < hi:
                    n += 1; inv += 100
                    if b['着順int'] == 1:
                        wins += 1; ret += b['_odds'] * 100
            roi_b = ret / inv if inv else 0
            adopt = (roi_b >= 1.0 and n >= 15)
            log_round(rid, 'P2', f"rank1単勝 オッズ{lo}-{hi} ({split_name})",
                      f"n={n} 勝率{wins/max(n,1)*100:.0f}% ROI{roi_b*100:.0f}%", adopt)
            if adopt:
                adopted.append(f"単勝オッズ帯{lo}-{hi}({split_name}): n={n} ROI{roi_b*100:.0f}%")
            rid += 1

    # ============================================================
    # Phase 3 (R061-075): 2頭軸ワイド的中セグメント
    # ============================================================
    print("\n[Phase3] rank1×rank2 2頭軸ワイド的中率（R061-075）")
    def wide_hit_rate(keys, cond=lambda k, h: True):
        n = hit = 0
        for k in keys:
            order = rank_map[k]
            if len(order) < 2 or not cond(k, order):
                continue
            n += 1
            if order[0]['着順int'] <= 3 and order[1]['着順int'] <= 3:
                hit += 1
        return n, (hit / n if n else 0)

    segs = [
        ("全体", lambda k, o: True),
        ("若馬戦(新馬未勝利)", lambda k, o: ('新馬' in o[0].get('レース名','')) or ('未勝利' in o[0].get('レース名',''))),
        ("古馬条件戦", lambda k, o: not (('新馬' in o[0].get('レース名','')) or ('未勝利' in o[0].get('レース名',''))) ),
        ("頭数<=10", lambda k, o: len(o) <= 10),
        ("頭数>=15", lambda k, o: len(o) >= 15),
        ("芝", lambda k, o: '芝' in str(o[0].get('距離',''))),
        ("ダート", lambda k, o: 'ダ' in str(o[0].get('距離',''))),
        ("短距離<=1400", lambda k, o: any(str(d) in str(o[0].get('距離','')) for d in [1000,1150,1200,1400])),
        ("rank2が5番人気以下", lambda k, o: o[1]['_ninki'] >= 5),
        ("rank1が1-2番人気", lambda k, o: 1 <= o[0]['_ninki'] <= 2),
        ("rank1が4番人気以下(妙味)", lambda k, o: o[0]['_ninki'] >= 4),
        ("札幌", lambda k, o: k[1] == '札幌'),
        ("新潟", lambda k, o: k[1] == '新潟'),
        ("中京", lambda k, o: k[1] == '中京'),
        ("函館", lambda k, o: k[1] == '函館'),
    ]
    base_n, base_rate = wide_hit_rate(list(races.keys()))
    for i, (name, cond) in enumerate(segs):
        rid = 61 + i
        n, rate = wide_hit_rate(list(races.keys()), cond)
        adopt = (rate >= base_rate + 0.05 and n >= 30)
        log_round(rid, 'P3', f"2頭軸ワイド: {name}",
                  f"n={n} 的中率{rate*100:.1f}%（全体{base_rate*100:.1f}%）", adopt)
        if adopt:
            adopted.append(f"2頭軸ワイド優位セグメント「{name}」: 的中率{rate*100:.1f}% (全体+{(rate-base_rate)*100:.1f}pt)")

    # ============================================================
    # Phase 4 (R076-090): 戦略フィルタ仮説
    # ============================================================
    print("\n[Phase4] 戦略フィルタ仮説（R076-090）")
    def strat_roi(keys, pick, cond=lambda k, o: True):
        """pick: order -> horse or None（単勝100円）"""
        n = inv = ret = 0
        for k in keys:
            order = rank_map[k]
            if not cond(k, order):
                continue
            b = pick(order)
            if b is None:
                continue
            n += 1; inv += 100
            if b['着順int'] == 1:
                ret += b['_odds'] * 100
        return n, (ret / inv if inv else 0)

    hypos = [
        ("若馬戦でrank1単勝", lambda o: o[0],
         lambda k, o: ('新馬' in o[0].get('レース名','')) or ('未勝利' in o[0].get('レース名',''))),
        ("若馬戦でrank2単勝", lambda o: o[1] if len(o) > 1 else None,
         lambda k, o: ('新馬' in o[0].get('レース名','')) or ('未勝利' in o[0].get('レース名',''))),
        ("古馬戦でrank1単勝", lambda o: o[0],
         lambda k, o: not (('新馬' in o[0].get('レース名','')) or ('未勝利' in o[0].get('レース名',''))) ),
        ("rank1(4番人気以下)単勝=妙味", lambda o: o[0] if o[0]['_ninki'] >= 4 else None,
         lambda k, o: True),
        ("rank1(6番人気以下)単勝=大穴", lambda o: o[0] if o[0]['_ninki'] >= 6 else None,
         lambda k, o: True),
        ("rank1が1番人気の時のrank2単勝", lambda o: o[1] if (o[0]['_ninki'] == 1 and len(o) > 1) else None,
         lambda k, o: True),
        ("重賞・特別戦のrank1単勝", lambda o: o[0],
         lambda k, o: ('S' in o[0].get('レース名','')) or ('特別' in o[0].get('レース名','')) or ('賞' in o[0].get('レース名',''))),
        ("頭数<=10でrank1単勝", lambda o: o[0], lambda k, o: len(o) <= 10),
        ("頭数>=15でrank1単勝", lambda o: o[0], lambda k, o: len(o) >= 15),
        ("札幌rank1単勝", lambda o: o[0], lambda k, o: k[1] == '札幌'),
        ("新潟rank1単勝", lambda o: o[0], lambda k, o: k[1] == '新潟'),
        ("中京rank1単勝", lambda o: o[0], lambda k, o: k[1] == '中京'),
        ("ダートrank1単勝", lambda o: o[0], lambda k, o: 'ダ' in str(o[0].get('距離',''))),
        ("芝rank1単勝", lambda o: o[0], lambda k, o: '芝' in str(o[0].get('距離',''))),
        ("rank1かつオッズ3-10倍のみ単勝", lambda o: o[0] if 3.0 <= o[0]['_odds'] < 10.0 else None,
         lambda k, o: True),
    ]
    for i, (name, pick, cond) in enumerate(hypos):
        rid = 76 + i
        tn, troi = strat_roi(train_keys, pick, cond)
        vn, vroi_ = strat_roi(valid_keys, pick, cond)
        adopt = (troi >= 0.95 and vroi_ >= 0.95 and tn >= 20 and vn >= 8)
        log_round(rid, 'P4', name,
                  f"train n={tn} ROI{troi*100:.0f}% / valid n={vn} ROI{vroi_*100:.0f}%", adopt)
        if adopt:
            adopted.append(f"戦略「{name}」: train ROI{troi*100:.0f}%×valid ROI{vroi_*100:.0f}%")

    # ============================================================
    # Phase 5 (R091-100): 自信度プロキシ較正
    # ============================================================
    print("\n[Phase5] 自信度較正（R091-100）")
    # スコア差デシル → rank1複勝率
    gaps = []
    for k, order in rank_map.items():
        if len(order) >= 2:
            g = clean_score(order[0], best_w) - clean_score(order[1], best_w)
            gaps.append((g, order[0]['着順int'] <= 3, order[0]['着順int'] == 1,
                         ('新馬' in order[0].get('レース名','')) or ('未勝利' in order[0].get('レース名',''))))
    gaps.sort(key=lambda x: x[0])
    n_dec = len(gaps) // 5
    for d in range(5):
        rid = 91 + d
        chunk = gaps[d*n_dec:(d+1)*n_dec] if d < 4 else gaps[4*n_dec:]
        t3r = sum(1 for _, t3_, _, _ in chunk if t3_) / len(chunk)
        wr = sum(1 for _, _, w_, _ in chunk if w_) / len(chunk)
        lo, hi = chunk[0][0], chunk[-1][0]
        adopt = d == 4 and t3r >= 0.75
        log_round(rid, 'P5', f"スコア差 第{d+1}五分位({lo:.2f}〜{hi:.2f})",
                  f"n={len(chunk)} 複勝率{t3r*100:.0f}% 勝率{wr*100:.0f}%", adopt)
        if adopt:
            adopted.append(f"スコア差上位20%（差{lo:.2f}+）: rank1複勝率{t3r*100:.0f}% → 高自信度の定量根拠")

    # 若馬 vs 古馬 rank1成績比較（R096-098）
    yg = [(t3_, w_) for _, t3_, w_, y in gaps if y]
    og = [(t3_, w_) for _, t3_, w_, y in gaps if not y]
    y_t3 = sum(1 for t, _ in yg if t) / max(len(yg), 1)
    o_t3 = sum(1 for t, _ in og if t) / max(len(og), 1)
    y_w = sum(1 for _, w in yg if w) / max(len(yg), 1)
    o_w = sum(1 for _, w in og if w) / max(len(og), 1)
    log_round(96, 'P5', "若馬戦rank1成績",
              f"n={len(yg)} 複勝{y_t3*100:.0f}% 勝率{y_w*100:.0f}%", False)
    log_round(97, 'P5', "古馬戦rank1成績",
              f"n={len(og)} 複勝{o_t3*100:.0f}% 勝率{o_w*100:.0f}%", False)
    cap_needed = (o_t3 - y_t3) >= 0.03 or (o_w - y_w) >= 0.03
    log_round(98, 'P5', "若馬戦の自信度キャップ要否",
              f"若馬-古馬差: 複勝{(y_t3-o_t3)*100:+.1f}pt 勝率{(y_w-o_w)*100:+.1f}pt", cap_needed)
    if cap_needed:
        adopted.append(f"若馬戦キャップ妥当: rank1成績が古馬比 複勝{(y_t3-o_t3)*100:+.1f}pt/勝率{(y_w-o_w)*100:+.1f}pt")
    else:
        adopted.append(f"若馬戦rank1成績は古馬と同等（複勝{y_t3*100:.0f}% vs {o_t3*100:.0f}%）→ 8/1の敗因は「事前clean情報の薄さ」でありDB結果ベースでは差が出ない。買い目側ガード(v5.2)は維持")

    # R099: 人気とcleanランクの乖離馬（妙味）top3率
    n_v = hit_v = 0
    for k, order in rank_map.items():
        b = order[0]
        if b['_ninki'] >= 4:
            n_v += 1
            if b['着順int'] <= 3:
                hit_v += 1
    vrate = hit_v / max(n_v, 1)
    log_round(99, 'P5', "妙味馬(clean1位×4番人気以下)複勝率",
              f"n={n_v} 複勝率{vrate*100:.0f}%", vrate >= 0.45)
    if vrate >= 0.45:
        adopted.append(f"妙味馬(clean1位×4人気以下)複勝率{vrate*100:.0f}% → ワイド軸として有効（実オッズ確認前提）")

    # R100: 総括
    log_round(100, 'P5', "総括ラウンド", f"採用{len(adopted)}項目 / 100ラウンド完了", True)

    # ── 保存 ─────────────────────────────────────────
    out_json = OUT_DIR / "PDCA100_結果_20260801.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({'rounds': rounds_log, 'adopted': adopted,
                   'best_weights': dict(zip(CLEAN_FACTORS, best_w))},
                  f, ensure_ascii=False, indent=1)

    print(f"\n{'='*90}")
    print(f"100回PDCA完了 — 採用{len(adopted)}項目")
    print(f"{'='*90}")
    for a in adopted:
        print(f"  ✅ {a}")
    print(f"\n[保存] {out_json}")


if __name__ == '__main__':
    main()
