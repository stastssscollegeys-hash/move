# -*- coding: utf-8 -*-
"""
kaime_format.py — 買い目表記ルール v2（2026-08-21・SNS/予想サイト表記リサーチ反映）の共通フォーマッタ

リサーチで確認した「読みやすい買い目」の共通項（netkeibaプロ予想・LINE配信・JRA-VAN・予想家投稿）:
  1. 先に「合計◯点・◯円」を出す（読者は最初に総額と点数を知りたい）
  2. 券種ごとにブロック化し、1行目に構造（軸 ― 相手 / BOX / フォーメーション1着:2着:3着）を書く
     → 組み合わせを1点ずつ羅列しない。同額なら「各◯円」で1行にまとめる
  3. 馬番は丸数字（①〜⑱）で金額・点数と視覚的に区別する。馬名は印一覧で既出なので軸馬のみ1回併記
  4. 順不同券種（馬連・ワイド・3連複）は「-」、着順指定（馬単・3連単）は「→」、マルチは「⇔」、総流しは「全」
  5. 各ブロック末尾に（点数・小計）、最後に役割（本線／回収ライン／保険／穴）を1行
  6. 全角スペースでの桁揃えはスマホで崩れるので使わない。1行1情報

使い方:
  from kaime_format import circ, fmt_bets
  lines = fmt_bets(res['bets'], recs)            # v5エンジン出力 → SNS行リスト
  lines = fmt_manual(total_points, total_yen, blocks, roles)  # 手組み（重賞）用
"""
from collections import OrderedDict

CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"
ORDERED = {'馬単', '3連単'}


def circ(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return CIRC[n - 1] if 1 <= n <= 18 else str(n)


def join_nums(nums, btype):
    j = "→" if btype in ORDERED else "-"
    return j.join(circ(x) for x in nums)


def _axis_label(items, btype, marks):
    """流し構造の検出: 全組合せに共通する馬番=軸、残り=相手。"""
    sets = [set(nums) for nums, _, _ in items]
    common = set.intersection(*sets) if sets else set()
    if not common or len(items) < 2:
        return None
    order = []
    for nums, _, _ in items:
        for x in nums:
            if x not in common and x not in order:
                order.append(x)
    axis = "".join(f"{marks.get(x, '')}{circ(x)}" for x in sorted(common, key=lambda x: -ord(marks.get(x, ' ')[0]) if marks.get(x) else 0))
    kind = "軸" if len(common) == 1 else f"{len(common)}頭軸"
    return f"{axis}{kind} ― 相手 {''.join(circ(x) for x in order)}"


def fmt_bets(bets, recs, roles=None, with_header=True):
    """v5 res['bets'] = [(btype, idxs, amount, odds), ...] → 行リスト。"""
    marks = {r['馬番']: r.get('AI印', '') for r in recs if r.get('AI印')}
    groups = OrderedDict()
    for btype, idxs, amount, odds in bets:
        nums = [recs[i]['馬番'] for i in idxs]
        groups.setdefault(btype, []).append((nums, amount, odds))
    lines, total, n = [], 0, 0
    for btype, items in groups.items():
        sub = sum(a for _, a, _ in items); cnt = len(items)
        total += sub; n += cnt
        combos = [join_nums(nums, btype) for nums, _, _ in items]
        amounts = {a for _, a, _ in items}
        axis = _axis_label(items, btype, marks)
        if cnt == 1:
            lines.append(f"【{btype}】{combos[0]} {items[0][1]:,}円（1点）")
        elif len(amounts) == 1:
            a = items[0][1]
            head = f"【{btype}】" + (f"{axis}　" if axis else "")
            lines.append(f"{head}各{a:,}円（{cnt}点 {sub:,}円）")
            for i in range(0, len(combos), 3):
                lines.append("　" + " / ".join(combos[i:i + 3]))
        else:
            head = f"【{btype}】" + (axis if axis else "")
            lines.append(f"{head}（{cnt}点 {sub:,}円）")
            for (nums, a, odds), c in zip(items, combos):
                lines.append(f"　{c} {a:,}円")
    out = []
    if with_header:
        out.append(f"💰 買い目 合計{n}点・{total:,}円")
    out += lines
    if roles:
        out.append(f"役割: {roles}")
    return out


def fmt_manual(blocks, roles=None, notes=None):
    """手組み用。blocks = [(券種ラベル, 構造ラベル or None, [(組合せ文字列, 金額), ...]), ...]
    組合せ文字列は呼び出し側で circ() 済みの文字列を渡す。"""
    lines, total, n = [], 0, 0
    for label, structure, items in blocks:
        sub = sum(a for _, a in items); cnt = len(items)
        total += sub; n += cnt
        amounts = {a for _, a in items}
        if cnt == 1:
            lines.append(f"【{label}】{items[0][0]} {items[0][1]:,}円（1点）")
        elif len(amounts) == 1:
            head = f"【{label}】" + (f"{structure}　" if structure else "")
            lines.append(f"{head}各{items[0][1]:,}円（{cnt}点 {sub:,}円）")
            combos = [c for c, _ in items]
            for i in range(0, len(combos), 3):
                lines.append("　" + " / ".join(combos[i:i + 3]))
        else:
            lines.append(f"【{label}】{structure or ''}（{cnt}点 {sub:,}円）")
            for c, a in items:
                lines.append(f"　{c} {a:,}円")
    out = [f"💰 買い目 合計{n}点・{total:,}円"] + lines
    if roles:
        out.append(f"役割: {roles}")
    if notes:
        out += [f"※{x}" for x in notes]
    return out
