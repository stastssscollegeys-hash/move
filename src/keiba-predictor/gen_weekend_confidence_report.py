# -*- coding: utf-8 -*-
"""
gen_weekend_confidence_report.py — 週末全レース 自信度付き予想レポート

collect_weekend_bigdata.py が出力した records.json を読み、
各レースの自信度（1〜10）を全ファクターから算出。
全レースに印+独自指数一覧、自信度7以上のレースには根拠付き予想文を記載。

使い方:
  python gen_weekend_confidence_report.py --json "C:/Users/User/Desktop/競馬予想レポート/20260801/週末ビッグデータ_20260801-0802_records.json"
"""
from __future__ import annotations
import sys, json, argparse
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

FONT = '游ゴシック'

FACTOR_LABELS = {
    'F01_後3F':  '後3F末脚',
    'F02_タイム': '走破タイム',
    'F03_着差':  '着差(接戦力)',
    'F04_騎手':  '騎手実勝率',
    'F05_厩舎':  '厩舎実勝率',
    'F06_枠':    '枠順バイアス',
    'F07_馬番':  '馬番内外',
    'F08_距離':  '距離適性',
    'F09_体重':  '馬体重',
    'F10_斤量':  '斤量妙味',
    'F11_性別':  '性別',
    'F12_年齢':  '年齢曲線',
    'F13_クラス': 'クラス実績',
    'F14_馬場':  '馬場適性',
    'F15_EV':    'EV',
    'F16_乖離':  '人気乖離',
    'F17_頭数':  '頭数',
}
FKEYS = list(FACTOR_LABELS.keys())


# ============================================================
# 自信度算出（1〜10）
# ============================================================
def calc_confidence(recs: list[dict]) -> tuple[int, list[str]]:
    """
    レース内の全馬レコード（総合指数降順）から自信度と根拠タグを返す。
      +基準3点
      上位差:   1位-2位の総合指数差 >=5→+3 / >=3→+2 / >=1.5→+1
      絶対水準: 1位総合 >=72→+2 / >=68→+1
      指標一致: 独自指数1位とML1位が同一馬→+2
      DB裏付け: 1位のDB最高指数 >=75→+1
      少頭数:   10頭以下→+1
      減点:     1位総合<60→-2 / 過去走ゼロ(新馬戦等)→-2
    """
    top = recs[0]
    conf = 3
    tags = []

    gap = top['総合指数'] - recs[1]['総合指数'] if len(recs) > 1 else 5.0
    if gap >= 5.0:
        conf += 3; tags.append(f"2位と{gap:.1f}pt差の断然評価")
    elif gap >= 3.0:
        conf += 2; tags.append(f"2位と{gap:.1f}pt差")
    elif gap >= 1.5:
        conf += 1; tags.append(f"2位と{gap:.1f}pt差")
    else:
        tags.append(f"上位拮抗({gap:.1f}pt差)")

    if top['総合指数'] >= 72:
        conf += 2; tags.append(f"総合指数{top['総合指数']}の高水準")
    elif top['総合指数'] >= 68:
        conf += 1

    dokuji_top = max(recs, key=lambda x: x['独自指数'])
    ml_top     = max(recs, key=lambda x: x['ML能力%'])
    if dokuji_top['馬番'] == top['馬番'] and ml_top['馬番'] == top['馬番']:
        conf += 2; tags.append("独自指数・ML能力の両系統で1位が一致")

    if top.get('DB最高指数', 0) and top['DB最高指数'] >= 75:
        conf += 1; tags.append(f"累積DB最高指数{top['DB最高指数']}点の実績裏付け")

    n = top.get('頭数', 16)
    if n <= 10:
        conf += 1; tags.append(f"{n}頭立ての少頭数")

    if top['総合指数'] < 60:
        conf -= 2; tags.append("全体スコア低調")
    no_past = sum(1 for r in recs if r.get('近5走平均着', 0) == 0)
    if no_past >= len(recs) * 0.5:
        conf -= 2; tags.append("過去走データ不足(新馬戦等)")

    return max(1, min(10, conf)), tags


def honmei_reasoning(top: dict, second: dict) -> list[str]:
    """本命馬の根拠文を因子データから生成する。"""
    lines = []

    # 最強ファクターTOP3
    fs = sorted(((k, top.get(k, 0)) for k in FKEYS), key=lambda x: -x[1])[:3]
    strong = "・".join(f"{FACTOR_LABELS[k]}{v:.0f}点" for k, v in fs)
    lines.append(f"最強ファクター: {strong}")

    if top.get('F01_後3F', 0) >= 80:
        lines.append(f"過去5走の最速上がりが優秀（F01={top['F01_後3F']}点）。決め手上位。")
    if top.get('騎手勝率%', 0) >= 12:
        lines.append(f"鞍上の実勝率{top['騎手勝率%']}%は出走騎手の中でも高水準。")
    if top.get('厩舎勝率%', 0) >= 12:
        lines.append(f"厩舎勝率{top['厩舎勝率%']}%と仕上げにも定評。")
    if top.get('同距離走数', 0) >= 2 and top.get('同距離複勝率%', 0) >= 50:
        lines.append(f"同距離{top['同距離走数']}走・複勝率{top['同距離複勝率%']:.0f}%とコース適性は実証済み。")
    if top.get('近5走複勝率%', 0) >= 60:
        lines.append(f"近5走複勝率{top['近5走複勝率%']:.0f}%（平均{top['近5走平均着']}着）と安定感抜群。")
    if top.get('DB最高指数', 0) >= 75:
        db_line = f"累積DB（実測9,259戦）でも最高指数{top['DB最高指数']}点"
        if top.get('DB平均着順', 0) and top['DB平均着順'] <= 3.5:
            db_line += f"・平均着順{top['DB平均着順']}着"
        lines.append(db_line + "と実績が裏付ける。")
    if top.get('ML能力%', 0) >= 28:
        lines.append(f"LightGBM v44のML能力{top['ML能力%']}%はフィールド最上位クラス。")

    gap = top['総合指数'] - second['総合指数']
    lines.append(
        f"対抗{second['馬番']}番{second['馬名']}（総合{second['総合指数']}）に"
        f"{gap:.1f}pt差。単勝・馬連の軸として信頼。"
    )
    return lines


# ============================================================
# Word出力
# ============================================================
def set_font(run, size=10, bold=False, color=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--conf-detail', type=int, default=7,
                    help='この自信度以上のレースに根拠付き予想を記載')
    args = ap.parse_args()

    with open(args.json, encoding='utf-8') as f:
        data = json.load(f)
    records = data['records']

    # レース単位にグループ化
    races = defaultdict(list)
    for r in records:
        races[(r['date'], r['競馬場'], r['R'])].append(r)
    for k in races:
        races[k].sort(key=lambda x: x['AI予測順位'])

    # 自信度計算
    race_conf = {}
    for k, recs in races.items():
        race_conf[k] = calc_confidence(recs)

    dates = sorted(set(k[0] for k in races))
    first, last = dates[0], dates[-1]

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(1.8); section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.0); section.right_margin = Cm(2.0)

    def h1(text, color=(15, 71, 97)):
        p = doc.add_heading(text, level=1)
        for run in p.runs:
            set_font(run, 14); run.font.color.rgb = RGBColor(*color)

    def h2(text, color=(40, 40, 40)):
        p = doc.add_heading(text, level=2)
        for run in p.runs:
            set_font(run, 12); run.font.color.rgb = RGBColor(*color)

    def body(text, size=10, bold=False):
        p = doc.add_paragraph()
        run = p.add_run(text)
        set_font(run, size, bold=bold)
        return p

    # ── タイトル ────────────────────────────────────────────
    t = doc.add_heading(
        f"週末全レース予想 自信度レポート {first[:4]}/{first[4:6]}/{first[6:]}〜{last[4:6]}/{last[6:]}",
        level=0)
    for run in t.runs:
        set_font(run, 16)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(
        "17ファクター独自指数 × LightGBM v44 ML能力 × 累積DB9,259戦照合 / 全72レース929頭")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in sub.runs:
        set_font(run, 10)
    doc.add_paragraph()

    # ── 自信度ランキング（サマリー表）───────────────────────
    h1("■ 自信度ランキング（全レース）")
    body("自信度 = 上位差・絶対水準・独自指数/ML一致・累積DB裏付け・頭数から10段階で算出", 9)

    ranked = sorted(races.keys(), key=lambda k: (-race_conf[k][0], k))
    tbl = doc.add_table(rows=1, cols=7)
    tbl.style = 'Table Grid'
    hdr = tbl.rows[0].cells
    for i, txt in enumerate(['自信度', '日付', '会場R', 'レース名', '距離', '本命◎', '総合指数']):
        hdr[i].text = txt
        for p_ in hdr[i].paragraphs:
            for run in p_.runs:
                set_font(run, 9, bold=True)
    for k in ranked:
        conf, _ = race_conf[k]
        recs = races[k]
        top = recs[0]
        row = tbl.add_row().cells
        row[0].text = f"{conf}/10 {'★'*conf}"
        row[1].text = f"{k[0][4:6]}/{k[0][6:]}"
        row[2].text = f"{k[1]}{k[2]}R"
        row[3].text = top['レース名'][:14]
        row[4].text = top['距離']
        row[5].text = f"{top['馬番']}番{top['馬名']}"
        row[6].text = str(top['総合指数'])
        for c in row:
            for p_ in c.paragraphs:
                for run in p_.runs:
                    set_font(run, 8.5)
    doc.add_paragraph()

    # ── 日別・レース別詳細 ──────────────────────────────────
    weekday = {0:'月',1:'火',2:'水',3:'木',4:'金',5:'土',6:'日'}
    import datetime as _dt
    for d in dates:
        wd = weekday[_dt.date(int(d[:4]), int(d[4:6]), int(d[6:])).weekday()]
        h1(f"■ {d[:4]}/{d[4:6]}/{d[6:]}（{wd}）", color=(150, 30, 30))
        day_keys = sorted([k for k in races if k[0] == d], key=lambda k: (k[1], k[2]))
        for k in day_keys:
            recs = races[k]
            top = recs[0]
            conf, tags = race_conf[k]
            grade = f" [{top['グレード']}]" if top['グレード'] else ""
            h2(f"{k[1]}{k[2]}R {top['レース名']}{grade} {top['距離']} {top['頭数']}頭"
               f"　自信度 {conf}/10 {'★'*conf}",
               color=(180, 80, 0) if conf >= args.conf_detail else (40, 40, 40))

            # 印一覧（上位5頭 + 印なし高独自指数馬）
            marked = [r for r in recs if r['AI印']]
            for r in marked:
                db_note = f"｜DB最高{r['DB最高指数']}" if r.get('DB最高指数') else ""
                body(f"{r['AI印']} {r['馬番']:>2}番 {r['馬名']}"
                     f"　独自{r['独自指数']}｜ML{r['ML能力%']}%｜総合{r['総合指数']}{db_note}"
                     f"｜{r.get('脚質','?')}｜騎手勝率{r.get('騎手勝率%',0)}%",
                     9.5)

            # 自信度が高いレース → 根拠付き予想
            if conf >= args.conf_detail:
                body("── 予想の根拠 ──", 9.5, bold=True)
                for tag in tags:
                    body(f"・{tag}", 9.5)
                body(f"◎{top['馬番']}番 {top['馬名']} を推す理由:", 9.5, bold=True)
                for line in honmei_reasoning(top, recs[1] if len(recs) > 1 else top):
                    body(f"　{line}", 9.5)
                # 買い方の方向性
                if conf >= 9:
                    bet = "単勝・馬連本線を厚めに。3連複は上位3頭軸で。"
                elif conf >= 8:
                    bet = "馬連本線を軸に、3連複で穴をカバー。"
                else:
                    bet = "馬連中心。対抗逆転にワイドで保険。"
                body(f"　買い方の方向性: {bet}", 9.5)
            doc.add_paragraph()

    out_dir = Path(args.json).parent
    out = out_dir / f"週末全レース予想_自信度レポート_{first}-{last[4:]}.docx"
    doc.save(str(out))

    # コンソールサマリー
    print(f"\n{'='*80}")
    print(f"自信度レポート完了: {len(races)}レース")
    dist = defaultdict(int)
    for k in races:
        dist[race_conf[k][0]] += 1
    print("自信度分布:", dict(sorted(dist.items(), reverse=True)))
    print(f"\n=== 自信度{args.conf_detail}以上のレース ===")
    for k in ranked:
        conf, _ = race_conf[k]
        if conf < args.conf_detail:
            break
        top = races[k][0]
        print(f"  {conf}/10 {k[0][4:6]}/{k[0][6:]} {k[1]}{k[2]:>2}R "
              f"{top['レース名'][:16]:<16} ◎{top['馬番']:>2}番{top['馬名']} 総合{top['総合指数']}")
    print(f"\n[保存] {out}")


if __name__ == '__main__':
    main()
