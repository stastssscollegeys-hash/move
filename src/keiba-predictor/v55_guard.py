# -*- coding: utf-8 -*-
"""
v55_guard.py — v5.5 実戦ガード（SKILL.md「v5.5 実戦ガード」2026-08-18制定）の運用レイヤー

gen_kaime_v5.py（ベースライン・改変禁止）の出力ランキングに対して後段で適用する。
  ① 週次フィードバック制御: 直近週の◎3着内率が45%未満の週は「◎軸1頭固定・1点集中型」を全面禁止し
     分散型（BOX／2頭軸／○軸／穴軸／本命外し）のみ採用。50%回復で解除
  ② 若馬戦参加上限: 新馬・未勝利は1日2レースまで、かつ自信度9以上のみ
  ③ 軸集中の条件制限（週次制御が解除されている週に適用）: ◎軸1頭固定型は
     「◎のモデル勝率p − 大衆勝率q ≧ +5pt（過小評価の妙味）」の時のみ許可

使い方:
  from v55_guard import choose_pattern_v55, apply_young_cap, WEEKLY_CONTROL_ON
"""
from gen_kaime_v5 import choose_pattern, is_young_race, EV_MIN

# 2026-08-19 設定: 8/15-16週の◎3着内33% < 45% → 今週（8/22-23）は週次制御ON。
# 毎週のD終了後フェーズ（週次設定レビュー）で実測に基づき更新する。
WEEKLY_CONTROL_ON = True
WEEKLY_CONTROL_REASON = "8/15-16週の◎3着内率33%（<45%）→ 軸1頭固定パターン全面禁止・分散型のみ"
GAMI_MAX = 0.35
YOUNG_MAX_PER_DAY = 2
YOUNG_MIN_CONF = 9
AXIS_GAP_MIN = 0.05   # ③ p−q が+5pt以上で◎軸固定を許可

# ── ④ 実測ガード（2026-09-16・review_weekend.py の公開買い目27R・6日）─────────
# 実際に公開した買い目の回収率は35%（バックテストの71〜80%の半分以下）。分解すると:
#   3連複 74点・84,800円 → 6,090円（7%）。賭け金の42%をここに置いていた
#   🔥穴  3着内 3/25（12%）。同人気帯（平均8番人気）の平均は16%で上乗せ価値なし
# → 3連複・3連単を買い目に入れない／🔥穴を軸にしたパターンを選ばない。
#   （印としての🔥穴の表示は残す。ここで止めるのは「買い目の軸にすること」だけ）
# 正本: docs/keiba_roi100_roadmap.md §7-7,8
BANNED_TICKETS = {'3連複', '3連単'}
BAN_ANA_AXIS = True
# 穴・妙味馬を「軸」にするパターン（相手として絡めるだけのA2は3連複なので券種側で落ちる）
#   W5=△の穴を軸に◎○へ ／ A1=🔥穴軸を◎○へ ／ A3=穴軸3連複 ／ A4=穴2着馬単 ／ V系=妙味軸
ANA_AXIS_CODES = {'A1', 'A3', 'A4', 'W5', 'V1', 'V2', 'V3', 'V4'}


def uses_banned_ticket(res) -> bool:
    """res['bets'] = [(券種, 馬番idx, 金額, 想定オッズ), ...]"""
    return any(b[0] in BANNED_TICKETS for b in (res or {}).get('bets', []))

# 「◎軸1頭固定・1点集中型」（週次制御ONの週は禁止）
AXIS_FIXED = {
    'T1', 'T2', 'T3', 'T4', 'U1', 'U2', 'U3', 'U4', 'E1', 'E3', 'E4', 'E6',
    'W1', 'W2', 'W3', 'F2', 'F3', 'F4', 'F8', 'S1', 'S2', 'S3', 'S4', 'S5',
    'N1', 'V1', 'V4', 'X1', 'X2', 'X3',
}
# 分散型（印上位を広く使う／◎が飛んでも拾える構造）
DISPERSED = {
    'U5', 'U6', 'E2', 'E5', 'W4', 'W5', 'F1', 'F5', 'F6', 'F7', 'F9', 'O1',
    'S6', 'N2', 'N3', 'A1', 'A2', 'A3', 'A4', 'V2', 'V3', 'X4', 'X5',
}


def _code(name):
    return name.split(' ')[0]


def choose_pattern_v55(recs, budget, odds_override=None, weekly_control=WEEKLY_CONTROL_ON):
    """v5エンジンの全パターン評価結果からv5.5ガードを満たす最良パターンを選ぶ。
    戻り値: (name, desc, res, ranking, p, q, info)
      info = {'engine': エンジン素の選択名, 'changed': bool, 'reason': str}
    """
    name, desc, res, ranking, p, q = choose_pattern(recs, budget, odds_override)
    info = {'engine': name, 'changed': False, 'reason': ''}
    if not ranking:
        return name, desc, res, ranking, p, q, info

    # ◎のp−q（過小評価の妙味）
    h = next((i for i, r in enumerate(recs) if r.get('AI印') == '◎'), 0)
    gap = (p[h] - q[h]) if (p and q) else 0.0

    def allowed(code):
        if BAN_ANA_AXIS and code in ANA_AXIS_CODES:
            return False
        if weekly_control:
            return code in DISPERSED
        if code in AXIS_FIXED:
            return gap >= AXIS_GAP_MIN
        return True

    if name is not None and allowed(_code(name)) and not uses_banned_ticket(res):
        return name, desc, res, ranking, p, q, info

    for nm, ds, rs in ranking:
        if not allowed(_code(nm)) or uses_banned_ticket(rs):
            continue
        if rs['E_rate'] >= EV_MIN and rs['gami_ratio'] <= GAMI_MAX:
            info.update(changed=True,
                        reason=(f"週次制御: {_code(name) if name else '見送り'}→{_code(nm)}（軸1頭固定禁止）"
                                if weekly_control else
                                f"軸集中制限: ◎p−q={gap*100:+.1f}pt<+5pt → {_code(nm)}"))
            return nm, ds, rs, ranking, p, q, info
    info.update(changed=(name is not None),
                reason=("週次制御: 分散型で基準（E115%×ガミ35%）を満たすパターンなし → 見送り"
                        if weekly_control else "軸集中制限: 許可パターンなし → 見送り"))
    return None, None, None, ranking, p, q, info


def apply_young_cap(keys, races, conf):
    """若馬戦（新馬・未勝利）は日ごとに自信度9以上の上位2レースのみ参加。
    戻り値: (参加キー集合, 除外理由dict{key: reason})"""
    from collections import defaultdict
    by_day = defaultdict(list)
    dropped = {}
    keep = set()
    for k in keys:
        title = races[k][0].get('レース名', '')
        if is_young_race(title):
            by_day[k[0]].append(k)
        else:
            keep.add(k)
    for day, ks in by_day.items():
        ks = sorted(ks, key=lambda k: (-conf[k][0], k[1], k[2]))
        n = 0
        for k in ks:
            c = conf[k][0]
            if c < YOUNG_MIN_CONF:
                dropped[k] = f"若馬戦上限: 自信度{c}<{YOUNG_MIN_CONF}"
            elif n >= YOUNG_MAX_PER_DAY:
                dropped[k] = f"若馬戦上限: 1日{YOUNG_MAX_PER_DAY}レースまで"
            else:
                keep.add(k); n += 1
    return keep, dropped
