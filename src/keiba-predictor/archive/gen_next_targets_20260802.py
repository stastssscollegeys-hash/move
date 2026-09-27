# -*- coding: utf-8 -*-
"""
アスメシ競馬予想 — 来週狙い目馬ベスト5 SNS投稿案（8/1-8/2週末データから選定）
確定選定条件: AI印◎○▲ / 着順2-4着 / 独自指数70+ / F01後3F80+ / F03着差85+ / 単勝オッズ6倍+
出力: 20260802/20260802_来週狙い目馬ベスト5_SNS投稿案.docx
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

DB = Path.home() / 'Desktop' / '競馬予想レポート' / 'daily_pdca' / 'db' / 'race_results.json'
OUT = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260802\20260802_来週狙い目馬ベスト5_SNS投稿案.docx")
FONT = '游ゴシック'
DATES = ('20260801', '20260802')

with open(DB, encoding='utf-8') as f:
    db = json.load(f)
cands = []
for e in db:
    if e.get('date') not in DATES:
        continue
    try:
        if (e.get('AI印') in ('◎', '○', '▲')
            and 2 <= int(e.get('着順int', 99)) <= 4
            and float(e.get('独自指数', 0)) >= 70
            and float(e.get('F01_後3F', 0)) >= 80
            and float(e.get('F03_着差', 0)) >= 85
            and float(e.get('単勝オッズ', 0)) >= 6.0):
            cands.append(e)
    except (TypeError, ValueError):
        continue
cands.sort(key=lambda x: -float(x['独自指数']))
top5 = cands[:5]

doc = Document()
for s in doc.sections:
    s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.8)
    s.left_margin = Cm(2.0); s.right_margin = Cm(2.0)

def set_font(run, size=10, bold=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT)

def h1(text, color=(15,71,97)):
    p = doc.add_heading(text, level=1)
    for r in p.runs:
        set_font(r, 14); r.font.color.rgb = RGBColor(*color)

def h3(text):
    p = doc.add_heading(text, level=3)
    for r in p.runs:
        set_font(r, 11)

def box(lines, size=10):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("\n".join(lines))
    set_font(r, size)

def horse_line(e):
    d = f"{e['date'][4:6]}/{e['date'][6:]}"
    return (f"{e['馬名']}（{d} {e['競馬場']}{int(e['R'])}R {e.get('レース名','')} {int(e['着順int'])}着）")

def horse_detail(e):
    kyaku = e.get('脚質', '') or '差し'
    return [
        f"・独自指数{e['独自指数']}点（週末{len(cands)}頭の惜敗馬の中でも上位）",
        f"・上がり3F評価 F01={e['F01_後3F']}点 / 着差評価 F03={e['F03_着差']}点（僅差の負け）",
        f"・単勝{e['単勝オッズ']}倍({int(float(e.get('人気',0)))}番人気)と過小評価されての{int(e['着順int'])}着",
        f"・脚質{kyaku}。展開ひとつで突き抜ける内容でした",
    ]

t = doc.add_heading("来週狙い目馬ベスト5 SNS投稿案 2026/08/02", level=0)
for r in t.runs: set_font(r, 16)
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub = doc.add_paragraph(f"8/1-8/2 全936頭から条件抽出（候補{len(cands)}頭→上位5頭）")
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
for r in sub.runs: set_font(r, 10)
doc.add_paragraph()

h1("■ 選定データ（投稿には貼らない）")
box([f"{i+1}. {horse_line(e)} 指数{e['独自指数']} F01={e['F01_後3F']} F03={e['F03_着差']} "
     f"{e['単勝オッズ']}倍{int(float(e.get('人気',0)))}人気 騎手{e.get('騎手','')}"
     for i, e in enumerate(top5)], 9)

# ── X投稿 ────────────────────────────────────────────────
h1("【X投稿①】メイン発表（コピー用）", color=(20,100,50))
lines = [
    "【コピー用】",
    "🏇【来週の狙い目馬ベスト5】8/1-8/2の全レースから発掘💎",
    "━━ 惜敗×高指数×人気薄 = 次走で狙える馬たち ━━",
    "",
    "週末の全936頭をAI分析し、",
    "「上がり最速級の脚を使って僅差で負けた、人気薄の実力馬」だけを抽出しました。",
    "",
]
for i, e in enumerate(top5, 1):
    lines.append(f"{i}位 {e['馬名']}")
    lines.append(f"　{e['date'][4:6]}/{e['date'][6:]} {e['競馬場']}{int(e['R'])}R {int(e['着順int'])}着"
                 f"（{e['単勝オッズ']}倍{int(float(e.get('人気',0)))}人気）指数{e['独自指数']}点")
lines += [
    "",
    "5頭とも「負けて強し」の内容。次走に出てきたら要チェックです🎯",
    "各馬の詳細は返信スレッドで👇",
    "",
    "#競馬予想 #AI予想 #狙い目馬 #次走注目",
]
box(lines)

h1("【X投稿②〜⑥】馬別個別スレッド（コピー用）", color=(20,100,50))
for i, e in enumerate(top5, 1):
    h3(f"スレッド{i+1}: {i}位 {e['馬名']}")
    box([
        "【コピー用】",
        f"🏇【来週の狙い目馬 {i}位】{e['馬名']}",
        f"━━ {e['date'][4:6]}/{e['date'][6:]} {e['競馬場']}{int(e['R'])}R "
        f"{e.get('レース名','')} {int(e['着順int'])}着 ━━",
        "",
        *horse_detail(e),
        "",
        "次走で人気を落としていたら絶好の狙い目です🎯",
        "",
        "#狙い目馬 #次走注目 #競馬予想",
    ])

# ── Threads ─────────────────────────────────────────────
h1("【Threads投稿】2投稿構成", color=(80,40,120))
h3("投稿①（発表版）")
th1 = [
    "🏇【来週の狙い目馬ベスト5】週末の全レースから発掘💎",
    "",
    "「上がり最速級の脚で僅差負け×人気薄」の実力馬だけを抽出👇",
    "",
]
for i, e in enumerate(top5, 1):
    th1.append(f"{i}位 {e['馬名']}（{e['競馬場']}{int(e['R'])}R {int(e['着順int'])}着・"
               f"{e['単勝オッズ']}倍）指数{e['独自指数']}点")
th1 += ["", "5頭とも「負けて強し」。次走に出てきたら要チェックです🎯", "",
        "#競馬予想 #狙い目馬"]
n1 = len("\n".join(th1))
box([f"【コピー用】（{n1}字/500字）"] + th1)

h3("投稿②（根拠版）")
e1 = top5[0]
th2 = [
    f"🏇【狙い目馬1位 {e1['馬名']}の根拠】",
    "",
    f"{e1['date'][4:6]}/{e1['date'][6:]} {e1['競馬場']}{int(e1['R'])}R {int(e1['着順int'])}着",
    *horse_detail(e1),
    "",
    "選定条件は「AI上位評価×2-4着惜敗×指数70点以上×",
    "上がり評価80点以上×僅差×単勝6倍以上」。",
    "先週から継続中の定点観測です。次走をお楽しみに🎯",
    "",
    "#狙い目馬 #競馬予想",
]
n2 = len("\n".join(th2))
box([f"【コピー用】（{n2}字/500字）"] + th2)

# ── Note ────────────────────────────────────────────────
h1("【Note記事】来週狙い目馬ベスト5（コピー用）", color=(180,80,0))
note = [
    "来週の狙い目馬ベスト5 — 8/1-8/2の全936頭から「負けて強し」を発掘",
    "",
    "こんにちは、アスメシ競馬予想です🍱",
    "週末の全レース・全936頭のデータから、次走で狙える「惜敗の実力馬」を抽出しました。",
    "",
    "選定条件（毎週固定のルールです）",
    "・AIの上位評価（◎○▲）を受けていた馬",
    "・着順2〜4着の惜敗",
    "・独自指数70点以上",
    "・上がり3F評価80点以上（最速級の脚を使っている）",
    "・着差評価85点以上（僅差の負け）",
    "・単勝オッズ6倍以上（人気薄=過小評価）",
    "",
    f"今週の該当は{len(cands)}頭。その中から指数上位5頭を紹介します。",
    "",
    "---",
    "",
]
for i, e in enumerate(top5, 1):
    note.append(f"第{i}位 {e['馬名']}")
    note.append(f"{e['date'][4:6]}/{e['date'][6:]} {e['競馬場']}{int(e['R'])}R "
                f"{e.get('レース名','')} {int(e['着順int'])}着（{e['単勝オッズ']}倍"
                f"{int(float(e.get('人気',0)))}番人気）")
    note += horse_detail(e)
    note.append("")
    note.append("---")
    note.append("")
note += [
    "使い方",
    "",
    "この5頭が次走に出てきたとき、特に「今回と同条件or短縮」「人気がさらに落ちている」",
    "場合は絶好の狙い目です。毎週日曜夜に更新する定点観測企画として続けていきます。",
    "",
    "予想が参考になったらフォロー＆いいねお願いします！",
    "みなさんの馬券のヒントになりますように🍜🎉",
    "",
    "#競馬予想 #AI予想 #JRA #狙い目馬 #次走注目",
]
box(note, 9.5)

doc.save(str(OUT))
print(f"保存完了: {OUT}")
print("TOP5: " + " / ".join(e['馬名'] for e in top5))
