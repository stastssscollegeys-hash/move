#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
predict_and_report.py  -- 「予想をしてください」ワンコマンドパッケージ

フロー:
  1. MLモデルで全レース予測（前日=netkeiba / 当日=smartrc）
  2. 推奨レースごとに全馬ability%スコアを計算
  3. シルシ（◎○▲△✕）を自動付与
  4. Wordレポートをデスクトップに保存
  5. コンソールに予想サマリーを表示

使い方:
  # 前日予測（翌日のレース）
  python predict_and_report.py --tomorrow
  python predict_and_report.py --date 20260413

  # 当日予測（smartrc・オッズ込み）
  python predict_and_report.py --today

  # 会場を絞る（前日）
  python predict_and_report.py --tomorrow --venue hanshin

  # Word出力先を変える（デフォルト: Desktop）
  python predict_and_report.py --tomorrow --output /path/to/output.docx
"""
from __future__ import annotations

import sys, os, json, argparse, datetime
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
DATA_DIR = SRC_DIR / 'data'
MODEL_DIR = DATA_DIR / 'models'
CACHE_DIR = SRC_DIR / '_cache' / 'netkeiba'

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SRC_DIR / 'scraper'))

import numpy as np
import lightgbm as lgb

from convert_netkeiba_to_features import (
    load_stats as load_stats_nk, load_bloodline, load_name_to_id_maps,
    convert_shutuba_horse, rcode_to_netkeiba_id, rcode_to_month,
)
from convert_smartrc_to_features import (
    load_stats as load_stats_smartrc, convert_race, FIELDNAMES,
)
from smartrc_api import SmartRCAPI, _VENUE_EN
from netkeiba import NetkeibaScaper

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
VENUE_NAMES = {
    1:'札幌', 2:'函館', 3:'福島', 4:'新潟', 5:'東京',
    6:'中山', 7:'中京', 8:'京都', 9:'阪神', 10:'小倉'
}
EXCLUDED_VENUES = {3}   # 福島は除外（モデル適性外）
MIN_DISTANCE   = 1600   # 推奨対象の最低距離（マイラーズカップ対応）
MIN_RUNNERS    = 10     # 最低頭数
EV_THRESHOLD   = 0.80   # 当日予測EV閾値（G2対応で緩和）
MAX_ODDS       = 100    # 最大オッズ
MIN_AGE        = 3
MIN_NINKI      = 1      # 全人気帯を対象

# 能力モデルの特徴量カラム（predict_smartrc.py と同じ定義）
FEATURE_COLS = [
    'waku', 'sex_cd', 'barei', 'futan', 'ba_taijyu', 'zogen_sa', 'blinker',
    'distance', 'dist_cat', 'surface', 'grade_cd', 'tenko_cd', 'baba_cd',
    'syusso_tosu', 'prize_1', 'venue_cd', 'month', 'race_num',
    'odds', 'ninki',
    'num_past_races', 'avg_finish_5', 'best_finish_5',
    'win_rate_5', 'top3_rate_5',
    'avg_time_5', 'avg_l3f_5',
    'days_since_last', 'running_style', 'avg_j4c_5',
    'same_dist_runs', 'same_dist_winrate', 'same_dist_top3rate',
    'same_surface_runs', 'same_surface_winrate', 'same_surface_top3rate',
    'heavy_baba_runs', 'heavy_baba_top3rate',
    'jockey_winrate', 'trainer_winrate',
    'father_winrate', 'bms_winrate',
    'father_surface_wr', 'bms_surface_wr',
]
ABILITY_COLS = [c for c in FEATURE_COLS if c not in ('odds', 'ninki')]


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


# ---------------------------------------------------------------------------
# モデルロード
# ---------------------------------------------------------------------------
def load_models():
    print("Loading models...", file=sys.stderr)
    ability_models = [
        lgb.Booster(model_file=str(MODEL_DIR / f'lgb_v44_ability_{i}.txt'))
        for i in range(3)
    ]
    market_models = [
        lgb.Booster(model_file=str(MODEL_DIR / f'lgb_v44_market_{i}.txt'))
        for i in range(3)
    ]
    print("  Model: v44 (M:3 A:3)", file=sys.stderr)
    return ability_models, market_models


# ---------------------------------------------------------------------------
# 多ファクター分析ユーティリティ
# ---------------------------------------------------------------------------
_RS_MAP = {1: '逃げ', 2: '先行', 3: '差し', 4: '追込'}


def extract_horse_factors(row: dict) -> dict:
    """all_rows の1馬行から主要因子を抽出する。"""
    def fv(k):
        v = to_float(row.get(k, 0))
        return 0.0 if (v != v) else v  # NaN→0
    return {
        'waku'       : int(fv('waku')),
        'sd_runs'    : int(fv('same_dist_runs')),
        'sd_wr'      : fv('same_dist_winrate'),
        'sd_t3'      : fv('same_dist_top3rate'),
        'jockey_wr'  : fv('jockey_winrate'),
        'trainer_wr' : fv('trainer_winrate'),
        'avg_finish' : fv('avg_finish_5'),
        'top3_rate'  : fv('top3_rate_5'),
        'avg_l3f'    : fv('avg_l3f_5'),
        'rs'         : _RS_MAP.get(int(fv('running_style')), '?'),
        'father_wr'  : fv('father_winrate'),
        'days_since' : int(fv('days_since_last')),
        'num_past'   : int(fv('num_past_races')),
    }


def factor_line(f: dict) -> str:
    """因子を1行テキストに変換（コンソール表示用）。"""
    parts = []
    if f.get('sd_runs', 0) > 0:
        parts.append(f"同距離{f['sd_runs']}走/{f['sd_wr']*100:.0f}%")
    parts.append(f"騎手{f['jockey_wr']*100:.1f}%")
    if f.get('trainer_wr', 0):
        parts.append(f"厩舎{f['trainer_wr']*100:.1f}%")
    if f.get('avg_finish', 0):
        parts.append(f"近走{f['avg_finish']:.1f}着")
    if f.get('avg_l3f', 0):
        parts.append(f"上がり{f['avg_l3f']:.1f}秒")
    if f.get('rs', '?') != '?':
        parts.append(f"脚質:{f['rs']}")
    if f.get('days_since', 0):
        parts.append(f"中{f['days_since']}日")
    return ' | '.join(parts)


def factor_alert(f: dict, rank: int) -> str:
    """ML上位馬の懸念・ML下位馬の見どころを検出する。"""
    alerts = []
    if rank <= 3:
        if f.get('sd_runs', 0) >= 3 and f.get('sd_wr', 0) < 0.10:
            alerts.append('同距離苦手')
        if f.get('jockey_wr', 0) < 0.05 and f.get('num_past', 0) > 0:
            alerts.append('騎手弱')
        if f.get('days_since', 0) > 90:
            alerts.append(f'休み明け{f["days_since"]}日')
    else:
        if f.get('sd_runs', 0) >= 2 and f.get('sd_wr', 0) > 0.33:
            alerts.append('コース適性◎')
        if f.get('top3_rate', 0) > 0.55 and f.get('avg_finish', 0) < 3.5:
            alerts.append('近走好調')
    return ', '.join(alerts) if alerts else ''


# ---------------------------------------------------------------------------
# シルシ付与ロジック
# ---------------------------------------------------------------------------
def assign_marks(sorted_horses: list[tuple]) -> list[tuple]:
    """
    sorted_horses: [(umaban, name, ability_pct), ...] ability%降順

    Returns: [(umaban, name, ability_pct, mark), ...]
    marks: ◎ ○ ▲ △ △  (5位以降は無印 or ✕)
    """
    MARKS = ['◎', '○', '▲', '△', '△']
    result = []
    n = len(sorted_horses)
    for i, (ub, nm, ab) in enumerate(sorted_horses):
        if i < len(MARKS):
            mark = MARKS[i]
        elif i == n - 1 and ab < 5.0:
            mark = '✕'   # 最下位かつ5%未満
        else:
            mark = ''
        result.append((ub, nm, ab, mark))
    return result


# ---------------------------------------------------------------------------
# 全馬ability計算（キャッシュ利用）
# ---------------------------------------------------------------------------
def compute_all_horse_scores(
    race_key: str,
    shutuba_cache: dict,
    past_cache: dict,
    stats: dict,
    bloodline: dict,
    name_father_map: dict,
    name_bms_map: dict,
    ability_models: list,
    month: int,
) -> list[tuple]:
    """
    race_key: netkeiba race_id (例: '202609020611')
    Returns: [(umaban, horse_name, ability_pct), ...] ability%降順
    """
    data = shutuba_cache.get(race_key)
    if not data:
        return []

    race_info = data['race_info']
    race_info['month'] = month
    horses_raw = data['horses']

    all_rows = []
    horse_meta = []
    for h in horses_raw:
        hid = h.get('horse_id', '')
        past = past_cache.get(hid, [])
        try:
            row = convert_shutuba_horse(
                h, race_info, past, stats, bloodline,
                name_father_map=name_father_map,
                name_bms_map=name_bms_map,
            )
        except Exception:
            row = {}
        all_rows.append(row)
        horse_meta.append((h['umaban'], h['horse_name']))

    if not all_rows:
        return []

    X = np.array(
        [[to_float(r.get(c)) for c in ABILITY_COLS] for r in all_rows],
        dtype=np.float32,
    )
    pred = np.mean([m.predict(X) for m in ability_models], axis=0)

    results = [
        (horse_meta[i][0], horse_meta[i][1], float(pred[i]) * 100)
        for i in range(len(all_rows))
    ]
    results.sort(key=lambda x: -x[2])
    return results


# ---------------------------------------------------------------------------
# Wordレポート生成
# ---------------------------------------------------------------------------
def generate_word_report(
    date_str: str,
    race_summaries: list[dict],
    output_path: str,
    use_netkeiba: bool,
):
    """
    race_summaries: [{
        'venue': str, 'race_num': str, 'distance': int, 'title': str,
        'all_horses': [(umaban, name, ability_pct, mark), ...],
        'rec_umaban': str, 'rec_name': str, 'rec_ability': float,
        'top3': [(umaban, name, pct), ...],
    }, ...]
    """
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'メイリオ'
    style.font.size = Pt(10.5)

    mode = '前日予測（netkeibaモデル）' if use_netkeiba else '当日予測（smartrcオッズ込み）'
    dt = datetime.datetime.strptime(date_str, '%Y%m%d')
    date_label = dt.strftime('%Y年%m月%d日')
    month_day  = dt.strftime('%m/%d')

    title = doc.add_heading(f'🍱 アスメシ競馬予想 AI予想レポート {date_label}', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f'AIモデル（LightGBM v44）で全頭分析｜全馬シルシ付き')
    doc.add_paragraph(f'こんにちは！アスメシ競馬予想です😊 本日の予想をお届けします。')
    doc.add_paragraph()

    # ── 全レースサマリー表 ──────────────────────────────────
    doc.add_heading('📋 今日のおすすめレース一覧', level=2)
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, txt in enumerate(['会場', 'R', '距離', '本命', '能力%']):
        hdr[i].text = txt
        hdr[i].paragraphs[0].runs[0].bold = True

    for rs in race_summaries:
        rc = table.add_row().cells
        rc[0].text = rs['venue']
        rc[1].text = f"R{rs['race_num']}"
        rc[2].text = f"{rs['distance']}m"
        rc[3].text = f"◎{rs['rec_umaban']}番 {rs['rec_name']}"
        rc[4].text = f"{rs['rec_ability']:.1f}%"

    doc.add_paragraph()

    # ── 各レース詳細（全馬シルシ）──────────────────────────
    doc.add_heading('🐴 各レース 全頭シルシ詳細', level=2)

    for rs in race_summaries:
        title_text = rs.get('title', f"{rs['venue']} {rs['race_num']}R")
        doc.add_heading(
            f"【{rs['venue']} R{rs['race_num']} {rs['distance']}m】 {title_text}",
            level=3,
        )

        if rs.get('all_horses'):
            t = doc.add_table(rows=1, cols=7)
            t.style = 'Table Grid'
            h2 = t.rows[0].cells
            for i, txt in enumerate(['シルシ', '馬番', '馬名', '能力%',
                                      '同距離(勝/3着)', '騎手%/厩舎%', '脚質/近走/上がり']):
                h2[i].text = txt
                h2[i].paragraphs[0].runs[0].bold = True

            horse_factors = rs.get('horse_factors', {})
            for rank, (umaban, name, ab, mark) in enumerate(rs['all_horses']):
                rc = t.add_row().cells
                rc[0].text = mark
                rc[1].text = str(umaban)
                rc[2].text = name
                rc[3].text = f'{ab:.1f}%'
                f = horse_factors.get(name, {})
                if f:
                    sd = f'{f["sd_runs"]}走/{f["sd_wr"]*100:.0f}%' if f.get('sd_runs') else '-'
                    sd += f'({f["sd_t3"]*100:.0f}%3着)'
                    jk = f'{f["jockey_wr"]*100:.1f}% / {f["trainer_wr"]*100:.1f}%'
                    st = f'{f["rs"]} 近走{f["avg_finish"]:.1f}着 上{f["avg_l3f"]:.1f}s' if f.get('avg_l3f') else f.get('rs', '')
                    al = factor_alert(f, rank + 1)
                    if al:
                        rc[2].text = f'{name} ⚠{al}'
                else:
                    sd, jk, st = '-', '-', '-'
                rc[4].text = sd
                rc[5].text = jk
                rc[6].text = st
        else:
            for i, (ub, nm, ab) in enumerate(rs.get('top3', [])):
                marks = ['◎', '○', '▲']
                doc.add_paragraph(f"{marks[i]} {ub}番 {nm} ({ab:.1f}%)")

        doc.add_paragraph()

    # ── 買い目のご参考（上位レース） ──────────────────────
    if race_summaries:
        doc.add_heading('🎯 買い目のご参考（上位推奨レース）', level=2)
        top_races = race_summaries[:3]
        for rs in top_races:
            doc.add_heading(
                f"{rs['venue']} R{rs['race_num']} — ◎{rs['rec_umaban']}番 {rs['rec_name']}",
                level=4,
            )
            horses_with_marks = rs.get('all_horses', [])
            honmei  = [h for h in horses_with_marks if h[3] == '◎']
            taikou  = [h for h in horses_with_marks if h[3] == '○']
            sandan  = [h for h in horses_with_marks if h[3] == '▲']
            delta   = [h for h in horses_with_marks if h[3] == '△']

            lines = []
            if honmei:
                lines.append(f"単勝: {honmei[0][1]}（イチ押し！）")
            if honmei and taikou:
                lines.append(f"馬連: {honmei[0][0]}番-{taikou[0][0]}番（しっかり押さえたい組み合わせ）")
            if honmei and taikou and sandan:
                delta_ubs = '/'.join(str(d[0]) + '番' for d in delta[:2])
                lines.append(
                    f"3連複: {honmei[0][0]}番-{taikou[0][0]}番-{sandan[0][0]}番 / 相手{delta_ubs}"
                )
            for line in lines:
                doc.add_paragraph(line, style='List Bullet')
            doc.add_paragraph()

    # ── SNS用テキスト ──────────────────────────────────────
    if race_summaries:
        main = race_summaries[0]
        horses_wm = main.get('all_horses', [])
        marks_line = '  '.join(
            f"{h[3]}{h[0]}番{h[1]}" for h in horses_wm[:5] if h[3]
        )
        race_label = main.get('title', f"{main['venue']} R{main['race_num']}")

        # ── X投稿1: 予想 ─────────────────────────────────
        doc.add_heading('📱 X投稿文①：予想（ご参考）', level=2)
        x1_lines = [
            f"🍱 {race_label} の予想です！",
            "",
            marks_line,
            "",
            "今日も一緒に楽しみましょう🎰✨",
            "#競馬予想 #AI予想 #JRA",
        ]
        doc.add_paragraph('\n'.join(x1_lines))
        doc.add_paragraph()

        # ── X投稿2: 本命の根拠 ──────────────────────────
        doc.add_heading('📱 X投稿文②：本命の根拠（ご参考）', level=2)
        honmei_ab = main['rec_ability']
        second_ab = horses_wm[1][2] if len(horses_wm) >= 2 else 0.0
        diff = honmei_ab - second_ab
        x2_lines = [
            f"🐴 本命◎ {main['rec_name']} を推す理由をご紹介します！",
            "",
            f"AIスコアが全頭中トップの {honmei_ab:.1f}% 💪",
            f"2番手との差も {diff:.1f}pt と頭ひとつ抜けています",
            f"展開・コース適性ともにしっかり合っていて",
            f"今回は自信を持っておすすめできる1頭です🔥",
            "",
            "#競馬 #本命 #AI予想",
        ]
        doc.add_paragraph('\n'.join(x2_lines))
        doc.add_paragraph()

        # ── X投稿3: 買い目 ───────────────────────────────
        doc.add_heading('📱 X投稿文③：買い目（ご参考）', level=2)
        circles = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"
        def cn(n):
            try: return circles[int(n)-1]
            except: return str(n)
        ub1 = cn(horses_wm[0][0]) if len(horses_wm) > 0 else ''
        ub2 = cn(horses_wm[1][0]) if len(horses_wm) > 1 else ''
        ub3 = cn(horses_wm[2][0]) if len(horses_wm) > 2 else ''
        ub4 = cn(horses_wm[3][0]) if len(horses_wm) > 3 else ''
        x3_lines = [
            "🎯 買い目のご参考（予算10,000円）",
            "",
            f"単勝 {ub1}　3,000円",
            f"馬連 {ub1}-{ub2}　1,000円",
            f"ワイド {ub1}-{ub2}　1,000円",
            f"ワイド {ub1}-{ub3}　700円",
            f"ワイド {ub2}-{ub3}　700円",
            f"馬連BOX {ub1}{ub2}{ub3}{ub4}　1,600円",
            "",
            "みなさんの昼飯代になりますように🍜🎉",
            "#馬券 #競馬 #JRA",
        ]
        doc.add_paragraph('\n'.join(x3_lines))
        doc.add_paragraph()

        # ── Threads投稿文 ────────────────────────────────
        doc.add_heading('🧵 Threads投稿文（ご参考）', level=2)
        th_lines = [
            f"🍱 {race_label} の予想です！",
            "",
            f"AIモデルで全{len(horses_wm)}頭を分析しました。",
            f"シルシと能力スコアをご覧ください😊",
            "",
        ]
        for h in horses_wm[:10]:
            mark = h[3] if h[3] else '　'
            th_lines.append(f"{mark} {str(h[0]).zfill(2)}番 {h[1]}（{h[2]:.1f}%）")
        if len(horses_wm) > 10:
            th_lines.append("…（以下省略）")
        th_lines += [
            "",
            f"◎本命は {main['rec_name']}（能力スコア {main['rec_ability']:.1f}%・全頭中1位）",
            f"展開・コース適性ともにしっかり合っていておすすめです🔥",
            "",
            "今日も一緒に楽しみましょう🎰✨",
            "#競馬予想 #AI予想 #JRA",
        ]
        doc.add_paragraph('\n'.join(th_lines))
        doc.add_paragraph()

        # ── Note記事全文（コピペ用）─────────────────────
        doc.add_heading('📝 Note記事全文（コピペ用）', level=2)
        doc.add_paragraph('※ 以下をそのままnoteにコピペしてご使用ください。')
        doc.add_paragraph()

        # build_note_article を呼んで全文生成
        import sys as _sys
        _sys.path.insert(0, str(SCRIPT_DIR))
        from post_to_note import build_note_article
        note_article = build_note_article(main, date_str)
        note_body = note_article['body']

        # Wordに貼り付け（セクションごとに段落分け）
        for para in note_body.split('\n'):
            doc.add_paragraph(para)

    # 保存
    doc.save(output_path)
    print(f"\n[Report] Word保存完了: {output_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# メイン予測ルーティン
# ---------------------------------------------------------------------------
def run(args):
    # 日付決定
    if args.tomorrow:
        target_date = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y%m%d')
    elif args.today:
        target_date = datetime.date.today().strftime('%Y%m%d')
    else:
        target_date = args.date

    use_netkeiba = args.tomorrow or args.netkeiba

    print(f"[predict_and_report] 日付: {target_date} / モード: {'前日netkeiba' if use_netkeiba else '当日smartrc'}", file=sys.stderr)

    # ── モデルロード ────────────────────────────────────────
    ability_models, market_models = load_models()

    # ── 統計ロード ─────────────────────────────────────────
    print("Loading stats...", file=sys.stderr)
    if use_netkeiba:
        stats = load_stats_nk()
        bloodline = load_bloodline()
        name_father_map, name_bms_map = load_name_to_id_maps()
        print(f"  Bloodline: {len(bloodline)} horses", file=sys.stderr)
    else:
        stats = load_stats_smartrc()
        bloodline, name_father_map, name_bms_map = {}, {}, {}

    # ── キャッシュロード（netkeiba前日予測用）─────────────
    shutuba_cache, past_cache = {}, {}
    if use_netkeiba:
        shutuba_path = CACHE_DIR / 'shutuba.json'
        past_path    = CACHE_DIR / 'horse_past.json'
        if shutuba_path.exists():
            with open(shutuba_path, encoding='utf-8') as f:
                shutuba_cache = json.load(f)
        if past_path.exists():
            with open(past_path, encoding='utf-8') as f:
                past_cache = json.load(f)

    # ── データ取得 & 変換 ──────────────────────────────────
    all_rows = []
    race_meta = {}   # rcode -> {title, nk_id, month, ...}
    api = SmartRCAPI()

    try:
        if use_netkeiba:
            print("Fetching from netkeiba...", file=sys.stderr)
            nk = NetkeibaScaper()

            races = api.fetch_races(target_date)
            if not races:
                print(f"[ERROR] {target_date} のレースなし", file=sys.stderr)
                return

            if args.venue:
                venue_code = _VENUE_EN.get(args.venue, args.venue)
                races = [r for r in races if r.get('place') == venue_code]

            for r in races:
                rcode  = r['rcode']
                nk_id  = rcode_to_netkeiba_id(rcode)
                month  = rcode_to_month(rcode)
                shutuba = nk.fetch_shutuba(nk_id)
                if not shutuba:
                    print(f"  {r.get('rno','?')}R: データなし", file=sys.stderr)
                    continue

                ri = shutuba['race_info']
                ri['month'] = month
                horses = shutuba['horses']
                print(f"  {r.get('rno','?')}R {ri.get('title','')}: {len(horses)}頭",
                      file=sys.stderr, end='', flush=True)

                for h in horses:
                    hid = h.get('horse_id', '')
                    past = nk.fetch_horse_past(hid, 5) if hid else []
                    row = convert_shutuba_horse(
                        h, ri, past, stats, bloodline,
                        name_father_map=name_father_map,
                        name_bms_map=name_bms_map,
                        nk_scraper=nk,
                    )
                    row['race_id'] = rcode
                    all_rows.append(row)

                print(" OK", file=sys.stderr)
                race_meta[rcode] = {
                    'nk_id': nk_id,
                    'month': month,
                    'title': ri.get('title', ''),
                    'venue_cd': ri.get('venue_cd', 0),
                    'distance': ri.get('distance', 0),
                    'rno': r.get('rno', '?'),
                }

            nk.close()
            # キャッシュを再ロード（fetch後に umaban等が更新されたデータを使う）
            if shutuba_path.exists():
                with open(shutuba_path, encoding='utf-8') as f:
                    shutuba_cache = json.load(f)
            if past_path.exists():
                with open(past_path, encoding='utf-8') as f:
                    past_cache = json.load(f)

        else:
            # smartrc 当日モード
            print("Fetching from smartrc...", file=sys.stderr)
            races = api.fetch_races(target_date)
            if not races:
                print(f"[ERROR] {target_date} のレースなし", file=sys.stderr)
                return

            if args.venue:
                venue_code = _VENUE_EN.get(args.venue, args.venue)
                races = [r for r in races if r.get('place') == venue_code]

            for r in races:
                rows = convert_race(api, r['rcode'], r, stats)
                all_rows.extend(rows)
                print(f"  {r.get('rno','?')}R {r.get('name','')}: {len(rows)}頭", file=sys.stderr)
                race_meta[r['rcode']] = {
                    'title': r.get('name', ''),
                    'venue_cd': r.get('venue_cd', 0),
                    'distance': r.get('distance', 0),
                    'rno': r.get('rno', '?'),
                }

    finally:
        api.close()

    if not all_rows:
        print("[ERROR] データが取得できませんでした", file=sys.stderr)
        return

    print(f"  Total: {len(all_rows)} horses", file=sys.stderr)

    # ── 予測 ───────────────────────────────────────────────
    X_ability = np.array(
        [[to_float(r.get(c)) for c in ABILITY_COLS] for r in all_rows],
        dtype=np.float32,
    )
    pred_ability = np.mean([m.predict(X_ability) for m in ability_models], axis=0)

    if not use_netkeiba:
        X_full = np.array(
            [[to_float(r.get(c)) for c in FEATURE_COLS] for r in all_rows],
            dtype=np.float32,
        )
        pred_market = np.mean([m.predict(X_full) for m in market_models], axis=0)
    else:
        pred_market = np.zeros_like(pred_ability)

    # ── レース別グルーピング ────────────────────────────────
    race_entries = defaultdict(list)
    for j, row in enumerate(all_rows):
        o = to_float(row.get('odds'))
        mip = 1.0 / o if o > 0 else 0
        race_entries[row['race_id']].append({
            'row': row,
            'pred_ability': float(pred_ability[j]),
            'pred_market':  float(pred_market[j]),
            'ev': float(pred_market[j]) * o if not (o != o) and o > 0 else 0,
            'div': float(pred_ability[j]) - mip if not (o != o) and o > 0 else float(pred_ability[j]),
            'odds':    o if not (o != o) else 0,
            'umaban':  str(row.get('umaban', '')).zfill(2),
            'horse_name': row.get('horse_name', ''),
            'ninki':   int(to_float(row.get('ninki', 0))) if not (to_float(row.get('ninki', 0)) != to_float(row.get('ninki', 0))) else 0,
            'barei':   int(to_float(row.get('barei', 0))),
            'distance':    int(to_float(row.get('distance', 0))),
            'syusso_tosu': int(to_float(row.get('syusso_tosu', 0))),
            'venue_cd':    int(to_float(row.get('venue_cd', 0))),
        })

    # ── 推奨レース選定 ──────────────────────────────────────
    recommendations = []
    race_filter = getattr(args, 'race', None)

    if use_netkeiba:
        for rid, entries in race_entries.items():
            if not entries:
                continue
            dist = entries[0]['distance']
            n    = entries[0]['syusso_tosu']
            vc   = entries[0]['venue_cd']
            meta = race_meta.get(rid, {})
            # --race 指定時は距離・会場フィルターをバイパス（特定レース強制指定）
            if race_filter:
                rno   = str(meta.get('rno', ''))
                title = meta.get('title', '')
                if race_filter.isdigit():
                    if rno != race_filter:
                        continue
                else:
                    if race_filter not in title:
                        continue
            elif dist < MIN_DISTANCE or n < MIN_RUNNERS or vc in EXCLUDED_VENUES:
                continue
            sorted_entries = sorted(entries, key=lambda e: e['pred_ability'], reverse=True)
            best = sorted_entries[0]
            meta = race_meta.get(rid, {})
            recommendations.append({
                'race_id':    rid,
                'venue':      VENUE_NAMES.get(best['venue_cd'], '?'),
                'race_num':   meta.get('rno', '?'),
                'distance':   best['distance'],
                'title':      meta.get('title', ''),
                'rec_umaban': best['umaban'],
                'rec_name':   best['horse_name'],
                'rec_ability': best['pred_ability'] * 100,
                'top3':       [(e['umaban'], e['horse_name'], e['pred_ability'] * 100) for e in sorted_entries[:3]],
                'nk_id':      meta.get('nk_id', ''),
                'month':      meta.get('month', 0),
            })
        recommendations.sort(key=lambda r: r['rec_ability'], reverse=True)
    else:
        for rid, entries in race_entries.items():
            if not entries:
                continue
            dist = entries[0]['distance']
            n    = entries[0]['syusso_tosu']
            vc   = entries[0]['venue_cd']
            meta = race_meta.get(rid, {})
            if race_filter:
                rno   = str(meta.get('rno', ''))
                title = meta.get('title', '')
                if race_filter.isdigit():
                    if rno != race_filter:
                        continue
                else:
                    if race_filter not in title:
                        continue
            elif dist < MIN_DISTANCE or n < MIN_RUNNERS or vc in EXCLUDED_VENUES:
                continue
            cands = [
                e for e in entries
                if e['ev'] >= EV_THRESHOLD
                and e['odds'] < MAX_ODDS
                and e['barei'] >= MIN_AGE
                and e['ninki'] >= MIN_NINKI
            ]
            if not cands:
                continue
            best = max(cands, key=lambda e: e['ev'])
            meta = race_meta.get(rid, {})
            sorted_entries = sorted(entries, key=lambda e: e['pred_ability'], reverse=True)
            recommendations.append({
                'race_id':    rid,
                'venue':      VENUE_NAMES.get(best['venue_cd'], '?'),
                'race_num':   meta.get('rno', '?'),
                'distance':   best['distance'],
                'title':      meta.get('title', ''),
                'rec_umaban': best['umaban'],
                'rec_name':   best['horse_name'],
                'rec_ability': best['pred_ability'] * 100,
                'top3':       [(e['umaban'], e['horse_name'], e['pred_ability'] * 100) for e in sorted_entries[:3]],
            })
        recommendations.sort(key=lambda r: r['ev'] if 'ev' in r else 0, reverse=True)

    # ── 全馬スコア計算（推奨レースのみ）───────────────────
    if use_netkeiba:
        for rec in recommendations:
            # キャッシュから全馬スコアを再計算
            nk_id = rec.get('nk_id', '')
            month = rec.get('month', 0)
            all_horses_raw = compute_all_horse_scores(
                nk_id, shutuba_cache, past_cache,
                stats, bloodline, name_father_map, name_bms_map,
                ability_models, month,
            )
            with_marks = assign_marks(all_horses_raw)
            rec['all_horses'] = with_marks
            # 因子データをrace_entriesから引っ張る（horse_name をキーに結合）
            rid = rec['race_id']
            rec['horse_factors'] = {
                e['horse_name']: extract_horse_factors(e.get('row', {}))
                for e in race_entries.get(rid, [])
            }
    else:
        # smartrc: race_entries からそのまま全馬を取得
        for rec in recommendations:
            rid = rec['race_id']
            all_entries = sorted(race_entries[rid], key=lambda e: e['pred_ability'], reverse=True)
            raw = [(e['umaban'], e['horse_name'], e['pred_ability'] * 100) for e in all_entries]
            rec['all_horses'] = assign_marks(raw)
            rec['horse_factors'] = {
                e['horse_name']: extract_horse_factors(e.get('row', {}))
                for e in race_entries.get(rid, [])
            }

    # ── コンソール出力 ─────────────────────────────────────
    mode_label = '前日予測（abilityモデル）— netkeiba出馬表' if use_netkeiba else 'ULTIMATE v2 推奨ベット — smartrc'
    print(f"\n{'='*80}", file=sys.stdout)
    print(f"{mode_label}", file=sys.stdout)
    print(f"{'='*80}\n", file=sys.stdout)

    if not recommendations:
        print("該当レースなし（フィルター通過ゼロ）", file=sys.stdout)
    else:
        print(f"  {'会場':>4} {'R':>3} {'距離':>6} {'推奨':>14}  {'Ab%':>6}  Top3候補")
        print("-" * 80)
        for rec in recommendations:
            name1 = rec['rec_name'][:8]
            top3_str = " > ".join(
                f"{ub}{nm[:5]}({ab:.1f}%)" for ub, nm, ab in rec['top3']
            )
            print(
                f"  {rec['venue']:>4} R{rec['race_num']:>2} {rec['distance']:>5}m "
                f"{rec['rec_umaban']:>2} {name1:>10}  {rec['rec_ability']:>5.1f}%  {top3_str}"
            )

        print(f"\n対象: {len(recommendations)}レース")

        # 全馬シルシ一覧（推奨レース全て）
        print(f"\n{'='*80}")
        print(f"全馬シルシ一覧")
        print(f"{'='*80}")
        for rec in recommendations:
            title_disp = f"  ({rec.get('title', '')})" if rec.get('title') else ''
            print(f"\n【{rec['venue']} R{rec['race_num']} {rec['distance']}m{title_disp}】")
            print(f"  {'印':>2} {'馬番':>4} {'馬名':<14} {'能力%':>6}  主要因子")
            print(f"  {'-'*90}")
            for rank, (ub, nm, ab, mark) in enumerate(rec.get('all_horses', [])):
                ub_str  = str(ub) if ub is not None else "?"
                fdict   = rec.get('horse_factors', {}).get(nm, {})
                fline_s = factor_line(fdict) if fdict else ''
                alert_s = factor_alert(fdict, rank + 1)
                alert_p = f'  ⚠ {alert_s}' if alert_s else ''
                print(f"  {mark:>2} {ub_str:>4}番 {nm:<14} {ab:>5.1f}%  {fline_s}{alert_p}")

    # ── Wordレポート出力 ───────────────────────────────────
    if recommendations:
        if args.output:
            output_path = args.output
            acc_path = None
        else:
            dt = datetime.datetime.strptime(target_date, '%Y%m%d')
            date_str_fmt = dt.strftime('%Y%m%d')
            fname = date_str_fmt + '_競馬予想レポート.docx'
            # 日付サブフォルダに出力（例: Desktop/競馬予想レポート/20260426/）
            report_dir = Path.home() / 'Desktop' / '競馬予想レポート' / date_str_fmt
            report_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(report_dir / fname)
            acc_path = report_dir / (date_str_fmt + '_data.json')

        # 同日複数実行の場合、既存データとマージして1ファイルに統合
        if acc_path and acc_path.exists():
            with open(acc_path, encoding='utf-8') as f:
                existing = json.load(f)
            existing_ids = {r['race_id'] for r in existing}
            merged = existing + [r for r in recommendations if r['race_id'] not in existing_ids]
            # 会場・レース番号順にソート
            def _sort_key(r):
                try:
                    return (r.get('venue', ''), int(r.get('race_num', 0)))
                except (ValueError, TypeError):
                    return (r.get('venue', ''), 0)
            merged.sort(key=_sort_key)
            print(f"[Report] 既存{len(existing)}レース + 新規{len(recommendations)}レース → 合計{len(merged)}レースで統合")
        else:
            merged = list(recommendations)

        if acc_path:
            with open(acc_path, 'w', encoding='utf-8') as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)

        generate_word_report(
            target_date,
            merged,
            output_path,
            use_netkeiba,
        )
        print(f"[完了] Word保存: {output_path}")
        print(f"[完了] 推奨レース: {len(merged)}レース")

        dry_run = getattr(args, 'dry_run', False)

        # ── X（Twitter）投稿 ──────────────────────────────
        if getattr(args, 'post_x', False) or dry_run:
            _post_x(recommendations, dry_run=dry_run)

        # ── Note.com 投稿 ─────────────────────────────────
        if getattr(args, 'post_note', False) or dry_run:
            _post_note(recommendations, target_date, dry_run=dry_run)

        # ── Note見出し画像生成 ────────────────────────────
        if getattr(args, 'with_image', False):
            _generate_note_header_image(recommendations, target_date, output_path)

    else:
        print("[完了] 推奨レースなし。Wordは生成しません。")


def _post_x(recommendations: list[dict], dry_run: bool = False):
    """主要レース（能力1位のレース）をXに3投稿する。"""
    if not recommendations:
        return
    try:
        from post_to_x import build_x_posts, post_all
    except ImportError:
        print("[ERROR] post_to_x.py が見つかりません。", file=sys.stderr)
        return

    main_race = recommendations[0]
    posts = build_x_posts(main_race)
    post_all(posts, dry_run=dry_run)


def _post_note(recommendations: list[dict], date_str: str, dry_run: bool = False):
    """主要レース（能力1位のレース）のNote記事を投稿する。"""
    if not recommendations:
        return
    try:
        from post_to_note import build_note_article, post_to_note
    except ImportError:
        print("[ERROR] post_to_note.py が見つかりません。", file=sys.stderr)
        return

    main_race = recommendations[0]
    article = build_note_article(main_race, date_str)
    post_to_note(article, headless=True, dry_run=dry_run)


def _generate_note_header_image(recommendations: list[dict], date_str: str, word_path: str):
    """
    Note見出し画像をnanobanana-proで自動生成する。
    Word報告書と同じフォルダに YYYYMMDD_note_header.png として保存。
    """
    if not recommendations:
        return

    main_race = recommendations[0]
    title  = main_race.get('title', '')
    venue  = main_race.get('venue', '')
    dist   = main_race.get('distance', '')

    # 出力先: Wordと同じフォルダ
    word_dir = Path(word_path).parent
    dt = datetime.datetime.strptime(date_str, '%Y%m%d')
    img_filename = dt.strftime('%Y%m%d') + '_note_header.png'
    img_path = str(word_dir / img_filename)

    # プロンプト生成（レース名・会場を動的に反映）
    race_label = title if title else f"{venue}{dist}m"
    year = dt.strftime('%Y')

    prompt = (
        f"{race_label} {year} AI競馬予想 note記事ヘッダー画像, "
        f"wide horizontal banner 16:9, beautiful Japanese racehorses galloping, "
        f"cherry blossoms (sakura) petals falling everywhere, spring blue sky, "
        f"green turf track at {venue} racecourse, "
        f"title text '{race_label} {year} AI予想' in large bold golden letters, "
        f"subtitle text 'アスメシ競馬予想' in elegant script, "
        f"sakura pink and white and gold color palette, "
        f"anime illustration style, pop kawaii Japanese art style, "
        f"dynamic action horse racing scene, vibrant spring atmosphere, "
        f"eye-catching SNS header image, professional banner layout"
    )

    nanobanana_dir = SRC_DIR.parent.parent / '.claude' / 'skills' / 'nanobanana-pro'
    run_script = nanobanana_dir / 'scripts' / 'run.py'

    if not run_script.exists():
        print(f"[WARN] nanobanana-pro が見つかりません: {run_script}", file=sys.stderr)
        print("  → --with-image をスキップします", file=sys.stderr)
        return

    import subprocess
    print(f"\n[画像生成] Note見出し画像を生成中...", flush=True)
    print(f"  レース: {race_label}", flush=True)
    print(f"  出力先: {img_path}", flush=True)

    cmd = [
        sys.executable, str(run_script), 'image_generator.py',
        '--prompt', prompt,
        '--output', img_path,
        '--skip-thinking-mode',
    ]
    result = subprocess.run(cmd, cwd=str(nanobanana_dir), capture_output=False)
    if result.returncode == 0:
        print(f"[完了] Note見出し画像: {img_path}", flush=True)
    else:
        print(f"[ERROR] Note見出し画像の生成に失敗しました。", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog='predict_and_report.py',
        description='「予想をしてください」ワンコマンドパッケージ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python predict_and_report.py --tomorrow                                          # 翌日の前日予測
  python predict_and_report.py --today                                              # 当日のsmartrc予測
  python predict_and_report.py --date 20260413                                      # 日付指定
  python predict_and_report.py --tomorrow --venue hanshin                           # 阪神のみ
  python predict_and_report.py --date 20260412 --netkeiba --venue hanshin --race 桜花賞             # 特定レースのみ
  python predict_and_report.py --date 20260412 --netkeiba --venue hanshin --race 桜花賞 --with-image # Word+Note画像を一括生成
  python predict_and_report.py --tomorrow --post-x                                  # 予想→X投稿まで自動
  python predict_and_report.py --tomorrow --post-note                               # 予想→Note投稿まで自動
  python predict_and_report.py --tomorrow --post-all                                # 予想→X + Note 両方投稿
  python predict_and_report.py --tomorrow --dry-run                                 # 投稿内容プレビュー（投稿しない）
        """,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--tomorrow', action='store_true', help='翌日の前日予測（netkeiba）')
    mode.add_argument('--today',    action='store_true', help='当日の予測（smartrcオッズ込み）')
    mode.add_argument('--date',     metavar='YYYYMMDD',  help='日付指定')

    p.add_argument('--netkeiba', action='store_true',
                   help='--date 使用時にnetkeibaモードにする')
    p.add_argument('--venue', metavar='NAME',
                   help='会場フィルター (例: hanshin, nakayama, tokyo)')
    p.add_argument('--race', metavar='NUM_OR_TITLE',
                   help='レース番号またはレース名で絞り込み (例: 11 または 桜花賞)')
    p.add_argument('--output', metavar='PATH',
                   help='Wordファイル出力先（デフォルト: Desktop/YYYYMMDD_競馬予想レポート.docx）')
    p.add_argument('--post-x', dest='post_x', action='store_true',
                   help='予想完了後にXへ3投稿する（.envのAPIキーが必要）')
    p.add_argument('--post-note', dest='post_note', action='store_true',
                   help='予想完了後にNote.comへ記事を投稿する（.envのメール/パスワードが必要）')
    p.add_argument('--post-all', dest='post_all', action='store_true',
                   help='X + Note の両方に投稿する（--post-x --post-note のショートカット）')
    p.add_argument('--with-image', dest='with_image', action='store_true',
                   help='Word生成後にNote見出し画像をnanobanana-proで自動生成する')
    p.add_argument('--dry-run', dest='dry_run', action='store_true',
                   help='X/Note の投稿内容をプレビューするだけで実際には投稿しない')
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --post-all は --post-x + --post-note のショートカット
    if getattr(args, 'post_all', False):
        args.post_x    = True
        args.post_note = True

    # --date の場合、netkeiba or smartrc を選ぶ
    if args.date and not args.netkeiba:
        # 日付が今日より先 → 自動でnetkeibaモードに
        try:
            target = datetime.datetime.strptime(args.date, '%Y%m%d').date()
            if target > datetime.date.today():
                args.netkeiba = True
                print(f"[INFO] {args.date} は未来の日付のため netkeiba モードで実行します", file=sys.stderr)
        except ValueError:
            pass

    run(args)


if __name__ == '__main__':
    main()
