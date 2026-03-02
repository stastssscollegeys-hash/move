---
name: cover-master-ss
description: Kindle電子書籍の表紙デザインYAMLプロンプトを自動生成する。ジャンルに応じて5スタイル（テキスト型/イラスト型/マンガ型/プレミアム型/ハイブリッド型）から自動選択し、NanoBanana Pro用のYAMLプロンプトをVersion A（文字入り）+ Version B（文字なし素材用）の2種同時出力する。v2.3: フラット構造・popups・sub_characters・Z-pattern・constraint最小化。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, Task
---

# Cover Master v2.3 - Kindle表紙YAMLプロンプト生成スキル

ベストセラー表紙40枚分析 + 3ペルソナディベート + Gemini技術調査 + 成功プロンプト逆算分析に基づくメタプロンプトシステム。
ジャンル自動判定 → スタイル選択 → NanoBanana Pro最適化YAMLプロンプト2種（A+B）生成 → 後工程ガイドまで一括出力。

## When to Use This Skill

- 「表紙を作って」「カバーデザイン」「Kindle表紙」
- 「表紙プロンプトを生成して」「表紙のプロンプト作って」
- 「本の表紙をデザインして」
- 「cover-master」「カバーマスター」
- ebook-creator-ss の Phase 8 で表紙作成が必要になった時

## 全体フロー

```
Step 1: ヒアリング（原稿/タイトル/ジャンル/ターゲット等）
  ▼
Step 2: 参照画像の確認（キャラ画像・漫画ページ・その他）
  ▼
Step 3: コンテンツ量ヒアリング（漫画ページ数・図解数・章数）
  ▼
Step 4: スタイル自動選択（A〜E）→ ユーザー確認
  ▼
Step 5: カラーパレット提案 → ユーザー確認
  ▼
Step 6: YAMLプロンプト生成（Version A + Version B 同時出力）
  ▼
Step 7: 出力（戦略コンセプト + YAML + 後工程ガイド）
  ▼
(任意) Step 8: nanobanana-pro で画像生成
```

---

## Step 1: ヒアリング

ユーザーに以下を確認する。すでに情報がある場合（ebook-creator-ssから呼ばれた場合等）はスキップ可。

```
こんにちは！Kindle表紙デザインの専門家です。
ベストセラーレベルの表紙を一緒に作りましょう。

以下の情報を教えてください：

1. **原稿またはタイトル**（本の内容がわかるテキスト）
2. **ジャンル**（ビジネス書/自己啓発/投資・マネー/マンガ・ラノベ/ダイエット・健康/実用書/エッセイ 等）
3. **ターゲット読者**（30代会社員、主婦、学生 など）
4. **帯に入れたいテキスト**（推薦文・実績・キャッチコピー）
5. **ブレット（見どころ3-5個）**
6. **色の好み**（あれば。なければジャンル最適色を提案します）
7. **参考にしたい表紙**（あれば画像やURLを）
```

**注意**: この段階ではまだプロンプト生成を開始しない。次のステップで画像とコンテンツ量を確認してから生成する。

---

## Step 2: 参照画像の確認

Step 1で原稿情報を受け取った後、**必ず以下を確認する**：

```
「表紙に使いたい参照画像はありますか？」

① キャラクター画像（表紙のメインキャラ）
② 漫画ページ画像（中身のコマをチラ見せ用に）
③ その他の参考画像（ロゴ、アイコン等）

→ ある場合: 画像を貼り付けてもらう
→ ない場合: テキスト情報からキャラクター/ビジュアルを生成
```

**ユーザーが画像を貼り付けたら**:
- 画像の外見を英語で詳細に記述し、プロンプトに反映する
- キャラクターのデザイン（色・形・アクセサリー等）を忠実に再現する指示を含める

### 漫画制作フローからの自動参照画像選定

**manga-produce-kobetsu-ss / manga-produce-creator-ss のStep 4から呼ばれた場合**、
以下の参照画像が自動的に利用可能になる。ユーザーに改めて貼り付けを求めず、自動で活用する。

#### A. キャラクターシート画像（必須で添付）
- `characters/{カタカナ名}.png` — キャラ個別シート（896x1200px）
- **メインキャラ + 重要サブキャラ**のシートを `--attach-image` で添付する
- キャラの外見はこのシート画像が正。テキスト描写はシートの補助として使用

#### B. 出来の良い漫画ページ（選定して添付）
- `panels/page_NNN.png` から**出来の良いページを1-2枚選定**する
- 選定基準:
  - キャラクターの描写が正確で魅力的なページ
  - 構図やカラーパレットが表紙映えするページ
  - メインキャラが大きく描かれているページ
- 選定した漫画ページを `--attach-image` で添付し、プロンプトに以下を追加:
  ```
  The attached manga pages show the actual art style and quality of the manga content.
  The cover MUST match this art style, color palette, and character rendering quality.
  ```
- **添付画像の合計は4-5枚まで**（キャラシート2-3枚 + 漫画ページ1-2枚 が目安）

#### C. キャラクター外見テキスト（プロンプトに埋め込み）
- `character_prompts.md` からキャラの英語外見テキストを取得
- YAMLプロンプトの `main_character.description` に埋め込む

---

## Step 3: コンテンツ量ヒアリング

参照画像の確認後、**本の中身のボリュームを確認する**：

```
「本の中身について教えてください（表紙のバッジや帯に反映します）」

① 漫画は何ページ分ありますか？（例: 100ページ、なし）
② 図解・イラストは何枚ありますか？（例: 50枚、なし）
③ チャート・表・ダイアグラムは何個ありますか？（例: 20個、なし）
④ 全体で何章構成ですか？（例: 全10章）
⑤ 総ページ数は？（任意）
```

### 取得した情報の表紙への反映方法

| コンテンツ量 | 表紙での表現例 | 配置箇所 |
|-------------|---------------|---------|
| 漫画100P超 | 「漫画100ページ超！」 | ポップアップバッジ or 帯 |
| 図解50枚 | 「図解50枚で理解度UP」 | ブレットポイント or 帯 |
| チャート20個 | 「チャート＆表20個収録」 | ブレットポイント |
| 全10章 | 「全10章でマスター」 | ポップアップバッジ |
| 総300P | 「大ボリューム300P」 | 帯の追加テキスト |

### 自動バッジ生成ルール

- 漫画ページ数が50以上 → バッジ候補に「漫画{N}P超！」を追加
- 図解・イラスト数が20以上 → ブレット候補に「図解{N}枚収録」を追加
- 章数が指定されている → バッジ候補に「全{N}章」を追加
- ユーザー指定バッジが優先。自動提案は候補として提示し、採用はユーザーが決める

---

## Step 4: スタイル自動選択

ユーザーの入力からジャンルを分析し、以下の5スタイルから最適なものを**自動選択**する。

| スタイル | 名称 | 最適ジャンル | 特徴 |
|----------|------|-------------|------|
| **A** | テキストインパクト型 | ビジネス書、自己啓発、話し方系 | 単色背景＋超大文字。シンプルで権威的 |
| **B** | イラスト＋テキスト型 | 実用書、健康、料理、趣味 | シンプルイラスト＋明瞭テキスト。親しみやすい |
| **C** | マンガ・アニメ型 | マンガ解説、ラノベ、AI/テック系 | キャラ中心＋パネル＋吹き出し。情報量多い |
| **D** | ダーク・プレミアム型 | 投資、戦略、経営、金融 | 暗色背景＋金/白文字。高級感と権威性 |
| **E** | ハイブリッド型 | 副業、ChatGPT系、入門書 | 上半分テキスト＋下半分帯域。情報整理型 |

### 自動選択ロジック

```
ビジネス/自己啓発/話し方/時間術 → A
料理/健康/ダイエット/生活改善/趣味 → B
マンガ解説/AI活用/テック入門/ラノベ → C
投資/金融/経営戦略/不動産 → D
副業/ChatGPT×副業/〇〇入門/ハウツー → E
恋愛小説/エッセイ → B or ヒアリング
```

選択後、AskUserQuestionで確認：
- 「スタイル[X]（名称）が最適と判断しました。[理由]。よろしいですか？」
- 別スタイルの選択肢も提示する

---

## Step 5: カラーパレット提案

ジャンルとスタイルに基づいて**3色のカラーパレット**を提案する。

| ジャンル | メイン | アクセント | ハイライト |
|---------|--------|----------|-----------|
| ビジネス | #FFFFFF 白 | #1A1A2E 紺 | #E74C3C 赤 |
| 自己啓発 | #FFF3CD 薄黄 | #E74C3C 赤 | #FFD700 金 |
| 投資・マネー | #1B2A4A 紺 | #D4AF37 金 | #FFFFFF 白 |
| 健康・ダイエット | #E8F5E9 薄緑 | #FF6B6B ピンク | #2E7D32 緑 |
| AI・テック | #1A73E8 青 | #FFD700 金 | #FF5252 赤 |
| 副業・稼ぐ系 | #FFF9C4 黄 | #1565C0 紺 | #FF5722 オレンジ |
| マンガ・ラノベ | コンテンツ依存 | コンテンツ依存 | #FFD700 金 |

ユーザーの好みがあればそちらを優先。なければ上記を提案してAskUserQuestionで確認。

---

## Step 6: YAMLプロンプト生成

以下のテンプレートにユーザー情報を埋め込み、**Version AとVersion Bの2つを同時に出力**する。

### 設計原則（v2.3 / 成功プロンプト逆算）

```
┌─────────────────────────────────────────────────────────────┐
│  1. フラット構造: text_elements に全テキストを集約           │
│  2. 簡潔記述: 1要素 = 2-3行。7プロパティに分解しない        │
│  3. 自然言語: Geminiは自然な文章の方が理解しやすい           │
│  4. constraint最小: 本当に重要な4-5個だけ                    │
│  5. popups: 吹き出し型の動的テキストで会話感を出す           │
│  6. Zパターン: 視線誘導を明示する                            │
│  7. 情報密度宣言: extremely high information density          │
│  8. 複数キャラ対応: メイン＋サブキャラの賑わい感              │
└─────────────────────────────────────────────────────────────┘
```

---

### Version A テンプレート（文字入り）

```yaml
# Kindle表紙 - {title} [文字入り・完全版]
# NanoBanana Pro YAML prompt / テキスト焼き込みあり

type: professional Kindle e-book cover design with Japanese text
quality: award-winning book cover, print-ready, 書店のベストセラー棚クオリティ
orientation: portrait 2:3 aspect ratio
importance: MUST be VERTICAL book cover layout, extremely high information density

# === テキスト配置 / Text Rendering ===
# ※ 全テキスト要素をここに集約（タイトル・帯・ブレット・バッジすべて）
text_elements:
  top_shout:
    text: "{キャッチフレーズ}"
    position: "top left area, angled 15 degrees"
    style: "{バナースタイル - 例: red background banner with white bold text}"
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
    font_size: "medium-small, highly readable"
    color: "{テキスト色}"

  bullet_points:
    text_list: ["{ポイント1}", "{ポイント2}", "{ポイント3}", "{ポイント4}"]
    position: "{配置}"
    style: "numbered list with glowing checkmarks"
    font_size: "medium-small"
    color: "{テキスト色}"

  obi_section:
    catchcopy: "{帯コピー}"
    position: "bottom 15% of cover"
    style: "vibrant {帯色} horizontal band, mimicking a physical book's belly band"
    color: "{テキスト色 on 帯背景色}"

  badge:
    text: "{バッジテキスト - 例: 全10章}"
    position: "bottom-right corner on the obi"
    style: "circular {バッジ色} sticker badge"
    color: "{テキスト色 on バッジ背景色}"

# === メインビジュアル / Main Visual ===
main_visual:
  concept: "{ビジュアルコンセプト JP+EN}"

  main_character:
    description: "Based on '{キャラ名}' from uploaded images: {1-2行の簡潔な外見記述}"
    position: "{配置}"

  sub_characters:
    description: "{サブキャラの簡潔な記述。なければこのセクション削除}"

  manga_element:
    description: "{漫画ページの使い方}"

  popups:
    - text: "{吹き出し1 - キャラの台詞や訴求}"
      style: "speech bubble next to {キャラ名}"
    - text: "{吹き出し2}"
      style: "impactful graphic bubble"

# === 構図と配色 / Composition & Colors ===
composition:
  layout: "Z-pattern layout. {視線誘導の説明}"
  background:
    base: "{背景色}"
    effects: ["{エフェクト1}", "{エフェクト2}"]

colors:
  primary: "{#HEX 色名}"
  accent: "{#HEX 色名}"
  highlight: "{#HEX 色名}"

# === 制約 / Constraints ===
constraints:
  - "Text MUST be clearly readable in Japanese"
  - "Character MUST look like the '{キャラ名}' provided in reference images"
  - "The obi band at the bottom MUST look like a separate layer/material"
  - "Ensure high contrast for the title to be readable at thumbnail size"
```

---

### Version B テンプレート（文字なし / 素材用）

```yaml
# Kindle表紙 - {title} [文字なし / 素材用]
# NanoBanana Pro YAML prompt / テキスト焼き込みなし

type: professional Kindle e-book cover design, clean illustration asset without any text
quality: award-winning book cover quality, 書店のベストセラー棚クオリティ
orientation: portrait 2:3 aspect ratio
importance: MUST be VERTICAL book cover layout

# === テキスト域 / Text Zones (空白確保) ===
text_zones:
  title_zone:
    area: "top 25% of cover"
    instruction: "clean open space for title overlay"
  info_zone:
    area: "{ブレット配置予定エリア}"
    instruction: "slightly dimmed area for text overlay later"
  obi_zone:
    area: "full width band at bottom 15%"
    instruction: "dimmed horizontal band for obi text overlay"
  badge_zone:
    area: "{バッジ配置予定エリア}"
    instruction: "small clean area for badge overlay"

# === メインビジュアル / Main Visual ===
main_visual:
  concept: "{Version Aと同一の世界観}"

  main_character:
    description: "Based on '{キャラ名}' from uploaded images: {Version Aと同一の記述}"
    position: "{配置}"

  sub_characters:
    description: "{Version Aと同一}"

  manga_element:
    description: "{Version Aと同一}"

# === 構図と配色 / Composition & Colors ===
composition:
  layout: "{Version Aと同じレイアウト構成、テキストなし}"
  background:
    base: "{Version Aと同一}"
    effects: ["{Version Aと同一}"]

colors:
  primary: "{#HEX}"
  accent: "{#HEX}"
  highlight: "{#HEX}"

# === 制約 / Constraints ===
constraints:
  - "DO NOT include any readable text, letters, numbers, or characters anywhere"
  - "Character MUST look like the '{キャラ名}' provided in reference images"
  - "Top 25% MUST be clean open space for title overlay"
  - "Bottom 15% should be slightly dimmed for obi overlay"
  - "This is a DESIGN ASSET - all text will be added later in Canva/Figma"
```

---

## Step 7: 出力フォーマット

以下の形式でユーザーに提出する：

```
━━━ 表紙プロンプト生成結果 ━━━

■ 選択スタイル: [X] - [名称]
■ カラーパレット: [メイン] / [アクセント] / [ハイライト]
■ キャラクター: [メインキャラ名] (+サブキャラ名)
■ 参照画像: キャラ画像 [あり/なし] / 漫画ページ [あり/なし]
■ コンテンツ量: 漫画[N]P / 図解[N]枚 / 全[N]章

━━━ Version A（文字入り） ━━━
{YAMLプロンプト全文}

━━━ Version B（文字なし / 素材用） ━━━
{YAMLプロンプト全文}

━━━ 後工程ガイド（Version B用） ━━━

テキスト配置マップ:
┌──────────────────────────────┐
│ [タイトルゾーン]    top 25%  │ ← メインタイトル + サブタイトル
│  ゴシック体太字、画像幅60-80% │    発光エフェクト推奨
├──────────────────────────────┤
│ ★ブレット  │ [キャラ]       │ ← 左: 見どころリスト
│ ★ポイント  │  +             │    右: キャラ+漫画プレビュー
│ ★リスト    │ [漫画ﾍﾟｰｼﾞ]   │
├══════════════════════════════┤
│ ▓▓▓ 帯（おび）▓▓▓          │ ← 帯コピー（全幅バンド）
│  キャッチコピー + 著者名     │    アクセント色背景
├──────────────────────────────┤
│ [フッター] ○バッジ          │ ← バッジ（右下）
└──────────────────────────────┘

推奨フォント:
- タイトル: Noto Sans JP Black / 源ノ角ゴシック Heavy
- サブタイトル: Noto Sans JP Bold
- キャッチコピー: Noto Sans JP Bold
- 著者名: Noto Sans JP Regular

推奨ツール: Canva / Figma / Photoshop
```

---

## Step 8: 画像生成（任意）

ユーザーが希望すれば、nanobanana-proスキルで画像を生成する。

- **参照画像がある場合**: NanoBanana Proに参照画像も一緒に添付して生成
- Version A → 文字入り画像を生成
- Version B → 素材画像を生成
- 両方生成することも可能

### 生成前の注意
- ユーザーにGeminiログイン確認を求める
- 思考モードが有効か確認を推奨
- 生成結果が気に入らない場合は、プロンプトを微調整して再生成

### 参照画像の添付方法（--attach-image）

nanobanana-proで画像生成する際、参照画像がある場合は `--attach-image` で添付する。
これによりGeminiがキャラクターの外見やアートスタイルを正確に再現できる。

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

# 漫画制作フローからの場合（キャラシート + 漫画ページを添付）
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{YAMLプロンプト全文}" \
  --attach-image "../../../output/manga-{slug}/characters/{メインキャラ名}.png" \
  --attach-image "../../../output/manga-{slug}/characters/{サブキャラ名}.png" \
  --attach-image "../../../output/manga-{slug}/panels/{出来の良いページ}.png" \
  --output "../../../output/manga-{slug}/cover.png" \
  --timeout 360

# 一般的な場合（ユーザー提供の参照画像を添付）
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{YAMLプロンプト全文}" \
  --attach-image "{参照画像パス}" \
  --output "../../../output/ebook-{slug}/images/cover.png" \
  --timeout 360
```

**添付画像の上限**: 合計4-5枚まで（バッチアップロードで一括送信）

---

## スタイル別プロンプト構築ガイド

### スタイルA: テキストインパクト型

Version Aで以下を適用：
- `top_shout`: 小さめカテゴリラベル
- `main_title`: 超巨大テキスト、画面の主役
- `background.base`: 単色、クリーンな背景
- `main_visual`: イラストなし。背景テクスチャのみ
- `popups`: 不要
- `constraints`: テキストコントラスト重視

### スタイルB: イラスト＋テキスト型

Version Aで以下を適用：
- `main_visual.main_character`: シンプルフラットイラスト or 線画
- `background.base`: 明るく温かみのある色
- `popups`: キャラの一言（任意）
- `manga_element`: 不要
- ムード: 親しみやすい、ガイドブック風

### スタイルC: マンガ・アニメ型

Version Aで以下を適用：
- `main_visual.main_character`: ダイナミックなアニメ風キャラ
- `sub_characters`: サブキャラで賑わい感
- `manga_element`: 漫画ページのチラ見せ
- `popups`: キャラの台詞吹き出し（必須）
- `background.effects`: 集中線、エネルギーパーティクル
- 情報密度: 最大

### スタイルD: ダーク・プレミアム型

Version Aで以下を適用：
- `background.base`: ダークカラー（紺・黒）
- `main_title.color`: 金 or 白
- `main_visual`: 抽象的グラフィックのみ（キャラなし）
- `obi_section`: 控えめだが高級感のある帯
- `popups`: 不要
- ムード: 権威的、プレミアム

### スタイルE: ハイブリッド型

Version Aで以下を適用：
- 上半分: テキスト中心（メイン色背景）
- 下半分: ビジュアル中心（アクセント色帯）
- 視覚的分割線（斜め or 波形）
- `badge`: 右下に丸型バッジ
- ムード: 情報整理型、信頼感

---

## YAMLプロンプト品質ルール

### プロンプト構築ルール
1. **YAML形式**: Geminiはコード学習済みモデルのため構造化データの理解が深い
2. **日本語+英語ミックス**: 日本語でコンテキスト補強 + 英語で技術指示
3. **ALL CAPSで強調**: `MUST`, `DO NOT` を適切に使用（乱用しない）
4. **色はHEX値+色名**: `#1A73E8 blue` のように両方記載
5. **自然言語で書く**: タグ列挙ではなく簡潔な文章で描写
6. **品質アンカー**: `award-winning`, `professional`, `print-ready` を含める
7. **portrait 2:3**: Kindle縦長比率を明示

### ビジュアル記述ルール
1. **キャラクターは1-2行の自然な文章**で描写（expression/pose/accessories等に分解しない）
2. **サブキャラクターを活用**: 賑わい感を出す。不要なら省略
3. **popups（吹き出し）を活用**: キャラの台詞や訴求ポイントを会話形式で配置
4. **漫画要素は1行で**: `stylized excerpt integrated as background panels` 程度で十分
5. **背景+エフェクトは2個まで**: 過剰指定するとGeminiが全部中途半端になる

### constraint（制約）ルール
1. **最大5個**: 本当にGeminiが間違えやすいことだけ
2. 「テキストが読めること」「キャラの再現」「帯の質感」「サムネイル視認性」が核
3. DON'Tの羅列は避ける

### Kindleサムネイル最適化
1. **50px幅で構造が識別できること**
2. **タイトルが最も目立つこと**
3. **白い表紙は避ける**（Kindleストアの白背景に溶ける）

### 参照画像の記述ルール
- 添付画像を見て、外見・色・構図を**英語で**簡潔に描写する（1-2行）
- 「from uploaded images」「provided in reference images」で参照を明示
- キャラデザインを勝手に変えない（参照画像が正）

---

## 絶対に守るルール

1. **ユーザーのタイトル・コピーを勝手に変えない**
2. **キャラクター外見は添付された参照画像が正**（勝手にデザイン変更しない）
3. **Version AとBは必ずセットで出力**
4. **プロンプトはYAML形式**（散文形式にしない）
5. **色のHEX値は必ず含める**
6. **後工程ガイドをVersion Bに添える**
7. **1要素の記述は2-3行に収める**（過剰なプロパティ分解は禁止）
8. **constraintは5個以内**（本当に重要なものだけ）

---

## 複数バリエーション対応

ユーザーが希望すれば「3パターン出しましょうか？」と提案可能：
- 最適スタイル + 別スタイル2つ
- 同スタイルで色パレット違い3パターン

---

## 関連スキル

| スキル | 連携 |
|--------|------|
| `nanobanana-pro` | 画像生成の実行 |
| `nanobanana-prompts` | プロンプト最適化の参考 |
| `ebook-creator-ss` | Phase 5.5で本スキルを呼び出し |
| `ebook-listings-ss` | Kindleメタデータ生成 |

## 使用例

```
「Kindle表紙を作りたい」
「この本の表紙プロンプトを生成して」
「マンガ風の表紙デザインをお願い」
「ビジネス書っぽい高級感のある表紙にしたい」
「cover-master で表紙作って」
```
