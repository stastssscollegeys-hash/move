---
name: keiba-predictor-ss
description: JRA中央競馬予想ツール - LightGBM v44 + 17因子モデルでワンコマンド全素材生成
type: skill
---

# 競馬予想スキル (keiba-predictor-ss) v3.2

## When to Use

- 「競馬予想して」「レース予想」「馬券教えて」と言われた場合
- 「桜花賞の予想して」「今日の予想して」など具体的なレース・日程の指定
- 「投稿用の素材を作って」「noteに記事書いて」と言われた場合

## 実行手順

**必ずプロジェクトルートを起点にコマンドを実行する。**

```bash
# 翌日の重賞予想
python src/keiba-predictor/scripts/predict_and_report.py --tomorrow

# 当日レース（オッズ込み）
python src/keiba-predictor/scripts/predict_and_report.py --today

# レース名指定（日付・会場・レース名を指定）
python src/keiba-predictor/scripts/predict_and_report.py \
  --date YYYYMMDD --netkeiba --venue VENUE --race レース名

# プレビュー（投稿しない）
python src/keiba-predictor/scripts/predict_and_report.py \
  --date YYYYMMDD --netkeiba --venue VENUE --race レース名 --dry-run

# X・note 自動投稿
python src/keiba-predictor/scripts/predict_and_report.py \
  --date YYYYMMDD --netkeiba --venue VENUE --race レース名 --post-all
```

## コマンドオプション

| オプション | 説明 |
|-----------|------|
| `--tomorrow` | 翌日レース（netkeiba前日予測） |
| `--today` | 当日レース（smartrcオッズ込み） |
| `--date YYYYMMDD` | 日付指定 |
| `--netkeiba` | `--date`使用時に必須 |
| `--venue NAME` | 会場絞り込み（tokyo/hanshin等） |
| `--race 名前` | レース絞り込み |
| `--dry-run` | 投稿内容をプレビューのみ |
| `--post-x` | X（Twitter）に3投稿スレッド |
| `--post-note` | note.comに記事を自動投稿 |
| `--post-all` | X + note 両方投稿 |

## SNS投稿フォーマット

**口調**: 敬語＋親しみやすい温かみ（polite-warm）
**絵文字**: 🍱🐴🎯🔥💪🎰✨🍜🎉 を適度に使用
**X投稿**: 140字以内厳守
**ハッシュタグ**: `#競馬予想 #AI予想 #JRA` + レース名タグ

### X投稿3スレッド構成

```
【投稿1: 予想・全馬シルシ】
🍱 〇〇(G1) の予想です！

◎ ⑭本命馬
○ ⑬対抗馬
▲ ①三番手
△ ⑦連下
今日も一緒に楽しみましょう🎰✨
#競馬予想 #AI予想 #JRA #レース名

【投稿2: 本命の根拠（返信）】
🐴 本命◎ 馬名 を推す理由をご紹介します！
AIスコアが全頭中トップの XX.X% 💪
展開・コース適性ともに合っていて自信を持っておすすめできる1頭です🔥
#競馬 #本命 #AI予想

【投稿3: 買い目（返信）】
🎯 買い目のご参考（予算10,000円）
単勝 ⑭  3,000円
馬連 ⑭-⑬  2,000円
...
みなさんの昼飯代になりますように🍜🎉
#馬券 #競馬 #JRA
```

## 予想印の優先順位

馬券種は以下の順で優先（複勝は妙味薄で最下位）：
単勝 > ワイド > 馬連 > 馬単 > 3連複 > 3連単 > 複勝

## 実績

- 複勝的中率: **69.7%**（894R, PDCA37, 2026/1/4〜4/5）
- 堅いレース(荒れ度0-2): **83.3%**
- 中間(3-5): **72.3%** / 荒れ(6+): **61.7%**
- ROI（バックテスト）: **273.3%**（LightGBM v44）
