# -*- coding: utf-8 -*-
"""
gen_digest_sns.py — 自信度7以上ダイジェスト SNS投稿案（X／Threads／Note＋Word）再構築版 2026-08-21

旧 gen_confidence_digest_YYYYMMDD.py（日付別コピー）を置き換える汎用版。
適用ルール（すべて機械適用）:
  - 平場にも重賞ルール: 印=◎○▲各1・△1〜5頭可変・🔥穴・❌危険な人気馬（flat_race_rules.assign_marks）
  - 買い目=4類型の多層テンプレ（A堅い/B中穴/C波乱/D見送り）をv5評価器で採点＋降格ロジック＋配当シナリオ
  - v5.5ガード: 週次制御・若馬戦上限（1日2レース・自信度9以上）
  - 買い目表記v2（kaime_format）: 合計先出し・券種ブロック・丸数字・役割
  - 冒頭ヘッダー（🏇【…】日付／━━ 競馬場 距離 頭数 ━━）を全投稿に付与、前日時制（明日）、内部用語なし
  - Noteは冒頭フック定型（アスメシ自己紹介＋結論先出し）、マークダウン記号なし
  - 重賞（キーンランドC・新潟2歳S）は別記事の印が正のため除外し導線のみ
使い方: python gen_digest_sns.py --date 20260822 [--odds-file odds.json]
出力:   Desktop/競馬予想レポート/{date}/週末自信度7以上_SNS投稿案.docx
"""
import sys, json, argparse
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from collections import defaultdict
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_weekend_confidence_report import calc_confidence
from v55_guard import apply_young_cap, WEEKLY_CONTROL_ON, WEEKLY_CONTROL_REASON
from kaime_format import fmt_bets, circ
from flat_race_rules import assign_marks, build_kaime, scenarios, MARK_ORDER, roles_from_marks
import os
RACE_NOTES = {}
from gen_kaime_v5 import public_probs

FONT = '游ゴシック'
CONF_MIN = 7

# ══════════════════════════════════════════════════════════════════════
# 2026-09-02: 週次の手動更新を廃止し、データから自動導出するようにした。
#   従来 GRADE_NAMES / WEEKDAY / DB_RECORDS / 競馬場名 をここに手で書いており、
#   更新を忘れると「先週の重賞名で動く」「先週の競馬場名が本文に出る」事故が起きていた。
#   （実際に9/5-6は新潟・中京→中山・阪神へ2場入れ替わる）
#   手で上書きしたい時だけ下の *_OVERRIDE を設定する。
# ══════════════════════════════════════════════════════════════════════
GRADE_NAMES: tuple = ()          # detect_grades() が実行時に埋める（重賞＝別記事に回す）
GRADE_NAMES_OVERRIDE: tuple = () # 自動検出を上書きしたい時だけ設定
VENUES: str = ''                 # 例 '中山・札幌・阪神'（実データから生成）
VENUE_TAGS: str = ''             # 例 '#中山競馬場 #札幌競馬場 #阪神競馬場'
VENUE_SET: set = set()           # 同上（馬場メモの絞り込みに使う）
DB_RECORDS = "—"                 # 累積DBの実レコード数を起動時に読む

# JRA公式の場コード順（表示順を毎回そろえるため）
_VENUE_ORDER = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']


def weekday_of(day: str) -> str:
    """'20260906' → '日'。曜日辞書の手動メンテを廃止。"""
    from datetime import date as _date
    return '月火水木金土日'[_date(int(day[:4]), int(day[4:6]), int(day[6:8])).weekday()]


def load_db_records() -> str:
    """累積DBの実レコード数。手動の書き換えを廃止。"""
    p = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'race_results.json'
    try:
        return f"{len(json.loads(p.read_text(encoding='utf-8'))):,}"
    except Exception:
        return "—"


def detect_grades(races: dict) -> list:
    """その日の重賞を records の「グレード」欄から自動検出する。

    戻り値 [(レース名, グレード), ...]。併せて GRADE_NAMES を埋める
    （is_grade() がこれを見てダイジェストから除外する）。
    """
    global GRADE_NAMES
    import re as _re
    found = []
    for recs in races.values():
        r = recs[0]
        g = (r.get('グレード') or '').strip()
        if not g:
            continue
        nm = _re.sub(r'[（(]\s*G[ⅠⅡⅢI1-3][)）]\s*$', '',
                     (r.get('レース名') or '').strip()).strip()
        if nm:
            found.append((nm, g))
    found.sort()
    if GRADE_NAMES_OVERRIDE:
        GRADE_NAMES = tuple(GRADE_NAMES_OVERRIDE)
    else:
        GRADE_NAMES = tuple(nm for nm, _ in found)
    return found


def detect_venues(races: dict) -> None:
    """その日の開催場を実データから拾い、本文用の文字列を作る。"""
    global VENUES, VENUE_TAGS, VENUE_SET
    vs = {k[1] for k in races}
    ordered = [v for v in _VENUE_ORDER if v in vs] + sorted(vs - set(_VENUE_ORDER))
    VENUES = '・'.join(ordered)
    VENUE_TAGS = ' '.join(f"#{v}競馬場" for v in ordered)
    VENUE_SET = set(vs)


def grade_link_lines(day: str, tense: str, grades: list) -> tuple:
    """重賞への導線文を自動生成（従来は GRADE_LINK に手書きしていた）。"""
    if not grades:
        return ('', '')
    names = 'と'.join(f"{nm}（{g}）" for nm, g in grades)
    head = f"{'本日' if tense == '本日' else '明日'}のメイン、{names}は"
    return (head, "全頭診断＋買い目まで反映した予想を別投稿で公開しています🎯")


def auto_baba_note(day: str) -> list:
    """直前の開催日の確定結果から馬場傾向を自動生成する（2026-09-02・手書きを廃止）。

    従来 BABA_NOTE に「前日の全36レースを集計した実測馬場」を手で書いていたが、
    その集計は race_results.json から機械的に出せる。書き忘れると馬場メモが
    丸ごと空になるため自動化した。手で上書きしたい時は BABA_NOTE に日付キーで書く。
    """
    if day in BABA_NOTE:                      # 手書きがあればそちらを優先
        return BABA_NOTE[day]
    p = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'race_results.json'
    try:
        res = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return []
    prev = sorted({r['date'] for r in res if r['date'] < day})
    if not prev:
        return []
    d0 = prev[-1]
    rows = [r for r in res if r['date'] == d0 and r.get('脚質')]
    if not rows:
        return []
    # 競馬場 × 芝/ダート ごとに、1着馬と3着内馬の脚質を集計する
    agg = defaultdict(lambda: {'win': [], 'top3': [], 'baba': set()})
    for r in rows:
        surf = '芝' if str(r.get('距離', '')).startswith('芝') else 'ダート'
        a = agg[(r['競馬場'], surf)]
        fin = r.get('着順int')
        if fin == 1:
            a['win'].append(r['脚質'])
        if fin and fin <= 3:
            a['top3'].append(r['脚質'])
        if r.get('馬場状態'):
            a['baba'].add(r['馬場状態'])
    FRONT, BACK = ('逃げ', '先行'), ('差し', '追込')
    # 今週の開催場だけを載せる。開催が替わった週（例 9/5-6は新潟・中京→中山・阪神）に
    # 走らない競馬場の馬場を書いてしまうのを防ぐ。
    cur = VENUE_SET or {v for v, _ in agg}
    carried = sorted({v for v, _ in agg} & cur)
    missing = sorted(cur - {v for v, _ in agg})
    when = '本日（土曜）' if weekday_of(d0) == '土' else f"{int(d0[4:6])}/{int(d0[6:])}"
    if not carried:
        return [f"今週から開催場が替わるため（{'・'.join(sorted(cur))}）、"
                f"前開催（{when}）の実測馬場は参考になりません。"
                f"当日の馬場発表と1〜3レースの決着を見てから判断します。"]
    out = [f"{when}の全{len({(r['競馬場'], r['R']) for r in rows})}レースを"
           f"集計した実測馬場です（当日の最終発表で必ず再確認してください）。"]
    for (v, surf), a in sorted(agg.items()):
        if v not in cur or len(a['top3']) < 6:
            continue
        f3 = sum(1 for s in a['top3'] if s in FRONT)
        b3 = sum(1 for s in a['top3'] if s in BACK)
        fw = sum(1 for s in a['win'] if s in FRONT)
        bw = sum(1 for s in a['win'] if s in BACK)
        if f3 > b3 * 1.3:
            judge = "前残り傾向"
        elif b3 > f3 * 1.3:
            judge = "差し優勢"
        else:
            judge = "前後拮抗"
        out.append(f"・{v}{surf}（{'/'.join(sorted(a['baba'])) or '—'}）: "
                   f"1着は先行勢{fw}・差し勢{bw}、3着内は先行勢{f3}・差し勢{b3} → {judge}")
    if missing:
        out.append(f"・{'・'.join(missing)}は前開催に実測が無いため、"
                   f"当日の馬場発表と序盤レースの決着で判断します。")
    return out if len(out) > 1 else []


# 日付別の馬場メモ（手書きで上書きしたい時だけ書く。無ければ auto_baba_note が自動生成）
BABA_NOTE = {
    '20260822': ["馬場傾向は先週の実測を参考にしています（開催が進むため当日の変化に注意）。",
                 "・札幌芝: 差し・追込優勢が2週継続（高速洋芝）", "・中京芝: 上がり33秒前後の高速決着で差しが届く馬場", "・新潟芝: 逃げ・差しが混在で中立"],
    '20260823': ["本日（土曜）の実測馬場はこちらです（全36レースの勝ち馬・3着内馬の脚質を集計）。",
                 "・札幌芝: 勝ち馬は先行3・差し2で拮抗、3着内は差し9・先行6 → 差しが届く洋芝だが前も残る",
                 "・中京芝: 勝ち馬差し4・先行2、3着内は差し9・先行7 → 差し優勢",
                 "・新潟芝: 勝ち馬差し4、3着内は差し12・先行3 → はっきり差し優勢（外回りの末脚勝負）",
                 "・ダート: 札幌・中京・新潟とも先行有利（札幌ダは3着内11/15が先行）"],
    '20260829': ["本日の馬場・天候は3場で条件が大きく分かれます（当日朝の最終発表で必ず再確認してください）。",
                 "・新潟: 芝・ダートとも良でスタート。ただし朝〜夕方に雨予報（降水確率40〜60%）で、午後の特別戦にかけて悪化する可能性",
                 "・中京: 芝(B)・ダートとも稍重スタート。昼過ぎ〜夜のはじめ頃に雷を伴う激しい雨の予報があり、3場で最も馬場悪化リスクが高い",
                 "・札幌: 芝(B)・ダートとも稍重スタートだが、終日晴れ・降水確率0%のため日中は乾いて良方向に回復する見込み"],
    '20260830': ["本日（土曜）の全36レースを集計した実測馬場です（明日の最終発表で必ず再確認してください）。",
                 "・新潟芝: 5レース目以降ずっと稍重。1着馬8頭中6頭が逃げ・先行（75%）、3着内24頭で追込は1頭のみ",
                 "　→ 脚質バイアス指数2.47の強い前残り。明日は降水確率90%でさらに悪化する方向",
                 "・中京芝: 終日良で1400mは1分19秒台の高速決着。ただしスローなら前残り／流れれば差し届くのペース依存型",
                 "　→ 明日は最高35℃・降水確率40%まで下がり、乾いて速くなる見込み",
                 "・札幌芝: 脚質バイアス指数1.91で前残り傾向",
                 "・ダート: 新潟・中京とも午後は稍重"],
}
# GRADE_LINK（重賞への導線文）は grade_link_lines() で自動生成する。
# 従来はここに日付キーで手書きしており、更新を忘れると KeyError で落ちていた。


# ─────────────── Word helpers ───────────────
def set_font(run, size=10, bold=False, color=None):
    run.font.name = FONT; run.font.size = Pt(size); run.font.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT)

def h1(doc, text, color=(15, 71, 97)):
    p = doc.add_heading(text, level=1)
    for r in p.runs: set_font(r, 14); r.font.color.rgb = RGBColor(*color)

def h3(doc, text):
    p = doc.add_heading(text, level=3)
    for r in p.runs: set_font(r, 11)

def box(doc, lines, size=10):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5); p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(8)
    r = p.add_run("\n".join(lines)); set_font(r, size)

def threads_box(doc, title, lines, ask=None):
    text = "\n".join(lines).rstrip()
    if ask:
        ls = text.split("\n")
        ti = next((i for i in range(len(ls)-1, -1, -1) if ls[i].startswith("#")), None)
        if ti is not None: ls.insert(ti, ask + "\n")
        else: ls.append("\n" + ask)
        text = "\n".join(ls)
    n = len(text.replace("\n", ""))
    ok = n <= 500
    h3(doc, f"{title}（{n}字/500字 {'OK' if ok else '⚠超過!要短縮'}）")
    if not ok: print(f"[WARN] Threads超過: {title} {n}字")
    box(doc, ["【コピー用】"] + text.split("\n"))
    return ok


# ─────────────── data ───────────────
def is_grade(title): return any(n in (title or '') for n in GRADE_NAMES)


def get_odds(odds_all, k):
    """実オッズdictからレースkのオッズを引く。
    キー形式が2系統あるため両方を見る（2026-08-30に不一致を発見）:
      ・"新潟8"          … 本スクリプト従来の形式
      ・"20260830_新潟_8" … gen_kaime_v5 の --odds-file 形式（odds_YYYYMMDD.json はこちら）
    """
    if not odds_all:
        return None
    return odds_all.get(f"{k[1]}{k[2]}") or odds_all.get(f"{k[0]}_{k[1]}_{k[2]}")

def combo_odds_ready(day):
    """当日朝に保存した券種別オッズ（odds_snapshot.py）で、馬連とワイドが発売済みのレース集合。
    発売前（前日夜）は単勝の予想オッズしか返らないので空になる。2026-09-16追加。"""
    import glob
    d = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'odds_snapshots' / day
    ready = set()
    if not d.exists():
        return ready
    for f in sorted(glob.glob(str(d / '*.json'))):
        try:
            s = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        o = s.get('odds') or {}
        if o.get('馬連') and o.get('ワイド') and s.get('venue') and s.get('R'):
            ready.add((s['venue'], int(s['R'])))
    return ready


def load(day, odds_all):
    base = Path.home() / 'Desktop' / '競馬予想レポート' / day
    # 2026-09-12: 土日2日分を1ファイル（週末ビッグデータ_20260912-0913_records.json）で作る週があるため、
    #   単日ファイルが無ければ「その日から始まる週末ファイル」を使い、その日のレースだけに絞る（_bak・_枠順前は除外）
    p = base / f"週末ビッグデータ_{day}-{day[4:]}_records.json"
    if not p.exists():
        # 土曜のフォルダに土日2日分を1ファイルで置く週があるため、週末フォルダをまたいで探す（_bak・_枠順前は除外）
        cands = sorted(base.glob(f"週末ビッグデータ_{day}-[0-9][0-9][0-9][0-9]_records.json"))
        if not cands:
            for f2 in sorted(base.parent.glob("*/週末ビッグデータ_[0-9]*-[0-9][0-9][0-9][0-9]_records.json")):
                try:
                    if any(r.get('date') == day for r in json.loads(f2.read_text(encoding='utf-8'))['records']):
                        cands.append(f2)
                except Exception:
                    continue
        if not cands:
            raise FileNotFoundError(p)
        p = cands[-1]
    with open(p, encoding='utf-8') as f:
        data = json.load(f)
    races = defaultdict(list)
    for r in data['records']:
        if r['date'] != day:
            continue
        races[(r['date'], r['競馬場'], r['R'])].append(r)
    # ── 脚質バイアス補正（v6.0 / 2026-08-31）────────────────────────
    # 現行の総合指数は逃げ馬を2.3倍に過大評価し、差し馬を半分に過小評価していた。
    # 脚質ごとの平均を全体平均に揃えるだけの後処理で、train/valid分割の検証では
    # 単勝回収率が74.4%→84.1%（+9.7pt）に改善している。
    # style_correction.ENABLED = False にすれば従来挙動に戻せる。
    from style_correction import apply_style_correction
    for k in races:
        apply_style_correction(races[k])
    for k in races: races[k].sort(key=lambda x: x['AI予測順位'])
    conf = {k: calc_confidence(v) for k, v in races.items()}
    flat = {}
    for k, v in races.items():
        odds = get_odds(odds_all, k)
        marks, roles, info = assign_marks(v, q=public_probs(v, odds) if odds else None)
        for r in v:
            m = marks.get(r['馬番'], ''); r['AI印'] = '' if m == '❌' else m
        note = RACE_NOTES.get(f"{k[1]}{k[2]}", {})
        if note.get('marks'):   # 外部データ統合後の手動判定（重賞レベル）で印を上書き
            from collections import OrderedDict as _OD
            marks = _OD((int(num), m) for num, m in note['marks'].items())
            roles, info = roles_from_marks(v, marks, info)
            for r in v:
                m = marks.get(r['馬番'], ''); r['AI印'] = '' if m == '❌' else m
        kb = build_kaime(v, conf[k][0], marks, roles, info, odds_override=odds) if conf[k][0] >= CONF_MIN else None
        if kb is not None: kb['notes'] = note.get('notes', [])
        flat[k] = (marks, roles, info, kb)
    return races, conf, flat


# ── 期待値ベースの資金配分（2026-08-29 ユーザー方針）──────────────────
# 「重賞だからお金をかけるっていうのも変な話。期待値が取れるレースは
#   その分お金をかけるっていうのは当たり前」
# 従来は自信度連動の固定額だったため、期待回収率125%のレースに15,100円、
# 224%のレースに5,000円という逆転配分が起きていた。
FLAT_TOTAL_BUDGET = 37000      # 平場に配る1日の総額（重賞は別記事の手組みで配分）
EV_ALLOC_CAP_RATIO = 0.35      # 1レース上限＝総額の35%（一極集中を防ぐ）
EV_ALLOC_FLOOR = 2000          # 買う以上は意味のある額


# 前日に確定した配分を当日もそのまま使う場合に指定する（2026-08-30 ユーザー指示
# 「前日の配分通りに買いましょう。実オッズを反映してください」）。
# ここにキーがあるレースは期待値による再按分を行わず、この金額で買い目を組み直す。
FIXED_BUDGET = {
    ('20260830', '札幌', 10): 13000,
    ('20260830', '札幌', 11): 10300,
    ('20260830', '新潟', 6):   4300,
    ('20260830', '札幌', 4):   3100,
    ('20260830', '中京', 8):   3000,
}


def conf_base_budget(recs, c):
    """自信度連動の基準額（10=15,000／9=12,000／8=8,000／7=5,000）。docxに明記している規定そのもの。
    新馬・未勝利の60%圧縮は build_kaime 側で掛かるので、ここでは掛けない（二重適用防止）。"""
    from gen_kaime_v5 import BUDGET_BY_CONF
    return BUDGET_BY_CONF.get(c, 5000)


def reallocate_by_ev(races, conf, flat, odds_all, play):
    """重み = (E−1.0) × 信頼度係数（実オッズ1.0／推定0.6） × √的中率 で総額を按分。
    推定オッズの期待値は「妙味の幻影」で膨らむため割り引く（8/22に穴軸2戦0勝−30,000円）。
    √的中率は的中率が極端に低いレースへの一極集中を緩和する項。
    FIXED_BUDGET に載っているレースは按分せず、その金額をそのまま使う。

    🔴 2026-09-16 変更: **期待値による按分を停止し、予算は自信度連動の規定額に戻した**。
    ユーザー方針「期待値が取れるレースにその分お金をかける」（8/29）そのものは正しいが、
    その入力である推定期待回収率が信用に足りないことが実測で確定したため（ユーザー承認済み）。
      ・公開買い目の実測（review_weekend.py・6日27R）は35%。払戻があった4レースは全て規定額未満で、
        15,000円・13,000円を置いた大口5本は全滅（うち2本は前日推定347%・231%の穴ワイド）
      ・買い目を変えず金額だけ規定どおりにすると35%→72%
    ⚠ 期待値配分を再開してよいのは、組み合わせ券種を実オッズで検算できるようになってから。
    （メモリ feedback-keiba-budget-by-ev の「方針は正しいが期待値の計測が信用に足りない」に対応）"""
    if any(k in FIXED_BUDGET for k in play):
        for k in play:
            nb = FIXED_BUDGET.get(k)
            if not nb:
                continue
            marks, roles, info, kb = flat[k]
            odds = get_odds(odds_all, k)
            kb2 = build_kaime(races[k], conf[k][0], marks, roles, info,
                              odds_override=odds, budget_override=nb)
            if kb2 and not kb2.get('skip') and kb2.get('res'):
                kb2['notes'] = kb.get('notes', [])
                kb2['fixed_budget'] = True
                flat[k] = (marks, roles, info, kb2)
        return flat
    for k in play:
        nb = conf_base_budget(races[k], conf[k][0])
        marks, roles, info, kb = flat[k]
        odds = get_odds(odds_all, k)
        kb2 = build_kaime(races[k], conf[k][0], marks, roles, info,
                          odds_override=odds, budget_override=nb)
        if kb2 and not kb2.get('skip') and kb2.get('res'):
            kb2['notes'] = kb.get('notes', [])
            kb2['ev_alloc'] = (kb['res']['total'], kb2['res']['total'])
            flat[k] = (marks, roles, info, kb2)
    return flat


MIXED_ARCH = '混合型 ◎は指数・相手は人気上位4頭（ワイド流し）'


def rebuild_mixed(recs, conf, marks, roles, info, odds, budget):
    """2026-09-19 ユーザー承認「今日の反省を踏まえて」: ◎は指数、相手は◎を除いた市場人気上位4頭。
    structure_backtest.py（レース前の印のみ452R）の「混合×ワイド◎流し(相手4)×推定配当に反比例」
    ＝回収率81%［68〜96%］・上位1除外76%・3期間85/85/72%・的中43.8%（印ベースは36.7%）で最も安定した組み方。
    9/19の公開5Rでは△が2着に来たレースが4つあり、○▲を指数2・3位から選んでいたことが敗因だった。
    印の表示も同じ定義に揃える（○▲△△＝人気順）。🔥穴・❌は表示のみ残す。"""
    from gen_kaime_v5 import est_odds, evaluate_pattern, is_young_race, YOUNG_RACE_BUDGET_MULT
    from collections import OrderedDict as _OD
    n = len(recs)
    if not odds:
        return None
    def _o(i):
        try:
            return float(odds.get(str(recs[i]['馬番'])))
        except (TypeError, ValueError):
            return 999.0
    aite = [i for i in sorted(range(n), key=_o) if i != 0][:4]
    if len(aite) < 4:
        return None
    if is_young_race(recs[0].get('レース名', '')):
        budget = max(3000, int(round(budget * YOUNG_RACE_BUDGET_MULT / 1000)) * 1000)
    q = info['q']
    num = lambda i: recs[i]['馬番']
    marks_m = _OD([(num(0), '◎'), (num(aite[0]), '○'), (num(aite[1]), '▲'), (num(aite[2]), '△'), (num(aite[3]), '△')])
    for hn, m in marks.items():
        if m in ('🔥穴', '❌') and hn not in marks_m:
            marks_m[hn] = m
    roles_m = dict(roles, H=0, O=aite[0], S=aite[1], D1=aite[2], D2=aite[3], D3=None, D4=None, D5=None)
    if roles.get('A') in aite:
        roles_m['A'] = None
    # Σ(1/配当)≦1（全点ガミなし・v7の設計則）を守る。◎が断然人気だと人気馬とのワイドは1倍台になり、
    # 1点だけ当たると必ず損をする。一番安い相手から外し、2点未満になるならそのレースは見送る。
    keys_all = ['O', 'S', 'D1', 'D2']
    use = [(k, j, est_odds(q, 'ワイド', (0, j)), 'ワイド') for k, j in zip(keys_all, aite)]
    dropped = []
    while len(use) >= 2 and sum(1 / x[2] for x in use) > 1.0:
        lo = min(use, key=lambda x: x[2]); use.remove(lo); dropped.append(lo)
    # 外した人気上位の相手は、Σ(1/配当)≦1 に収まる限り馬連で持ち直す（オールカマー最終版と同じ扱い）
    re_added = []
    for k, j, _, _ in sorted(dropped, key=lambda x: x[2]):
        e2 = est_odds(q, '馬連', (0, j))
        if sum(1 / x[2] for x in use) + 1 / e2 <= 1.0:
            use.append((k, j, e2, '馬連')); re_added.append(j)
    dropped = [x for x in dropped if x[1] not in re_added]
    if len(use) < 2 or sum(1 / x[2] for x in use) > 1.0:
        kb = {'arch_name': MIXED_ARCH, 'target': '—', 'skip': True, 'res': None, 'mixed': True, 'why': '',
              'skip_note': f"◎{recs[0]['馬名']}が断然人気で、人気馬とのワイドに配当がつかない（どう組んでも1点的中が損になる）"}
        return marks_m, roles_m, kb
    est = [x[2] for x in use]
    n_use = len(use)
    w = [1 / e for e in est]
    amts = [max(100, int(round(budget * x / sum(w) / 100)) * 100) for x in w]
    while sum(amts) != budget:   # 合計を予算ちょうどに（100円単位）
        d = budget - sum(amts)
        i = min(range(n_use), key=lambda j: amts[j] * est[j]) if d > 0 else max((j for j in range(n_use) if amts[j] > 100), key=lambda j: amts[j] * est[j])
        amts[i] += 100 if d > 0 else -100
    legs = [(bt, ('H', k), a / budget) for (k, _, _, bt), a in zip(use, amts)]
    pe = [0.5 * a + 0.5 * b for a, b in zip(info['p'], q)]; s_ = sum(pe) or 1
    res = evaluate_pattern(legs, roles_m, [x / s_ for x in pe], q, budget)
    if not res:
        return None
    over = sum(1 / e for e in est)
    cut = ("。" + "・".join(f"{recs[j]['馬名']}（推定{e:.1f}倍）" for _, j, e, _ in dropped)
           + "とのワイドは配当が安く1点的中が損になるため外した") if dropped else ""
    cut += ("。" + "・".join(recs[j]['馬名'] for j in re_added)
            + "とはワイドだと1点的中が損になるため馬連で持つ") if re_added else ""
    kb = {'arch_name': MIXED_ARCH, 'target': '100〜200%', 'skip': False, 'res': res, 'mixed': True,
          'why': (f"◎は独自指数1位、相手は市場の人気上位（◎を除く）。{n_use}点とも◎からの流しで、"
                  f"どれが当たってもほぼ同じ額が戻るように推定配当に反比例で配分（Σ1/配当={over:.2f}）{cut}")}
    return marks_m, roles_m, kb


def mark_items(recs, marks):
    name = {r['馬番']: r['馬名'] for r in recs}
    return [(m, num, name[num]) for m, num in sorted(((m, n) for n, m in marks.items()), key=lambda x: (MARK_ORDER[x[0]], x[1]))]

def marks_line(recs, marks, with_danger=False):
    items = [(m, n, nm) for m, n, nm in mark_items(recs, marks) if with_danger or m != '❌']
    return "　".join(f"{m}{circ(n)}{nm}" for m, n, nm in items)

def horse_phrase(r, top):
    bits = []
    if r.get('DB最高指数', 0) and r['DB最高指数'] >= 75: bits.append("累積データ上位")
    if (r.get('近5走複勝率%') or 0) >= 60: bits.append("近走安定")
    if (r.get('騎手勝率%') or 0) >= 12: bits.append("好騎手")
    if (r.get('同距離複勝率%') or 0) >= 50 and (r.get('同距離走数') or 0) >= 2: bits.append("同距離巧者")
    if (r.get('近5走平均着') or 0) >= 4.0 and r['独自指数'] >= 68: bits.append("近走不振も能力指数は高い")
    if r is top and r['ML能力%'] >= 30: bits.append("機械学習の能力評価も突出")
    base = f"総合指数{r['総合指数']}（独自{r['独自指数']}・ML{r['ML能力%']}%）"
    if r.get('脚質') and r['脚質'] != '?': base += f"・{r['脚質']}"
    return base + (("／" + "・".join(bits[:2])) if bits else "")

def hdr(k, recs, c, day, wd):
    return [f"🏇【{k[1]}{k[2]}R {recs[0]['レース名']}】{day[:4]}/{day[4:6]}/{day[6:]}（{wd}）",
            f"━━ {k[1]}競馬場 {recs[0]['距離']} / {recs[0]['頭数']}頭 / AI自信度{c}/10 ━━"]

# ⭐ 2026-09-16: 期待回収率は「実オッズで検算できた場合だけ」数値を出す。
# 9/13 中山10Rは前日推定347%で実測0%、中山12Rは231%で実測0%。組み合わせ券種のオッズは
# 単勝から推定しているため、推定値のまま出すと当たらない買い目に大きな期待を持たせてしまう。
# 組み合わせオッズは当日朝にならないと発売されない（odds_snapshot.py のメモ）ので、
# 前日版では数値を出さず、当日朝に実オッズを入れて再実行した版でだけ出す。
# 正本: docs/keiba_roi100_roadmap.md §7-10
EV_HIDDEN_NOTE = "期待回収率: 非表示（組み合わせ券種は当日朝まで発売されず、推定値しか出せないため）"


def why_text(kb):
    """判定文。実オッズで検算していない版では、中に出てくる期待回収率の数値を伏せる。"""
    w = kb['why']
    if not kb.get('ev_verified'):
        import re
        w = re.sub(r'期待回収率\d+%', '期待回収率（推定）', w)
        w = re.sub(r'が\d+%で上回った', 'が推定の期待回収率で上回った', w)
    return w


def kaime_block(recs, roles, kb, indent=""):
    res = kb['res']
    verified = kb.get('ev_verified')
    out = [f"{indent}【買い目の型】{kb['arch_name']}（目標回収率{kb['target']}）", f"{indent}判定: {why_text(kb)}"]
    out += [f"{indent}{l}" for l in fmt_bets(res['bets'], recs)]
    tail = f"300%超の確率{res['P_target']*100:.0f}% / ガミ率{res['gami_ratio']*100:.0f}%"
    if not verified:
        out.append(f"{indent}→ {EV_HIDDEN_NOTE} / {tail}")
    elif kb.get('gate_fail') and not kb.get('phantom'):
        out.append(f"{indent}→ 期待回収率{res['E_rate']*100:.0f}%（実オッズ・基準115%未満のため縮小予算）/ {tail}")
    elif kb.get('phantom'):
        out.append(f"{indent}→ 期待回収率: 参考値（市場オッズとモデル評価の乖離が大きく数値が発散するため非表示）/ {tail}")
    else:
        out.append(f"{indent}→ 期待回収率{res['E_rate']*100:.0f}%（実オッズ）/ {tail}")
    sc = scenarios(recs, roles, res, circ)
    if sc and verified:
        out.append(f"{indent}📌 的中シナリオ（実オッズ）"); out += [f"{indent}　{s}" for s in sc]
    return out

def skip_reason(kb):
    if kb.get('skip_note'):
        return kb['skip_note']
    b = kb['res']
    return f"多層でも最良{b['E_rate']*100:.0f}%と期待値基準（115%）未満" if b else "期待値基準を満たす構成なし"


# ─────────────── main ───────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True); ap.add_argument('--odds-file')
    ap.add_argument('--aite', choices=['index', 'market'], default='index',
                    help='market=◎は指数・相手は市場人気上位4頭のワイド流し（2026-09-19〜）')
    a = ap.parse_args()
    global DB_RECORDS
    day = a.date; wd = weekday_of(day); md = f"{int(day[4:6])}/{int(day[6:])}"
    DB_RECORDS = load_db_records()
    from datetime import date as _d
    _today = _d.today().strftime('%Y%m%d')
    tense = '本日' if day == _today else '明日'          # 当日実行なら本日表記
    tense_asa = '今朝' if day == _today else '明日朝'
    odds_all = json.load(open(a.odds_file, encoding='utf-8')) if a.odds_file else {}
    _np = Path.home() / 'Desktop' / '競馬予想レポート' / day / f'race_notes_{day}.json'
    if _np.exists(): RACE_NOTES.update(json.load(open(_np, encoding='utf-8')))
    races, conf, flat = load(day, odds_all)
    n_races = len(races); n_horses = sum(len(v) for v in races.values())
    # 重賞・開催場を実データから自動検出（週次の手動更新を廃止・2026-09-02）
    grades = detect_grades(races)
    detect_venues(races)
    glink = grade_link_lines(day, tense, grades)
    print(f"[auto] {day}({wd}) 開催場={VENUES} / 累積DB={DB_RECORDS}レコード")
    print(f"[auto] 検出した重賞: "
          + ("、".join(f"{nm}({g})" for nm, g in grades) if grades else "なし")
          + "（ダイジェストからは除外し導線のみにする）")

    keys = [k for k in races if conf[k][0] >= CONF_MIN and not is_grade(races[k][0]['レース名'])]
    keep, young_dropped = apply_young_cap(keys, races, conf)
    keys.sort(key=lambda k: (-conf[k][0], k[1], k[2]))
    play = [k for k in keys if k in keep and not flat[k][3]['skip']]
    # 参加レースが確定してから、期待値の大きさで総額を按分し直す（2026-08-29ユーザー方針）
    flat = reallocate_by_ev(races, conf, flat, odds_all, play)
    play = [k for k in keys if k in keep and not flat[k][3]['skip']]
    if a.aite == 'market':
        for k in play:
            marks, roles, info, kb = flat[k]
            r = rebuild_mixed(races[k], conf[k][0], marks, roles, info, get_odds(odds_all, k),
                              conf_base_budget(races[k], conf[k][0]))
            if r:
                m2, roles2, kb2 = r
                kb2['notes'] = kb.get('notes', [])
                flat[k] = (m2, roles2, info, kb2)
                for rr in races[k]:
                    mm = m2.get(rr['馬番'], ''); rr['AI印'] = '' if mm == '❌' else mm
        print("[aite] 相手＝市場人気上位4頭（◎は指数）のワイド流しで組み直し: "
              + " / ".join(f"{k[1]}{k[2]}R" + ("(見送り)" if flat[k][3].get('skip') else "") for k in play if flat[k][3].get('mixed')))
        play = [k for k in keys if k in keep and not flat[k][3]['skip']]
    # 期待回収率を数値で出してよいのは、組み合わせオッズが発売済み＝当日朝の版だけ（2026-09-16）
    ready = combo_odds_ready(day)
    for k in keys:
        kb = flat[k][3]
        if kb:
            kb['ev_verified'] = (k[1], k[2]) in ready
    print(f"[auto] 組み合わせオッズ発売済み: {len(ready)}レース"
          + ("（前日版のため期待回収率は非表示）" if not ready else "（期待回収率を実オッズで表示）"))
    skipped = [(k, young_dropped[k]) for k in keys if k not in keep] + \
              [(k, skip_reason(flat[k][3])) for k in keys if k in keep and flat[k][3]['skip']]
    total_yen = sum(flat[k][3]['res']['total'] for k in play)
    play_by_E = sorted(play, key=lambda k: -flat[k][3]['res']['E_rate'])

    out = Path.home() / 'Desktop' / '競馬予想レポート' / day / "週末自信度7以上_SNS投稿案.docx"
    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.8); s.left_margin = Cm(2.0); s.right_margin = Cm(2.0)
    t = doc.add_heading(f"{tense} 自信度7以上 注目レース SNS投稿案（{md}{wd}・{'当日版' if day == _today else '前日夜投稿版'}／再構築版）", level=0)
    for r in t.runs: set_font(r, 16)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(f"全{n_races}レース{n_horses}頭 / 自信度7以上{len(keys)}レース → 参加{len(play)}・見送り{len(skipped)} / 参加合計{total_yen:,}円 / "
                            f"17ファクター独自指数×ML v44×累積DB{DB_RECORDS}レコード / 前日推定オッズ版")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in sub.runs: set_font(r, 9.5)
    g = doc.add_paragraph(
        f"※適用ルール: 印=◎○▲各1・△1〜5頭可変・🔥穴・❌危険な人気馬／買い目=4類型の多層構成（v5評価器採点・降格あり）＋配当シナリオ／"
        f"買い目表記v2／v5.5ガード（週次制御{'ON' if WEEKLY_CONTROL_ON else 'OFF'}: {WEEKLY_CONTROL_REASON}・若馬戦は1日2レース自信度9以上）／"
        f"実測ガード2026-09-16（3連複・3連単を使わない・🔥穴を軸にしない・予算は自信度連動の規定額・期待回収率は実オッズ時のみ表示）。"
        f"重賞（{'・'.join(GRADE_NAMES[:2])}）は別記事の最終予想版の印が正。当日朝の実オッズ再実行（--odds-file）は必須")
    for r in g.runs: set_font(r, 9, color=(0, 90, 160))
    doc.add_paragraph()

    # ═══ X① 日別ダイジェスト ═══
    h1(doc, f"【X投稿①】{tense}ダイジェスト（印一覧＋型・点数／見送りも公開）", color=(20, 100, 50))
    L = [f"🏇【{tense}{md}（{wd}）AI注目レース 自信度7以上】",
         f"━━ {VENUES} 全{n_races}レース中{len(keys)}レース / 参加{len(play)}・見送り{len(skipped)} ━━", "",
         "独自の17ファクター指数×機械学習×累積1万2千レコードで全レースを採点。",
         "自信度7以上だけを厳選し、印は◎○▲に加えて△を1〜5頭に可変、",
         "🔥穴（実力＞人気のズレ）と❌危険な人気馬まで機械判定しています👇", ""]
    by_venue = defaultdict(list)
    for k in keys: by_venue[k[1]].append(k)
    for venue in sorted(by_venue, key=lambda v: -max(conf[k][0] for k in by_venue[v])):
        L.append(f"【{venue}競馬場】")
        for k in sorted(by_venue[venue], key=lambda k: -conf[k][0]):
            recs = races[k]; c = conf[k][0]; marks, roles, info, kb = flat[k]
            L.append(f"■{k[2]}R {recs[0]['レース名']} {recs[0]['距離']} {recs[0]['頭数']}頭 自信度{c}/10")
            L.append("　" + marks_line(recs, marks))
            if info['danger'] is not None:
                dg = recs[info['danger']]; L.append(f"　❌{circ(dg['馬番'])}{dg['馬名']}（人気先行・AI評価{info['danger']+1}位）")
            if k in play:
                er = ('期待回収率は当日朝の実オッズで算出' if not kb.get('ev_verified')
                      else '期待回収率は参考値' if kb.get('phantom')
                      else f"期待回収率{kb['res']['E_rate']*100:.0f}%")
                L.append(f"　💰{kb['arch_name']}・{len(kb['res']['bets'])}点{kb['res']['total']:,}円（{er}）")
            else:
                L.append(f"　⏸見送り（{dict(skipped)[k]}）")
        L.append("")
    L += [f"参加{len(play)}レース・合計{total_yen:,}円。買い目の全点と的中シナリオはスレッドで👇",
          (f"期待回収率は前日発売の実オッズで計算。{tense_asa}の最新オッズで最終調整します。" if ready else f"オッズは推定値なので{tense_asa}の実オッズで最終調整します。"), ""]
    if glink[0]:
        L += [glink[0], glink[1], ""]
    L += ["#競馬予想 #AI予想 #JRA #ビッグデータ競馬"]
    box(doc, ["【コピー用】"] + L)

    # ═══ X② 参加レース個別スレッド ═══
    h1(doc, f"【X投稿②〜】参加レース個別スレッド（{len(play)}本・返信で連結）", color=(20, 100, 50))
    for i, k in enumerate(play_by_E, 1):
        recs = races[k]; c, tags = conf[k]; marks, roles, info, kb = flat[k]
        L = hdr(k, recs, c, day, wd) + [""]
        L.append("─────────────────────"); L.append("🎯 予想印と根拠"); L.append("─────────────────────")
        for m, num, nm in mark_items(recs, marks):
            r = next(x for x in recs if x['馬番'] == num)
            if m == '🔥穴':
                L.append(f"🔥穴 {circ(num)} {nm}：{info['ana_reason']}")
            elif m == '❌':
                L.append(f"❌ {circ(num)} {nm}：推定人気上位でもAI評価{info['danger']+1}位（{horse_phrase(r, recs[0])}）")
            else:
                L.append(f"{m} {circ(num)} {nm}：{horse_phrase(r, recs[0])}")
        L.append(f"自信度の根拠: {' / '.join(tags)}")
        if kb.get('notes'):
            L.append(""); L.append("📊 外部データ照合"); L += [f"・{t}" for t in kb['notes']]
        L.append(""); L.append("─────────────────────"); L.append("💰 買い目"); L.append("─────────────────────")
        L += kaime_block(recs, roles, kb)
        L += ["", f"※{tense_asa}の実オッズで最終調整します。", "", f"#競馬予想 #AI予想 #JRA #{k[1]}競馬場"]
        h3(doc, f"スレッド{i}/{len(play)}: {k[1]}{k[2]}R {recs[0]['レース名']}（自信度{c}・{kb['arch_name']}）")
        box(doc, ["【コピー用】"] + L)

    # ═══ X③ 見送り公開 ═══
    if skipped:
        h1(doc, "【X投稿③】見送りレースの公開（買わない判断も公開コンテンツ）", color=(20, 100, 50))
        L = [f"🏇【{tense}{md}（{wd}）見送りレース {len(skipped)}本】", "━━ 自信度7以上でも「買わない」と判断したレース ━━", "",
             "自信度が高くても、期待値が基準（期待回収率115%以上×ガミ率35%以下）に",
             "届かなければ買いません。印だけ参考にどうぞ👇", ""]
        for k, why in skipped:
            recs = races[k]; marks = flat[k][0]
            L.append(f"■{k[1]}{k[2]}R {recs[0]['レース名']} 自信度{conf[k][0]}/10")
            L.append("　" + marks_line(recs, marks)); L.append(f"　⏸{why}"); L.append("")
        L += ["当日オッズが想定より付けば再判定します。", "", "#競馬予想 #AI予想 #JRA"]
        box(doc, ["【コピー用】"] + L)

    # ═══ Threads ═══
    h1(doc, "【Threads投稿】競馬場別ダイジェスト＋参加レース別買い目（各500字以内）", color=(80, 40, 120))
    def venue_post(venue, ks, part=None):
        tag = f" その{part}" if part else ""
        L = [f"🏇【{tense}{md}（{wd}）{venue}の注目レース{tag}】", "━━ AI自信度7以上だけ厳選 ━━", ""]
        for k in ks:
            recs = races[k]; marks, roles, info, kb = flat[k]
            L.append(f"■{k[2]}R {recs[0]['レース名']} 自信度{conf[k][0]}/10")
            L.append(marks_line(recs, marks))
            L.append(f"💰{kb['arch_name'].split('→')[0]}{len(kb['res']['bets'])}点" if k in play else "⏸見送り")
            L.append("")
        L += ["買い目はNote記事で全公開🎯", "", "#競馬予想 #AI予想 #JRA"]
        return L

    def tlen(lines, ask):
        return len("".join(lines)) + (len(ask) if ask else 0)

    for venue in sorted(by_venue, key=lambda v: -max(conf[k][0] for k in by_venue[v])):
        ks_all = sorted(by_venue[venue], key=lambda k: -conf[k][0])
        ask = f"{venue}で気になるレースはありますか？👇"
        if tlen(venue_post(venue, ks_all), ask) <= 500:
            threads_box(doc, f"Threads {venue}ダイジェスト", venue_post(venue, ks_all), ask=ask)
        else:
            # 500字超 → 2レースずつに分割して投稿を分ける（事前判定・超過投稿は出力しない）
            chunks = [ks_all[i:i + 2] for i in range(0, len(ks_all), 2)]
            for part, ks in enumerate(chunks, 1):
                threads_box(doc, f"Threads {venue}ダイジェスト その{part}/{len(chunks)}", venue_post(venue, ks, part), ask="気になる馬はいますか？👇")
    for k in play_by_E:
        recs = races[k]; c = conf[k][0]; marks, roles, info, kb = flat[k]; res = kb['res']
        L = hdr(k, recs, c, day, wd) + ["", marks_line(recs, marks), ""]
        L.append(f"💰 {kb['arch_name'].split('→')[0]}・合計{len(res['bets'])}点{res['total']:,}円")
        # 構造行のみ（1点ごとの行は省略して500字に収める）
        for l in fmt_bets(res['bets'], recs, with_header=False):
            if l.startswith("【"): L.append(l)
        L.append(EV_HIDDEN_NOTE if not kb.get('ev_verified')
                 else '期待回収率は参考値（市場との乖離大）' if kb.get('phantom')
                 else f"期待回収率{res['E_rate']*100:.0f}%（実オッズ）")
        sc = scenarios(recs, roles, res, circ)
        if sc and kb.get('ev_verified'): L.append(sc[0].replace("本線: ", "本線 "))
        L += ["", "全点と根拠はNoteで🎯", "", f"#競馬予想 #{k[1]}競馬場"]
        threads_box(doc, f"Threads 買い目 {k[1]}{k[2]}R", L, ask="この買い目、あなたならどう組みますか？👇")

    # ═══ Note ═══
    h1(doc, "【Note記事全文】自信度7以上 全レース詳細（印・穴・消し・買い目・的中シナリオ）", color=(180, 80, 0))
    top_k = play_by_E[0] if play_by_E else None
    N = [f"{tense}{md}（{wd}）AI注目レース 自信度7以上・全{len(keys)}レース完全版 — アスメシ競馬予想", "",
         "こんにちは、アスメシ競馬予想です🍱",
         "「明日の飯代」を懸けて、AIとデータで競馬に挑む予想アカウントです。",
         f"{tense}{md}（{wd}）の{VENUES}、全{n_races}レース{n_horses}頭を",
         f"17ファクター独自指数×機械学習×累積{DB_RECORDS}レコードのビッグデータで分析し、",
         "自信度10段階で7以上のレースだけを厳選した前日版をお届けします。", ""]
    if top_k:
        tr = races[top_k]; tk = flat[top_k][3]
        N += [f"結論を先に言います。{tense}の参加は厳選{len(play)}レース・合計{total_yen:,}円。",
              f"期待値が最も高いのは{top_k[1]}{top_k[2]}R {tr[0]['レース名']}、本命は{circ(tr[0]['馬番'])}{tr[0]['馬名']}"
              + (f"（{tk['arch_name'].split('→')[0]}・期待回収率{tk['res']['E_rate']*100:.0f}%）。"
                 if tk.get('ev_verified') else f"（{tk['arch_name'].split('→')[0]}）。"),
              f"そして——自信度7以上でも{len(skipped)}レースは「見送り」。買わない判断まで全部公開します。", ""]
    if a.aite == 'market':
        N += auto_baba_note(day) + ["",
              "今週から印と買い目の組み方を変えました。",
              "本命◎は独自の指数1位。対抗○・単穴▲・△は、◎を除いた単勝人気の上位4頭です。",
              "昨日は◎が5レース中3勝したのに、△の馬が2着に来たレースが4つあり、○▲の3頭だけで組んだ買い目が全滅しました。",
              "過去452レースで比べても、相手を人気上位から選ぶ組み方が一番安定していました（的中率43.8%）。",
              "買い目は◎からの流しです。基本はワイド4点で、どれが当たってもほぼ同じ額が戻るように配分しています。",
              "◎が断然人気のレースでは人気馬とのワイドが1倍台になり、1点だけ当たると損をするので、その相手は馬連に替えるか外します。",
              "🔥穴は印としては出しますが、買い目の軸にはしません。",
              "予算は自信度連動（10=15,000円／9=12,000円／8=8,000円／7=5,000円、新馬・未勝利は60%）です。",
              (f"期待回収率は前日発売の実オッズで計算しています。{tense_asa}の最新オッズで最終調整します。" if ready
               else f"オッズは前日の単勝オッズで組んでいます。{tense_asa}の実オッズで最終調整します。"), "", "---", ""]
    else:
      N += auto_baba_note(day) + ["",
          "印の付け方はこうです。◎○▲は各1頭、△は指数の並びで1〜5頭に可変、",
          "🔥穴は「実力評価が推定人気より明確に高い馬」、❌は「人気先行でAI評価が低い危険な人気馬」を機械判定しています。",
          "買い目はレースの性質を4つの型（堅い決着型／標準中穴型／波乱狙い型／見送り型）に機械判定し、",
          "型ごとの多層構成（本線＋回収ライン＋◎飛び保険＋穴）を期待回収率115%以上×ガミ率35%以下の基準で採点。",
          "基準に届かなければ1段保守的な型に落とし、それでも届かなければ正直に見送ります。",
          "券種は馬連とワイドだけを使います。過去に公開した買い目を全部数え直したところ、",
          "3連複は投資84,800円に対して払戻6,090円（7%）で、賭け金の4割をそこに置いていたためです。",
          "🔥穴は印としては出しますが、買い目の軸にはしません（3着以内に来た率が人気どおりだったため）。",
          "予算は自信度連動（10=15,000円／9=12,000円／8=8,000円／7=5,000円、新馬・未勝利は60%）で、",
          "期待値はこの金額を減らす方向にだけ使います（推定の期待値で増額しない）。",
          (f"期待回収率は前日発売の実オッズで計算しています。{tense_asa}の最新オッズで最終調整します。" if ready
           else f"オッズは推定値で、{tense_asa}に実オッズで最終調整します。"), "", "---", ""]
    for k in keys:
        recs = races[k]; c, tags = conf[k]; marks, roles, info, kb = flat[k]
        N.append(f"{k[1]}{k[2]}R {recs[0]['レース名']} {recs[0]['距離']} {recs[0]['頭数']}頭　自信度{c}/10 {'★'*c}")
        for m, num, nm in mark_items(recs, marks):
            r = next(x for x in recs if x['馬番'] == num)
            if m == '🔥穴': N.append(f"　🔥穴 {circ(num)} {nm}　{horse_phrase(r, recs[0])}／{info['ana_reason']}")
            elif m == '❌': N.append(f"　❌危険な人気馬 {circ(num)} {nm}　推定人気上位でもAI評価{info['danger']+1}位（{horse_phrase(r, recs[0])}）")
            else: N.append(f"　{m} {circ(num)} {nm}　{horse_phrase(r, recs[0])}")
        N.append(f"　根拠: {' / '.join(tags)}")
        if kb and kb.get('notes'):
            N += [f"　・{t}" for t in kb['notes']]
        if k in play:
            N += kaime_block(recs, roles, kb, indent="　")
        else:
            N.append(f"　⏸見送り: {dict(skipped)[k]}。当日オッズが想定より付けば再判定")
        N.append("")
    N += ["---", ""]
    if glink[0]:
        N += [glink[0], glink[1].replace("🎯", "。"), ""]
    N += [
          "予想が参考になったらフォロー＆いいねお願いします！",
          f"みなさんの{'土曜' if wd == '土' else '日曜'}が楽しいものになりますように🍜🎉", "",
          f"#競馬予想 #AI予想 #JRA #ビッグデータ競馬 {VENUE_TAGS}"]
    box(doc, N, size=9.5)

    doc.save(str(out))
    print(f"保存完了: {out}")
    print(f"自信度7以上 {len(keys)}レース → 参加{len(play)}（{total_yen:,}円）/ 見送り{len(skipped)}")
    for k in play_by_E:
        kb = flat[k][3]; print(f"  {k[1]}{k[2]}R {races[k][0]['レース名'][:12]} {kb['arch_name'][:22]} {len(kb['res']['bets'])}点 {kb['res']['total']:,}円 E{kb['res']['E_rate']*100:.0f}%")


if __name__ == '__main__':
    main()
