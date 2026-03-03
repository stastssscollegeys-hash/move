---
name: note-article-creator-ss
description: |
  note記事の構成設計から画像生成・統合まで一括で行う複合スキル。
  PASCALフレームワーク + diagram-illustration + nanobanana-pro を統合。
  記事本文（7,000〜15,000字）+ 画像（8〜18枚）を一括生成。
  Use when: (1) user says「note記事を画像入りで作って」「noteの記事を図解付きで」,
  (2) user wants to create note articles with inline images,
  (3) user mentions「note 図解入り」「note 画像付き記事」「note記事を一発で」.
  Do NOT use for: 画像なしnote記事（note-marketingを使用）、
  Kindle本（ebook-creator-ssを使用）、SNS投稿（sns-marketingを使用）。
---

# Note Article Creator - note記事一発生成スキル

参考資料 → リサーチ → 記事本文（7,000〜15,000字）+ 画像（8〜18枚）を一括生成。

## Important: Gemini思考モード必須

**日本語テキストを含む画像を生成する際は、Geminiの「思考モード」を必ず使用してください。**

「高速モード」では日本語テキストが文字化けする可能性が高いです。nanobanana-proスキルは自動切り替えを試みますが、手動確認を推奨します：
1. Gemini右下のモードトグルを確認
2. 「高速」→「思考」に切り替え

## When to Use This Skill

- 「note記事を画像入りで作って」「noteの記事を図解付きで」
- 「note記事を一発で」「noteに画像と一緒に記事を作って」
- 「〇〇というテーマでnote記事を作って」
- 「この資料を元にnote記事にして」

## 全体フロー（10フェーズ）

```
Phase 1: ヒアリング
   │  記事タイプ・テーマ・ターゲット・文字数・添付資料を確認
   ▼
Phase 2: リサーチ
   │  note競合分析 + ターゲットの悩み調査 + SNSトレンド
   ▼
Phase 3: PASCAL構成設計
   │  6セクション構成 + 画像挿入位置決定 → ユーザー承認
   ▼
Phase 4: 分割執筆
   │  3パートに分けて執筆 + 画像タグ挿入（都度確認）
   ▼
Phase 5: 画像一括生成
   │  NanoBanana で8〜18枚の図解を生成
   ▼
Phase 6: アイキャッチバナー作成
   │  3スタイルから選択 → プロ級noteバナー生成
   ▼
Phase 7: 統合・推敲
   │  画像タグを実際のパスに置換 + note形式に整形
   ▼
Phase 8: まとめ漫画生成
   │  manga-creator-ssで記事まとめ漫画を生成（右→左読み）
   ▼
Phase 9: X投稿文作成
   │  記事からノウハウを抽出 → 3パターンのX投稿文を生成
   ▼
Phase 10: DOCX変換
   │  Pandoc で画像埋め込みWord形式に変換
   ▼
完成！
```

## 生成物の仕様

| 項目 | 内容 |
|------|------|
| 総文字数 | 7,000 / 10,000 / 12,000 / 15,000字から選択 |
| 構成 | PASCALフレームワーク（6セクション） |
| 記事タイプ | 有料販売記事 / 無料教育記事 / LINE・外部誘導記事 |
| アイキャッチ画像 | 1枚（1280x670px） |
| セクション区切り画像 | 2〜5枚（1280x400px） |
| 本文中図解 | 3〜8枚（1080x1080px） |
| CTA画像 | 1〜3枚（1080x400px） |
| まとめ画像 | 0〜1枚（1080x1080px） |
| まとめ漫画 | 1枚（896×1152px）見出し用 |
| 画像合計 | 約9〜19枚（文字数に応じて） |
| 出力形式 | DOCX（Word）+ Markdown + images/ フォルダ |

### 文字数別の画像枚数

| 文字数 | アイキャッチ | 区切り | 図解 | CTA | まとめ | 合計 |
|--------|------------|--------|------|-----|--------|------|
| 7,000字 | 1 | 2 | 3 | 1 | 1 | 8枚 |
| 10,000字 | 1 | 3 | 5 | 2 | 1 | 12枚 |
| 12,000字 | 1 | 4 | 6 | 2 | 1 | 14枚 |
| 15,000字 | 1 | 5 | 8 | 3 | 1 | 18枚 |

## 出力先

```
output/note-{テーマslug}/
├── article.docx            # ★ 最終成果物（Word形式・画像埋め込み済み）
├── article.md              # Markdown版（note貼り付け用）
├── article_raw.md          # 中間ファイル（画像タグ付き原稿）
├── research.md             # リサーチ結果まとめ
├── structure.md            # PASCAL構成設計書
├── x_posts.md              # X投稿文（3パターン）
└── images/
    ├── eyecatch.png        # アイキャッチ（1280x670px）
    ├── section_01.png      # セクション区切り1
    ├── section_02.png      # セクション区切り2
    ├── ...
    ├── inline_01.png       # 本文図解1
    ├── inline_02.png       # 本文図解2
    ├── ...
    ├── cta_01.png          # CTA画像1
    ├── cta_02.png          # CTA画像2
    ├── summary.png         # まとめ画像
    └── manga_summary.png   # まとめ漫画（見出し用）
```

**最終成果物は `article.md`**。画像がすべてリンクされた状態のMarkdown。
note編集画面にテキストを貼り付け、画像を手動で挿入する。

---

## Phase 1: ヒアリング

### 手順

1. 記事タイプを確認する
2. テーマ・ターゲット・文字数・添付資料を確認する
3. LINE誘導記事の場合は誘導先URLを取得する
4. 著者情報（任意）を確認する
5. 受け取った情報を整理し、Phase 2 に渡す

### ユーザーへの質問テンプレート

```
note記事作成のご依頼ありがとうございます。
最高のコンテンツにするため、以下を教えてください。

1. 記事タイプ:
   a. 有料販売記事（収益化重視）
   b. 無料教育記事（信頼獲得・価値提供重視）
   c. LINE・外部誘導記事（リード獲得重視）

2. テーマ（記事タイトル案）:

3. ターゲット読者（どんな人に読んでほしい？）:

4. 希望文字数（7,000 / 10,000 / 12,000 / 15,000字）:
   ※ わからなければこちらで提案します

5. 参考資料（あれば）:
   - ファイルパス / URL / テキスト

6. バックエンド商品やLINE誘導先（あれば）:
   - 商品名・URL・特典内容など

7. 著者プロフィール（あれば）:
   - 名前・肩書き・実績など
   ※ なければ汎用的な文体で執筆します

8. 特に強調したいポイント（あれば）:
```

### 受け取れる資料の形式

| 形式 | 例 | 処理方法 |
|------|------|----------|
| ファイル | PDF、テキスト、Markdown | Read ツールで読み込み |
| URL | ブログ記事、Web ページ | WebFetch で内容取得 |
| テキスト | チャットに直接貼り付け | そのまま使用 |
| 複数資料 | 上記の組み合わせ | すべて読み込んで統合 |

### 記事タイプ別の設計方針

| 記事タイプ | 構成の重点 | CTA設計 | 画像の特徴 |
|-----------|-----------|---------|-----------|
| 有料販売記事 | 販売フック・コピー重視 | 有料パート誘導CTA | 無料パートで価値を見せる図解 |
| 無料教育記事 | 信頼・教育・価値提供重視 | シェア・フォロー誘導CTA | 教育的な図解・インフォグラフィック |
| LINE誘導記事 | 共感・メリット・行動喚起重視 | LINE登録CTA（バナー+QRコード配置スペース） | 特典訴求・ベネフィット可視化 |

資料を受け取ったら内容を要約し、「この内容をもとにリサーチを進めます」と伝えて Phase 2 へ。

---

## Phase 2: リサーチ

### 手順

1. ヒアリング内容からテーマ・キーワードを抽出する
2. 以下の3層リサーチを実行する
3. リサーチ結果を `output/note-{slug}/research.md` に保存する
4. リサーチ結果の要点をユーザーに共有し、Phase 3 へ進む

### 3層リサーチ（すべて実行すること）

#### Layer 1: note 競合分析

テーマに関するnote記事の成功事例を調査する。

```
手順:
1. WebSearch で「{テーマ} site:note.com」を検索
2. 上位記事を5〜10本特定
3. WebFetch で各記事の内容を取得
4. 以下を抽出:
   - 記事の構成・切り口
   - スキ数・コメント数（人気度の指標）
   - 有料/無料の区分と価格設定
   - 著者の専門性・実績
   - 独自のフレームワーク・メソッド
   - 具体的な数値・事例
5. 有料記事は概要・目次部分から構成の参考にする
```

#### Layer 2: ターゲットの悩み・ニーズ

ターゲット読者のリアルな声を収集する。

```
手順:
1. WebSearch で以下を検索:
   - 「{テーマ} 悩み」「{テーマ} わからない」
   - 「{テーマ} site:detail.chiebukuro.yahoo.co.jp」（Yahoo知恵袋）
   - 「{テーマ} 初心者 つまづく」
2. WebFetch で上位のQ&Aページを取得
3. 以下を抽出:
   - よくある質問・つまづきポイント
   - 初心者が最初にぶつかる壁
   - 解決策として支持されている回答
```

#### Layer 3: SNS・トレンド調査

最新トレンドとバズっている切り口を調査する。

```
手順:
1. WebSearch で以下を検索:
   - 「{テーマ} 2026 トレンド」
   - 「{テーマ} SNS バズ」
   - 「{テーマ} X(Twitter) 話題」
2. 以下を抽出:
   - 今バズっているキーワード・ハッシュタグ
   - インフルエンサーが推しているポイント
   - 競合にない切り口（差別化チャンス）
```

### リサーチの品質基準

- **note競合**: 最低5記事から構成・切り口を分析
- **読者の声**: 最低10件の悩み・質問を収集
- **トレンド**: 最新のバズワード・切り口を3つ以上特定

### リサーチ結果の保存形式（research.md）

```markdown
# リサーチ結果: {テーマ}

## 参考資料の要約
{受け取った資料のポイント整理}

---

## Layer 1: note 競合分析

### 調査した記事
| # | 著者 | 記事タイトル | スキ数 | 有料/無料 | 要点 |
|---|------|-------------|--------|----------|------|
| 1 | {著者} | {タイトル} | {数} | {区分} | {要点} |

### 成功パターン
- {パターン1}
- {パターン2}

---

## Layer 2: ターゲットの悩み・ニーズ

### よくある悩み TOP10
1. {悩み1}（出典: {ソース}）
2. {悩み2}

### 初心者がつまづく壁
- {壁1}
- {壁2}

---

## Layer 3: SNS・トレンド

### バズキーワード
- #{タグ1}（{なぜ人気か}）

### 差別化チャンス
- {差別化ポイント1}

---

## 総合分析: 記事の方向性

### 推奨する切り口
{リサーチを統合した記事の方向性}

### 盛り込むべきポイント
1. {ポイント1}
2. {ポイント2}
```

### リサーチエンジンの使い分け

| スキル/ツール | 用途 |
|--------------|------|
| **WebSearch** | 各Layerの個別キーワード検索 |
| **WebFetch** | note記事・Q&Aページの内容取得 |
| **mega-research** | 利用可能なら全体像を掴むために最初に実行 |
| **research-free** | APIキー不要のフォールバック |

---

## Phase 3: PASCAL構成設計

### 手順

1. ヒアリング（Phase 1）とリサーチ結果（Phase 2）を元にPASCAL構成を設計する
2. 各セクションに画像タグの挿入位置を決定する
3. ビジュアルトーン設定を決定する
4. AskUserQuestion でユーザーに構成を確認してもらう
5. 承認を得たら Phase 4 へ進む

### PASCALフレームワーク

| セクション | 役割 | 推奨画像タイプ |
|-----------|------|---------------|
| **P** (Problem) | 読者の問題を提示、共感を誘う | before-after / illustration |
| **A** (Agitation) | 問題の深刻さを煽る、危機感を持たせる | scale-circles / comparison-table |
| **S** (Solution) | 解決策を提示する | flow-horizontal / stairs |
| **C** (Credibility) | 信頼性・権威・実績を示す | pyramid / network / list |
| **A** (Action) | 具体的な行動ステップを示す | flow-vertical / list |
| **L** (Lead) | CTA、次のアクションへ誘導する | CTA画像 |

### 構成設計テンプレート

以下の形式で構成を生成する：

```
記事タイトル: {テーマ}
記事タイプ: {有料販売 / 無料教育 / LINE誘導}
想定読者: {ターゲット}
読者のゴール: {この記事を読んで何が変わるか}
文字数: {7,000 / 10,000 / 12,000 / 15,000字}

---

アイキャッチ画像:
  - [EYECATCH] {記事テーマを象徴するビジュアルの説明}

導入部（{文字数の10%}字）
  - フック: {読者の注意を引く冒頭の一文}
  - 読者への約束: {この記事で得られること}

---

P: Problem セクション（{文字数の15%}字）
  キーポイント:
    1. {問題点1}
    2. {問題点2}
  画像:
    - [SECTION] セクション区切り（Problem）
    - [INLINE] {問題を可視化する図解の説明}

A: Agitation セクション（{文字数の15%}字）
  キーポイント:
    1. {煽り1: 放置するとどうなるか}
    2. {煽り2: 最悪の未来}
  画像:
    - [SECTION] セクション区切り（Agitation）
    - [INLINE] {深刻さを示す図解の説明}

S: Solution セクション（{文字数の25%}字）
  キーポイント:
    1. {解決策1}
    2. {解決策2}
    3. {解決策3}
  画像:
    - [SECTION] セクション区切り（Solution）
    - [INLINE] {解決策のプロセスを示す図解}
    - [INLINE] {具体的な手法の図解}

C: Credibility セクション（{文字数の15%}字）
  キーポイント:
    1. {実績・事例1}
    2. {社会的証明}
  画像:
    - [SECTION] セクション区切り（Credibility）
    - [INLINE] {信頼性を示す図解}

A: Action セクション（{文字数の15%}字）
  キーポイント:
    1. {具体的ステップ1}
    2. {具体的ステップ2}
    3. {具体的ステップ3}
  画像:
    - [INLINE] {アクションステップの図解}
    - [CTA] CTA画像（記事タイプに応じて）

L: Lead セクション（{文字数の5%}字）
  - まとめ
  - 最終CTA
  画像:
    - [SUMMARY] まとめ画像
    - [CTA] メインCTA画像
```

### ビジュアルトーン統一のルール

記事全体で統一するために、Phase 3 開始時に以下を決定する:

```
ビジュアルトーン設定:
- メインカラー: {テーマから決定、HEXコード}
- サブカラー: {補色、HEXコード}
- アクセントカラー: {強調色、HEXコード}
- イラストスタイル: flat design / watercolor / 3D render など
- 雰囲気: warm / cool / professional / casual など
```

全プロンプトにこのトーン設定を追記して一貫性を保つ。

### 構成設計のルール

- PASCALの各セクションは明確に役割を持たせる
- 読者が「自分ごと」として読める構成にする
- 有料記事の場合: SolutionセクションのStep2以降を有料パートにする（無料パートで十分な価値を見せる）
- LINE誘導記事の場合: 各セクション末にCTAを配置する（最低3箇所）
- 図解候補は具体的に記述する（「概要図」ではなく「3つのステップを矢印でつないだフロー図」のように）

---

## Phase 4: 分割執筆

### 手順

1. Phase 3 で承認された構成 + 参考資料（Phase 1）+ リサーチ結果（Phase 2）に基づいて執筆する
2. **3パートに分割**して自律的に執筆する（パートごとのユーザー確認は不要）
3. 画像の挿入位置にタグを埋め込む
4. 全パート完成後、`output/note-{slug}/article_raw.md` に保存する
5. 全パート完了後にまとめてユーザーに報告する

### 3パート分割

| パート | 含むセクション | 文字数目安（10,000字の場合） |
|--------|--------------|--------------------------|
| パート1 | 導入部 + P(Problem) + A(Agitation) | 約4,000字 |
| パート2 | S(Solution) + C(Credibility) | 約4,000字 |
| パート3 | A(Action) + L(Lead) | 約2,000字 |

### 執筆ルール

- **文体**: です・ます調、親しみやすく実用的
- **段落**: 3〜4文ごとに改行。note上での読みやすさ重視
- **具体例**: 各セクションに最低1つの具体例・事例を含める
- **数値**: できるだけ具体的な数値を含める（「多くの」→「87%の」）
- **著者情報**: Phase 1 で著者プロフィールを受け取っている場合はその文体・トーンで執筆。ない場合は汎用的な文体で執筆
- **ストーリー**: PASCALの流れに沿って、読者が主人公のストーリーを展開する
- **表（テーブル）の使用**: Markdownの表記法（`| ... |`形式）を使用してOK
  - Pandocが自動的にWordのテーブル機能に変換する
  - 比較表・機能一覧・仕様表などで積極的に使用
  - 例:
    ```markdown
    | 項目 | 説明 | 価格 |
    |------|------|------|
    | プランA | 基本機能 | 1,000円 |
    | プランB | 全機能 | 3,000円 |
    ```
  - Word出力時に整ったテーブルとして表示される
- **箇条書き**: 通常のMarkdownリスト記法（`-`, `1.`）を使用してOK
  - Pandocが適切にWord形式に変換する
  - 例:
    ```markdown
    - 項目1
    - 項目2

    1. 手順1
    2. 手順2
    ```

### 画像タグの挿入ルール

原稿中に以下のタグを埋め込む。タグは独立した行に記述する。

#### 5つの画像タイプ

本文中画像は以下の5タイプから選択する。**図解（diagram）がメインだが、内容に応じて他タイプも活用する。**

| タイプ | type値 | 用途 | プロンプト特徴 |
|--------|--------|------|---------------|
| **図解** | `diagram` | 比較表・フロー図・ステップ図 | 4要素構造、日本語テキスト埋め込み、26パターンテンプレート使用 |
| **イメージ画像** | `concept` | セクション区切り・雰囲気演出 | コンセプトアート、抽象的ビジュアル |
| **スクリーンショット風** | `screenshot` | ツール操作画面・手順解説 | UIモックアップ、操作画面の再現 |
| **実写風** | `photo` | 商品写真・人物・風景 | フォトリアリスティック |
| **漫画/アニメ風** | `manga` | キャラクター・ストーリー表現 | 漫画/アニメスタイルイラスト |

#### 画像タイプ自動選定ルール

```
セクション区切り → concept（雰囲気演出）
本文中の比較・手順・データ → diagram（図解テンプレート）※メイン
ツール紹介・使い方 → screenshot（操作画面）
事例・体験談 → photo（リアル感）or manga（親しみやすさ）
CTA → diagram or concept（訴求に応じて）
まとめ → diagram（要点整理）
迷ったら → diagram（図解がデフォルト）
```

#### アイキャッチ画像（記事冒頭、タイトルの直後）
```
<!-- [EYECATCH_IMAGE: {記事テーマを象徴するビジュアルの説明。日本語で50〜80字}] -->
```

#### セクション区切り画像（PASCALの各セクション冒頭）
```
<!-- [SECTION_IMAGE: section={P/A/S/C/A/L} | mood={そのセクションの感情} | description={視覚的な説明}] -->
```

#### 本文中画像（約800〜1,500字ごと）

**type=diagram の場合（メイン・デフォルト）:**
直前の内容に最適な26パターンの**図解テンプレート**を選定し、タグに含める。
```
<!-- [INLINE_IMAGE: type=diagram | pattern={パターン名} | title={図解タイトル} | elements={要素1,要素2,要素3,...} | description={補足説明}] -->
```

**type=concept の場合:**
```
<!-- [INLINE_IMAGE: type=concept | mood={hopeful/anxious/energetic/calm/professional} | desc={雰囲気・シーンの説明}] -->
```

**type=screenshot の場合:**
```
<!-- [INLINE_IMAGE: type=screenshot | tool={ツール名} | action={操作の説明}] -->
```

**type=photo の場合:**
```
<!-- [INLINE_IMAGE: type=photo | scene={被写体・構図の説明}] -->
```

**type=manga の場合:**
```
<!-- [INLINE_IMAGE: type=manga | scene={シーンの説明} | style={少年漫画風/少女漫画風/Webtoon風}] -->
```

**重要: type を省略した場合は `diagram` として扱う（後方互換性維持）。**

#### CTA画像（誘導ポイント）
```
<!-- [CTA_IMAGE: type={line/premium/benefit/follow} | text={CTA上に表示したいテキスト} | description={デザインの説明}] -->
```

#### まとめ画像（記事末尾）
```
<!-- [SUMMARY_IMAGE: title={まとめタイトル} | elements={要点1,要点2,要点3,...}] -->
```

### 図解パターン選定ルール（26種類）

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
| 箇条書き（縦型） | 情報の整然とした一覧 | `list-vertical` |
| 箇条書き（横型） | 横並びカード型 | `list-horizontal` |
| 箇条書き（羅列） | 高密度情報一覧 | `list-dense` |

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
内容が「一覧・列挙」 → list-vertical / list-horizontal / honeycomb
内容が「時系列」 → gantt
内容が「論理式」 → formula
内容が「雰囲気・概念」 → illustration
```

### タグ記述の例

```
良い例:
<!-- [EYECATCH_IMAGE: 明るいワークスペースでノートPCに向かうクリエイター。画面にはnoteの記事が表示されている。前向きな雰囲気] -->

<!-- [SECTION_IMAGE: section=P | mood=不安・焦り | description=暗い背景に「？」マークが浮かぶ。悩んでいる人のシルエット] -->

<!-- [INLINE_IMAGE: type=diagram | pattern=flow-horizontal | title=AI活用の3ステップ | elements=情報収集,分析・選定,実践・改善 | description=各ステップにシンプルなアイコン付き、左から右への自然な流れ] -->

<!-- [INLINE_IMAGE: type=diagram | pattern=comparison-table | title=デザイン手段 徹底比較 | elements=外注,Canva,Midjourney,NanoBanana Pro | rows=コスト,品質,手軽さ,日本語対応 | description=NanoBanana Pro列を青でハイライト] -->

<!-- [INLINE_IMAGE: type=concept | mood=hopeful | desc=扉が開いて光が差し込む、新しい可能性の象徴] -->

<!-- [INLINE_IMAGE: type=screenshot | tool=Gemini | action=NanoBanana Proで画像生成している画面、プロンプト入力中] -->

<!-- [INLINE_IMAGE: type=photo | scene=デスクワークしている人の手元、ノートPCとコーヒー、自然光] -->

<!-- [INLINE_IMAGE: type=manga | scene=主人公がAIツールを発見して驚いている、吹き出し付き | style=少年漫画風] -->

<!-- [CTA_IMAGE: type=line | text=【無料】7日間メール講座を受け取る | description=LINE緑のグラデーション背景、ギフトアイコン、QRコード配置スペース] -->

<!-- [SUMMARY_IMAGE: title=この記事のまとめ | elements=ポイント1: 〇〇が重要,ポイント2: △△を実践,ポイント3: □□で成果が出る] -->

悪い例:
<!-- [EYECATCH_IMAGE: いい感じの画像] -->
<!-- [INLINE_IMAGE: pattern=flow-horizontal | title=流れ | elements=A,B,C | description=] -->
<!-- [INLINE_IMAGE: type=diagram | title=概要 | elements=A,B] -->  ← patternがない
<!-- [INLINE_IMAGE: Orange gradient marketing banner with white bold text] --> ← タグ形式不正、4要素構造なし
```

### 原稿のMarkdown構造

```markdown
# {記事タイトル}

<!-- [EYECATCH_IMAGE: {説明}] -->

{導入部 フック + 読者への約束}

---

## {Problemセクション見出し}

<!-- [SECTION_IMAGE: section=P | mood={感情} | description={説明}] -->

{本文 約800〜1,500字}

<!-- [INLINE_IMAGE: type=diagram | pattern={パターン} | title={タイトル} | elements={要素} | description={説明}] -->

{本文 約800〜1,500字}

---

## {Agitationセクション見出し}

<!-- [SECTION_IMAGE: section=A | mood={感情} | description={説明}] -->

{本文}

<!-- [INLINE_IMAGE: type=diagram | pattern={パターン} | title={タイトル} | elements={要素} | description={説明}] -->

{本文}

<!-- [CTA_IMAGE: {説明}] -->  ← LINE誘導記事の場合

---

## {Solutionセクション見出し}

<!-- [SECTION_IMAGE: section=S | mood={感情} | description={説明}] -->

{本文（最も分量が多いセクション）}

<!-- [INLINE_IMAGE: type=diagram | pattern={パターン} | title={タイトル} | elements={要素} | description={説明}] -->

{本文}

<!-- [INLINE_IMAGE: type=screenshot | tool={ツール名} | action={操作説明}] -->  ← ツール紹介の場合

{本文}

---

## {Credibilityセクション見出し}

<!-- [SECTION_IMAGE: section=C | mood={感情} | description={説明}] -->

{本文}

<!-- [INLINE_IMAGE: type=diagram | pattern={パターン} | title={タイトル} | elements={要素} | description={説明}] -->

---

## {Actionセクション見出し}

{本文}

<!-- [INLINE_IMAGE: type=diagram | pattern={パターン} | title={タイトル} | elements={要素} | description={説明}] -->

<!-- [CTA_IMAGE: {説明}] -->

---

## まとめ

{まとめ本文}

<!-- [SUMMARY_IMAGE: {説明}] -->

<!-- [CTA_IMAGE: {メインCTA}] -->
```

---

## Phase 5: 画像一括生成

### 重要: 画像生成前の確認事項

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️  画像生成を開始する前に、必ず以下を確認・実行してください       │
└─────────────────────────────────────────────────────────────────────┘
```

**1. 認証状態の確認:**
```bash
cd 開発1/.claude/skills/nanobanana-pro
python scripts/run.py auth_manager.py status
```
- 「✓ Authenticated」が表示されない場合は、`setup` で再認証

**2. --show-browser オプションを常に使用:**
- 画像生成コマンドには必ず `--show-browser` を付ける
- ブラウザが表示されることで、ログイン状態や思考モード切替を目視確認できる

**3. ログインが必要になった場合:**
- ブラウザが開き「ログインしてください」というメッセージが表示される
- Googleアカウントでログインすると、自動的にセッションが保存される
- ログイン完了後、画像生成が自動的に再開される

**4. 思考モード切替:**
- nanobanana-pro は自動的に「高速」→「思考」モードに切り替えを試みる
- 切替に失敗した場合は手動で切り替える（Gemini画面右下のトグル）
- 思考モードでないと日本語テキストが文字化けする可能性が高い

### エラー発生時の対処フロー

```
画像生成失敗
    │
    ├─ 「Not authenticated」エラー
    │      → python scripts/run.py auth_manager.py setup で再認証
    │
    ├─ 「画像の作成ボタンが見つかりません」
    │      → ブラウザでGoogleにログイン（自動待機）
    │
    ├─ 「Target page, context or browser has been closed」
    │      → ブラウザが閉じられた
    │      → タイムアウトを延長 --timeout 600
    │      → 再実行
    │
    ├─ 「Timeout after 300s」（タイムアウト）
    │      ⚠️  重要: プロンプトをシンプルにしてはいけない
    │      ⚠️  4要素構造を変えてはいけない
    │
    │      原因: nanobanana-proの画像検出ロジックの問題
    │            （画像は生成されているが、検出できていない）
    │
    │      対処法:
    │      → nanobanana-proスキルのメンテナンスが必要
    │      → image_generator.pyのセレクタ修正が必要
    │      → 一時的な回避策はない（スキル本体の修正が必要）
    │
    ├─ 日本語が文字化け
    │      → 思考モードになっているか確認
    │      → 手動で「高速」→「思考」に切り替え
    │
    └─ その他のエラー
           → --show-browser で状況を確認
           → ブラウザを閉じて再実行
```

### 手順

1. `article_raw.md` から全画像タグを抽出する
2. 各タグを NanoBanana 用プロンプトに変換する
3. nanobanana-pro スキルで画像を1枚ずつ生成する（`--show-browser` 必須）
4. 生成した画像パスでタグを置換し、`article.md` を作成する

### 画像タグ → NanoBanana プロンプト変換ルール

**プロンプト形式: Nano Banana / Imagen 3 最適化形式**

すべてのプロンプトは以下の形式で構成する：

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

### タイプ別プロンプト変換ルール

INLINE_IMAGE タグの `type` 値に応じて、以下のルールでプロンプトを変換する。

#### type=diagram の場合（メイン）
- `pattern`値 → 後述の26パターンテンプレートを自動適用
- 4要素構造（Subject/Layout/Visuals/Style）**必須**
- 日本語テキスト埋め込み**必須**
- Style末尾に "Japanese font, 4k" を**必ず**追加

#### type=concept の場合
```
* Subject: (Professional concept art for note article. Mood: {mood}. {descを英訳}.)
* Layout: (Square composition. {moodに応じた構図}. Atmospheric composition with depth.)
* Visuals: (Color palette matching mood: {mood別カラー}. Soft gradients. Abstract visual elements. NO text in the image.)
* Style: (Modern digital art, atmospheric, consistent with article theme, high resolution 4k.)
```

mood別カラー:
- hopeful: 暖かいオレンジ→ゴールド系
- anxious: ダークグレー→ブルーグレー系
- energetic: ビビッドレッド→オレンジ系
- calm: ソフトブルー→ミントグリーン系
- professional: ネイビー→シルバー系

#### type=screenshot の場合
```
* Subject: (Realistic screenshot mockup of {tool} interface showing {actionを英訳}.)
* Layout: (Square composition. Browser window frame at top. Main content area showing {tool} UI with Japanese text.)
* Visuals: (Clean UI elements. Realistic browser chrome. Japanese text labels: "{操作の日本語説明}". Cursor pointing at key action area.)
* Style: (Realistic screenshot mockup, browser window frame, crisp UI rendering, high resolution 4k.)
```

#### type=photo の場合
```
* Subject: (Professional photograph of {sceneを英訳}.)
* Layout: (Square composition. {構図の英語指示 - rule of thirds, centered, etc.}.)
* Visuals: (Natural lighting. Shallow depth of field. Warm color temperature. Professional quality. NO text overlay.)
* Style: (Photorealistic, professional photography, natural bokeh, high resolution 4k.)
```

#### type=manga の場合
```
* Subject: (Manga panel illustration. {sceneを英訳}.)
* Layout: (Square composition. {style}構図. Speech bubbles with Japanese text: "{セリフ}". Dynamic panel composition.)
* Visuals: (Speed lines. Expressive character faces. {style}トーン. Bold outlines. Emotion effects.)
* Style: ({style} manga illustration, dynamic composition, Japanese text in speech bubbles, high resolution 4k.)
```

style別指示:
- 少年漫画風: "Shonen manga style, action-oriented, bold lines, high energy"
- 少女漫画風: "Shoujo manga style, flowery backgrounds, sparkling eyes, soft lines"
- Webtoon風: "Webtoon style, vertical panel, clean lines, modern digital art"

### 禁止事項（厳守）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️  警告: 以下のルールを破ると日本語テキストが文字化けします      │
└─────────────────────────────────────────────────────────────────────┘
```

**絶対に禁止：**
1. **4要素構造（Subject/Layout/Visuals/Style）を使わない**図解プロンプト
   - 文字化けの最大の原因
   - 必ず `* Subject:` `* Layout:` `* Visuals:` `* Style:` の4要素に分離する

2. **1行の長文プロンプト**
   - NG例: `"Horizontal process flow infographic. Title text reads "フロー図". Step 1 text reads "ステップ1". ...（長文）"`
   - OK例: 4要素構造に分割したテンプレート

3. **日本語テキストの翻訳・省略**
   - タグ内の日本語テキストは**一言一句そのまま**使用
   - 英訳・要約・簡略化は**絶対禁止**

4. **text reads形式の省略**
   - 日本語テキストは必ず `text reads "日本語"` 形式で記述
   - または4要素構造の中に `"{日本語}"` として埋め込む

5. **Styleキーワードの省略**
   - 必須スタイル: `Flat vector design, modern business presentation style, clean Japanese typography, bold sans-serif fonts, corporate color palette, white background, high resolution 4k.`
   - 最低でも `Japanese typography, 4k` は必須

6. **英語だけの抽象的プロンプト**
   - NG例: `"Orange gradient marketing banner with white bold text"`
   - 日本語テキストを含まない画像は品質が低下する

### プロンプト形式の鉄則（文字化け防止）

**鉄則:**
1. **日本語テキスト固定:** `text reads "日本語"` 内のテキスト、または4要素内の `"{日本語}"` は**絶対に翻訳せず、そのまま使用**
2. **スタイル統一:** 必須スタイルキーワード（Flat vector design, modern business presentation style, clean Japanese typography, bold sans-serif fonts, corporate color palette, white background, high resolution 4k）を常に含める
3. **視覚的優先度:** 最も重要な要素には `vivid highlight color` を指定し、他は `soft gray` / `neutral colors`
4. **レイアウト詳細:** 図解パターンごとのテンプレートを使用して空間配置を指定

**必ず以下の4要素形式を使う:**
```
* Subject: (Professional infographic with Japanese text.)
* Layout: (Specific spatial arrangement. Elements: "{日本語テキスト1}", "{日本語テキスト2}".)
* Visuals: (Color palette details. Style keywords. Japanese typography requirements.)
* Style: (Flat vector design, modern business presentation style, clean Japanese typography, bold sans-serif fonts, 4k.)
```

**絶対にやってはいけない（文字化けの原因）:**
```
❌ BAD: "Comparison chart infographic with Japanese text. Title: デザイン手段...（1行の長文）"
❌ BAD: type=diagramだがpatternなし
❌ BAD: 4要素構造なしの1行プロンプト
❌ BAD: 日本語テキストを英訳してしまう
```

→ 1行の長文プロンプトは日本語テキストが文字化けする最大の原因

### Before/After例

```
❌ BAD: "Orange gradient marketing banner with white bold text"
❌ BAD: type=diagramだがpatternなし
❌ BAD: 4要素構造なしの1行プロンプト

✅ GOOD (diagram):
* Subject: (Comparison infographic with Japanese text.)
* Layout: (4-column table. Headers: "外注","Canva","Midjourney","NanoBanana Pro". NanoBanana Pro column highlighted blue.)
* Visuals: (Blue #4285F4 highlight. Gold star ratings. White background.)
* Style: (Professional flat infographic, bold Japanese sans-serif font, 4k.)

✅ GOOD (concept):
* Subject: (Professional concept art. Mood: hopeful. A door opening with light streaming in, symbolizing new possibilities.)
* Layout: (Square composition. Centered composition. Dramatic lighting from right side.)
* Visuals: (Warm orange-gold gradient. Soft light rays. Abstract doorway silhouette. NO text.)
* Style: (Modern digital art, atmospheric, cinematic lighting, high resolution 4k.)

✅ GOOD (manga):
* Subject: (Manga panel of character discovering AI design tool.)
* Layout: (Square composition. Single panel, character center with surprised expression. Speech bubble: "これなら私でもできる！")
* Visuals: (Speed lines radiating from center. Sparkle effects. Bright warm colors. Bold outlines.)
* Style: (Shonen manga style, dynamic composition, Japanese text in speech bubbles, 4k.)
```

---

#### アイキャッチ画像（1280x670px）

Phase 6 で生成したバナー画像（`eyecatch.png`）をそのまま使用する。
Phase 5 の時点ではタグ `<!-- [EYECATCH_IMAGE: ...] -->` を配置するだけでよい。
実際のバナー生成は Phase 6 で3スタイルから選択して行う。

#### セクション区切り画像

```
* Subject: (Wide banner image for article section divider. Mood: {mood}. {descriptionを英訳}.)
* Layout: (Wide landscape 16:9. {mood}に応じた構図. Gradient background.)
* Visuals: (Color gradient matching mood: {mood別カラー}. Subtle visual elements. NO text in the image.)
* Style: (Minimal, atmospheric, consistent with article theme, high resolution 4k.)
```

セクション別のムードカラー:
- P (Problem): グレー→ダークブルー系（不安・問題意識）
- A (Agitation): ダークレッド→オレンジ系（危機感・緊急性）
- S (Solution): ブルー→グリーン系（希望・解決）
- C (Credibility): ゴールド→ネイビー系（信頼・権威）
- A (Action): グリーン→ブライトブルー系（行動・エネルギー）
- L (Lead): メインカラー→アクセントカラー（誘導・CTA）

#### CTA画像

**type=line の場合:**
```
* Subject: (Call-to-action banner for LINE registration with Japanese text.)
* Layout: (Wide landscape banner. Left side: gift/present icon. Center: text area for "{text}". Right side: white square placeholder for QR code. Arrow pointing to QR code.)
* Visuals: (Background gradient #22C55E to #16A34A (LINE green). White text area. Sparkle effects. Modern clean design.)
* Style: (Marketing banner, high contrast, eye-catching, professional, 4k.)
```

**type=premium の場合:**
```
* Subject: (Premium content divider banner for note.com paid article.)
* Layout: (Wide landscape banner. Lock icon on left. Text area: "{text}". Star/diamond decoration.)
* Visuals: (Background gradient gold #D4AF37 to dark #1A1A2E. Elegant, premium feel. Subtle glow effects.)
* Style: (Luxury, premium, professional typography, high resolution 4k.)
```

**type=benefit の場合:**
```
* Subject: (Benefit/offer announcement banner with Japanese text.)
* Layout: (Wide landscape banner. Gift box icon. Text area: "{text}". Checkmark list of benefits.)
* Visuals: (Background {アクセントカラー} gradient. Bright, positive energy. Celebration effects.)
* Style: (Marketing, energetic, eye-catching, professional, 4k.)
```

**type=follow の場合:**
```
* Subject: (Follow/share call-to-action banner for note.com article.)
* Layout: (Wide landscape banner. Heart/bookmark icon. Text area: "{text}". Social sharing icons.)
* Visuals: (Background soft gradient using {メインカラー}. Warm, friendly atmosphere.)
* Style: (Social media optimized, clean, inviting, professional, 4k.)
```

#### まとめ画像

```
* Subject: (Summary infographic with Japanese text. Stylized vertical list design.)
* Layout: (Square composition. Title: "{title}" at top. Vertical list with items: {elements}.)
* Visuals: (Modern checkmark icons. Alternating light/dark backgrounds for rows. High-contrast labels. Color palette: {メインカラー}.)
* Style: (Clean UI design, professional sans-serif, easy-to-read layout, shareable on social media, 4k.)
```

#### 本文中図解（INLINE_IMAGE） - 26パターン

タグの `pattern` 値に応じて、以下のテンプレートを使い分ける。
画像サイズは 1080x1080px（正方形、モバイル最適化）。

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

**No.25 イメージイラスト (`illustration`)**
```
* Subject: (Professional digital illustration for note article. {descriptionを英訳}.)
* Layout: ({descriptionの構図を英語で指示}.)
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
2. pattern に対応する NanoBanana テンプレートを取得
3. テンプレートの {title}, {elements} に日本語テキストをそのまま埋め込む
   - 図中テキストは翻訳せず日本語のまま使用
   - Layout と Visuals の構造指示は英語のまま維持
4. {メインカラー}, {サブカラー}, {アクセントカラー} をビジュアルトーン設定から埋め込む
5. description の補足があれば Visuals に追記
```

### 画像生成の実行

nanobanana-pro スキルを使用する:

```bash
cd /c/Users/baseb/dev/開発1/.claude/skills/nanobanana-pro

# ⚠️ 重要: 必ず --show-browser と --timeout 300 を指定する
# - --show-browser: ログイン状態・思考モード切替を目視確認
# - --timeout 300: 長いプロンプトや混雑時のタイムアウト対策

# アイキャッチ
PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../../output/note-{slug}/images/eyecatch.png" \
  --show-browser --timeout 300

# セクション区切り
PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../../output/note-{slug}/images/section_01.png" \
  --show-browser --timeout 300

# 本文中図解
PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../../output/note-{slug}/images/inline_01.png" \
  --show-browser --timeout 300

# CTA画像
PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../../output/note-{slug}/images/cta_01.png" \
  --show-browser --timeout 300

# まとめ画像
PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
  --prompt "{変換後プロンプト}" \
  --output "../../../output/note-{slug}/images/summary.png" \
  --show-browser --timeout 300
```

### 最終原稿の組み立て

タグを画像参照に置換:

```
変換前: <!-- [EYECATCH_IMAGE: 説明] -->
変換後: ![アイキャッチ](images/eyecatch.png)

変換前: <!-- [SECTION_IMAGE: 説明] -->
変換後: ![セクション区切り](images/section_01.png)

変換前: <!-- [INLINE_IMAGE: 説明] -->
変換後: ![図解: タイトル](images/inline_01.png)

変換前: <!-- [CTA_IMAGE: 説明] -->
変換後: ![CTA](images/cta_01.png)

変換前: <!-- [SUMMARY_IMAGE: 説明] -->
変換後: ![まとめ](images/summary.png)
```

完成した原稿を `article.md` として保存。

---

## Phase 6: アイキャッチバナー作成（noteバナー職人）

### 概要

noteバナー職人のデザイン手法を統合。
記事の内容に合わせて、読者が思わずクリックして読みたくなるプロ級アイキャッチ画像（1280x670px）を生成する。

**成果物:** `images/eyecatch.png` - note記事のアイキャッチに設定する画像

### 手順

#### Step 1: バナー情報のヒアリング

記事本文（Phase 4）が完成した時点で、以下をユーザーに確認する:

```
アイキャッチバナーを作成します。以下を教えてください：

1. 画像に入れたい文字:
   - メインタイトル: （記事タイトル）
   - サブタイトル/キャッチコピー: （伝えたいメッセージ）
   - カテゴリ/タグ: （例：「ビジネス」「エッセイ」「保存版」）
   ※ お任せの場合は、記事内容から最適なものを提案します

2. デザインスタイル:
   A: インパクト＆エンタメ風（極太袋文字、集中線、賑やかな装飾。強い主張やエンタメ向け）
   B: コミックエッセイ・温かいイラスト風（手書き線画、水彩パステル。エッセイ・日常・共感系向け）
   C: スタイリッシュ・ビジネス風（写真素材、洗練タイポグラフィ、美しい余白。ビジネス・技術向け）
   ※ お任せの場合は、記事内容に最適なスタイルを選択します
```

#### Step 2: バナー要素の抽出

記事（article_raw.md）から以下を自動抽出する:

| 要素 | 抽出元 | 例 |
|------|--------|-----|
| メインタイトル | 記事タイトル | 「AI副業で月10万円稼ぐ完全ガイド」 |
| サブタイトル | 記事の核心メッセージ | 「初心者でも今日から始められる」 |
| カテゴリ/タグ | 記事ジャンル | 「ビジネス」「AI活用」 |
| 記事の世界観 | 記事全体のトーン | ビジネス系、エッセイ系、技術系 etc. |

#### Step 3: スタイル選定

ユーザーの選択、または記事内容に基づいて最適なスタイルを決定する。

**自動選定の基準:**

| 記事の特徴 | 推奨スタイル |
|-----------|-------------|
| 副業・稼ぐ・AI活用・ノウハウ系 | **A: インパクト＆エンタメ風**（推奨デフォルト） |
| エッセイ・日常・体験談・共感系 | B: コミックエッセイ風 |
| ビジネス・技術・知見・分析系 | C: スタイリッシュ・ビジネス風 |
| 判断に迷う場合 | **A: インパクト＆エンタメ風**（最もクリック率が高い傾向） |

#### Step 4: プロンプト構築（3パターン）

選択されたスタイルに応じて、以下のテンプレートでプロンプトを構築する。
**出力サイズのアスペクト比は `1.91:1`（1280x670px相当）を必ず指定する。**

##### パターンA: インパクト＆エンタメ風（推奨デフォルト）

YouTubeサムネに近いテイスト。極太の袋文字グラデーション、集中線、賑やかな装飾。強い主張やエンタメ記事向け。

```
note header image, vibrant high-energy illustration style, maximalist composition, Japanese pop design aesthetic, high resolution. Dynamic illustration representing the core concept of {記事の内容を英語で要約}. Expressive characters or elements showing strong emotion and action. Bold, saturated colors. Dynamic gradient background with speed lines, abstract shapes, subtle sparkles, pop art feel. Huge, thick Japanese Gothic font reading "{メインタイトル}" with gradient fill, thick double outline, 3D effect popping out. Prominent subtitle text reading "{サブタイトル}" in a contrasting color ribbon or banner box. Small badge icons in the corner reading "{カテゴリ/タグ}". --ar 1.91:1
```

**プロンプト構成要素（参考）:**
- **Style:** note header image, vibrant high-energy illustration style, maximalist composition, Japanese pop design aesthetic, high resolution
- **Visual:** Dynamic illustration representing the core concept of [記事本文]. Expressive characters or elements showing strong emotion/action. Bold colors.
- **Background:** Dynamic gradient background with speed lines, abstract shapes, subtle sparkles. Pop art feel.
- **Typography & Layout:**
  - **Main Title:** Huge, thick Japanese Gothic font reading "[メインタイトル]". Gradient fill with a thick double outline. 3D effect popping out.
  - **Subtitle:** Prominent subtitle text reading "[サブタイトル]". In a contrasting color ribbon or banner box.
  - **Tags:** Small badge icons in the corner reading "[カテゴリ/タグ]".

##### パターンB: コミックエッセイ・温かいイラスト風

親しみやすい手書き線画、水彩やパステルの優しい色彩。エッセイ、日常、共感系向け。

```
note header image, gentle flat vector illustration, comic essay style, hand-drawn textures, pastel and soft colors, simple lines, warm atmosphere, high resolution. Center or right, a cute simple character or scene representing the story of {記事の内容を英語で要約}. Soft, friendly expressions. Watercolor texture overlay. Large hand-written style playful typography reads "{メインタイトル}" in dark brown or natural color. Floating organic shapes or speech bubbles containing "{サブタイトル}". Small hand-drawn tag style element containing "{カテゴリ/タグ}". --ar 1.91:1
```

**プロンプト構成要素（参考）:**
- **Style:** note header image, gentle flat vector illustration, comic essay style, hand-drawn textures, pastel and soft colors, simple lines, warm atmosphere
- **Visual:** Center/Right, a cute simple character or scene representing the story of [記事本文]. Soft, friendly expressions. Watercolor texture overlay.
- **Typography:**
  - Large hand-written style playful typography reads "[メインタイトル]" in dark brown or natural color.
  - Floating organic shapes or speech bubbles containing "[サブタイトル]".
  - Small hand-drawn tag style element containing "[カテゴリ/タグ]".

##### パターンC: スタイリッシュ・ビジネス＆インテリジェンス風

高品質な写真素材、洗練されたタイポグラフィ、美しい余白。ビジネス、技術、知見共有向け。

```
note header image, professional photography, cinematic lighting, shallow depth of field, modern minimalist layout, sophisticated editorial design, high resolution. Right side, high-quality conceptual photograph representing the topic of {記事の内容を英語で要約}. Blurred, clean background. Elegant, heavy Sans-serif or Serif typography reads "{メインタイトル}" in Gold, White, or Black. High contrast, clean layout with negative space. A clean, semi-transparent overlay box containing "{サブタイトル}". Minimalist text element for "{カテゴリ/タグ}". --ar 1.91:1
```

**プロンプト構成要素（参考）:**
- **Style:** note header image, professional photography, cinematic lighting, shallow depth of field, modern minimalist layout, sophisticated editorial design
- **Visual:** Right side, high-quality conceptual photograph representing the topic of [記事本文] (e.g., person thinking, modern desk setup, abstract tech visualization). Blurred, clean background.
- **Typography:**
  - Elegant, heavy Sans-serif or Serif typography reads "[メインタイトル]" in Gold, White, or Black. High contrast, clean layout with negative space.
  - A clean, semi-transparent overlay box containing "[サブタイトル]".
  - Minimalist text element for "[カテゴリ/タグ]".

#### Step 5: 画像生成

nanobanana-pro で画像を生成する:

```bash
cd /c/Users/baseb/dev/開発1/.claude/skills/nanobanana-pro

# ⚠️ 重要: --show-browser と --timeout 300 を必ず指定
PYTHONIOENCODING=utf-8 python scripts/run.py image_generator.py \
  --prompt "{Step 4で構築したプロンプト}" \
  --output "../../../output/note-{slug}/images/eyecatch.png" \
  --show-browser --timeout 300
```

生成後、`article.md` の冒頭にある `<!-- [EYECATCH_IMAGE: ...] -->` を以下に置換:
```
![アイキャッチ](images/eyecatch.png)
```

### デザイン品質基準

| 要素 | 基準 |
|------|------|
| Typography | 記事タイトルが読みやすく、テーマに合った美しいフォントデザイン |
| Atmosphere | 記事内容に完璧にマッチした色彩とライティング |
| Layout | 1280x670pxの横長構図を活かしたバランスの取れた構成 |
| アスペクト比 | 1.91:1（1280x670px相当）を必ず指定 |

---

## Phase 7: 統合・推敲

### 手順

1. `article.md` の全体を通読し、推敲する
2. note形式に最適化する（改行・太字・箇条書き等）
3. クロスメディア展開戦略を提案する

### note形式の最適化

- **改行**: 2〜3文ごとに空行を入れる（noteは行間が詰まりやすい）
- **太字**: 重要なポイントは `**太字**` にする
- **箇条書き**: 3つ以上の項目は箇条書きにする
- **区切り線**: セクション間に `---` を入れる
- **見出し**: `##` で大見出し、`###` で小見出し

### noteへの貼り付け手順

```
1. article.md のテキストをコピー
2. note.com で新規記事を作成
3. テキストを貼り付け
4. images/ フォルダ内の画像を、テキスト中の画像参照位置に手動で挿入
5. アイキャッチ画像を記事のアイキャッチに設定
6. プレビューで確認
```

### クロスメディア展開戦略の提案

記事完成後、以下の展開戦略を提案する:

1. **Kindle出版**: 記事を拡張して電子書籍化（ebook-creator-ssスキルで対応）
2. **SNS共有用画像**: まとめ画像をInstagram/X用に最適化

※ X投稿はPhase 7で自動生成する

---

## Phase 8: まとめ漫画生成

### 概要

記事の内容を漫画で要約し、記事の見出し画像として使用できる1ページ漫画を生成する。
ユーザー確認なしで一気に進める。

**成果物:** `images/manga_summary.png` - 記事まとめ漫画

**漫画の仕様:**
- コマ数: 3〜6コマ（記事の長さに応じて調整）
- 読み方: **右→左読み（日本式）**
- レイアウト: manga-creator-ssスキルが自動決定
- スタイル: フルカラー、Webtoon/現代漫画風

### 自動実行フロー

```
記事内容の分析
    ↓
ストーリー作成（3コマ構成）
    ↓
キャラクター設定（1〜2人）
    ↓
ページ構成・コマ詳細
    ↓
NanoBanana用プロンプト生成
    ↓
画像生成
    ↓
完成！
```

### Step 1: ストーリー作成

記事の内容を漫画のストーリーに自動変換する：

**基本構成（3〜6コマ）:**
- 起: 主人公が[記事で扱う問題]に困っている（Problem/Agitation）
- 承: [記事の解決策]を発見して目を輝かせる（Solution）
- 転: 実際に試してみる（Action）
- 結: 解決して喜ぶ「[記事のベネフィット]！」（Lead）

**コマ割りルール:**
- **右→左読み（日本式）を厳守**
- 見開きの場合：右ページ→左ページ
- 1ページの場合：右上→左上→右下→左下
- manga-creator-ssが自動的に最適なコマ割りを決定

### Step 2: キャラクター設定

記事のターゲット読者を擬人化して1人のキャラクターを作成する。

**キャラクター設定テンプレート:**
```
名前: [カタカナ3〜4文字]
年齢: [ターゲット層に合わせる]
職業: [ターゲットの職業]
性格: 好奇心旺盛、素直、頑張り屋
服装: [ターゲットに合わせたカジュアルな服装]
```

**キャラクタープロンプト形式:**
```
1girl/1boy, Japanese, [年代], [表情], [髪型・髪色], [目の色], [服装詳細], [ポーズ], anime-style, webtoon style
```

### Step 3: ページ構成

**レイアウト:** 縦長1ページ（896×1152px）、3コマ縦並び
**読み進め方:** 上から下へ（悩み→発見→解決）
**共通トーン:** anime-style, webtoon, modern manga illustration, soft light, smooth shading, delicate linework, expressive eyes, full color

**コマ構成テンプレート:**

```
●コマ1（上段・横長）
- シーン: 主人公が困っている
- 表情: 困惑、悩み、焦り
- 背景: [問題に関連する場所]
- セリフ: 「[悩みを表すセリフ]」

●コマ2（中段・横長）
- シーン: 解決策を発見
- 表情: 驚き、目がキラキラ
- 背景: [解決策に関連するビジュアル]
- セリフ: 「[発見の驚きを表すセリフ]」

●コマ3（下段・横長）
- シーン: 成功して喜ぶ
- 表情: 笑顔、ガッツポーズ
- 背景: [成功を象徴するビジュアル]
- セリフ: 「[喜びを表すセリフ]」
```

### Step 4: manga-creator-ssスキルを使用

**重要:** まとめ漫画の生成は `manga-creator-ss` スキルを使用する。
nanobanana-proを直接呼び出すことは禁止。

**実行方法:**

```bash
# Skillツールでmanga-creator-ssを呼び出す
# 3コマ構成、記事の要約ストーリーを渡す
```

**manga-creator-ssへの入力:**

```markdown
テーマ: OpenClaw入門記事のまとめ漫画（3コマ）

ストーリー:
- コマ1: [記事のProblem部分から悩みを抽出]
- コマ2: [記事のSolution部分から発見を抽出]
- コマ3: [記事のAction部分から成功を抽出]

キャラクター設定:
- 想定読者を擬人化（記事のターゲット層に合わせる）
- 親しみやすい、共感できるキャラクター

出力先: ../../../output/note-{slug}/images/manga_summary.png
ページ数: 1ページ（3コマ縦並び）
サイズ: 896×1152px
```

**注意:**
- manga-creator-ssが自動的にキャラクター設計・コマ割り・プロンプト生成を行う
- Phase 8では、manga-creator-ssに記事内容を要約して渡すだけでよい
- 手動でプロンプトを組み立てることは禁止（スキルに任せる）

### 禁止事項

- **白黒漫画は絶対禁止** - 必ずフルカラーで生成
- **セリフの省略禁止** - 記事の核心を表すセリフを必ず含める
- **確認待ち禁止** - ユーザー確認なしで一気に完成まで進める

### 実行例

```
1. 記事内容からストーリーを抽出:
   - Problem: ChatGPTのモヤモヤ（会話を忘れる、実際に動かない）
   - Solution: OpenClawの3つのスゴさ（記憶・能動性・PC操作）
   - Success: 「これなら私でもできる！」

2. manga-creator-ss スキルを呼び出し:
   - テーマ: 「OpenClaw入門記事のまとめ」
   - ページ数: 1ページ（3コマ）
   - ストーリー: 上記の3段階
   - キャラクター: 記事のターゲット読者を擬人化

3. スキルが自動実行:
   - キャラクター詳細設計
   - コマ割り・セリフ作成
   - プロンプト生成
   - nanobanana-proで画像生成

4. 完成:
   → images/manga_summary.png に保存（896×1152px）
```

### article.mdへの漫画挿入（必須）

漫画生成後、`article.md` の**先頭（アイキャッチ画像の直後）**にまとめ漫画を挿入する:

```markdown
![アイキャッチ](images/eyecatch.png){ width=100% }

![まとめ漫画](images/manga_summary.png){ width=100% }

---
```

これにより Phase 10 の DOCX変換時にも漫画が自動的に含まれる。

---

## Phase 9: X投稿文作成

### 概要

完成したnote記事から、Xでの拡散・誘導を最大化する投稿文を3パターン自動生成する。
「AI・テクノロジー界隈」で大きなインプレッションを獲得し、noteへの流入を狙う。

**成果物:** `output/note-{slug}/x_posts.md` - 3パターンのX投稿文

### 手順

1. `article.md` の全文を読み、**最も価値のあるノウハウ・具体例を1つだけ**特定する
2. 以下の4つの構成要素でX投稿文を3パターン作成する
3. `x_posts.md` として保存し、ユーザーに提示する

### 投稿文の構成要素（4つの仕掛け）

| # | 要素 | 役割 |
|---|------|------|
| 1 | **フック** | 「世間の誤解」を解く、または「最新の検証結果」で注意を引く |
| 2 | **ノウハウの「ちょい出し」** | 記事の中の最も価値のある一節や、具体的なステップを1つだけ具体的に書く |
| 3 | **ベネフィット** | それを実行することで「どうなれるか」を短く提示 |
| 4 | **クリフハンガー** | 「さらに深い手順」や「裏技」はnoteにあることを示唆し、リンクへ誘導 |

### 3パターン

| パターン | スタイル | 特徴 |
|---------|---------|------|
| **A: 衝撃・トレンド型** | 「まだ〇〇で消耗してるの？」 | 常識を覆す切り口で注意を引く |
| **B: 即実践・有益型** | 「これだけは覚えて」 | 具体的な1Tipsを教えるスタイル |
| **C: 本質・思考型** | 技術の裏側にある「考え方」 | 知的好奇心を刺激するスタイル |

### スタイルルール

- **文字数**: 140〜200文字（1ポストで完結）
- **最後に必ず `[URL]` プレースホルダー**を配置（記事公開後にURLを差し替え）
- **ハッシュタグ**: 0〜1個（最小限）
- **箇条書き・区切り線**（=== や ---）を使い視認性を高める
- **改行を多用**し、スマホで1画面に収まる「抜け感」のあるレイアウト
- **感情を揺さぶる言葉**: 「ヤバい」「怖いくらい」「保存版」等を自然に活用
- 専門用語を使いつつも「自分でもできそう」と思える平易な解説

### 出力テンプレート（x_posts.md）

```markdown
# X投稿文（note記事拡散用）

記事: {記事タイトル}
ピックアップしたノウハウ: {選定した核心ポイント}

---

## パターンA: 衝撃・トレンド型

{投稿文本文}

[URL]

---

## パターンB: 即実践・有益型

{投稿文本文}

[URL]

---

## パターンC: 本質・思考型

{投稿文本文}

[URL]
```

### 品質チェックリスト

- [ ] 140〜200文字に収まっているか
- [ ] フック → ちょい出し → ベネフィット → クリフハンガーの流れになっているか
- [ ] note記事の核心ノウハウが「ちょい出し」されているか（全部バラさない）
- [ ] 最後に `[URL]` があるか
- [ ] スマホで読みやすい改行・レイアウトか
- [ ] ハッシュタグが1個以下か

---

## Phase 10: DOCX変換（Word形式出力）

### 概要

生成したnote記事をWord形式（.docx）に変換し、画像を埋め込んだ状態で出力する。
noteへの貼り付けだけでなく、納品物やアーカイブとしても使用可能。

**成果物:** `article.docx` - 画像埋め込み済みWord形式

### 手順

1. `article.md` の最終チェック（画像パス・改ページの確認）
2. Pandoc で画像を埋め込んだ Word ファイルを作成する
3. 完成した DOCX をユーザーに通知する

### 変換前の最終チェック（必須）

DOCX変換の前に、`article.md` が以下を満たしていることを確認する:

```
チェック項目:
□ すべての画像に { width=100% } 属性が付いている
□ 画像パスが相対パス（images/xxx.png）になっている
□ すべての画像行の前後に空行が1行ずつある
□ セクション区切りに `---` が入っている
□ 見出しレベル（# ## ###）が適切か
```

不備があれば修正してから変換すること。

### 変換コマンド

```bash
cd /c/Users/baseb/dev/開発1/output/note-{slug}

pandoc article.md \
  -o article.docx \
  --from markdown \
  --to docx \
  --resource-path=. \
  --standalone \
  --dpi=150
```

### 変換後の構造

```
output/note-{slug}/
├── article.md               # Markdown版（note貼り付け用）
├── article_raw.md           # 中間ファイル（画像タグ）
├── article.docx             # ← Word版（画像埋め込み済み）
├── x_posts.md               # X投稿文
└── images/                  # 生成画像
```

### 補足

**画像サイズについて:**
- Markdownで `{ width=100% }` を付与することで、Pandocが画像をページ幅に自動フィットさせる
- `--dpi=150` で適切な解像度を指定（大きすぎるとはみ出し、小さすぎると粗くなる）
- これによりA4/B5サイズいずれでもページ内に収まる

**空行について:**
- 画像前後の空行はDOCX上で適切なスペースとして反映される
- 図と本文がくっつかず、読みやすいレイアウトになる

**その他:**
- Pandoc が `images/` フォルダ内の画像を自動で DOCX に埋め込む
- 見出し（`#` `##` `###`）は Word のスタイル（見出し1、見出し2、見出し3）に自動変換される
- DOCX を Google Drive にアップロードすれば Google ドキュメントとしても開ける
- Pandoc が未インストールの場合は `doc-convert-pandoc` スキルのセットアップ手順に従う

---

## 関連スキル

| スキル | 用途 | Phase |
|--------|------|-------|
| `mega-research` | 6API統合リサーチ | Phase 2 |
| `research-free` | APIキー不要の統合リサーチ（フォールバック） | Phase 2 |
| `nanobanana-prompts` | 画像プロンプト最適化の4つの黄金ルール | Phase 5 |
| `nanobanana-pro` | Gemini NanoBanana で画像生成 | Phase 5 |
| `doc-convert-pandoc` | Markdown → DOCX 変換 | Phase 8 |
| `note-marketing` | note記事戦略（画像なし版） | - |
| `ebook-creator-ss` | 電子書籍版（Kindle向け） | - |

## 使用例

```
/note-article 副業で月10万円稼ぐためのAI活用術
/note-article ChatGPTを使った最強の時短仕事術
/note-article 初心者でもわかるプログラミング入門
```
