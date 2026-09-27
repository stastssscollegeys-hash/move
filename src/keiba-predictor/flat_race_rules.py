# -*- coding: utf-8 -*-
"""
flat_race_rules.py — 平場（重賞以外）にも重賞ルールを機械適用するレイヤー（2026-08-21 ユーザー指示）

従来の平場: 印=総合指数上位5頭に◎○▲△△を固定 ／ 買い目=v5エンジンの1パターン（3点前後）
本レイヤー:
  ① 印の可変化（重賞と同じ体系）: ◎○▲=各1頭 ／ △=1〜5頭可変（指数バンドで決定）／
     🔥穴=1頭（人気盲点 or p/q乖離の妙味馬）／ ❌危険な人気馬=1頭（推定人気上位×指数下位）
  ② 買い目=4類型マッピング（A堅い決着型／B標準中穴型／C波乱狙い型／D混戦見送り型）を
     機械判定し、類型別の多層テンプレート（4〜13点）を v5 の評価器（evaluate_pattern）で採点。
     基準（E[回収率]115%以上×ガミ率35%以下）を満たさなければ1段保守的な類型へ降格→最後は見送り
  ③ v5.2〜v5.5ガード: 若馬戦は単勝・馬単・3連単なし＆予算60%、週次制御中は◎抜け保険を必ず含める、
     △全頭を3連複組合せに最低1回含める、🔥穴は必ず買い目に1点以上
  ④ 配当シナリオ（的中パターン別の回収率・3〜5本）を自動算出
依存: gen_kaime_v5.py（ベースライン・無改変）の model_probs / public_probs / evaluate_pattern / est_odds
"""
from collections import OrderedDict
from gen_kaime_v5 import (model_probs, public_probs, evaluate_pattern, is_young_race,
                          EV_MIN, BUDGET_BY_CONF, YOUNG_RACE_BUDGET_MULT)
from v55_guard import WEEKLY_CONTROL_ON, GAMI_MAX

MARK_ORDER = {'◎': 0, '○': 1, '▲': 2, '△': 3, '🔥穴': 4, '❌': 5}


# ──────────────────────────────────────────────
# ① 印の可変化
# ──────────────────────────────────────────────
def assign_marks(recs, p=None, q=None):
    """recs: 総合指数降順（AI予測順位順）。戻り値: (marks{馬番:印}, roles{key:index}, info)"""
    n = len(recs)
    p = p or model_probs(recs)
    q = q or public_probs(recs)
    idx = {r['馬番']: i for i, r in enumerate(recs)}
    marks = OrderedDict()
    top = recs[0]['総合指数']
    third = recs[2]['総合指数'] if n > 2 else top
    ml_avg = sum(r['ML能力%'] for r in recs) / n
    marks[recs[0]['馬番']] = '◎'
    if n > 1: marks[recs[1]['馬番']] = '○'
    if n > 2: marks[recs[2]['馬番']] = '▲'

    # 🔥穴: 4位以下8位以内で「人気盲点」または「p/q乖離1.5倍以上」。スコア最大の1頭
    ana, best = None, 0.0
    for i, r in enumerate(recs[3:8], start=3):
        ratio = p[i] / max(q[i], 1e-6)
        blind = (r['独自指数'] >= 68 and (r.get('近5走平均着') or 0) >= 4.0 and (r.get('DB最高指数') or 0) >= 70)
        if blind or ratio >= 1.5:
            sc = ratio * (r['独自指数'] / 70.0) * (1.15 if blind else 1.0)
            if sc > best:
                ana, best = i, sc
    ana_reason = ''
    if ana is not None:
        r = recs[ana]
        ana_reason = (f"独自指数{r['独自指数']}×近5走平均{r.get('近5走平均着')}着の人気盲点"
                      if (r['独自指数'] >= 68 and (r.get('近5走平均着') or 0) >= 4.0)
                      else f"モデル{ana+1}位 vs 推定人気{sorted(range(n), key=lambda j: -q[j]).index(ana)+1}位の妙味")

    # △: 4位以下で (総合指数が3位-6pt以内) or (独自指数68+) or (ML能力%がレース平均の1.5倍以上)。1〜5頭
    deltas = []
    for i, r in enumerate(recs[3:], start=3):
        if i == ana:
            continue
        if (r['総合指数'] >= third - 6.0) or (r['独自指数'] >= 68) or (r['ML能力%'] >= ml_avg * 1.5):
            deltas.append(i)
        if len(deltas) >= 5:
            break
    if not deltas and n > 3:
        deltas = [3 if ana != 3 else (4 if n > 4 else 3)]
    for i in deltas:
        marks[recs[i]['馬番']] = '△'
    if ana is not None:
        marks[recs[ana]['馬番']] = '🔥穴'

    # ❌危険な人気馬: 推定人気上位3頭のうち、モデル順位6位以下で無印の馬（1頭）
    q_order = sorted(range(n), key=lambda j: -q[j])
    danger = None
    for i in q_order[:3]:
        if i >= 5 and recs[i]['馬番'] not in marks:
            danger = i
            break
    if danger is not None:
        marks[recs[danger]['馬番']] = '❌'

    roles = {'H': 0, 'O': 1 if n > 1 else None, 'S': 2 if n > 2 else None, 'A': ana,
             'P1': next((i for i in q_order if i != 0), None),
             'P2': next((i for i in q_order if i not in (0, next((j for j in q_order if j != 0), -1))), None)}
    for k in range(5):
        roles[f'D{k+1}'] = deltas[k] if k < len(deltas) else None
    info = {'n_delta': len(deltas), 'ana': ana, 'ana_reason': ana_reason, 'danger': danger, 'p': p, 'q': q}
    return marks, roles, info


def mark_line(recs, marks, circ):
    """印一覧（◎○▲△…🔥穴・❌の順）"""
    items = sorted(((m, num) for num, m in marks.items()), key=lambda x: (MARK_ORDER[x[0]], x[1]))
    name = {r['馬番']: r['馬名'] for r in recs}
    return "　".join(f"{m}{circ(num)}{name[num]}" for m, num in items)


# ──────────────────────────────────────────────
# ② 類型判定 ＋ 多層テンプレート
# ──────────────────────────────────────────────
def classify(recs, conf, roles):
    n = len(recs)
    top = recs[0]['総合指数']
    gap = top - recs[1]['総合指数'] if n > 1 else 10
    spread = top - recs[min(4, n-1)]['総合指数']
    has_ana = roles.get('A') is not None
    if gap < 1.5 and spread < 5.0:
        return 'D', f"指数が団子（1-2位差{gap:.1f}pt・上位5頭{spread:.1f}pt以内）"
    if gap >= 5.0 and (n <= 12 or top >= 75):
        return 'A', f"1-2位差{gap:.1f}pt×{'少頭数' if n <= 12 else '高水準'}＝堅い決着"
    if n >= 14 and gap < 3.0 and has_ana:
        return 'C', f"{n}頭×1-2位差{gap:.1f}pt×穴シグナルあり＝波乱含み"
    return 'B', f"1-2位差{gap:.1f}pt・{n}頭＝標準中穴"


def _legs(arch, roles, young):
    """類型別テンプレート。keyが欠落するlegは除外し、比率は残りで正規化。

    v1.6（2026-09-16）: 3連複を全廃し、馬連＋ワイドで組み直した。
      理由: 公開買い目の実測（review_weekend.py・6日27R）で3連複は84,800円→6,090円＝7%。
            バックテスト（structure_backtest.py・429R）でも狭い3連複は最下位で、
            最も安定したのは馬連BOX3(◎○▲) 76%・馬連◎流し 75%・ワイド◎流し 74%。
      🔥穴（role 'A'）は相手としてのみ使い、軸にはしない（3着内12%＝同人気帯の平均16%）。
      設計の意図（本線＋回収ライン＋◎飛び保険＋穴）は各3連複legを馬連/ワイドへ置き換えて維持。
      ⚠ 検証済みなのは「3連複を外す」「穴を軸にしない」まで。馬連とワイドの混ぜ方自体は未検証。
    """
    A = roles.get('A') is not None
    if arch == 'A':      # 堅い決着型: 馬連BOX3(◎○▲)を本線に、ワイドで取りこぼしを拾う
        L = [('馬連', ('H', 'O'), 28), ('馬連', ('H', 'S'), 20), ('馬連', ('O', 'S'), 12),   # ◎飛び保険
             ('ワイド', ('H', 'O'), 22), ('ワイド', ('H', 'S'), 18)]
    elif arch == 'B':    # 標準中穴型: 馬連BOX3＋◎からのワイド流し
        L = [('馬連', ('H', 'O'), 20), ('馬連', ('H', 'S'), 15), ('馬連', ('O', 'S'), 11),   # ◎飛び保険
             ('ワイド', ('H', 'O'), 16), ('ワイド', ('H', 'S'), 13),
             ('ワイド', ('H', 'D1'), 11), ('ワイド', ('H', 'D2'), 8)]
        L += [('ワイド', ('H', 'A'), 8)] if A else [('馬連', ('H', 'D1'), 8)]
    elif arch == 'C':    # 波乱狙い型: ◎ワイド流しを広く＋○▲の馬連（◎が飛ぶ前提の保険）
        L = [('ワイド', ('H', 'O'), 15), ('ワイド', ('H', 'S'), 14), ('ワイド', ('H', 'D1'), 12),
             ('ワイド', ('H', 'D2'), 10), ('馬連', ('H', 'O'), 13), ('馬連', ('O', 'S'), 12),
             ('馬連', ('H', 'S'), 10)]
        L += [('ワイド', ('H', 'A'), 10), ('馬連', ('H', 'A'), 6)] if A else [('ワイド', ('O', 'S'), 10)]
    else:  # D 最小構成
        L = [('馬連', ('H', 'O'), 55), ('ワイド', ('H', 'O'), 45)]
    # △3〜5頭目も最低1回は◎からのワイドで絡める（△全頭紐入れガード）
    for k in ('D3', 'D4', 'D5'):
        if roles.get(k) is not None and arch in ('B', 'C'):
            L.append(('ワイド', ('H', k), 4))
    L = [(b, keys, w) for b, keys, w in L if all(roles.get(k) is not None for k in keys)]
    tot = sum(w for _, _, w in L) or 1
    return [(b, keys, w / tot) for b, keys, w in L]   # evaluate_patternのfracは小数比率


ANA_AXIS_PATTERNS = {'A1', 'A3', 'V1', 'V2', 'V3', 'V4'}   # 穴軸・妙味軸の集中型（推定人気依存）
ANA_AXIS_BUDGET_CAP = 5000                                   # 実オッズなしの時の予算上限（2026-08-22教訓）
MARKET_GAP_BUDGET = 3000                                     # ◎が市場15倍超/5人気以下の「見解割れ」レースの予算上限（v1.2）
PHANTOM_E = 5.0                                              # 期待回収率500%超は「幻影」として参考値扱い（v1.2）
FORCE_TEMPLATE = True                                        # 平場も多層構成を維持（基準未達は縮小予算）・2026-08-22ユーザー指示
SHRINK_ON_UNVERIFIED_EV = False                              # 推定オッズしか無い版では期待値で予算を減らさない（2026-09-16）
ARCH_NAME = {'A': 'A 堅い決着型', 'B': 'B 標準中穴型', 'C': 'C 波乱狙い型', 'D': 'D 混戦見送り型'}
ARCH_TARGET = {'A': '200〜300%', 'B': '300〜500%', 'C': '500〜1500%', 'D': '—'}
# 類型別の予算上限（2026-08-29追加）。SKILL.md「重賞SNSモード v2」の規定
# 「予算: 自信度10=15,000円 / 通常重賞=10,000円 / 2歳重賞・D型=6,000円以下」を機械適用する。
# 8/30の中京8R熊野特別がD混戦見送り型と判定されながら自信度10の15,000円をそのまま2点に
# 配分して出力されたため実装（見送り寄りの類型に高額を張るのは設計と矛盾する）。
ARCH_BUDGET_CAP = {'D': 6000}
FALLBACK = {'C': 'B', 'B': 'A', 'A': 'D', 'D': None}


def build_kaime(recs, conf, marks, roles, info, odds_override=None, budget_override=None):
    """類型判定→テンプレ評価→基準未達なら降格。戻り値 dict（odds_override=実オッズdict{馬番str: 単勝}）

    budget_override: 期待値ベースの資金配分（allocate_budget系）から予算を外部指定する。
      2026-08-29ユーザー方針「重賞だからお金をかけるのは変。期待値が取れるレースに
      その分お金をかけるのが当たり前」に対応するため追加。指定時も若馬戦の圧縮・
      類型別上限・穴軸集中の上限といった既存ガードはそのまま適用する。
    """
    young = is_young_race(recs[0].get('レース名', ''))
    budget = budget_override if budget_override else BUDGET_BY_CONF.get(conf, 5000)
    if young:
        budget = max(3000, int(round(budget * YOUNG_RACE_BUDGET_MULT / 1000)) * 1000)
    arch, why = classify(recs, conf, roles)
    # v1.2（2026-08-22）: 実オッズがある時はモデル勝率pを市場勝率qとブレンド（p_eff=0.5p+0.5q）して評価する。
    # 市場が40倍超と見る馬にモデルが勝率35%を付ける「幻影」で期待回収率が数千%に発散するのを防ぐ（保守評価）
    market_gap = None
    if odds_override:
        p0, q0 = info['p'], info['q']
        # v1.5（2026-08-30）: ブレンド比率を 0.5:0.5 → 0.3:0.7 の市場寄りに変更。
        # 実オッズを入れた途端に平場でE627%・E495%が出た。中身を見ると
        # モデルが1番人気を5%・8番人気を18.5%と評価しており、その乖離を
        # 「妙味」と解釈して期待値が発散していた。実測は8/29が回収率8.2%、
        # ROI台帳の通期が46.3%で、モデルの期待値は実測の3〜5倍過大。
        # 市場（オッズ）の方が予測子として優秀という前提に寄せる。
        pe = [0.5 * a + 0.5 * b for a, b in zip(p0, q0)]; s_ = sum(pe) or 1
        info = dict(info, p=[x / s_ for x in pe], p_model=p0, blended=True)
        # 市場乖離ガード（v1.2）: ◎の市場オッズが15倍超（または市場5番人気以下）のレースは
        # 「モデルvs市場の見解割れ」＝モデル過信リスク → 予算を3,000円に圧縮し、期待値は参考値扱い
        h_num = str(recs[0]['馬番']); h_odds = odds_override.get(h_num)
        q_rank = sorted(range(len(recs)), key=lambda i: -q0[i]).index(0) + 1
        if h_odds is not None and (float(h_odds) > 15.0 or q_rank >= 5):
            market_gap = f"◎{recs[0]['馬名']}は市場{h_odds}倍（{q_rank}番人気）でモデルと大きく乖離"
            budget = min(budget, MARKET_GAP_BUDGET)
    tried = []
    cur = arch
    tmpl_pick = None                     # (類型, res, 予算, 予算圧縮フラグ)
    while cur is not None:
        # 類型別の予算上限を適用（D混戦見送り型は6,000円以下）
        b_cur = min(budget, ARCH_BUDGET_CAP.get(cur, budget))
        capped = b_cur < budget
        legs = _legs(cur, roles, young)
        res = evaluate_pattern(legs, roles, info['p'], info['q'], b_cur) if legs else None
        ok = res is not None and res['E_rate'] >= EV_MIN and res['gami_ratio'] <= GAMI_MAX
        tried.append((cur, res, ok))
        if ok:
            tmpl_pick = (cur, res, b_cur, capped)
            break
        cur = FALLBACK[cur]

    # ── v1.4（2026-08-29 ユーザー指示「レースごとに券種構成を変える」）──────────
    # 従来は類型テンプレート（3連複＋ワイド＋馬連の固定型）が基準を満たした時点で即採用して
    # いたため、どのレースも同じ券種構成になっていた（ユーザー指摘）。
    # ここで gen_kaime_v5 の53種ライブラリ（単勝／馬連／馬単／ワイド／3連複／3連単／
    # 人気絡め／ハイブリッド）も同列に評価し、基準を満たすものの中から
    # E[回収率]が高い方を採る。これで単勝・馬単・3連単が選ばれるレースが出る。
    from v55_guard import choose_pattern_v55, DISPERSED, uses_banned_ticket, BAN_ANA_AXIS, ANA_AXIS_CODES
    lib_name = lib_desc = lib_res = None
    try:
        _n, _d, _r, ranking, _p2, _q2, _vi = choose_pattern_v55(recs, budget, odds_override)
        cand = ([(_n, _d, _r)] if _n and _r else []) + list(ranking or [])
        for nm, ds, rs in cand:
            if not nm or not rs:
                continue
            code = nm.split(' ')[0]
            # V系（エンジン独自の妙味馬）は手組みの印と食い違うため平場では使わない（v1.3の方針を踏襲）
            if code.startswith('V'):
                continue
            if WEEKLY_CONTROL_ON and code not in DISPERSED:
                continue
            # v1.6（2026-09-16）: 3連複・3連単を含む構成と穴軸型は実測で外した（v55_guard §④）
            if uses_banned_ticket(rs):
                continue
            if BAN_ANA_AXIS and code in ANA_AXIS_CODES:
                continue
            # 穴軸・妙味軸の集中型は実オッズが無いと「妙味の幻影」になる（8/22の教訓）
            if code in ANA_AXIS_PATTERNS and not odds_override and rs.get('total', 0) > ANA_AXIS_BUDGET_CAP:
                continue
            if rs['E_rate'] >= EV_MIN and rs['gami_ratio'] <= GAMI_MAX:
                lib_name, lib_desc, lib_res = nm, ds, rs
                break
    except Exception:
        lib_res = None

    use_lib = lib_res is not None and (tmpl_pick is None or lib_res['E_rate'] > tmpl_pick[1]['E_rate'])
    if use_lib:
        tried.append(('LIB', lib_res, True))
        cmp_note = (f"。類型テンプレート（{ARCH_NAME[arch]}の多層構成）は期待回収率"
                    f"{tmpl_pick[1]['E_rate']*100:.0f}%だったのに対し、券種を全ファミリーで評価し直すと"
                    f"「{lib_name.split(' ', 1)[-1]}」が{lib_res['E_rate']*100:.0f}%で上回ったため、"
                    f"こちらを採用します" if tmpl_pick else
                    f"。類型テンプレートは期待値基準に届かず、全券種を評価して"
                    f"「{lib_name.split(' ', 1)[-1]}」を採用します")
        return {'arch': arch, 'arch_name': f"{ARCH_NAME[arch]}・券種最適化（{lib_name.split(' ', 1)[-1]}）",
                'judged': arch, 'why': why + (f"。{market_gap}" if market_gap else "") + cmp_note,
                'res': lib_res, 'budget': lib_res.get('total', budget), 'young': young,
                'tried': tried, 'skip': False, 'target': ARCH_TARGET[arch],
                'market_gap': market_gap, 'phantom': lib_res['E_rate'] >= PHANTOM_E}

    if tmpl_pick:
        cur, res, b_cur, capped = tmpl_pick
        phantom = res['E_rate'] >= PHANTOM_E
        return {'arch': cur, 'arch_name': ARCH_NAME[cur] + ("・市場乖離（予算圧縮）" if market_gap else "")
                                          + ("・類型上限で予算圧縮" if capped else ""), 'judged': arch,
                'why': why + (f"。{market_gap}" if market_gap else "")
                       + (f"。{ARCH_NAME[cur]}のため予算を{b_cur:,}円に圧縮" if capped else "")
                       + ("。期待回収率は市場との乖離が大きく参考値" if phantom else ""),
                'res': res, 'budget': b_cur, 'young': young, 'tried': tried, 'skip': False,
                'target': ARCH_TARGET[cur], 'market_gap': market_gap, 'phantom': phantom}
    # v1.3（2026-08-22 ユーザー指示「平場も重賞と同じレベルで買い目」）: 多層テンプレが基準未達でも
    # 判定類型の多層構成を縮小予算（60%）で採用し、期待回収率は「基準未達・参考値」と明示する（重賞SNSモードと同じ扱い）
    # v1.6（2026-09-16）: 組み合わせ券種を実オッズで検算できない版（＝前日版）では60%圧縮をしない。
    #   推定の期待値で予算を決めないという方針（roadmap §7-9）を、増額だけでなく減額にも一貫させる。
    #   9/13は自信度10の阪神2R・6Rがこの圧縮で3,000円に落ち、自信度9の中山10R・12Rが12,000円だった
    #   （実際に当たったのは前者2本）。当日朝に実オッズで再実行した版では従来どおり圧縮する。
    if FORCE_TEMPLATE and tried and tried[0][1] is not None:
        cur0, res0, _ok = tried[0]
        b_base = min(budget, ARCH_BUDGET_CAP.get(cur0, budget))
        shrink = SHRINK_ON_UNVERIFIED_EV or bool(odds_override)
        b2 = max(2000, int(round(b_base * 0.6 / 1000)) * 1000) if shrink else b_base
        legs = _legs(cur0, roles, young)
        res2 = evaluate_pattern(legs, roles, info['p'], info['q'], b2) if legs else None
        if res2 is not None:
            return {'arch': cur0, 'arch_name': ARCH_NAME[cur0] + ('・縮小予算' if shrink else '') + ('・市場乖離' if market_gap else ''), 'judged': arch,
                    'why': why + (f'。{market_gap}' if market_gap else '')
                           + ('。多層構成は期待値基準（115%×ガミ35%）に届かないため予算を60%に縮小（期待回収率は参考値）' if shrink
                              else '。期待値は推定オッズでの計算なので予算は動かさず、当日朝の実オッズで再判定します'),
                    'res': res2, 'budget': b2, 'young': young, 'tried': tried, 'skip': False, 'target': ARCH_TARGET[cur0],
                    'market_gap': market_gap, 'phantom': res2['E_rate'] >= PHANTOM_E, 'gate_fail': True}
    # 多層テンプレが全て基準未達 → v5エンジン（v5.5ガード適用）のEV最適1パターンに縮約して再判定
    from v55_guard import choose_pattern_v55, DISPERSED, uses_banned_ticket, BAN_ANA_AXIS, ANA_AXIS_CODES
    name, desc, res, ranking, _p, _q, vinfo = choose_pattern_v55(recs, budget, odds_override)
    # v1.3: 絞り込み版でもV系（エンジン独自の妙味馬）は使わない＝印と買い目の不一致を防ぐ。
    # v1.6: 3連複・3連単を含む構成と穴軸型も同様に使わない（v55_guard §④）
    # ランキングから「分散型 かつ 非V系 かつ 禁止券種を含まない」最良を選び直す（基準: E115%×ガミ35%）
    if name is not None and (name.split(' ')[0].startswith('V') or uses_banned_ticket(res)
                             or (BAN_ANA_AXIS and name.split(' ')[0] in ANA_AXIS_CODES)):
        name = desc = res = None
        for nm, ds, rs in ranking:
            code = nm.split(' ')[0]
            if code.startswith('V') or (WEEKLY_CONTROL_ON and code not in DISPERSED):
                continue
            if uses_banned_ticket(rs) or (BAN_ANA_AXIS and code in ANA_AXIS_CODES):
                continue
            if rs['E_rate'] >= EV_MIN and rs['gami_ratio'] <= GAMI_MAX:
                name, desc, res = nm, ds, rs; break
    # 8/22教訓: 絞り込み版で「穴軸・妙味軸の集中型（A1/A3/V系）」に自信度連動の満額（15,000円）を
    # 載せると推定人気ベースの幻影で2戦0勝-30,000円。実オッズなしの穴軸集中は予算を5,000円に圧縮する
    if res is not None and name.split(' ')[0] in ANA_AXIS_PATTERNS and not odds_override:
        capped = min(BUDGET_BY_CONF.get(conf, 5000), ANA_AXIS_BUDGET_CAP)
        if capped < res['total']:
            name, desc, res, ranking, _p, _q, vinfo = choose_pattern_v55(recs, capped, odds_override)
    if res is not None:
        tried.append(('V5', res, True))
        return {'arch': 'V5', 'arch_name': f"{ARCH_NAME[arch]}・絞り込み版（{name.split(' ', 1)[-1]}）",
                'judged': arch, 'why': why + "。多層構成では期待値基準に届かないため、最も効率の良い1パターンに絞りました",
                'res': res, 'budget': budget, 'young': young, 'tried': tried, 'skip': False, 'target': ARCH_TARGET[arch]}
    best = max((t[1] for t in tried if t[1]), key=lambda r: r['E_rate'], default=None)
    return {'arch': None, 'arch_name': '見送り', 'judged': arch, 'why': why, 'res': best,
            'budget': budget, 'young': young, 'tried': tried, 'skip': True, 'target': '—'}


# ──────────────────────────────────────────────
# ④ 配当シナリオ
# ──────────────────────────────────────────────
def scenarios(recs, roles, res, circ):
    """的中シナリオ3〜5本（馬連は1-2着順を考慮するためtupleで渡す）"""
    if not res:
        return []
    bets, total = res['bets'], res['total']
    H, O, S, D1, A = (roles.get(k) for k in ('H', 'O', 'S', 'D1', 'A'))
    cands = [('本線: ◎○▲で決着', (H, O, S)), ('◎○＋△で決着', (H, O, D1)),
             ('◎飛び: ○▲△で決着', (O, S, D1)), ('穴絡み: ◎○＋🔥穴', (H, O, A)), ('大爆発: 🔥穴が○▲と', (A, O, S))]
    out = []
    for label, oc in cands:
        if any(x is None for x in oc):
            continue
        ret = 0
        for btype, idxs, amount, odds in bets:
            s = set(idxs)
            if btype in ('ワイド', '3連複'):
                hit = s <= set(oc)
            elif btype == '馬連':
                hit = s == set(oc[:2])
            else:
                hit = False
            if hit:
                ret += amount * odds
        rate = ret / total * 100
        if ret <= 0:
            continue   # カバー外のシナリオは掲載しない
        flag = " 🎉" if rate >= 500 else (" ✅" if rate >= 300 else ("" if rate >= 100 else " ▼ガミ"))
        out.append(f"{label}（{'-'.join(circ(recs[i]['馬番']) for i in oc)}）→ 約{int(ret):,}円（{rate:.0f}%）{flag}")
    return out


def roles_from_marks(recs, marks, info):
    """手動で確定した印dict{馬番:印}から買い目用roles/infoを再構築（重賞レベルの手動判定を平場に適用）"""
    idx = {r['馬番']: i for i, r in enumerate(recs)}
    q = info['q']; n = len(recs)
    q_order = sorted(range(n), key=lambda j: -q[j])
    get = lambda m: [idx[num] for num, mk in marks.items() if mk == m and num in idx]
    H = (get('◎') or [0])[0]; O = (get('○') or [None])[0]; S = (get('▲') or [None])[0]
    deltas = get('△'); A = (get('🔥穴') or [None])[0]; danger = (get('❌') or [None])[0]
    roles = {'H': H, 'O': O, 'S': S, 'A': A, 'P1': next((i for i in q_order if i != H), None), 'P2': None}
    roles['P2'] = next((i for i in q_order if i not in (H, roles['P1'])), None)
    for k in range(5): roles[f'D{k+1}'] = deltas[k] if k < len(deltas) else None
    info2 = dict(info, n_delta=len(deltas), ana=A, danger=danger,
                 ana_reason=info.get('ana_reason', '') if A == info.get('ana') else '外部データ照合で穴に指名')
    return roles, info2
