---
name: ebook-creator-ss
description: 参考資料とリサーチを元に電子書籍の原稿（25,000字・5章構成）と全イメージ画像を一括生成する複合スキル。research-free + kindle-publishing + nanobanana-prompts + nanobanana-pro を統合。既存原稿の拡充モード対応。
---

# eBook Creator - 電子書籍一発生成スキル

参考資料 → リサーチ → 原稿（25,000字）+ 図解（40〜60枚）+ DOCX を一括生成。
既存原稿がある場合は拡充モードで加筆も可能。

## Important: Gemini思考モード必須

**日本語テキストを含む画像を生成する際は、Geminiの「思考モード」を必ず使用してください。**

「高速モード」では日本語テキストが文字化けする可能性が高いです。nanobanana-proスキルは自動切り替えを試みますが、手動確認を推奨します：
1. Gemini右下のモードトグルを確認
2. 「高速」→「思考」に切り替え

## When to Use This Skill

- 「電子書籍を作って」「eBookを作りたい」
- 「本を書いて画像も作って」
- 「Kindle本を一発で」「原稿と画像をまとめて」
- 「〇〇というテーマで本を作って」
- 「この資料を元に本にして」

## 全体フロー（8フェーズ）

```
Phase 0: モード判定（新規 or 拡充）
   │  既存の manuscript.md を検出 → 拡充モードを提案
   ▼
Phase 1: 参考資料の受け取り
   │  ユーザーから資料を受け取る（ファイル / URL / テキスト）
   ▼
Phase 2: リサーチ
   │  参考資料のテーマについて深掘り調査
   │  ※拡充モードではスキップ可能
   ▼
Phase 3: 構成設計
   │  資料 + リサーチ結果から目次を作成 → ユーザー承認
   │  ※拡充モードでは既存構成に新セクションを追加
   ▼
Phase 4: 原稿執筆
   │  25,000字を執筆 + 画像タグ挿入
   │  ※拡充モードでは既存原稿に加筆
   ▼
Phase 5: 画像一括生成
   │  NanoBanana で40〜60枚の図解を生成（表紙は除く）
   │  ※拡充モードでは新規追加分のみ生成
   ▼
Phase 6: DOCX変換
   │  Pandoc で画像埋め込みWord形式に変換
   │  → manuscript.docx（原稿+図解のWord、表紙なし）
   ▼
Phase 7: 漫画確認 → 漫画統合版リビルド（★必須確認ステップ）
   │  ┌─────────────────────────────────────────────────────┐
   │  │ 表紙作成の前に必ず漫画の要否をユーザーに確認する    │
   │  │ 確認なしに表紙（Phase 8）へ進むことは絶対禁止       │
   │  └─────────────────────────────────────────────────────┘
   │  panels/ が存在する場合 → 漫画統合版リビルド
   │  panels/ が存在しない場合 → ユーザーに漫画制作の要否を確認
   │    ├── 漫画を作る → manga-produce-kobetsu-ss で漫画制作 → リビルド
   │    └── 漫画なしで進む → Phase 8 へ
   ▼
Phase 8: 表紙作成（最終ステップ）
   │  マンガ風帯付き表紙のヒアリング → プロンプト生成 → 画像生成
   │  + Amazon提出用プロンプトを別ファイルとして出力
   │  ※拡充モードではスキップ（既存表紙を維持）
   │  ※漫画が cover.png を生成するため、表紙は必ず漫画の後に作る
   ▼
完成！
```

## 生成物の仕様

| 項目 | 内容 |
|------|------|
| 総文字数 | 約25,000字 |
| 構成 | はじめに + 5章 + おわりに |
| 1章あたり | 約4,000〜5,000字 |
| 表紙画像 | 1枚（マンガ風帯付き表紙） |
| 章ヘッダー図解 | 5枚（章の全体像を示す図解） |
| 本文中図解 | 各小見出し（###）ごとに最低1枚 + 難解箇所は追加 |
| 画像合計 | 約40〜60枚（章構成による） |
| Amazon提出用表紙プロンプト | 1ファイル（cover_prompt_amazon.md） |
| 出力形式 | DOCX（Word） + Markdown + images/ フォルダ + Amazon用プロンプト |

## 出力先

**1冊の書籍タイトルにつき1フォルダ（`output/{slug}/`）に全成果物を統合する。**
電子書籍（本スキル）と漫画化（manga-produce-*-ss）が同じフォルダを共有する。

```
output/{slug}/
│
│  ── Phase 4-6: 本スキル（ebook-creator-ss）が生成するファイル ──
├── manuscript.md             # Markdown版（図解画像リンク付き）★ DOCX変換はこちらを使用
├── manuscript_raw.md         # 中間ファイル（画像タグ付き原稿）※ DOCX変換に使用禁止
├── manuscript.docx           # 原稿+図解のみのWord（Phase 6）
├── research.md               # リサーチ結果まとめ（Phase 2）
├── images/                   # 図解画像（40〜60枚、Phase 5）
│   ├── ch1_header.png        # 第1章ヘッダー
│   ├── ch1_img1.png          # 第1章 図解1
│   └── ...
│
│  ── 漫画化スキル（manga-produce-*-ss）が追加するファイル ──
├── story_structure.md        # 漫画ストーリー構成案
├── character_prompts.md      # キャラクター外見プロンプトDB
├── page_prompts.md           # 漫画ページプロンプト
├── characters/               # キャラクターシート画像
├── panels/                   # 漫画ページ画像（896x1200px）
│
│  ── Phase 7: 漫画統合版リビルド ──
├── manga_compiled.md         # 統合Markdown（原稿+漫画）
├── final_book.docx           # ★ 最終成果物（原稿+図解+漫画の統合Word）
│
│  ── Phase 8: 表紙作成（cover-master-ss、最後に実行） ──
├── images/cover.png          # 表紙画像（本文埋め込み用）
└── cover_prompt_amazon.md    # Amazon KDP提出用 表紙プロンプト
```

**本スキルの最終成果物:**
- 漫画なし: `manuscript.docx`（原稿+図解+表紙のWord）+ `cover_prompt_amazon.md`
- 漫画あり: `final_book.docx`（原稿+図解+漫画+表紙の統合Word）+ `cover_prompt_amazon.md`
- 表紙は常に最後（Phase 8）に cover-master-ss で作成する

---

## Phase 0: モード判定（新規 or 拡充）

### 手順

1. `output/` 配下のフォルダを確認する
2. ユーザーが指定したテーマに対応する既存の `output/{slug}/manuscript.md` が存在するか確認する
3. 存在する場合、AskUserQuestion で「新規作成 / 拡充」を聞く

### 判定ロジック

```
既存の manuscript.md がある？
  ├── YES → 「拡充モード」を提案
  │         ユーザーが承認 → 拡充モードで Phase 1 へ
  │         ユーザーが新規を希望 → 通常モードで Phase 1 へ
  └── NO  → 通常モードで Phase 1 へ
```

### 拡充モードの質問テンプレート

```
既存の原稿が見つかりました:
  ファイル: output/{slug}/manuscript.md
  現在の文字数: 約{N}字
  章構成: {既存の章タイトル一覧}

どうしますか？
1. 拡充する（既存原稿に新しい素材を加えて加筆）
2. 新規作成（ゼロから作り直す）
```

### 拡充モードの動作

拡充モードが選択された場合、以下のフェーズが変化する:

| フェーズ | 通常モード | 拡充モード |
|---------|-----------|-----------|
| Phase 1 | テーマ + 資料を受け取る | **追加素材のみ**受け取る |
| Phase 2 | 5層リサーチを全実行 | **スキップ可能**（ユーザーに確認） |
| Phase 3 | ゼロから目次作成 | 既存構成を読み込み、**追加セクションを提案** |
| Phase 4 | 全文執筆 | **既存原稿を読み込み、加筆のみ**実行 |
| Phase 5 | 全画像生成（表紙除く） | **新規追加分の画像のみ**生成 |
| Phase 6 | DOCX変換 | DOCX再変換 |
| Phase 7 | 漫画統合版リビルド | 漫画統合版リビルド |
| Phase 8 | 表紙作成 | **スキップ**（既存表紙を維持） |

### 拡充モードでの Phase 4 の注意点

- 既存の `manuscript.md`（または `manuscript_raw.md`）を必ず Read で読んでから加筆する
- 既存の文章は**変更しない**（追加・挿入のみ）
- 新しいセクション（`###`）を追加する場合、既存の章構成の中に自然に挿入する
- 追加した部分には新しい画像タグ（`<!-- [INLINE_IMAGE: ...] -->`）を埋め込む
- 加筆後、全体の文字数が25,000字に近づくよう調整する

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
   b. 文字起こしが必要な場合 → video-agent スキルの文字起こし機能を使用
      - yt-dlp で音声ダウンロード → Whisper で文字起こし
   c. 動画の要点・独自のノウハウ・具体的手法を抽出
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
4. apify-research スキルが利用可能な場合はそちらも活用
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
| ... | ... | ... | ... | ... |

### 抽出したノウハウ
- {ノウハウ1: 具体的な手法・フレームワーク}
- {ノウハウ2}
- ...

### 専門家間の共通点・相違点
{整理}

---

## Layer 2: note 専門家の記事

### 調査した記事
| # | 著者 | 記事タイトル | スキ数 | 要点 |
|---|------|-------------|--------|------|
| 1 | {著者} | {タイトル} | {数} | {要点} |
| ... | ... | ... | ... | ... |

### 抽出したフレームワーク・メソッド
- {メソッド1}
- {メソッド2}
- ...

---

## Layer 3: SNS / ショート動画トレンド

### バズキーワード・ハッシュタグ
- #{タグ1}（{なぜ人気か}）
- #{タグ2}
- ...

### トレンドの切り口
- {切り口1: なぜ響いているか}
- {切り口2}
- ...

---

## Layer 4: 競合書籍分析

### 調査した書籍
| # | 書名 | 著者 | 評価 | 強み | 弱み |
|---|------|------|------|------|------|
| 1 | {書名} | {著者} | {★} | {強み} | {弱み} |
| ... | ... | ... | ... | ... | ... |

### 競合にない切り口（差別化チャンス）
- {差別化ポイント1}
- {差別化ポイント2}
- ...

---

## Layer 5: 読者の悩み・ニーズ

### よくある悩み TOP10
1. {悩み1}（出典: {ソース}）
2. {悩み2}
3. ...

### 初心者がつまづく壁
- {壁1}
- {壁2}
- ...

---

## 総合分析: 本書の方向性

### 推奨する切り口
{参考資料 + 5層リサーチを統合した本書ならではの方向性}

### 盛り込むべきポイント
1. {ポイント1}
2. {ポイント2}
3. ...

### 避けるべきこと（競合と同じになる罠）
- {避けること1}
- {避けること2}
```

### リサーチエンジンの使い分け

Phase 2 では以下のリサーチスキル・ツールを**組み合わせて**使用する。

| スキル/ツール | 使うLayer | 用途 |
|--------------|-----------|------|
| **mega-research** (deep mode) | Layer 1-5 全体 | 6つの検索API（Tavily/SerpAPI/Brave/NewsAPI/Reddit/Perplexity）で網羅的に調査。**Phase 2 の最初に実行し、全体像を掴む** |
| **gpt-researcher** | Layer 1, 4 | 自律型深層リサーチ。数百ソースを自動探索し出典付きレポートを生成。**専門知識の深掘りに使う** |
| **WebSearch** | Layer 1-5 | 各Layerの個別キーワード検索（site:youtube.com、site:note.com 等） |
| **WebFetch** | Layer 1-5 | YouTube/note/Amazon等の個別ページ内容取得 |
| **video-agent** | Layer 1 | YouTube動画の文字起こし（yt-dlp + Whisper） |
| **research-free** | 補足 | APIキー不要の統合リサーチ（APIキーが未設定の場合のフォールバック） |
| **apify-research** | Layer 3 | Instagram/SNSデータ取得（利用可能な場合） |

### リサーチ実行順序

```
Step 1: mega-research（deep mode）でテーマ全体を網羅調査
  → 市場・ニュース・コミュニティの声を一括収集
  → 6つのAPIで重複排除・クロス検証済みの信頼性の高い情報を取得

Step 2: gpt-researcher で専門領域を深掘り
  → mega-research で見つかった重要トピックを更に掘り下げ
  → 数百ソースから出典付きの詳細レポートを生成

Step 3: Layer別の個別調査
  → WebSearch + WebFetch で YouTube / note / SNS / Amazon を個別に深掘り
  → video-agent で重要なYouTube動画の文字起こし
  → apify-research でInstagramデータ取得（可能な場合）

Step 4: 統合・整理
  → 全リサーチ結果を research.md に統合
  → 矛盾点の検証、信頼度スコアリング
```

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
  図解候補:
    - [HEADER] {章の内容を象徴するビジュアルの説明}
    - [INLINE] {ポイント1を説明する図解の説明}
    - [INLINE] {ポイント2を説明する図解の説明}
    - [INLINE] {ポイント3を説明する図解の説明}
    - [INLINE] {まとめや比較の図解の説明}

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
- 図解候補は具体的に（「概要図」ではなく「3つのステップを矢印でつないだフロー図」のように）

---

## Phase 4: 原稿執筆

### 手順

1. Phase 3 で承認された目次 + 参考資料（Phase 1）+ リサーチ結果（Phase 2）に基づいて全原稿を執筆する
2. 画像の挿入位置にタグを埋め込む
3. 完成した原稿を `output/{slug}/manuscript_raw.md` に保存する

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
- **図解との連携**: 本文中で「以下の図をご覧ください」「この流れを図で整理すると次のようになります」など、図解への導入文を入れる
- **会話の扱い**: キャラクター間の会話（対話形式）は本文中に自然に組み込んでよい。ただし「【漫画シーン】」のようなト書き・場面指示は入れない。漫画は原稿とは別工程で制作するため、原稿には場面描写・演出指示を含めないこと
  - NG: `### 【漫画シーン】カフェにて` → ト書き風の場面指示
  - OK: 本文の流れの中でキャラクターが会話する形式（説明の導入や要約として自然に挿入）
- **表（テーブル）の使用禁止**: Markdownの表記法（`| ... |`形式）は**使用禁止**
  - Word出力時にレイアウトが崩れやすく、電子書籍の読みやすさを損なう
  - 比較・一覧・対比などの情報は、すべて**図解画像タグ（INLINE_IMAGE）**で表現すること
  - 適切なパターン例：`comparison-table`（項目比較）、`list-horizontal`（横型リスト）、`list-vertical`（縦型リスト）、`before-after`（ビフォーアフター）
  - テーブルで表現しがちな内容は、図解にすることで視覚的にもわかりやすくなる
- **箇条書き**: 通常のMarkdownリスト記法（`-`, `1.`）を使用してOK
  - Pandocが適切にWord形式に変換する
  - 例:
    ```markdown
    - 項目1
    - 項目2

    1. 手順1
    2. 手順2
    ```
- **ASCII図・記号図の禁止**: 罫線文字（`┌─┐│└─┘`等）や記号を組み合わせて図を表現しないこと。電子書籍では確実に崩れる。図は画像として挿入する
- **コードブロック（` ``` `）の禁止**: コマンド等は通常テキストとしてそのまま記述する。コードブロック記法はWord変換で意図しないフォーマットになる場合がある
- **画像の前後に空行**: `![alt](path){ width=100% }` の前後には必ず空行を1行入れる

### 改ページルール（DOCX出力時に反映）

原稿中に `\newpage` を挿入することで、DOCX変換時に改ページが入る。
以下のタイミングで**必ず**改ページを入れること:

1. **各章の前**: `## 第N章` の直前に `\newpage`
2. **章内の各節の前**: `### N.M` 節の直前に `\newpage`
3. **小見出しの単元が終わるタイミング**: 内容のまとまりが変わる箇所

### 図の前後の空行ルール（必須）

画像タグ（`<!-- [HEADER_IMAGE: ...]-->` / `<!-- [INLINE_IMAGE: ...] -->`）の前後には**必ず1行ずつ空行**を入れること。これはDOCX変換後の読みやすさに直結する。

```
良い例:
{本文テキスト}

<!-- [INLINE_IMAGE: pattern=flow-horizontal | title=... | ...] -->

{次の本文テキスト}

悪い例:
{本文テキスト}
<!-- [INLINE_IMAGE: pattern=flow-horizontal | title=... | ...] -->
{次の本文テキスト}
```

### 画像タグの挿入ルール

原稿中に以下のタグを埋め込む。タグは独立した行に記述する。
**全画像は「図解・インフォグラフィック」スタイルで統一する。漫画風イラストは使用しない。**

#### 章ヘッダー図解（各章の冒頭、章タイトルの直後）

章ヘッダーもイラストではなく**章の全体像を示す図解**として生成する。
章内で扱う主要トピックの関係性や流れを1枚の図にまとめるイメージ。

```
<!-- [HEADER_IMAGE: pattern={パターン名} | title={章タイトル} | elements={章内の主要トピック} | description={補足}] -->
```

#### 本文中図解（各小見出し `###` ごとに最低1枚）

**挿入基準:**
- **各小見出し（`###`）のセクションに最低1枚**は図解を入れる
- 難しい概念や複雑な比較がある箇所には**追加の図解**を入れる
- 連続する文章が400字以上続く場合は図解の追加を検討する

直前の内容に最適な**図解パターン**を選定し、タグに含める。

```
<!-- [INLINE_IMAGE: pattern={パターン名} | title={図解タイトル} | elements={要素1,要素2,要素3,...} | description={補足説明}] -->
```

### 図解パターン選定ルール（23種類）

直前の内容を分析し、以下から最適なパターンを選ぶ。

#### カテゴリ1: 構造・分類（情報を整理する場面）
| パターン | 使う場面 | pattern値 |
|---------|---------|-----------|
| ツリー図 | 階層構造・グループ分け | `tree` |
| ピラミッド図 | 土台→上位への積み上げ | `pyramid` |
| 階層レイヤー | 立体的な基盤構造 | `layers` |
| ハニカム構造 | 同列要素の拡張性 | `honeycomb` |
| グループ図 | 要素の分類・クラスタ | `group` |

#### カテゴリ2: 流れ・変化（プロセスを説明する場面）
| パターン | 使う場面 | pattern値 |
|---------|---------|-----------|
| フロー図（横型） | 左→右の手順・流れ | `flow-horizontal` |
| フロー図（縦型） | 上→下の詳細ステップ | `flow-vertical` |
| サイクル図 | PDCA・継続的な運用 | `cycle` |
| 階段ステップ図 | 成長・段階 | `stairs` |
| ガントチャート | スケジュール・工程 | `gantt` |

#### カテゴリ3: 比較・分析（違いを見せる場面）
| パターン | 使う場面 | pattern値 |
|---------|---------|-----------|
| ビフォーアフター | 導入前後の変化 | `before-after` |
| マトリクス | 2軸のポジショニング | `matrix` |
| 項目比較図 | 複数項目の対比 | `comparison-table` |
| 規模比較図 | 数値の大小を円で表現 | `scale-circles` |
| 規模分析図 | TAM-SAM-SOM型 | `concentric` |
| ベン図 | 重なり・共通点 | `venn` |

#### カテゴリ4: 関係・論理（つながりを示す場面）
| パターン | 使う場面 | pattern値 |
|---------|---------|-----------|
| 相関図 | 要素同士の複雑な関係 | `network` |
| 放射図 | 中心からの広がり | `radial` |
| トライアングル | 3要素の相互作用 | `triangle` |
| 数式図 | A + B = C の論理 | `formula` |
| 地図・マップ | エリア分布 | `map` |

#### カテゴリ5: 簡易・リスト（一覧する場面）
| パターン | 使う場面 | pattern値 |
|---------|---------|-----------|
| 箇条書き | 情報の整然とした一覧 | `list` |

#### 特別: イメージ図（図解が不向きな場面）
| パターン | 使う場面 | pattern値 |
|---------|---------|-----------|
| イメージイラスト | 概念・雰囲気・感情の表現 | `illustration` |

### パターン選定の判断基準

```
内容が「手順・流れ」 → flow-horizontal / flow-vertical / stairs
内容が「構造・分類」 → tree / pyramid / layers / group
内容が「比較・対比」 → before-after / comparison-table / matrix
内容が「循環・繰り返し」 → cycle
内容が「関係性」 → network / radial / triangle
内容が「数値の大小」 → scale-circles / concentric
内容が「重複・共通」 → venn
内容が「一覧・列挙」 → list / honeycomb
内容が「時系列」 → gantt
内容が「論理式」 → formula
内容が「雰囲気・概念」 → illustration
```

### タグ記述の例

```
良い例:
<!-- [HEADER_IMAGE: 明るいオフィスでノートPCに向かう若いビジネスパーソン。画面にはグラフとデータが表示されている。やる気に満ちた表情] -->

<!-- [INLINE_IMAGE: pattern=flow-horizontal | title=AI活用の3ステップ | elements=情報収集,分析・選定,実践・改善 | description=各ステップにシンプルなアイコン付き、左から右への自然な流れ] -->

<!-- [INLINE_IMAGE: pattern=before-after | title=AI導入の効果 | elements=導入前:手作業で3時間,導入後:AIで15分 | description=左側はモノクロで疲れた表情、右側はカラフルで笑顔] -->

<!-- [INLINE_IMAGE: pattern=pyramid | title=スキル習得の4段階 | elements=基礎知識,ツール操作,応用実践,収益化 | description=土台の基礎知識から頂点の収益化へ積み上げ] -->

<!-- [INLINE_IMAGE: pattern=comparison-table | title=主要AIツール比較 | elements=ChatGPT:文章生成◎・画像×,Claude:分析◎・文章◎,Gemini:画像◎・検索◎ | description=おすすめツールをアクセントカラーでハイライト] -->

<!-- [INLINE_IMAGE: pattern=illustration | title=副業成功のイメージ | elements= | description=カフェでノートPCを開き、穏やかな笑顔で作業するフリーランサー。画面にはグラフが上昇している] -->

悪い例:
<!-- [HEADER_IMAGE: 第1章のイメージ] -->
<!-- [INLINE_IMAGE: pattern=flow-horizontal | title=流れ | elements=A,B,C | description=] -->
```

### 原稿のMarkdown構造

```markdown
# {書籍タイトル}

<!-- [COVER_IMAGE] -->

## はじめに

{はじめに本文 1,200〜1,500字}

\newpage

## 第1章 {章タイトル}

<!-- [HEADER_IMAGE: {説明}] -->

{本文 約600字}

<!-- [INLINE_IMAGE: {説明}] -->

{本文 約600字}

\newpage

### 1.1 {節タイトル}

{本文 約800字}

<!-- [INLINE_IMAGE: {説明}] -->

{本文 約800字}

\newpage

### 1.2 {節タイトル}

{本文 約800字}

<!-- [INLINE_IMAGE: {説明}] -->

{本文 約800字}

...（4,000〜5,000字になるまで繰り返し）

\newpage

## 第2章 {章タイトル}

（同様の構造。章・節の前に \newpage、図の前後に空行）

...

\newpage

## おわりに

{おわりに本文 1,200〜1,500字}
```

**ポイント:**
- `\newpage` は各章（`##`）の前、各節（`###`）の前に必ず入れる
- 画像タグの前後には必ず空行1行ずつ
- `<!-- [COVER_IMAGE] -->` はPhase 8で表紙画像に置換される

---

## Phase 5: 画像一括生成

### 手順

1. `manuscript_raw.md` から全画像タグを抽出する
2. 各タグを NanoBanana 用プロンプトに変換する
3. nanobanana-pro スキルで画像を1枚ずつ生成する
4. 生成した画像パスでタグを置換し、`manuscript.md` を作成する

### 画像タグ → NanobananaPro プロンプト変換ルール

**プロンプト形式: Nano Banana / Imagen 3 最適化形式**

```
┌─────────────────────────────────────────────────────────────────────┐
│  日本語テキストの指定方法（最重要）                                 │
│  → text reads "日本語" の形式で指定する                            │
│  → 絶対に翻訳せず、そのまま一言一句正確に使用                      │
└─────────────────────────────────────────────────────────────────────┘
```

**必須スタイルキーワード（すべてのプロンプトに含める）:**
```
Flat vector design, modern business presentation style, clean Japanese typography, bold sans-serif fonts, corporate color palette, white background, high resolution 4k.
```

**鉄則:**
1. **日本語テキスト固定:** `text reads "日本語"` 内のテキストは**絶対に翻訳せず、そのまま使用**
2. **スタイル統一:** 上記の必須スタイルキーワードを常に含める
3. **視覚的優先度:** 最も重要な要素には `vivid highlight color` を指定し、他は `soft gray` / `neutral colors`
4. **レイアウト詳細:** 図解パターンごとの `Prompt Logic` を使用して空間配置を指定

---

#### 表紙画像（本文埋め込み用）

Phase 8 で生成した表紙画像（`cover.png`）をそのまま使用する。
Phase 5 の時点では表紙タグ `<!-- [COVER_IMAGE] -->` を原稿冒頭に配置するだけでよい。
実際の画像生成は Phase 8（漫画化の後）で行う。

#### 章ヘッダー図解

```
* Subject: (Professional infographic overview for e-book chapter. Topic: {HEADER_IMAGEタグの説明を英訳}.)
* Layout: (Wide landscape 16:9. Central title area with surrounding topic icons/elements arranged in a structured layout.)
* Visuals: (Flat vector design, modern business presentation style, clean Japanese typography, bold sans-serif fonts, corporate color palette using {メインカラー} tones, white background.)
* Style: (Clean infographic, consistent diagram style across all chapters, professional e-book quality, high resolution 4k. NO illustration, NO character art.)
```

#### 本文中図解（INLINE_IMAGE） - NanobananaPro 24パターン

タグの `pattern` 値に応じて、以下の NanobananaPro テンプレートを使い分ける。

**No.1 ツリー図 (`tree`)**
```
* Subject: (Professional infographic of a Tree Diagram with Japanese text.)
* Layout: (Hierarchical tree structure. Top node is "{title}". Branches lead down to sub-nodes: {elementsを個別にクォート}.)
* Visuals: (Minimalist flat design. Rectangular boxes with soft rounded corners. Connection lines clean and thin. Color palette: {メインカラー} and gray.)
* Style: (Modern UI, white background, high-quality Japanese typography, 4k.)
```

**No.2 ピラミッド図 (`pyramid`)**
```
* Subject: (Infographic of a Pyramid Diagram with Japanese text.)
* Layout: (A large triangle divided into {N} horizontal layers. Top layer: "{elements[-1]}", Bottom layer: "{elements[0]}". Title: "{title}".)
* Visuals: (Gradient colors from bottom to top. Dark {メインカラー} base to light top. Bold Japanese fonts centered in each layer.)
* Style: (Clean, flat vector, professional presentation style, white background, 4k.)
```

**No.3 マトリクス (`matrix`)**
```
* Subject: (Professional 2x2 Matrix chart with Japanese text.)
* Layout: (A large square divided into four quadrants by two perpendicular axes. Vertical axis: "{縦軸}", Horizontal axis: "{横軸}". Quadrants: {elements}.)
* Visuals: (Each quadrant has a distinct light pastel background. High contrast for the target quadrant in {アクセントカラー}.)
* Style: (Business style, minimalist, high resolution, vector illustration, 4k.)
```

**No.4 ベン図 (`venn`)**
```
* Subject: (Venn Diagram with overlapping circles and Japanese text.)
* Layout: (Circles labeled: {elements}. Center overlap highlighted. Title: "{title}".)
* Visuals: (Translucent colors. Overlapping areas create subtle new color tones. Soft drop shadows.)
* Style: (Elegant, clean design, professional Japanese sans-serif font, white background, 4k.)
```

**No.5 放射図 (`radial`)**
```
* Subject: (Radial/Mind-map style infographic with Japanese text.)
* Layout: (Central circle containing "{title}". Lines radiating outward to circles: {elements}.)
* Visuals: (Vibrant colors for each branch. Thin, curved connecting lines. Professional icons next to each element.)
* Style: (Modern tech style, clean layout, high definition, Japanese typography, 4k.)
```

**No.6 フロー図：横型 (`flow-horizontal`)**
```
* Subject: (Horizontal Flow Chart showing a process with Japanese text.)
* Layout: (Linear progression left to right. Steps connected by bold arrows: {elements}. Title: "{title}".)
* Visuals: (Chevron-shaped boxes for each step. Cohesive color palette {メインカラー}. High-quality icons above each step.)
* Style: (Professional, sleek, flat design, white background, Japanese font, 4k.)
```

**No.7 フロー図：縦型 (`flow-vertical`)**
```
* Subject: (Vertical Flow Chart process with Japanese text.)
* Layout: (Top-to-bottom progression. Boxes connected by downward arrows: {elements}. Title: "{title}".)
* Visuals: (Numbered bullets next to each box. Detailed sub-text in smaller Japanese font inside boxes.)
* Style: (Clean UI design, professional, white background, high resolution, 4k.)
```

**No.8 サイクル図 (`cycle`)**
```
* Subject: (Circular Cycle Diagram with Japanese text.)
* Layout: (Continuous circular arrow loop. Segments: {elements}. Center contains "{title}".)
* Visuals: (Gradient colors along the circle. Smooth arrows showing clockwise movement. Bold Japanese text in segments.)
* Style: (Modern vector, professional look, high resolution, white background, 4k.)
```

**No.9 ビフォーアフター (`before-after`)**
```
* Subject: (Before and After comparison infographic with Japanese text.)
* Layout: (Split-screen. Left "Before": "{before要素}", Right "After": "{after要素}". Large arrow pointing right. Title: "{title}".)
* Visuals: (Left: Dull gray tones with negative icon. Right: Bright vivid tones with success icon. High contrast.)
* Style: (Bold typography, high-impact visuals, flat design, professional Japanese font, 4k.)
```

**No.10 項目比較図 (`comparison-table`)**
```
* Subject: (Comparison chart with Japanese text.)
* Layout: (Grid comparing items across features: {elements}. Recommended column highlighted.)
* Visuals: (Bright checkmarks for recommended, gray X marks for others. Highlighted column with bold border in {アクセントカラー}.)
* Style: (Corporate style, clean lines, easy-to-read Japanese, professional, 4k.)
```

**No.11 階段ステップ図 (`stairs`)**
```
* Subject: (Staircase Step Diagram with Japanese text.)
* Layout: (Rising steps labeled: {elements}. Character icon at top. Title: "{title}".)
* Visuals: (Isometric 3D perspective steps. Color intensity increases with height. Clear bold Japanese labels.)
* Style: (Achievement-oriented, motivational style, high-quality vector, 4k.)
```

**No.12 地図・マップ (`map`)**
```
* Subject: (Map-based infographic showing locations with Japanese text.)
* Layout: (Simplified map. Pin icons at: {elements}. Each pin has a callout box. Title: "{title}".)
* Visuals: (Minimalist map in light gray. Pin icons vibrant {アクセントカラー}. Callout boxes with clear Japanese text.)
* Style: (Modern flat design, professional, clean layout, high resolution, 4k.)
```

**No.13 ハニカム構造 (`honeycomb`)**
```
* Subject: (Honeycomb/Hexagon grid infographic with Japanese text.)
* Layout: (Cluster of interlocking hexagons. Center: "{title}", surrounding: {elements}.)
* Visuals: (Modern icons inside each hexagon. Subtle gradient colors. Clean connecting points.)
* Style: (Tech-oriented, geometric, minimalist, high-quality Japanese typography, 4k.)
```

**No.14 相関図 (`network`)**
```
* Subject: (Complex Correlation Map with Japanese text.)
* Layout: (Nodes connected by directional arrows. Relationships labeled. Players: {elements}. Title: "{title}".)
* Visuals: (Different line thicknesses for strength. Color-coded zones to group related players.)
* Style: (Clear logical flow, professional business diagram, white background, 4k.)
```

**No.15 数式図 (`formula`)**
```
* Subject: (Math equation style infographic with Japanese text.)
* Layout: (Horizontal equation: {elements} with bold "+" and "=" symbols. Title: "{title}".)
* Visuals: (Each element in a stylized box/circle with icon. High contrast for final result in {アクセントカラー}.)
* Style: (Iconic, minimalist, bold fonts, clear Japanese typography, 4k.)
```

**No.16 グループ図：少 (`group-small`)**
```
* Subject: (Grouped icons diagram for small count with Japanese text.)
* Layout: (Circular arrangement of circles around central space: {elements}. Title: "{title}".)
* Visuals: (Soft pastel colors. High-quality icon in each circle related to the topic.)
* Style: (Clean UI design, modern vector, professional presentation style, 4k.)
```

**No.17 グループ図：多 (`group-large`)**
```
* Subject: (Multi-element grid infographic with Japanese text.)
* Layout: (Structured grid layout for items: {elements}. Each item is a small card with label. Title: "{title}".)
* Visuals: (Uniform card design. Consistent icon style. Background zoning for sub-categories.)
* Style: (Clean, organized, high-density information design, white background, 4k.)
```

**No.18 規模比較図 (`scale-circles`)**
```
* Subject: (Comparison of scale using circles with Japanese text.)
* Layout: (Circles of different sizes side-by-side: {elements}. Title: "{title}".)
* Visuals: (Vibrant colors. Numerical values or labels inside/next to each circle in Japanese.)
* Style: (Impactful, bold, high-resolution vector, clear contrast, 4k.)
```

**No.19 規模分析図 TAM-SAM-SOM (`concentric`)**
```
* Subject: (TAM-SAM-SOM Market Analysis infographic with Japanese text.)
* Layout: (Three concentric circles. Outer: "{elements[0]}", Middle: "{elements[1]}", Inner: "{elements[2]}". Title: "{title}".)
* Visuals: (Gradient overlays. Innermost circle highlighted with glow in {アクセントカラー}. Percentage text.)
* Style: (Clean, professional, high-end corporate style, 4k.)
```

**No.20 階層レイヤー (`layers`)**
```
* Subject: (3D Layered stack infographic with Japanese text.)
* Layout: (Vertical stack of isometric planes: {elements}. Title: "{title}".)
* Visuals: (Soft shadows between planes. Semi-transparent colors. Bold Japanese text on side of each layer.)
* Style: (Sleek, futuristic, high-end design, high resolution, 4k.)
```

**No.21 トライアングル (`triangle`)**
```
* Subject: (Triangle/Trinity diagram with Japanese text.)
* Layout: (Equilateral triangle with element at each vertex: {elements}. Center label: "{title}".)
* Visuals: (Arrows connecting vertices showing mutual influence. Each corner has distinct theme color.)
* Style: (Bold, iconic, professional Japanese typography, 4k.)
```

**No.22 箇条書き：縦型 (`list-vertical`)**
```
* Subject: (Stylized vertical list design with Japanese text.)
* Layout: (Vertical list with items: {elements}. Title: "{title}".)
* Visuals: (Modern checkmark icons. Alternating light/dark backgrounds for rows. High-contrast labels.)
* Style: (Clean UI design, professional sans-serif, easy-to-read layout, 4k.)
```

**No.23 箇条書き：横型 (`list-horizontal`)**
```
* Subject: (Stylized horizontal grid list with Japanese text.)
* Layout: (Horizontal card grid with items: {elements}. Title: "{title}".)
* Visuals: (Uniform card design with icons. Spaced layout for clarity. Accent color for key items.)
* Style: (Clean UI design, professional sans-serif, easy-to-read layout, 4k.)
```

**No.24 箇条書き：羅列 (`list-dense`)**
```
* Subject: (Dense array list infographic with Japanese text.)
* Layout: (Compact grid with many items: {elements}. Title: "{title}".)
* Visuals: (Small uniform cards. Consistent icon style. Background zoning for categories.)
* Style: (High-density information design, clean, organized, white background, 4k.)
```

**No.25 イメージイラスト (`illustration`) ※図解が不向きな場面**
```
* Subject: (Professional digital illustration for e-book. {description を英訳})
* Layout: ({description の構図を英語で指示})
* Visuals: (Warm, inviting atmosphere. Color palette: {メインカラー} tones. Professional quality.)
* Style: (Clean, modern illustration, NO text in image, high resolution 4k.)
```

**No.26 ガントチャート (`gantt`)**
```
* Subject: (Timeline/Gantt chart infographic with Japanese text.)
* Layout: (Horizontal progress bars along calendar axis. Tasks: {elements}. Title: "{title}".)
* Visuals: (Color-coded bars by category. Milestone markers. Clear date labels in Japanese.)
* Style: (Modern business project visual, professional, clean layout, 4k.)
```

---

### プロンプト組み立て手順

```
1. タグから pattern, title, elements, description を抽出
2. pattern に対応する NanobananaPro テンプレートを取得
3. テンプレートの {title}, {elements} に日本語テキストをそのまま埋め込む
   - 図中テキストは翻訳せず日本語のまま使用
   - Layout と Visuals の構造指示は英語のまま維持
4. {メインカラー}, {サブカラー}, {アクセントカラー} をビジュアルトーン設定から埋め込む
5. description の補足があれば Visuals に追記
```

### プロンプト組み立ての例

タグ:
```
<!-- [INLINE_IMAGE: pattern=flow-horizontal | title=AI活用の3ステップ | elements=情報収集,分析・選定,実践・改善 | description=各ステップにシンプルなアイコン付き] -->
```

生成されるプロンプト:
```
* Subject: (Horizontal Flow Chart showing a process with Japanese text.)
* Layout: (Linear progression left to right. Steps connected by bold arrows: "情報収集", "分析・選定", "実践・改善". Title: "AI活用の3ステップ".)
* Visuals: (Chevron-shaped boxes for each step. Cohesive color palette #2563EB. High-quality icons above each step.)
* Style: (Professional, sleek, flat design, white background, Japanese font, 4k.)
```

### ビジュアルトーン統一のルール

書籍全体で統一するために、Phase 3 開始時に以下を決定する:

```
ビジュアルトーン設定:
- メインカラー: {テーマから決定、HEXコード}
- サブカラー: {補色、HEXコード}
- アクセントカラー: {強調色、HEXコード}
- イラストスタイル: flat design / watercolor / 3D render など
- 雰囲気: warm / cool / professional / casual など
```

全プロンプトにこのトーン設定を追記して一貫性を保つ。

### 画像生成の実行

nanobanana-pro スキルを使用する:

```bash
cd /c/Users/baseb/dev/taisun_agent/.claude/skills/nanobanana-pro

# 表紙
python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../output/{slug}/images/cover.png"

# 章ヘッダー
python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../output/{slug}/images/ch1_header.png"

# 本文中図解
python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../output/{slug}/images/ch1_img1.png"
```

### 最終原稿の組み立て

タグを画像参照に置換する。**画像サイズ属性 `{ width=100% }` を必ず付与**し、
DOCX変換時にページ幅に収まるようにする。
また、**画像の前後に必ず空行1行ずつ**を維持する。

```
変換前: <!-- [COVER_IMAGE] -->
変換後:
![表紙](images/cover.png){ width=100% }

変換前: <!-- [HEADER_IMAGE: 説明] -->
変換後:
![第1章ヘッダー](images/ch1_header.png){ width=100% }

変換前: <!-- [INLINE_IMAGE: 説明] -->
変換後:
![図解: 説明の要約](images/ch1_img1.png){ width=100% }
```

**注意:** 各画像行の前後に空行が1行ずつあることを必ず確認する。

完成した原稿を `manuscript.md` として保存。

---

## Phase 6: DOCX変換（Word形式出力）

### 手順

1. `manuscript.md` の最終チェック（画像サイズ属性・改ページ・空行の確認）
2. Pandoc で画像を埋め込んだ Word ファイルを作成する
3. 完成した DOCX をユーザーに通知する

### 変換前の最終チェック（必須）

```
⚠️ DOCX変換には必ず manuscript.md を使用する。manuscript_raw.md は使用禁止。
   manuscript_raw.md は図解画像がHTMLコメント（プレースホルダー）のままで、
   Wordに図解が含まれなくなる。
```

DOCX変換の前に、`manuscript.md` が以下を満たしていることを確認する:

```
チェック項目:
□ すべての画像に { width=100% } 属性が付いている
□ 各章（## 第N章）の直前に \newpage がある
□ 各節（### N.M）の直前に \newpage がある
□ すべての画像行の前後に空行が1行ずつある
□ 表紙タグ（<!-- [COVER_IMAGE] -->）が冒頭にある（表紙画像は Phase 8 で生成）
```

不備があれば修正してから変換すること。

### 実行コマンド

```bash
cd /c/Users/baseb/dev/開発1/output/{slug}

pandoc manuscript.md \
  -o manuscript.docx \
  --from markdown \
  --to docx \
  --resource-path=. \
  --standalone \
  --dpi=150
```

**画像サイズについて:**
- Markdownで `{ width=100% }` を付与することで、Pandocが画像をページ幅に自動フィットさせる
- `--dpi=150` で適切な解像度を指定（大きすぎるとはみ出し、小さすぎると粗くなる）
- これによりA4/B5/新書サイズいずれでもページ内に収まる

**改ページについて:**
- Markdown中の `\newpage` がDOCXの改ページに自動変換される
- 章の前・節の前・単元終了時に改ページが入る

**空行について:**
- 画像前後の空行はDOCX上で適切なスペースとして反映される
- 図と本文がくっつかず、読みやすいレイアウトになる

### 出力ファイル

```
output/{slug}/
├── manuscript.md             # Markdown版（画像リンク）
├── manuscript_raw.md         # 中間ファイル（画像タグ）
├── manuscript.docx           # ← Word版（図解画像埋め込み済み・改ページ済み）
└── images/                   # 生成画像（図解のみ、表紙はPhase 8で追加）
```

### 補足

- Pandoc が `images/` フォルダ内の画像を自動で DOCX に埋め込む
- `{ width=100% }` により画像がページ幅に収まる（はみ出し防止）
- `\newpage` により章・節の前で必ず改ページが入る
- 画像前後の空行により図と本文に適切なスペースが入る
- DOCX を Google Drive にアップロードすれば Google ドキュメントとしても開ける
- 見出し（`#` `##` `###`）は Word のスタイル（見出し1、見出し2、見出し3）に自動変換される
- Pandoc が未インストールの場合は `doc-convert-pandoc` スキルのセットアップ手順に従う

---

## Phase 7: 漫画確認 → 漫画統合版リビルド（★必須確認ステップ）

### 概要

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 8（表紙作成）に進む前に、必ずこのフェーズでユーザーに        │
│  漫画制作の要否を確認すること。確認なしにPhase 8へ進むのは絶対禁止  │
└─────────────────────────────────────────────────────────────────────┘
```

原稿完成後、漫画を作るかどうかをユーザーに確認する。
panels/ が既に存在する場合は統合版リビルドを実行する。

### 判定ロジック

```
output/{slug}/panels/ が存在する？
  ├── YES → 漫画統合版リビルド（Step 1〜3）を実行 → Phase 8 へ
  └── NO  → ★ ユーザーに漫画制作の要否を確認（Step 0）
              ├── 漫画を作る → manga-produce-kobetsu-ss で漫画制作
              │                → panels/ 完成後に Step 1〜3 を実行
              │                → Phase 8 へ
              └── 漫画なしで進む → Phase 8 へ
```

### Step 0: 漫画制作の要否確認（panels/ が存在しない場合に必須）

panels/ フォルダが存在しない場合、**必ず** AskUserQuestion でユーザーに確認する:

```
仕様書に漫画（冒頭漫画・中盤漫画等）の指定はありますか？
漫画を作成する場合、表紙は漫画完成後に作成します。

1. 漫画を作成する（manga-produce-kobetsu-ss で制作後、表紙へ進む）
2. 漫画なしで表紙へ進む
3. 漫画は後で作る（このセッションでは表紙まで先に進め、漫画は次回）
```

- 選択肢1の場合: manga-produce-kobetsu-ss スキルを実行 → panels/ 完成後に Step 1〜3 → Phase 8
- 選択肢2の場合: Phase 8 へ直接進む
- 選択肢3の場合: Phase 8 へ進むが、SESSION_HANDOFF.md に「漫画未制作」と明記する

### 手順

#### Step 1: 既存の manga_compiled.md の構造を読み取る

```
1. 既存の manga_compiled.md を Read で読む
2. 漫画ページの挿入パターンを特定する:
   - 各章の後にどの漫画ページ（panels/page_XXX.png）が挿入されているか
   - ページ番号と章の対応関係を記録する
```

#### Step 2: manga_compiled.md を再生成

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ 必ず manuscript.md を使用すること！                            │
│                                                                     │
│  manuscript.md     = 図解画像が ![](images/...) で埋め込み済み     │
│  manuscript_raw.md = <!-- [INLINE_IMAGE] --> プレースホルダーのまま │
│                                                                     │
│  manuscript_raw.md を使うと図解画像がWordに含まれない！            │
└─────────────────────────────────────────────────────────────────────┘
```

```
1. 更新された manuscript.md のテキストを読み込む
2. Step 1 で記録した漫画ページの挿入パターンに従って、
   テキストの間に漫画ページ参照を挿入する
3. 以下の形式で漫画ページを挿入:

   {章のテキスト}

   \newpage

   ![漫画 ページN](panels/page_XXX.png){ width=100% }

   \newpage

   {次の章のテキスト}

4. 表紙画像のパスに注意:
   - 表紙: cover.png（images/cover.png ではなく root直下）
   - 本文中図解: images/ch1_img1.png 等（images/ プレフィックス付き）
   - 漫画ページ: panels/page_XXX.png（panels/ プレフィックス付き）
5. 生成した manga_compiled.md を保存する
```

#### Step 3: final_book.docx を再ビルド

```
1. output/{slug}/build_docx.py が存在するか確認する
2. 存在する場合:
   cd output/{slug}
   python build_docx.py
3. 存在しない場合:
   Pandoc で直接変換する:
   cd output/{slug}
   pandoc manga_compiled.md \
     -o final_book.docx \
     --from markdown \
     --to docx \
     --resource-path=. \
     --standalone \
     --dpi=150
4. 生成結果（ファイルサイズ・画像数・パラグラフ数）をユーザーに報告する
```

### Python パスの注意（Windows環境）

Windows では `python` コマンドが通らない場合がある。
以下の順で試行する:

```bash
# 1. python を試す
python build_docx.py

# 2. python3 を試す
python3 build_docx.py

# 3. フルパスで実行（Python 3.12 の一般的なインストール先）
/c/Users/baseb/AppData/Local/Programs/Python/Python312/python.exe build_docx.py
```

### 出力ファイル

```
output/{slug}/
├── manga_compiled.md         # ← 再生成（原稿+漫画の統合Markdown）
└── final_book.docx           # ← 再ビルド（原稿+図解+漫画の統合Word）
```

---

## Phase 8: 表紙作成（cover-master-ss を使用）※最終ステップ

### 概要

表紙は **cover-master-ss スキル**を使って作成する。
漫画化スキルが cover.png を上書きするため、表紙は**必ず漫画の後**（Phase 7 の後）に作成する。

### 手順

1. **cover-master-ss スキルを呼び出す**（Skill ツールで実行）
2. スキルが原稿情報・ジャンル・ターゲット等をヒアリング
3. 5スタイル（テキスト型/イラスト型/マンガ型/プレミアム型/ハイブリッド型）から自動選択
4. NanoBanana Pro 用 YAML プロンプト（Version A + B）を生成
5. nanobanana-pro で画像を生成し `images/cover.png` として保存
6. `manuscript.md` の `<!-- [COVER_IMAGE] -->` を `![表紙](images/cover.png){ width=100% }` に置換
7. Amazon KDP 用の表紙プロンプトを `cover_prompt_amazon.md` として保存

### 拡充モードでの扱い

- 拡充モードでは Phase 8 を**スキップ**する（既存表紙を維持）
- ユーザーが「表紙も作り直したい」と言った場合のみ実行する

### 漫画化しない場合

- Phase 7 でユーザーが「漫画なし」を選択した場合のみ、Phase 8 へ進む
- **Phase 7 の確認ステップを経ずに Phase 8 を実行することは禁止**

---

## 関連スキル

| スキル | 用途 | Phase |
|--------|------|-------|
| `mega-research` | 6API統合リサーチ（Tavily/SerpAPI/Brave/NewsAPI/Reddit/Perplexity） | Phase 2 |
| `gpt-researcher` | 自律型深層リサーチ（数百ソース探索・出典付き） | Phase 2 |
| `research-free` | APIキー不要の統合リサーチ（フォールバック） | Phase 2 |
| `video-agent` | YouTube動画の文字起こし（yt-dlp + Whisper） | Phase 2 |
| `apify-research` | Instagram/SNSデータ取得 | Phase 2 |
| `kindle-publishing` | 書籍構成テンプレートの参考 | Phase 3 |
| `nanobanana-prompts` | 画像プロンプト最適化の4つの黄金ルール | Phase 5 |
| `nanobanana-pro` | Gemini NanoBanana で画像生成 | Phase 5, 8 |
| `doc-convert-pandoc` | Markdown → DOCX 変換 | Phase 6 |
| `cover-master-ss` | Kindle表紙YAMLプロンプト生成（5スタイル対応） | Phase 8 |

## 使用例

```
/ebook 副業で月10万円稼ぐためのAI活用術
/ebook ChatGPTを使った最強の時短仕事術
/ebook 初心者でもわかるプログラミング入門
```
