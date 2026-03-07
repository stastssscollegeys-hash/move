---
name: kindle-theme-research-ss
description: Kindle漫画テーマの空白市場を発掘・評価するリサーチスキル。YouTube需要×Kindle競合×著作権判定を実行し、スコア制で着手推奨テーマをランク付き出力。既存50テーマの統合データベースをベースに増分リサーチ。
argument-hint: "[テーマ or キーワード] [--mode quick|deep|eval|update] [--focus youtube|books|overseas|trend]"
allowed-tools: Agent, WebSearch, WebFetch, Read, Write, Glob, Grep, Bash, AskUserQuestion
model: sonnet
version: "2.0.0"
author: 清水昴
category: research
tags: [kindle, manga, theme-research, market-gap, youtube]
dependencies: []
---

# Kindle漫画テーマリサーチ v2

## 概要

「漫画でわかる○○」系Kindle本の量産テーマを発掘・評価するリサーチスキル。
50テーマの統合データベース（`hokan/kindle-theme-research/`）を基盤とし、新テーマの評価・トレンド更新・競合変化の追跡を行う。

## When to Use

- 「Kindleのテーマを探して」「新しいテーマをリサーチして」
- 「このテーマはKindleで出せる？」「競合チェックして」
- 「テーマランキングを更新して」「トレンドを調べて」
- 「著作権は大丈夫？」「このテーマのリスクは？」

## 使い方

```bash
# 特定テーマを評価
/kindle-theme-research-ss 宇宙エレベーター --mode eval

# トレンドで既存データを更新
/kindle-theme-research-ss --mode update

# 新規ジャンルを全調査（初回 or 追加調査）
/kindle-theme-research-ss 心理学 --mode deep

# quickモード（YouTube + Kindle + 著作権のみ）
/kindle-theme-research-ss --mode quick

# 特定ソースに集中
/kindle-theme-research-ss --focus trend
/kindle-theme-research-ss --focus overseas
```

## モード

| モード | 用途 | 所要時間 |
|--------|------|---------|
| `eval` | 特定テーマ1つを4軸評価（既存ランキングとの比較付き） | 2-3分 |
| `update` | 既存ランキングのトレンド更新（新書大賞、YouTube最新等） | 5-10分 |
| `quick` | 新テーマ発掘（Phase 1-3: YouTube + Kindle + 著作権） | 5分 |
| `deep` | 全ソース完全調査（Phase 1-6: 海外YouTube + 書籍トレンド含む） | 15分 |

## 既存データベース

```
hokan/kindle-theme-research/
├── 00_summary.md              # 統合ランキング（50テーマ、SS/S/A/Bランク）
├── 01_kindle_competition.md   # Kindle競合チェック（35テーマ）
├── 02_youtube_themes.md       # YouTube需要分析（49チャンネル＋需要スコア）
├── 03_copyright_guide.md      # 著作権判定ガイド（50テーマ+KDP規約+チェックリスト）
├── 04_youtube_channels_full.md # 49チャンネル完全リスト
├── 05_overseas_themes.md      # 海外教育YouTube発25テーマ
├── 06_blank_themes_from_books.md # 書籍トレンド発30テーマ
└── 07_trend_themes.md         # 2025-2026トレンドテーマ（新書大賞・SNS話題）
```

**重要**: リサーチ実行前に必ず `00_summary.md` を読んで既存データを把握すること。

## テーマ評価フレームワーク（4軸スコアリング）

### スコア算出

```
総合スコア = 需要(30%) + 空白度(30%) + 著作権安全度(20%) + 漫画化適性(20%)
```

### 需要（30%）

| スコア | 基準 |
|--------|------|
| 95（最高） | 複数の大手YouTubeチャンネルで扱われ＋書籍化済み |
| 85（高） | 1つ以上の大手チャンネルで人気 or ベストセラー入り |
| 65（中） | ニッチだが一定のファン層あり |
| 45（低） | 需要未実証 |

調査方法: YouTube再生数（国内49ch + 海外12ch）、Amazonベストセラー、新書大賞、SNS話題性

### 空白度（30%）

| スコア | 基準 |
|--------|------|
| 100（空白） | Kindleに「漫画でわかる○○」が存在しない |
| 85（高） | 絵本・子ども向けのみ。大人向け教養漫画なし |
| 70（少ない） | 1-2冊あるが古い or 質が低い |
| 50（中） | 数冊あるが差別化可能 |
| 0（激戦） | 「まんがで読破」「講談社学術文庫」等の大手が複数参入 |

調査方法: Amazon Kindle検索（「漫画でわかる」「まんがで読破」「講談社まんが学術文庫」「100分de名著マンガ版」）

### 著作権安全度（20%）

| スコア | 基準 |
|--------|------|
| 100（安全） | 歴史的事実・古代文献PD・学術概念。自由に漫画化OK |
| 50（要注意） | 没後70年未満の著者。思想の解説はOK、著作の表現は不可 |
| 0（危険） | 現代著作物の漫画化。テーマ自体は使えるが原著の構成は不可 |

判定ルール:
- 歴史的事実・学術概念 → 安全（アイデアに著作権なし）
- 著者没後80年以上 → 安全（戦時加算含めても余裕）
- 著者没後70年未満 → 要注意
- 現代書籍がベース → 危険
- イスラム教関連 → KDP規約で要注意（預言者の描写は絶対NG）

### 漫画化適性（20%）

| スコア | 基準 |
|--------|------|
| 100（最高） | キャラクター・エピソードが豊富。1話完結でシリーズ化可能 |
| 75（高） | ドラマチックな展開がある。ビジュアル化しやすい |
| 50（中） | 抽象的だが工夫次第で漫画化可能 |
| 25（低） | 文字情報が主体。漫画化のメリットが薄い |

### ランク分け

| ランク | スコア | 意味 |
|--------|--------|------|
| **SS** | 85以上 + 著作権安全 | 即着手推奨 |
| **S** | 70〜84 | 空白大×需要あり |
| **A** | 55〜69 | 高チャンス |
| **B** | 40〜54 | 差別化次第で参入可能 |

## 実行フロー

### eval モード（特定テーマ評価）

```
1. hokan/kindle-theme-research/00_summary.md を読む
   → 既にランキングに入っているか確認

2. 4軸評価（WebSearch 3件以内/バッチ）
   → 需要: YouTube再生数 + ベストセラー確認
   → 空白度: Kindle「漫画でわかる {テーマ}」検索
   → 著作権: 03_copyright_guide.md の基準で判定
   → 漫画化適性: エピソード量・ビジュアル表現のしやすさ

3. スコア算出 & ランキング内での位置づけを報告
4. ランキングへの追加は清水さんに確認してから
```

### update モード（トレンド更新）

```
1. WebSearch で最新トレンドを調査
   → 新書大賞・本屋大賞の最新受賞作
   → YouTube教養系の最新バズ動画
   → SNSで話題の教養書

2. 既存テーマの競合変化チェック
   → 新しい「まんがでわかる○○」が出ていないか

3. 新テーマ候補を3-5件ピックアップ → eval

4. 変更点を報告。清水さんの承認後にファイル更新
```

### quick/deep モード（新規調査）

```
Phase 1: YouTube需要調査（必須）
  → 国内49チャンネル（04_youtube_channels_full.md参照）
  → テーマごとに需要スコア算出

Phase 2: Kindle競合調査（必須）
  → Amazon Kindle検索
  → 空白/少ない/激戦を判定

Phase 3: 著作権判定（必須）
  → 03_copyright_guide.md の基準で自動判定

Phase 4: 海外テーマ発掘（deepのみ）
  → Kurzgesagt, OverSimplified, TED-Ed等12チャンネル
  → 日本未到達テーマを発見

Phase 5: 書籍トレンド発掘（deepのみ）
  → 新書大賞、本屋大賞、Amazonベストセラー
  → SNS（note、はてブ）の話題書籍

Phase 6: 統合ランキング生成（必須）
  → スコア算出 → SS/S/A/Bランク付け
  → 既存データとマージ
```

## サブエージェント構成

リサーチは3つのサブエージェントに委譲（research-delegation.md準拠）:

```
メインプロセス
├── Agent 1: YouTube需要 + Kindle競合（Phase 1-2）
├── Agent 2: 著作権判定 + 海外テーマ（Phase 3-4）
└── Agent 3: 書籍トレンド + SNSトレンド（Phase 5）
        ↓
メインプロセス: Phase 6 統合ランキング生成
```

各エージェント内のWebSearch/WebFetchは最大3件/バッチ。

## 出力フォーマット

### eval モードの報告

```markdown
## テーマ評価: {テーマ名}

| 項目 | スコア | 根拠 |
|------|--------|------|
| 需要 | {score} | {根拠} |
| 空白度 | {score} | {根拠} |
| 著作権 | {score} | {根拠} |
| 漫画化適性 | {score} | {根拠} |
| **総合** | **{score}** | **{ランク}ランク相当（既存ランキング{N}位付近）** |

### 結論
{推奨/非推奨の理由}
```

### quick/deep モードの出力先

既存ファイルを更新（清水さんの承認後）:
```
hokan/kindle-theme-research/  ← 統合データベース
```

## 注意事項

- YouTube再生数は変動する。定期的に `--mode update` を推奨
- Kindle競合は新刊で変わる。月1回程度の再チェック推奨
- 著作権判定は目安。実際の出版前に法的確認を推奨
- 「安全」でも翻訳書の表現コピーはNG。一次資料から独自に書く
- **既存ファイルの更新は清水さんの承認後**に行う
- 出力先はhokanフォルダ（outputではない）

## 典型的なワークフロー

```
1. /kindle-theme-research-ss --mode eval {テーマ}  ← テーマ評価
2. /kindle-theme-research-ss --mode deep           ← 新規テーマ発掘
3. 00_summary.md を確認してテーマ選定
4. /ebook-creator-ss                               ← 原稿生成
5. /manga-creator-ss                               ← 漫画化
6. /ebook-listings-ss                              ← メタデータ生成
```

## 関連スキル

| スキル | 連携方法 |
|--------|---------|
| `ebook-creator-ss` | テーマ決定後の電子書籍生成 |
| `manga-creator-ss` | 漫画一括生成 |
| `cover-master-ss` | Kindle表紙生成 |
| `ebook-listings-ss` | Kindleメタデータ生成 |
| `note-research` | note.comリサーチ |
