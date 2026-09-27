#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_to_x.py  -- X（Twitter）への予想3投稿パッケージ

投稿構成:
  1. 予想投稿    : 全馬シルシ一覧（メインレース）
  2. 本命の根拠  : ◎本命馬の詳細分析
  3. 買い目      : 馬券戦略・投資額

使い方（単体実行）:
  python post_to_x.py --dry-run   # 投稿内容のみ表示（実際には投稿しない）
  python post_to_x.py             # 実際に投稿する

predict_and_report.py から呼び出し:
  from post_to_x import build_x_posts, post_all
"""
from __future__ import annotations

import sys, os, json, time, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SRC_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# .env ロード（python-dotenv がなくても動く簡易版）
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
# Xクライアント初期化
# ---------------------------------------------------------------------------
def _get_client():
    """Tweepy Client（v2）を返す。認証情報が未設定なら None。"""
    try:
        import tweepy
    except ImportError:
        print("[ERROR] tweepy が見つかりません: pip install tweepy", file=sys.stderr)
        return None

    api_key    = os.environ.get('X_API_KEY', '')
    api_secret = os.environ.get('X_API_SECRET', '')
    acc_token  = os.environ.get('X_ACCESS_TOKEN', '')
    acc_secret = os.environ.get('X_ACCESS_TOKEN_SECRET', '')

    if not all([api_key, api_secret, acc_token, acc_secret]):
        print("[WARN] X API認証情報が未設定です。.envを確認してください。", file=sys.stderr)
        return None

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=acc_token,
        access_token_secret=acc_secret,
        wait_on_rate_limit=True,
    )


# ---------------------------------------------------------------------------
# 投稿テキスト生成
# ---------------------------------------------------------------------------
def build_x_posts(race_summary: dict) -> tuple[str, str, str]:
    """
    race_summary: predict_and_report.py の recommendations[0] 相当の dict

    Returns: (post1_予想, post2_根拠, post3_買い目)
    各テキストは140字以内に収めること。
    """
    venue     = race_summary.get('venue', '')
    race_num  = race_summary.get('race_num', '')
    distance  = race_summary.get('distance', '')
    title     = race_summary.get('title', '')
    rec_name  = race_summary.get('rec_name', '')
    rec_ub    = race_summary.get('rec_umaban', '')
    rec_ab    = race_summary.get('rec_ability', 0.0)

    all_horses = race_summary.get('all_horses', [])
    # シルシ付き馬のみ抽出（◎○▲△△）
    marked = [(ub, nm, ab, mk) for ub, nm, ab, mk in all_horses if mk]
    # ✕は除外（記載不要）
    marked = [(ub, nm, ab, mk) for ub, nm, ab, mk in marked if mk != '✕']

    # レースラベル
    race_label = f"{venue}{race_num}R"
    if title:
        race_label = f"{title}"

    # ── 投稿1: 予想 ────────────────────────────────────────
    lines1 = [f"🍱 {race_label} の予想です！"]
    lines1.append("")
    for ub, nm, ab, mk in marked:
        lines1.append(f"{mk} {_circle_num(int(ub))}{nm}")
    lines1.append("")
    lines1.append("今日も一緒に楽しみましょう🎰✨")
    lines1.append("#競馬予想 #AI予想 #JRA")
    if title:
        race_tag = title.split('(')[0].strip().replace('　', '').replace(' ', '')
        lines1.append(f"#{race_tag}")
    post1 = '\n'.join(lines1)

    # ── 投稿2: 本命の根拠 ──────────────────────────────────
    lines2 = [f"🐴 本命◎ {rec_name} を推す理由をご紹介します！"]
    lines2.append("")
    lines2.append(f"AIスコアが全頭中トップの {rec_ab:.1f}% 💪")
    if len(all_horses) >= 2:
        second_ab = all_horses[1][2]
        diff = rec_ab - second_ab
        lines2.append(f"2番手との差も {diff:.1f}pt と頭ひとつ抜けています")
    lines2.append(f"展開・コース適性ともにしっかり合っていて")
    lines2.append(f"今回は自信を持っておすすめできる1頭です🔥")
    lines2.append("")
    lines2.append("#競馬 #本命 #AI予想")
    post2 = '\n'.join(lines2)

    # ── 投稿3: 買い目 ──────────────────────────────────────
    top4 = [(ub, nm, ab, mk) for ub, nm, ab, mk in all_horses[:4]]
    main_ub = _circle_num(int(rec_ub))
    ub2 = _circle_num(int(top4[1][0])) if len(top4) > 1 else ''
    ub3 = _circle_num(int(top4[2][0])) if len(top4) > 2 else ''
    ub4 = _circle_num(int(top4[3][0])) if len(top4) > 3 else ''

    lines3 = ["🎯 買い目のご参考（予算10,000円）"]
    lines3.append("")
    lines3.append(f"単勝 {main_ub}　3,000円")
    if ub2:
        lines3.append(f"馬連 {main_ub}-{ub2}　1,000円")
        lines3.append(f"ワイド {main_ub}-{ub2}　1,000円")
    if ub3:
        lines3.append(f"ワイド {main_ub}-{ub3}　700円")
    if ub2 and ub3:
        lines3.append(f"ワイド {ub2}-{ub3}　700円")
    if ub2 and ub3 and ub4:
        lines3.append(f"馬連BOX {main_ub}{ub2}{ub3}{ub4}　1,600円")
    lines3.append("")
    lines3.append("みなさんの昼飯代になりますように🍜🎉")
    lines3.append("#馬券 #競馬 #JRA")
    post3 = '\n'.join(lines3)

    return post1, post2, post3


def _circle_num(n: int) -> str:
    """馬番を丸数字に変換: 1→①, 18→⑱"""
    circles = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"
    if 1 <= n <= 18:
        return circles[n - 1]
    return str(n)


# ---------------------------------------------------------------------------
# 投稿実行
# ---------------------------------------------------------------------------
def post_all(posts: tuple[str, str, str], dry_run: bool = False) -> bool:
    """
    3投稿を順番にXへ投稿する。

    Parameters
    ----------
    posts:   (post1, post2, post3)
    dry_run: True の場合は表示のみ（実際には投稿しない）

    Returns: True=成功 / False=失敗
    """
    post1, post2, post3 = posts

    print("\n" + "="*70, flush=True)
    print("X 投稿内容プレビュー", flush=True)
    print("="*70, flush=True)
    print(f"\n【投稿1: 予想】({len(post1)}字)")
    print(post1)
    print(f"\n【投稿2: 本命の根拠】({len(post2)}字)")
    print(post2)
    print(f"\n【投稿3: 買い目】({len(post3)}字)")
    print(post3)
    print("="*70 + "\n", flush=True)

    if dry_run:
        print("[DRY-RUN] 実際の投稿はスキップしました。", flush=True)
        return True

    client = _get_client()
    if client is None:
        print("[ERROR] X APIクライアントの初期化に失敗しました。", file=sys.stderr)
        print("  → src/keiba-predictor/.env にAPIキーを設定してください。", file=sys.stderr)
        print("  → .env.example を参考にしてください。", file=sys.stderr)
        return False

    try:
        print("[X] 投稿1（予想）を送信中...", flush=True)
        r1 = client.create_tweet(text=post1)
        tweet1_id = r1.data['id']
        print(f"  ✓ 投稿完了: https://x.com/i/web/status/{tweet1_id}")
        time.sleep(3)

        print("[X] 投稿2（本命の根拠）を送信中...", flush=True)
        r2 = client.create_tweet(text=post2, in_reply_to_tweet_id=tweet1_id)
        tweet2_id = r2.data['id']
        print(f"  ✓ 投稿完了: https://x.com/i/web/status/{tweet2_id}")
        time.sleep(3)

        print("[X] 投稿3（買い目）を送信中...", flush=True)
        r3 = client.create_tweet(text=post3, in_reply_to_tweet_id=tweet2_id)
        tweet3_id = r3.data['id']
        print(f"  ✓ 投稿完了: https://x.com/i/web/status/{tweet3_id}")

        print(f"\n[完了] 3投稿をスレッド形式でXに投稿しました。")
        print(f"  最初のツイート: https://x.com/Asumeshi_Keba/status/{tweet1_id}")
        return True

    except Exception as e:
        print(f"[ERROR] X投稿に失敗しました: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# テスト用: サンプルデータで投稿テキストを確認
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
        ('01', 'フェスティバルヒル',  16.4, '▲'),
        ('07', 'アランカール',        12.6, '△'),
        ('11', 'ジッピーチューン',    10.5, '△'),
        ('12', 'スウィートハピネス',   9.7, ''),
        ('03', 'ディアダイヤモンド',   9.0, ''),
        ('08', 'ロンギングセリーヌ',   9.0, ''),
        ('10', 'ナムラコスモス',       8.8, ''),
        ('15', 'スターアニス',         8.2, ''),
        ('05', 'ギャラボーグ',         8.2, ''),
        ('17', 'ブラックチャリス',     6.8, ''),
        ('06', 'アイニードユー',       6.8, ''),
        ('04', 'エレガンスアスク',     6.7, ''),
        ('02', 'サンアントワーヌ',     6.2, ''),
        ('09', 'ルールザウェイヴ',     6.2, ''),
        ('16', 'ショウナンカリス',     4.4, ''),
        ('18', 'プレセピオ',           2.0, '✕'),
    ],
}


def main():
    parser = argparse.ArgumentParser(
        prog='post_to_x.py',
        description='X（Twitter）への競馬予想3投稿スクリプト',
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='投稿内容を表示するだけで実際には投稿しない')
    parser.add_argument('--sample', action='store_true',
                        help='サンプルデータでテスト実行')
    parser.add_argument('--json', metavar='FILE',
                        help='predict_and_report.py が出力したJSONから読み込む')
    args = parser.parse_args()

    if args.json:
        with open(args.json, encoding='utf-8') as f:
            race_summary = json.load(f)
    else:
        race_summary = SAMPLE_RACE

    posts = build_x_posts(race_summary)
    post_all(posts, dry_run=args.dry_run or args.sample)


if __name__ == '__main__':
    main()
