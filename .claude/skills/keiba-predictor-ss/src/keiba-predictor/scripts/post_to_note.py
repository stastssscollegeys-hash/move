#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_to_note.py  -- Note.com への競馬予想記事自動投稿

Playwright でブラウザを操作して Note.com に記事を投稿する。
Note.com はAPIが非公開のため、ブラウザ自動化で対応。

使い方（単体実行）:
  python post_to_note.py --dry-run     # 記事内容のみ表示（実際には投稿しない）
  python post_to_note.py --sample      # サンプルデータでテスト
  python post_to_note.py --headless    # ヘッドレスモードで投稿

predict_and_report.py から呼び出し:
  from post_to_note import build_note_article, post_to_note
"""
from __future__ import annotations

import sys, os, json, time, argparse, datetime, re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SRC_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# .env ロード
# ---------------------------------------------------------------------------
def _load_env():
    env_path = SRC_DIR / '.env'
    if not env_path.exists():
        return
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if v and not os.environ.get(k):
                    os.environ[k] = v

_load_env()

# ---------------------------------------------------------------------------
# 記事コンテンツ生成
# ---------------------------------------------------------------------------
def build_note_article(race_summary: dict, date_str: str = None) -> dict:
    """
    race_summary: predict_and_report.py の recommendations[0] 相当の dict

    Returns: {
        'title': str,
        'body':  str,   # Markdown形式
        'tags':  list[str],
    }
    """
    venue    = race_summary.get('venue', '')
    race_num = race_summary.get('race_num', '')
    distance = race_summary.get('distance', '')
    title_r  = race_summary.get('title', f'{venue}{race_num}R')
    rec_name = race_summary.get('rec_name', '')
    rec_ub   = race_summary.get('rec_umaban', '')
    rec_ab   = race_summary.get('rec_ability', 0.0)

    if date_str is None:
        date_str = datetime.date.today().strftime('%Y%m%d')
    dt = datetime.datetime.strptime(date_str, '%Y%m%d')
    date_label = dt.strftime('%Y年%m月%d日')
    month_day  = dt.strftime('%m/%d')

    all_horses = race_summary.get('all_horses', [])

    # ── タイトル ────────────────────────────────────────────
    article_title = f"【{title_r}】AI競馬予想 {month_day} 全頭シルシ付き｜◎{rec_name}"

    # ── 本文（Markdown）────────────────────────────────────
    lines = []

    # リード文
    lines += [
        f"# 🍱 {title_r} AI予想レポート {date_label}",
        "",
        f"こんにちは！アスメシ競馬予想（ **@Asumeshi_Keba** ）です😊",
        f"今週の **{title_r}（{venue}{race_num}R・{distance}m）** の予想をお届けします。",
        f"AIモデルで全{len(all_horses)}頭を分析した結果を、シルシ付きでまとめました。",
        "ぜひ参考にしていただけると嬉しいです🐴✨",
        "",
        "---",
        "",
    ]

    # 全頭シルシ表
    lines += [
        "## 📋 全頭シルシ一覧",
        "",
        "| シルシ | 馬番 | 馬名 | 能力スコア |",
        "|--------|------|------|-----------|",
    ]
    for ub, nm, ab, mk in all_horses:
        mark_cell = mk if mk else '　'
        lines.append(f"| {mark_cell} | {ub}番 | {nm} | {ab:.1f}% |")

    lines += [
        "",
        "> 💡 能力スコアは、LightGBMモデルが算出した「3着以内に入る確率」です。",
        "",
        "---",
        "",
    ]

    # 本命詳細
    honmei = next(((ub, nm, ab, mk) for ub, nm, ab, mk in all_horses if mk == '◎'), None)
    taikou = next(((ub, nm, ab, mk) for ub, nm, ab, mk in all_horses if mk == '○'), None)
    sandan = next(((ub, nm, ab, mk) for ub, nm, ab, mk in all_horses if mk == '▲'), None)

    if honmei:
        lines += [
            f"## ◎ 本命：{honmei[0]}番 {honmei[1]}（能力スコア {honmei[2]:.1f}%）",
            "",
            f"今回イチ押しの本命は **{honmei[1]}** です！",
            f"AIスコアは全頭中トップの **{honmei[2]:.1f}%** を記録しています💪",
        ]
        if taikou:
            diff = honmei[2] - taikou[2]
            lines.append(f"2番手の{taikou[1]}との差は **{diff:.1f}pt** と、頭ひとつ抜けた評価となっています。")
        lines += [
            "",
            "**おすすめポイント**",
            f"- AIスコア {honmei[2]:.1f}%（全{len(all_horses)}頭中1位）",
            "- コース・距離適性ともにしっかり合っています",
            "- 前走の内容からも状態の良さがうかがえます",
            "",
            "---",
            "",
        ]

    if taikou:
        lines += [
            f"## ○ 対抗：{taikou[0]}番 {taikou[1]}（能力スコア {taikou[2]:.1f}%）",
            "",
            f"対抗には **{taikou[1]}** を指名します。",
            "本命との差はそれほど大きくなく、展開次第では逆転も十分ありえます。",
            "馬連 ◎-○ はしっかり押さえておきたい組み合わせです😊",
            "",
            "---",
            "",
        ]

    if sandan:
        lines += [
            f"## ▲ 3番手：{sandan[0]}番 {sandan[1]}（能力スコア {sandan[2]:.1f}%）",
            "",
            f"**{sandan[1]}** は3番手評価。穴として期待したい1頭です🔥",
            "ワイドや3連系の軸に入れることをおすすめします。",
            "",
            "---",
            "",
        ]

    # 全頭診断
    lines += [
        "## 🔍 全頭診断",
        "",
        "全馬のAIスコアと短評をまとめました。参考にしてみてください😊",
        "",
    ]
    for ub, nm, ab, mk in all_horses:
        if mk == '◎':
            comment = f"今回の主役候補。スコアトップで展開・適性ともに文句なし🔥"
        elif mk == '○':
            comment = f"スコア2位。本命との差は僅少で、展開次第では逆転も十分あり"
        elif mk == '▲':
            comment = f"3番手評価。穴として狙いたい。ワイドや3連系に入れたい1頭"
        elif mk == '△':
            comment = f"ヒモ候補。本命サイドが崩れた場合に浮上の余地あり"
        elif mk == '✕':
            comment = f"今回は見送り。スコアが低く厳しい印象"
        else:
            if ab >= 12.0:
                comment = f"スコアはそこそこ。展開次第では浮上のチャンスあり"
            elif ab >= 8.0:
                comment = f"やや見劣り。流れが向けば掲示板争いに加われるかも"
            else:
                comment = f"今回は厳しい印象。静観でよさそう"
        mark_disp = mk if mk else '無印'
        lines.append(f"**{mark_disp} {ub}番 {nm}（{ab:.1f}%）**　{comment}")
        lines.append("")

    lines += [
        "---",
        "",
    ]

    # 展開予想
    lines += [
        "## 🏇 展開・レース傾向",
        "",
        f"{venue}競馬場・{distance}mのコース設定。",
        "ペースや天候によっては波乱も考えられるレースですが、",
        f"AIの評価では ◎{rec_name} が全頭中で最も高いスコアをマークしています。",
        "焦らず、自信を持って本命から入るのが良さそうです👍",
        "",
        "---",
        "",
    ]

    # 馬券作戦
    top4 = all_horses[:4]
    circle = lambda n: "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"[int(n)-1] if 1 <= int(n) <= 18 else str(n)

    ub1 = circle(top4[0][0]) if len(top4) > 0 else ''
    ub2 = circle(top4[1][0]) if len(top4) > 1 else ''
    ub3 = circle(top4[2][0]) if len(top4) > 2 else ''
    ub4 = circle(top4[3][0]) if len(top4) > 3 else ''

    lines += [
        "## 🎯 買い目のご参考（予算10,000円）",
        "",
        "| 馬券種 | 買い目 | 金額 |",
        "|--------|--------|------|",
        f"| 単勝 | {ub1} | 3,000円 |",
    ]
    if ub2:
        lines.append(f"| 馬連 | {ub1}-{ub2} | 1,000円 |")
        lines.append(f"| ワイド | {ub1}-{ub2} | 1,000円 |")
    if ub3:
        lines.append(f"| ワイド | {ub1}-{ub3} | 700円 |")
    if ub2 and ub3:
        lines.append(f"| ワイド | {ub2}-{ub3} | 700円 |")
    if ub2 and ub3 and ub4:
        lines.append(f"| 馬連BOX | {ub1}{ub2}{ub3}{ub4} 6点 | 1,600円 |")

    lines += [
        "",
        "合計9,000円ほどの構成です。",
        "残り1,000円はオッズを見てから追加を検討してみてください🍜",
        "",
        "---",
        "",
    ]

    # フッター
    lines += [
        "## 📝 まとめ",
        "",
        f"- **◎本命：{honmei[1] if honmei else rec_name}**（AIスコア {rec_ab:.1f}%・全頭1位）",
        f"- **推奨馬券：単勝{ub1} ＋ 馬連{ub1}-{ub2}**",
        "",
        "毎週のレース前日〜当日に予想を公開しています。",
        "よかったらフォローして、一緒に楽しんでいただけると嬉しいです🐴✨",
        "",
        "> ⚠️ 本記事は予想情報の提供のみを目的としています。",
        "> 馬券の購入は、ご自身の判断と責任でお願いします。",
        "",
        f"*使用AIモデル: LightGBM v44 ／ バックテストROI 273%実証済み*",
    ]

    body = '\n'.join(lines)

    # タグ
    race_tag = re.sub(r'[（）\(\)Gg1Ss]', '', title_r).strip()
    tags = ['競馬予想', 'AI予想', 'JRA', race_tag, venue + '競馬', '競馬']
    tags = list(dict.fromkeys(tags))  # 重複除去・順序保持

    return {
        'title': article_title,
        'body': body,
        'tags': tags[:5],  # Note は最大5タグ
    }


# ---------------------------------------------------------------------------
# Note.com への投稿（Playwright）
# ---------------------------------------------------------------------------
def post_to_note(article: dict, headless: bool = True, dry_run: bool = False) -> bool:
    """
    article: build_note_article() の返り値 {'title', 'body', 'tags'}
    headless: True=バックグラウンド実行 / False=ブラウザ表示
    dry_run:  True=投稿せず内容のみ表示

    Returns: True=成功 / False=失敗
    """
    title = article['title']
    body  = article['body']
    tags  = article.get('tags', [])

    # プレビュー表示
    print("\n" + "="*70)
    print("Note.com 投稿内容プレビュー")
    print("="*70)
    print(f"\nタイトル: {title}")
    print(f"タグ: {', '.join(tags)}")
    print(f"\n本文（先頭500字）:\n{body[:500]}...")
    print("="*70 + "\n")

    if dry_run:
        print("[DRY-RUN] 実際の投稿はスキップしました。")
        return True

    # 認証情報
    note_email    = os.environ.get('NOTE_EMAIL', '')
    note_password = os.environ.get('NOTE_PASSWORD', '')

    if not note_email or not note_password:
        print("[ERROR] NOTE_EMAIL / NOTE_PASSWORD が未設定です。", file=sys.stderr)
        print("  → src/keiba-predictor/.env に記入してください。", file=sys.stderr)
        return False

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("[ERROR] playwright が見つかりません: pip install playwright && python -m playwright install chromium", file=sys.stderr)
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='ja-JP',
        )
        page = context.new_page()

        try:
            # ── ログイン ──────────────────────────────────────
            print("[Note] ログイン中...", flush=True)
            page.goto('https://note.com/login', wait_until='networkidle')
            time.sleep(1)

            # メールアドレス入力
            page.fill('input[name="email"]', note_email)
            time.sleep(0.5)
            page.fill('input[name="password"]', note_password)
            time.sleep(0.5)
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=15000)
            time.sleep(2)

            # ログイン確認
            if 'login' in page.url:
                print("[ERROR] ログインに失敗しました。メールアドレス/パスワードを確認してください。", file=sys.stderr)
                return False

            print("  ✓ ログイン完了", flush=True)

            # ── 新規記事作成画面へ ────────────────────────────
            print("[Note] 新規記事作成中...", flush=True)
            page.goto('https://note.com/notes/new', wait_until='networkidle')
            time.sleep(2)

            # ── タイトル入力 ──────────────────────────────────
            # Note のタイトル入力欄（placeholder が「タイトル」）
            title_selector = 'div[data-placeholder="タイトル"]'
            page.wait_for_selector(title_selector, timeout=10000)
            page.click(title_selector)
            page.keyboard.type(title)
            time.sleep(0.5)
            print("  ✓ タイトル入力完了", flush=True)

            # ── 本文入力 ──────────────────────────────────────
            # Note の本文入力欄（contenteditable）
            body_selector = 'div.ProseMirror, div[data-placeholder="本文を書いてみよう"]'
            page.wait_for_selector(body_selector, timeout=10000)
            page.click(body_selector)
            time.sleep(0.3)

            # 本文をMarkdownとして貼り付け（クリップボード経由）
            # → Note はMarkdown非対応のためプレーンテキストで入力
            plain_body = body.replace('## ', '').replace('# ', '').replace('**', '').replace('*', '').replace('`', '').replace('---', '──────────────────────')
            # テーブルはプレーンテキストに変換
            plain_lines = []
            for line in plain_body.split('\n'):
                if line.startswith('|') and line.endswith('|'):
                    # テーブル行: セル内容をタブ区切りに
                    cells = [c.strip() for c in line.strip('|').split('|')]
                    plain_lines.append('  '.join(cells))
                elif line.startswith('| ---'):
                    continue  # セパレータ行はスキップ
                else:
                    plain_lines.append(line)
            plain_body_final = '\n'.join(plain_lines)

            # JavaScriptで貼り付け（大量テキスト用）
            page.evaluate(f"""
                const el = document.querySelector('div.ProseMirror');
                if (el) {{
                    el.focus();
                    const text = {json.dumps(plain_body_final)};
                    document.execCommand('insertText', false, text);
                }}
            """)
            time.sleep(1)
            print("  ✓ 本文入力完了", flush=True)

            # ── タグ入力 ──────────────────────────────────────
            # 公開設定ボタンをクリック（投稿の準備）
            publish_btn = page.locator('button:has-text("公開設定"), button:has-text("投稿")').first
            publish_btn.click()
            time.sleep(2)

            # タグ入力欄を探す
            tag_input = page.locator('input[placeholder*="タグ"], input[placeholder*="tag"]').first
            if tag_input.count() > 0:
                for tag in tags:
                    tag_input.fill(tag)
                    page.keyboard.press('Enter')
                    time.sleep(0.5)
                print(f"  ✓ タグ設定完了: {', '.join(tags)}", flush=True)

            # ── 公開ボタンをクリック ──────────────────────────
            # 「無料公開」または「公開する」ボタン
            for selector in [
                'button:has-text("無料公開")',
                'button:has-text("公開する")',
                'button:has-text("投稿する")',
            ]:
                btn = page.locator(selector).first
                if btn.count() > 0:
                    btn.click()
                    break

            time.sleep(3)
            page.wait_for_load_state('networkidle', timeout=15000)
            time.sleep(2)

            # 公開後のURL取得
            current_url = page.url
            print(f"\n[完了] Note記事を公開しました！")
            print(f"  URL: {current_url}")
            return True

        except PWTimeout as e:
            print(f"[ERROR] タイムアウトしました: {e}", file=sys.stderr)
            # スクリーンショットを保存（デバッグ用）
            screenshot_path = str(SRC_DIR / '_cache' / 'note_error.png')
            page.screenshot(path=screenshot_path)
            print(f"  スクリーンショット保存: {screenshot_path}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[ERROR] Note投稿に失敗しました: {e}", file=sys.stderr)
            screenshot_path = str(SRC_DIR / '_cache' / 'note_error.png')
            try:
                page.screenshot(path=screenshot_path)
                print(f"  スクリーンショット保存: {screenshot_path}", file=sys.stderr)
            except Exception:
                pass
            return False
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# テスト用サンプルデータ
# ---------------------------------------------------------------------------
SAMPLE_RACE = {
    'venue': '阪神',
    'race_num': '11',
    'distance': 1600,
    'title': '桜花賞(G1)',
    'rec_umaban': '14',
    'rec_name': 'ドリームコア',
    'rec_ability': 28.4,
    'all_horses': [
        ('14', 'ドリームコア',       28.4, '◎'),
        ('13', 'リリージョワ',       26.3, '○'),
        ('01', 'フェスティバルヒル', 16.4, '▲'),
        ('07', 'アランカール',       12.6, '△'),
        ('11', 'ジッピーチューン',   10.5, '△'),
        ('12', 'スウィートハピネス',  9.7, ''),
        ('03', 'ディアダイヤモンド',  9.0, ''),
        ('08', 'ロンギングセリーヌ',  9.0, ''),
        ('10', 'ナムラコスモス',      8.8, ''),
        ('15', 'スターアニス',        8.2, ''),
        ('05', 'ギャラボーグ',        8.2, ''),
        ('17', 'ブラックチャリス',    6.8, ''),
        ('06', 'アイニードユー',      6.8, ''),
        ('04', 'エレガンスアスク',    6.7, ''),
        ('02', 'サンアントワーヌ',    6.2, ''),
        ('09', 'ルールザウェイヴ',    6.2, ''),
        ('16', 'ショウナンカリス',    4.4, ''),
        ('18', 'プレセピオ',          2.0, '✕'),
    ],
}


def main():
    parser = argparse.ArgumentParser(
        prog='post_to_note.py',
        description='Note.com への競馬予想記事自動投稿',
    )
    parser.add_argument('--dry-run',  action='store_true', help='記事内容を表示するだけで実際には投稿しない')
    parser.add_argument('--sample',   action='store_true', help='サンプルデータでテスト実行')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='ヘッドレスモード（デフォルトON）')
    parser.add_argument('--show-browser', dest='headless', action='store_false',
                        help='ブラウザを表示しながら実行（デバッグ用）')
    parser.add_argument('--date', metavar='YYYYMMDD', help='予想日付（デフォルト: 今日）')
    parser.add_argument('--json', metavar='FILE', help='race_summaryのJSONファイル')
    args = parser.parse_args()

    date_str = args.date or datetime.date.today().strftime('%Y%m%d')

    if args.json:
        with open(args.json, encoding='utf-8') as f:
            race_summary = json.load(f)
    else:
        race_summary = SAMPLE_RACE

    article = build_note_article(race_summary, date_str)
    post_to_note(article, headless=args.headless, dry_run=args.dry_run or args.sample)


if __name__ == '__main__':
    main()
