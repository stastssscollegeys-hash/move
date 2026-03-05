---
name: ebook-word-ss
description: 電子書籍の原稿（25,000字・5章構成）をテキストのみで執筆し、見出し・改ページ・段落を徹底整形した高品質DOCXを出力。完成原稿を元に表紙も一括生成する量産向け高速スキル。画像生成なし。
---

# eBook Word - 電子書籍テキスト＋Word＋表紙 一括生成スキル

参考資料 → リサーチ → 原稿（25,000字）→ 高品質DOCX → 表紙 を一括生成。
画像生成を省き、テキストとWord整形に特化した量産向けスキル。

## When to Use This Skill

- 「電子書籍をWordで作って」「画像なしで本を作りたい」
- 「eBookを量産したい」「テキストだけの電子書籍」
- 「Kindle本をWord形式で」「原稿とWordと表紙をまとめて」
- 「ebook-word」「イーブックワード」

## 全体フロー（6フェーズ）

```
Phase 1: 参考資料の受け取り
   │  ユーザーから資料を受け取る（ファイル / URL / テキスト）
   ▼
Phase 2: リサーチ
   │  参考資料のテーマについて深掘り調査
   ▼
Phase 3: 構成設計
   │  資料 + リサーチ結果から目次を作成 → ユーザー承認
   ▼
Phase 4: 原稿執筆（テキストのみ）
   │  25,000字を執筆。画像タグなし、テキストに集中
   ▼
Phase 5: DOCX変換（強化版整形）
   │  見出し・改ページ・段落・空行を徹底整形した高品質Word
   ▼
Phase 6: 表紙作成
   │  完成原稿の全文を元に cover-master-ss のロジックで表紙生成
   ▼
完成！
```

## 生成物の仕様

| 項目 | 内容 |
|------|------|
| 総文字数 | 約25,000字 |
| 構成 | はじめに + 5章 + おわりに |
| 1章あたり | 約4,000〜5,000字 |
| 表紙画像 | 1枚（cover-master-ss で生成） |
| 本文中画像 | なし（テキストのみ） |
| 出力形式 | DOCX（Word）+ Markdown + 表紙画像 + Amazon用表紙プロンプト |

## 出力先

```
output/{slug}/
├── manuscript.md             # Markdown版原稿
├── manuscript.docx           # 高品質整形済みWord
├── research.md               # リサーチ結果まとめ
├── images/
│   └── cover.png             # 表紙画像
└── cover_prompt_amazon.md    # Amazon KDP提出用 表紙プロンプト
```

---

## Phase 1: 参考資料の受け取り

### 手順

1. ユーザーにテーマと参考資料を聞く
2. 以下の形式で資料を受け取る
3. 受け取った資料を整理し、Phase 2 に渡す

### 受け取れる資料の形式

| 形式 | 例 | 処理方法 |
|------|------|----------|
| ファイル | PDF、テキスト、Markdown | Read ツールで読み込み |
| URL | ブログ記事、Web ページ | WebFetch で内容取得 |
| テキスト | チャットに直接貼り付け | そのまま使用 |
| 複数資料 | 上記の組み合わせ | すべて読み込んで統合 |

### ユーザーへの質問テンプレート

```
以下を教えてください：

1. テーマ（書籍タイトル案）:
2. 参考資料:
   - ファイルパスがあれば指定してください
   - URL があれば貼ってください
   - テキストがあればそのまま貼ってください
3. 特に強調したいポイント（あれば）:
4. 想定読者（あれば）:
```

資料を受け取ったら内容を要約し、「この内容をもとにリサーチを進めます」と伝えて Phase 2 へ。

---

## Phase 2: 深層リサーチ

### 手順

1. 参考資料からテーマ・キーワードを抽出する
2. 以下の5層リサーチを**すべて**実行する
3. リサーチ結果を `output/{slug}/research.md` に保存する
4. リサーチ結果の要点をユーザーに共有し、Phase 3 へ進む

### 5層リサーチ（すべて実行すること）

#### Layer 1: YouTube 専門家の知見

テーマに関する専門チャンネルの動画を調査し、ノウハウを抽出する。

```
手順:
1. WebSearch で「{テーマ} site:youtube.com」を検索
2. 再生回数が多い動画・専門チャンネルを特定（5〜10本）
3. 各動画について:
   a. WebFetch で動画ページを取得し、タイトル・概要欄・チャンネル情報を確認
   b. 動画の要点・独自のノウハウ・具体的手法を抽出
4. 専門家ごとに主張や手法の違いを整理する
```

検索キーワード例:
- `{テーマ} やり方 解説`
- `{テーマ} 初心者 完全ガイド`
- `{テーマ} プロ 実践`
- `{テーマ} 2025 2026 最新`

#### Layer 2: note 専門家の記事

note.com で専門的に発信している人の記事を深掘りする。

```
手順:
1. WebSearch で「{テーマ} site:note.com」を検索
2. 上位記事を5〜10本特定
3. WebFetch で各記事の内容を取得
4. 以下を抽出:
   - 著者の専門性・実績
   - 独自のフレームワーク・メソッド
   - 具体的な数値・事例
   - 読者からの反応（コメント・スキ数で人気度を判断）
5. 有料記事は概要・目次部分から構成の参考にする
```

#### Layer 3: Instagram / TikTok / ショート動画トレンド

最新トレンドとバズっている切り口を調査する。

```
手順:
1. WebSearch で以下を検索:
   - 「{テーマ} Instagram リール 人気」
   - 「{テーマ} TikTok バズ」
   - 「{テーマ} ショート動画 トレンド」
   - 「{テーマ} SNS 話題」
2. トレンド系まとめサイト・ニュースを WebFetch で取得
3. 以下を抽出:
   - 今バズっているキーワード・ハッシュタグ
   - ショート動画で多い切り口・フォーマット
   - インフルエンサーが推しているポイント
   - Z世代・若年層に響いている表現や訴求
```

#### Layer 4: 市場・競合・書籍分析

既存の書籍・コンテンツとの差別化ポイントを調査する。

```
手順:
1. WebSearch で「{テーマ} 本 おすすめ」「{テーマ} Kindle」を検索
2. Amazon の書籍ページを WebFetch で取得（上位5冊）
3. 以下を抽出:
   - 各書籍の目次構成・切り口
   - 読者レビューで「良かった点」「足りない点」
   - 星1-2のレビューから読者の不満・期待
4. 競合にない切り口、カバーされていない領域を特定
```

#### Layer 5: 読者の悩み・ニーズ

ターゲット読者のリアルな声を収集する。

```
手順:
1. WebSearch で以下を検索:
   - 「{テーマ} 悩み」「{テーマ} わからない」
   - 「{テーマ} site:detail.chiebukuro.yahoo.co.jp」（Yahoo知恵袋）
   - 「{テーマ} site:reddit.com」（海外の議論）
2. WebFetch で上位のQ&Aページを取得
3. 以下を抽出:
   - よくある質問・つまづきポイント
   - 初心者が最初にぶつかる壁
   - 「こういう本があれば」という要望
   - 解決策として支持されている回答
```

### リサーチの品質基準

- **YouTube**: 最低5本の動画からノウハウ抽出
- **note**: 最低5記事から専門知識を収集
- **SNSトレンド**: 最新のバズワード・切り口を3つ以上特定
- **競合書籍**: 最低3冊の構成・レビューを分析
- **読者の声**: 最低10件の悩み・質問を収集

### リサーチ結果の保存形式（research.md）

```markdown
# リサーチ結果: {テーマ}

## 参考資料の要約
{受け取った資料のポイント整理}

---

## Layer 1: YouTube 専門家の知見

### 調査した動画
| # | チャンネル | 動画タイトル | 再生回数 | 要点 |
|---|-----------|-------------|---------|------|
| 1 | {チャンネル名} | {タイトル} | {回数} | {要点} |

### 抽出したノウハウ
- {ノウハウ1: 具体的な手法・フレームワーク}

### 専門家間の共通点・相違点
{整理}

---

## Layer 2: note 専門家の記事

### 調査した記事
| # | 著者 | 記事タイトル | スキ数 | 要点 |
|---|------|-------------|--------|------|
| 1 | {著者} | {タイトル} | {数} | {要点} |

### 抽出したフレームワーク・メソッド
- {メソッド1}

---

## Layer 3: SNS / ショート動画トレンド

### バズキーワード・ハッシュタグ
- #{タグ1}（{なぜ人気か}）

### トレンドの切り口
- {切り口1: なぜ響いているか}

---

## Layer 4: 競合書籍分析

### 調査した書籍
| # | 書名 | 著者 | 評価 | 強み | 弱み |
|---|------|------|------|------|------|
| 1 | {書名} | {著者} | {評価} | {強み} | {弱み} |

### 競合にない切り口（差別化チャンス）
- {差別化ポイント1}

---

## Layer 5: 読者の悩み・ニーズ

### よくある悩み TOP10
1. {悩み1}（出典: {ソース}）

### 初心者がつまづく壁
- {壁1}

---

## 総合分析: 本書の方向性

### 推奨する切り口
{参考資料 + 5層リサーチを統合した本書ならではの方向性}

### 盛り込むべきポイント
1. {ポイント1}

### 避けるべきこと（競合と同じになる罠）
- {避けること1}
```

### リサーチエンジンの使い分け

| スキル/ツール | 使うLayer | 用途 |
|--------------|-----------|------|
| **mega-research** (deep mode) | Layer 1-5 全体 | 6つの検索APIで網羅的に調査。Phase 2 の最初に実行 |
| **gpt-researcher** | Layer 1, 4 | 自律型深層リサーチ。専門知識の深掘り |
| **WebSearch** | Layer 1-5 | 各Layerの個別キーワード検索 |
| **WebFetch** | Layer 1-5 | 個別ページ内容取得 |
| **research-free** | 補足 | APIキー不要の統合リサーチ（フォールバック） |

---

## Phase 3: 構成設計

### 手順

1. 参考資料（Phase 1）とリサーチ結果（Phase 2）を元に目次を生成する
2. AskUserQuestion でユーザーに目次を確認してもらう
3. 承認を得たら Phase 4 へ進む

### 目次生成テンプレート

以下の形式で目次を生成せよ：

```
書籍タイトル: {ユーザー指定のテーマ}
想定読者: {テーマから推定}
読者のゴール: {この本を読んで何ができるようになるか}

---

はじめに（1,200〜1,500字）
  - この本の目的
  - 読者への約束
  - 本書の使い方

第1章: {章タイトル}（4,000〜5,000字）
  キーポイント:
    1. {ポイント1}
    2. {ポイント2}
    3. {ポイント3}

第2章: {章タイトル}（4,000〜5,000字）
  （同上の形式）

第3章: {章タイトル}（4,000〜5,000字）
  （同上の形式）

第4章: {章タイトル}（4,000〜5,000字）
  （同上の形式）

第5章: {章タイトル}（4,000〜5,000字）
  （同上の形式）

おわりに（1,200〜1,500字）
  - まとめ
  - 読者への次のステップ
  - 応援メッセージ
```

### 構成設計のルール

- 章の順序は「基礎 → 応用 → 実践」の流れにする
- 各章は独立して読んでも価値があるようにする
- 章をまたいで内容が行ったり来たりしないようにする
- 読者が「次に何をすればいいか」がわかる構成にする

---

## Phase 4: 原稿執筆（テキストのみ）

### 手順

1. Phase 3 で承認された目次 + 参考資料 + リサーチ結果に基づいて全原稿を執筆する
2. 完成した原稿を `output/{slug}/manuscript.md` に保存する

### 執筆ルール

- **総文字数**: 約25,000字（はじめに + 5章 + おわりに）
- **1章あたり**: 4,000〜5,000字
- **はじめに/おわりに**: 各1,200〜1,500字
- **文字数の厳守**: AIは文字数を過少に生成しがち。各章の執筆後に文字数をカウントし、4,000字に満たない章は加筆すること
- **文体**: **です・ます調で統一**（「〜です」「〜ます」「〜ください」）。親しみやすく丁寧な語り口
  - NG: 「〜だ」「〜である」「〜しよう」
  - OK: 「〜です」「〜になります」「〜してみましょう」「〜してください」
- **段落**: 3〜4文ごとに改行。読みやすさ重視
- **具体例**: 各章に最低2つの具体例・事例を含める
- **画像なし**: 画像タグ（`<!-- [INLINE_IMAGE] -->` 等）は一切使用しない。テキストのみで完結させる
- **表（テーブル）の使用禁止**: Markdownの表記法（`| ... |`形式）は**使用禁止**。Word出力時にレイアウトが崩れやすい。比較・一覧情報は箇条書きで表現する
- **箇条書き**: 通常のMarkdownリスト記法（`-`, `1.`）を使用してOK
- **ASCII図・記号図の禁止**: 罫線文字（`┌─┐│└─┘`等）や記号を組み合わせて図を表現しないこと
- **コードブロック（` ``` `）の禁止**: コマンド等は通常テキストとしてそのまま記述する

### 改ページ・整形ルール（DOCX出力品質に直結）

```
┌─────────────────────────────────────────────────────────────────────┐
│  改ページと空行の挿入が Word の読みやすさを決定する                  │
│  以下のルールを厳守すること                                          │
└─────────────────────────────────────────────────────────────────────┘
```

#### 改ページ（`\newpage`）の挿入位置

1. **各章（`##`）の直前**: `## 第N章` の前に必ず `\newpage`
2. **各節（`###`）の直前**: `### N.M` の前に必ず `\newpage`
3. **はじめに・おわりにの直前**: `## はじめに` `## おわりに` の前にも `\newpage`

#### 空行ルール

1. **見出し（`##` `###`）の前**: 改ページ（`\newpage`）+ 空行1行 + 見出し
2. **見出しの後**: 見出し + 空行1行 + 本文開始
3. **段落間**: 段落と段落の間に空行1行（Markdownの通常ルール）
4. **箇条書きの前後**: 箇条書きブロックの前後に空行1行ずつ

#### 見出しレベルの使い分け

| Markdownレベル | Wordスタイル | 用途 |
|---------------|-------------|------|
| `#` | 見出し1 | 書籍タイトル（冒頭1回のみ） |
| `##` | 見出し2 | 章タイトル（はじめに、第1章〜第5章、おわりに） |
| `###` | 見出し3 | 節タイトル（1.1, 1.2, ...） |
| `####` | 見出し4 | 小見出し（必要に応じて） |

### 原稿のMarkdown構造

```markdown
# {書籍タイトル}

\newpage

## はじめに

{はじめに本文 1,200〜1,500字}

{段落1: 3〜4文}

{段落2: 3〜4文}

{段落3: 3〜4文}

\newpage

## 第1章 {章タイトル}

{章の導入文 2〜3文}

\newpage

### 1.1 {節タイトル}

{本文 800〜1,000字}

{段落1}

{段落2}

- ポイント1
- ポイント2
- ポイント3

{段落3}

\newpage

### 1.2 {節タイトル}

{本文 800〜1,000字}

{段落1}

{段落2}

{段落3}

...（4,000〜5,000字になるまで繰り返し）

\newpage

## 第2章 {章タイトル}

（同様の構造）

...

\newpage

## おわりに

{おわりに本文 1,200〜1,500字}
```

---

## Phase 5: DOCX変換（強化版整形）

### 概要

```
┌─────────────────────────────────────────────────────────────────────┐
│  このフェーズが本スキルの核心。読みやすいWordを出力する              │
│  見出し・改ページ・段落スペースを徹底的に整形する                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 手順

1. `manuscript.md` の整形チェック（下記チェックリスト）
2. 不備があれば自動修正する
3. Pandoc + カスタム reference.docx で高品質Word変換
4. 完成した DOCX をユーザーに通知する

### 変換前チェックリスト（必須）

```
□ 各章（## 第N章）の直前に \newpage がある
□ 各節（### N.M）の直前に \newpage がある
□ はじめに・おわりにの直前に \newpage がある
□ 見出しの前後に空行がある
□ 段落間に空行がある
□ 箇条書きの前後に空行がある
□ テーブル記法（| ... |）が使われていない
□ コードブロック（```）が使われていない
□ ASCII図（罫線文字）が使われていない
□ 画像タグ（<!-- [IMAGE] -->）が混入していない
```

不備があればEditツールで自動修正してから変換する。

### reference.docx の作成（初回のみ）

高品質なWordスタイルを適用するため、カスタム reference.docx を使用する。

```bash
# reference.docx の雛形を生成
cd "/c/Users/baseb/dev/開発1/.claude/skills/ebook-word-ss"
pandoc -o reference.docx --print-default-data-file reference.docx 2>/dev/null || true
```

reference.docx が存在しない場合は Pandoc のデフォルトスタイルで変換する（十分に読みやすい）。

### 実行コマンド

```bash
cd "/c/Users/baseb/dev/開発1/output/{slug}"

# reference.docx がある場合（高品質スタイル適用）
REFERENCE="/c/Users/baseb/dev/開発1/.claude/skills/ebook-word-ss/reference.docx"
if [ -f "$REFERENCE" ]; then
  pandoc manuscript.md \
    -o manuscript.docx \
    --from markdown \
    --to docx \
    --reference-doc="$REFERENCE" \
    --standalone \
    --toc \
    --toc-depth=3
else
  # デフォルトスタイルで変換
  pandoc manuscript.md \
    -o manuscript.docx \
    --from markdown \
    --to docx \
    --standalone \
    --toc \
    --toc-depth=3
fi
```

### Pandocオプションの説明

| オプション | 効果 |
|-----------|------|
| `--toc` | 目次を自動生成（見出しから） |
| `--toc-depth=3` | 見出し3（###）まで目次に含める |
| `--reference-doc` | カスタムWordスタイルを適用 |
| `--standalone` | 完全なドキュメントとして出力 |

### 変換結果の確認

変換後、以下をユーザーに報告する:

```
DOCX変換完了:
- ファイル: output/{slug}/manuscript.docx
- ファイルサイズ: {N} KB
- 目次: 自動生成済み（見出し3まで）
- 改ページ: 章・節ごとに挿入済み
- 見出しスタイル: 見出し1〜3 が自動適用
```

---

## Phase 6: 表紙作成（cover-master-ss ロジック統合）

### 概要

完成した原稿の全文を分析し、最適な表紙を自動生成する。
cover-master-ss のロジックをこのフェーズに統合している。

### 手順

```
Step 1: 原稿分析 → ジャンル・テーマ・キーワード自動抽出
  ▼
Step 2: スタイル自動選択（A〜E） → ユーザー確認
  ▼
Step 3: カラーパレット提案 → ユーザー確認
  ▼
Step 4: YAMLプロンプト生成（Version A + B）
  ▼
Step 5: nanobanana-pro で画像生成 → images/cover.png
  ▼
Step 6: Amazon用プロンプトを cover_prompt_amazon.md に保存
```

### Step 1: 原稿分析

`manuscript.md` を読み込み、以下を自動抽出する:

- **書籍タイトル**: `#` 見出しから
- **ジャンル**: 本文のキーワード・トーンから判定
- **ターゲット読者**: 本文中の語りかけや想定シーンから推定
- **キーポイント**: 各章のメインテーマを3〜5個抽出
- **帯コピー候補**: 本文中のインパクトのあるフレーズを抽出

抽出結果をユーザーに提示し、修正や追加があるか確認する。

### Step 2: スタイル自動選択

ジャンルに基づいて5スタイルから最適なものを自動選択する。

| スタイル | 名称 | 最適ジャンル |
|----------|------|-------------|
| **A** | テキストインパクト型 | ビジネス書、自己啓発、話し方系 |
| **B** | イラスト＋テキスト型 | 実用書、健康、料理、趣味 |
| **C** | マンガ・アニメ型 | マンガ解説、ラノベ、AI/テック系 |
| **D** | ダーク・プレミアム型 | 投資、戦略、経営、金融 |
| **E** | ハイブリッド型 | 副業、ChatGPT系、入門書 |

自動選択ロジック:
```
ビジネス/自己啓発/話し方/時間術 → A
料理/健康/ダイエット/生活改善/趣味 → B
マンガ解説/AI活用/テック入門/ラノベ → C
投資/金融/経営戦略/不動産 → D
副業/ChatGPT×副業/〇〇入門/ハウツー → E
```

AskUserQuestionで確認: 「スタイル[X]が最適と判断しました。よろしいですか？」

### Step 3: カラーパレット提案

| ジャンル | メイン | アクセント | ハイライト |
|---------|--------|----------|-----------|
| ビジネス | #FFFFFF 白 | #1A1A2E 紺 | #E74C3C 赤 |
| 自己啓発 | #FFF3CD 薄黄 | #E74C3C 赤 | #FFD700 金 |
| 投資・マネー | #1B2A4A 紺 | #D4AF37 金 | #FFFFFF 白 |
| 健康・ダイエット | #E8F5E9 薄緑 | #FF6B6B ピンク | #2E7D32 緑 |
| AI・テック | #1A73E8 青 | #FFD700 金 | #FF5252 赤 |
| 副業・稼ぐ系 | #FFF9C4 黄 | #1565C0 紺 | #FF5722 オレンジ |

ユーザーの好みがあればそちらを優先。

### Step 4: YAMLプロンプト生成

cover-master-ss と同一のYAMLテンプレートを使用する。
Version A（文字入り）+ Version B（文字なし素材用）の2種を同時出力。

**Version A テンプレート（文字入り）:**

```yaml
# Kindle表紙 - {title} [文字入り・完全版]
type: professional Kindle e-book cover design with Japanese text
quality: award-winning book cover, print-ready
orientation: portrait 2:3 aspect ratio
importance: MUST be VERTICAL book cover layout, extremely high information density

text_elements:
  top_shout:
    text: "{キャッチフレーズ}"
    position: "top left area, angled 15 degrees"
    style: "{バナースタイル}"
    color: "{テキスト色 on 背景色}"

  main_title:
    text: "{メインタイトル}"
    position: "top 15-30%"
    style: "enormous bold dynamic font, extreme visibility for Kindle thumbnail"
    font_size: "largest text on cover"
    color: "{タイトル色}"

  subtitle:
    text: "{サブタイトル}"
    position: "middle-top, just below title"
    style: "{サブタイトルスタイル}"
    color: "{テキスト色}"

  bullet_points:
    text_list: ["{ポイント1}", "{ポイント2}", "{ポイント3}"]
    position: "{配置}"
    style: "numbered list with glowing checkmarks"
    color: "{テキスト色}"

  obi_section:
    catchcopy: "{帯コピー}"
    position: "bottom 15% of cover"
    style: "vibrant {帯色} horizontal band"
    color: "{テキスト色 on 帯背景色}"

  badge:
    text: "{バッジテキスト}"
    position: "bottom-right corner on the obi"
    style: "circular {バッジ色} sticker badge"
    color: "{テキスト色 on バッジ背景色}"

main_visual:
  concept: "{ビジュアルコンセプト}"

composition:
  layout: "Z-pattern layout. {視線誘導の説明}"
  background:
    base: "{背景色}"
    effects: ["{エフェクト1}", "{エフェクト2}"]

colors:
  primary: "{#HEX 色名}"
  accent: "{#HEX 色名}"
  highlight: "{#HEX 色名}"

constraints:
  - "Text MUST be clearly readable in Japanese"
  - "The obi band at the bottom MUST look like a separate layer/material"
  - "Ensure high contrast for the title to be readable at thumbnail size"
```

**Version B テンプレート（文字なし / 素材用）:**

```yaml
# Kindle表紙 - {title} [文字なし / 素材用]
type: professional Kindle e-book cover design, clean illustration asset without any text
quality: award-winning book cover quality
orientation: portrait 2:3 aspect ratio
importance: MUST be VERTICAL book cover layout

text_zones:
  title_zone:
    area: "top 25% of cover"
    instruction: "clean open space for title overlay"
  obi_zone:
    area: "full width band at bottom 15%"
    instruction: "dimmed horizontal band for obi text overlay"

main_visual:
  concept: "{Version Aと同一の世界観}"

composition:
  layout: "{Version Aと同じレイアウト構成、テキストなし}"
  background:
    base: "{Version Aと同一}"
    effects: ["{Version Aと同一}"]

colors:
  primary: "{#HEX}"
  accent: "{#HEX}"
  highlight: "{#HEX}"

constraints:
  - "DO NOT include any readable text, letters, numbers, or characters anywhere"
  - "Top 25% MUST be clean open space for title overlay"
  - "Bottom 15% should be slightly dimmed for obi overlay"
  - "This is a DESIGN ASSET - all text will be added later in Canva/Figma"
```

### Step 5: 画像生成

nanobanana-proスキルで表紙画像を生成する。

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{Version A の YAMLプロンプト全文}" \
  --output "../../../output/{slug}/images/cover.png" \
  --timeout 360
```

### Step 6: Amazon用プロンプト保存

生成に使用したプロンプト（Version A + B）を `cover_prompt_amazon.md` に保存する。
Amazon KDP で外注する場合や、Canva/Figma で作り直す場合に利用できる。

---

## 関連スキル

| スキル | 用途 | Phase |
|--------|------|-------|
| `mega-research` | 6API統合リサーチ | Phase 2 |
| `gpt-researcher` | 自律型深層リサーチ | Phase 2 |
| `research-free` | APIキー不要のリサーチ（フォールバック） | Phase 2 |
| `nanobanana-pro` | Gemini NanoBanana で表紙画像生成 | Phase 6 |
| `doc-convert-pandoc` | Pandoc セットアップの参考 | Phase 5 |
| `cover-master-ss` | 表紙ロジックの原本（本スキルに統合済み） | - |

## 使用例

```
/ebook-word 副業で月10万円稼ぐためのAI活用術
/ebook-word ChatGPTを使った最強の時短仕事術
/ebook-word 初心者でもわかるプログラミング入門
「画像なしで電子書籍をWordで作って」
「テキストだけのKindle本を量産したい」
```
