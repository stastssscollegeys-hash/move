# -*- coding: utf-8 -*-
"""
来週狙い目馬ベスト5 SNS投稿案 — 2026/05/30-31 週末データ版
出力: Desktop/競馬予想レポート/20260601/20260601_来週狙い目馬ベスト5_SNS投稿案.docx
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

OUTPUT = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260601\20260601_来週狙い目馬ベスト5_SNS投稿案.docx")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

FONT = '游ゴシック'

# ============================================================
# 来週狙い目馬ベスト5（5/30-31 PDCAから選定）
# 選定条件: AI印◎○▲・2-4着惜敗・独自指数70+・後3F100・着差F03=85+
# ============================================================
# 1. ゴーイントゥスカイ  東京11R日本ダービー4着 ◎77.5点 6.6倍 武豊
# 2. ダノンシーマ        東京12R目黒記念3着   ◎77.5点 3.8倍 川田
# 3. ハーバーライト      東京4R障害未勝利3着  ○76.5点 6.1倍 難波
# 4. ギオンバヤシ        京都4R3歳未勝利3着   ○75.7点 7.6倍 武豊
# 5. イヌボウノウタゴエ  東京7R1勝クラス2着   ◎76.0点 4.0倍 横山武

TARGETS = [
    {
        "rank":    1,
        "name":    "ゴーイントゥスカイ",
        "date":    "2026/05/31",
        "venue":   "東京",
        "race":    "日本ダービー G1",
        "result":  "4着（1着ロブチェンから0.4秒差）",
        "jockey":  "武豊",
        "odds":    6.6,
        "score":   77.5,
        "mark":    "◎",
        "comment": """\
青葉賞Vの東京2400m実績を引き下げ、ダービー本番で4着。
後3F=100点の末脚は全18頭の上位レベルで、終い33.8秒の伸びはメンバー中でもトップクラス。
ロブチェン・パントルナイーフ・バステールに次ぐ4着という事実が実力を証明。
武豊継続騎乗の可能性が高く、次走（古馬GII・GTAあたり）では人気が落ちてEV+に転じる公算大。
今週の反省ルール「惜敗馬の巻き返しに注目」をそのまま体現する一頭。""",
        "next_race": "神戸新聞杯（G2）など秋の古馬重賞が次走目標と推測",
        "ev_note":   "6.6倍→次走は人気落ちでさらにEV+",
    },
    {
        "rank":    2,
        "name":    "ダノンシーマ",
        "date":    "2026/05/31",
        "venue":   "東京",
        "race":    "目黒記念 G2",
        "result":  "3着（1着ファイアンクランツのハナ差）",
        "jockey":  "川田将雅",
        "odds":    3.8,
        "score":   77.5,
        "mark":    "◎",
        "comment": """\
直線長いコース成績 4-0-1-0 → 本日で 4-0-2-0 へ更新。崩れなかった。
目黒記念で本命評価も3着に終わったが、ハナ差クビ差の僅差決着。
ファイアンクランツ（1着）とはほぼ同等の力。
川田将雅継続騎乗かつ、次走でも「直線長いコース」を選択すれば確実に巻き返す。
オッズが3.8倍と低めだが、堅軸として安定回収を狙える信頼度最高の1頭。""",
        "next_race": "秋のAJCC・タフな長距離重賞が目標か",
        "ev_note":   "安定軸として馬連・ワイドのベース馬",
    },
    {
        "rank":    3,
        "name":    "ハーバーライト",
        "date":    "2026/05/30",
        "venue":   "東京",
        "race":    "4歳以上障害未勝利",
        "result":  "3着（○・76.5点）",
        "jockey":  "難波",
        "odds":    6.1,
        "score":   76.5,
        "mark":    "○",
        "comment": """\
障害未勝利で3着惜敗。後3F=100点の走りで着差スコア97点（わずか僅差）。
オッズ6.1倍でEV+の好条件。次走の障害戦で勝ち上がりのチャンス。
難波騎手との相性が良く、続けて乗れれば勝利圏内と判断。""",
        "next_race": "障害未勝利戦（東京・中京あたり）",
        "ev_note":   "6倍超でEV+。障害入門戦の狙い目",
    },
    {
        "rank":    4,
        "name":    "ギオンバヤシ",
        "date":    "2026/05/30",
        "venue":   "京都",
        "race":    "3歳未勝利",
        "result":  "3着（○・75.7点）",
        "jockey":  "武豊",
        "odds":    7.6,
        "score":   75.7,
        "mark":    "○",
        "comment": """\
武豊騎乗の3歳未勝利馬。7.6倍という好オッズで後3F=100点の末脚。
着差スコア85点（0.5馬身以内）の惜敗。
未勝利戦なので次走で勝ち上がれる力量は十分。
武豊継続騎乗なら本命候補に昇格する可能性が高い。""",
        "next_race": "3歳未勝利戦（京都・阪神）",
        "ev_note":   "7.6倍の高EV+。次走は◎候補",
    },
    {
        "rank":    5,
        "name":    "イヌボウノウタゴエ",
        "date":    "2026/05/30",
        "venue":   "東京",
        "race":    "3歳1勝クラス",
        "result":  "2着（◎・76.0点）",
        "jockey":  "横山武史",
        "odds":    4.0,
        "score":   76.0,
        "mark":    "◎",
        "comment": """\
3歳1勝クラスで本命評価も2着惜敗。後3F=100点で着差スコア85点（わずか届かず）。
横山武史継続騎乗の可能性高く、1勝クラスを勝ち上がる力量は十分。
オッズ4倍は6倍未満だが、◎本命評価×惜敗×指数76点という条件で選出。""",
        "next_race": "3歳1勝クラス（東京・中京）",
        "ev_note":   "次走も◎軸として堅実に回収を狙う",
    },
]

# ============================================================
# Word文書生成
# ============================================================
doc = Document()
for sec in doc.sections:
    sec.top_margin    = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin   = Cm(2.5)
    sec.right_margin  = Cm(2.5)

def set_font(run, size_pt=10.5, bold=False, color=None):
    run.font.name = FONT
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:hint'), 'eastAsia')
    rFonts.set(qn('w:eastAsia'), FONT)
    rpr.insert(0, rFonts)

def add_box(lines, bg="F5F5F5"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = 'Table Grid'
    cell = tbl.rows[0].cells[0]
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), bg)
    tcPr.append(shd)
    for line in lines:
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, 10.5)
    doc.add_paragraph()

def h1(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True; run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    run.font.name = FONT
    return p

def h2(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True; run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    run.font.name = FONT
    return p

def h3(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True; run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x37, 0x5C, 0x21)
    run.font.name = FONT
    return p

# ヘッダー
t = doc.add_heading("来週狙い目馬ベスト5  2026/06/01（月）", level=0)
for run in t.runs:
    run.font.size = Pt(16)
    run.font.name = FONT
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub = doc.add_paragraph("2026/05/30-31 PDCA振り返り → 次走注目馬選定")
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in sub.runs:
    set_font(run, 10)
doc.add_paragraph()

# ──── X投稿 ────
h1("X投稿文（認証済み・長文版）")

h2("X投稿①  来週狙い目馬 予告メイン")
picks_preview = "\n".join([
    f"🐴{t['rank']}位 {t['name']}（{t['race']} {t['result']} / {t['odds']}倍）"
    for t in TARGETS
])
add_box([
    "【コピー用】",
    "🔍【来週狙い目馬ベスト5】2026/06/01",
    "━━ 先週惜敗した隠れ好走馬を厳選！ ━━",
    "",
    picks_preview,
    "",
    "選定条件：AI印◎○▲×2〜4着惜敗×後3F上位×着差0.5馬身以内×独自指数70点以上",
    "",
    "最注目は1位のゴーイントゥスカイ！",
    "ダービー4着の実力をそのままに、次走で人気が落ちればEV+の絶好機🔥",
    "",
    "#来週狙い目 #競馬予想 #AI予想 #JRA",
], "FFF3E0")

# 各馬別投稿（2〜4）
for t in TARGETS[:3]:
    h2(f"X投稿  {t['rank']}位 {t['name']} 詳細")
    add_box([
        "【コピー用】",
        f"🐴【来週注目馬 {t['rank']}位】{t['name']}（{t['jockey']}）",
        f"━━ {t['date']} {t['venue']} {t['race']} {t['result']} ━━",
        "",
        f"アスメシ式独自指数 {t['score']}点 / AI印{t['mark']}",
        f"前走オッズ {t['odds']}倍 → {t['ev_note']}",
        "",
        *t['comment'].split('\n'),
        "",
        f"次走目標：{t['next_race']}",
        "",
        "#来週注目馬 #競馬予想 #AI予想",
    ], "E3F2FD")

# ──── Threads ────
h1("Threads投稿（5スレッド）")
threads = [
    ("1/5 イントロ", [
        "🔍【来週狙い目馬ベスト5】",
        "先週末の惜敗馬から「次走で巻き返す馬」を厳選しました。",
        "",
        "選定基準：AI印◎○▲×2〜4着×後3F上位",
        f"今週末({', '.join(t['name'] for t in TARGETS[:3])})が有力候補！",
        "",
        "#来週注目馬 #競馬 #AI予想",
    ]),
    ("2/5 1位 ゴーイントゥスカイ", [
        f"【1位】ゴーイントゥスカイ（武豊）",
        "ダービー4着（0.4秒差）・後3F=100点",
        "本番で上位の末脚を見せた。次走で人気落ちならEV+。",
        "武豊継続騎乗×直線長いコースで◎本命候補！",
        "",
        "#ゴーイントゥスカイ #来週注目 #競馬",
    ]),
    ("3/5 2位 ダノンシーマ", [
        "【2位】ダノンシーマ（川田将雅）",
        "目黒記念3着（ハナ差）・直線長いコース5-0-2-0に更新",
        "崩れない安定感が武器。次走でも◎軸候補。",
        "オッズは低めでも堅実に回収できる信頼度最高の一頭。",
        "",
        "#ダノンシーマ #来週注目 #競馬",
    ]),
    ("4/5 3〜5位", [
        "【3位】ハーバーライト（難波）",
        "障害3着・後3F=100点・6.1倍EV+",
        "",
        "【4位】ギオンバヤシ（武豊）",
        "3歳未勝利3着・7.6倍の高EV+・武豊継続",
        "",
        "【5位】イヌボウノウタゴエ（横山武史）",
        "1勝クラス2着・後3F=100点",
        "",
        "#来週注目馬 #競馬",
    ]),
    ("5/5 まとめ・予告", [
        "来週のレース情報が確定次第、",
        "この5頭の出走情報をチェックして予想に組み込みます。",
        "",
        "特に1位ゴーイントゥスカイが出走するレースは",
        "◎本命で勝負する予定🔥",
        "",
        "フォローしてお待ちください🐴",
        "#競馬予想 #AI予想 #来週 #JRA",
    ]),
]
for title, lines in threads:
    h3(f"Threads {title}")
    add_box(["【コピー用】"] + lines, "FAFAFA")

# ──── Note記事 ────
h1("Note記事（来週狙い目馬ベスト5）")
note_lines = [
    "来週狙い目馬ベスト5 — 2026年6月第1週 アスメシ競馬予想",
    "",
    "今週末（5/30-31）のJRA競馬でAI印◎○▲をつけながら惜敗した馬たちを分析。",
    "「次走で巻き返す可能性が最も高い5頭」を選定しました。",
    "",
    "選定基準：AI印◎○▲ × 2〜4着惜敗 × 後3Fスコア80点以上 × 着差0.5馬身以内 × 独自指数70点以上",
    "（今週末は31頭が惜敗条件を満たし、その上位5頭を選出）",
    "",
    "───────────────────────────────────",
]
for t in TARGETS:
    note_lines += [
        f"{t['rank']}位  {t['name']}（{t['jockey']}）",
        f"前走：{t['date']} {t['venue']} {t['race']}  {t['result']}",
        f"独自指数：{t['score']}点 / AI印：{t['mark']} / 前走オッズ：{t['odds']}倍",
        "",
        t['comment'],
        f"次走目標：{t['next_race']}",
        f"EV評価：{t['ev_note']}",
        "",
        "───────────────────────────────────",
    ]
note_lines += [
    "以上、来週の狙い目馬ベスト5でした。",
    "出走情報が確定したら、各馬の詳細予想を投稿予定です。",
    "フォロー&いいねをよろしくお願いします！🐴",
    "",
    "#競馬予想 #AI予想 #JRA #来週注目馬 #狙い目馬",
]
p = doc.add_paragraph("\n".join(note_lines))
for run in p.runs:
    run.font.name = FONT
    run.font.size = Pt(10)

doc.save(str(OUTPUT))
print(f"✅ 保存完了: {OUTPUT}")
