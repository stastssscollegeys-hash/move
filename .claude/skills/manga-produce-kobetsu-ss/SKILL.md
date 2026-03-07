---
name: manga-produce-kobetsu-ss
description: 電子書籍を漫画化することに特化したスキル（キャラ個別シート版）。章構成を解析し、各章3-5ページの漫画を生成。キャラごとに個別シートを作成し、ページごとに該当キャラのシートを添付して一貫性を確保。
---

# Manga Produce Kobetsu - 書籍漫画化特化スキル（キャラ個別シート版）

電子書籍 → 章ごと解析 → 重要ポイント抽出 → キャラ個別シート作成 → 漫画化（各章3-5ページ）。

## When to Use This Skill

- **「書籍を作った後に漫画作りたい」と言われた時**
- 「電子書籍を漫画化して」
- 「この本を漫画で分かるようにして」
- 「各章を漫画にして」
- ebook-creator-ss で作成した書籍の漫画化

## Do NOT Use for

- ゼロから漫画を作る → `manga-creator-ss` を使用
- 単発の漫画パネル1枚 → `nanobanana-pro` を使用
- キャラクターシートのみ → `custom-character` を使用
- アニメ動画制作 → `anime-production` を使用
- CSV形式で出力したい → `comicle-ss` を使用

## 📚 書籍漫画化の特化機能

### 1. 章ベースの構成
- 原稿に含まれる**各章を対象**とする
- 章タイトル（`## 第N章`）を自動検出
- 各章を独立した漫画シーンとして構成

### 2. ページ数の最適化
- **各章につき3-5ページ程度**の漫画を作成
- 全5章なら合計15-25ページ
- 章の長さに応じて3-5ページの範囲で調整

### 3. 重要ポイントの抽出
- 章全体の内容を、**重要度に応じて取捨選択**して構成してよい
- **すべてを網羅する必要はない**
- **章の主旨が伝わることを最重視**
- 具体例・エピソード・数字など、インパクトのある部分を優先

### 4. 教育的な内容の漫画化
- ビジネス書・ハウツー本など、教育的内容を分かりやすく
- データ・図解を漫画のコマに組み込む
- 「解説役」と「学ぶ役」の対話形式で構成

## 参考フォルダ

テンプレート画像やリファレンス画像は以下に格納:

```
.claude/shared/manga-templates/
├── テンプレ1.jpg     # テンプレ1: ページ全体を使った1コマ
├── テンプレ2.jpg     # テンプレ2: 上下2分割（上段→下段）
├── テンプレ3.jpg     # テンプレ3: 上下2分割（上段小→下段大）
├── テンプレ4.jpg     # テンプレ4: 上下2分割（上段大→下段小）
├── テンプレ5.jpg     # テンプレ5: 上・中・下の3段構成
├── テンプレ6.jpg     # テンプレ6: 上段1コマ+下段左右2コマ
├── テンプレ7.jpg     # テンプレ7: 上段左右2コマ+下段1コマ
├── テンプレ8.jpg     # テンプレ8: 上段横長+中段左右+下段横長
├── テンプレ9.jpg     # テンプレ9: 上段横長+下段右縦長+左上下分割
└── テンプレ10.jpg    # テンプレ10: 上段横長+下段左縦長+右上下分割
```

## 全体フロー（5ステップ + 画像生成）

**前提: ebook-creator-ss が先に `output/{slug}/` フォルダを作成済み。**
**本スキルは同じフォルダに漫画関連ファイルを追加していく。**

```
Step 1: ストーリー構成案の作成
   │  ユーザーから原稿/文章を受け取る（必須）
   │  ★ 元原稿は output/{slug}/manuscript.md にある
   │  神話の法則で感情曲線設計
   │  書籍の長さに合わせたコマ数で細かいカット割り台本作成
   │  → 確認なしで即Step 2へ
   ▼
Step 2: キャラクター設計画（個別シート方式）
   │  2回以上登場する全キャラの設計画プロンプトを作成
   │  ★ キャラ1人につき1枚の個別シート画像を生成
   │  ★ ファイル名はキャラのカタカナ名（例: ケイコ.png）
   │  ★ サイズは896x1200px（漫画ページと同じ）
   │  各キャラの外見プロンプトテキストをDBとして保存
   │  → 確認なしで即Step 3へ
   ▼
Step 3: ページ別プロンプト生成
   │  各ページのNanoBanana用プロンプトを英語で作成（セリフ部分のみ日本語）
   │  ★ キャラ参照は「MUST match the character in attached '{カタカナ名}.png'」方式
   │  全ページ分を一括出力
   │  → 確認なしで画像一括生成へ
   ▼
画像一括生成:
   │  nanobanana-pro で全ページ順次生成
   │  各ページで登場キャラの個別シート画像を --attach-image で添付
   │  生成後 896x1200px にリサイズ
   │  進捗トラッキング + 中断再開対応
   ▼
Step 4: 表紙作成（cover-master-ss 連携）
   │  漫画ページ完成後、ユーザーに表紙作成を確認
   │  cover-master-ss スキルを呼び出し
   │  ★ 個別キャラシート画像を参照画像として自動提供
   │  ★ メインキャラのシートをcover-master-ssのStep 2に渡す
   │  キャラクターの外見情報をcover-master-ssに引き継ぎ
   ▼
Step 5: DOCX統合（原稿+漫画ページの統合Word）
   │  元の電子書籍原稿（manuscript.md）を読み込み
   │  各章の末尾に対応する漫画ページを挿入
   │  Pandoc で原稿テキスト+漫画統合DOCXに変換
   │  final_book.docx として出力
   ▼
完成！
```

### キャラクター一貫性の確保方法

**個別キャラシート + テキスト埋め込みの併用で一貫性を最大化する:**

#### 1. 個別キャラシート画像の添付（`--attach-image`）
- Step 2でキャラ1人につき1枚のキャラクターシート画像を生成する
- ファイル名はカタカナ名（例: `ケイコ.png`, `アカリ.png`）
- 画像生成時に、そのページに登場するキャラの個別シート画像を `--attach-image` で添付する
- テキストだけでは回を重ねるうちにキャラの外見がブレるため、画像参照で補強する

#### 2. テキスト埋め込み（必須）
- Step 2で各キャラの外見プロンプト（英語テキスト）を定義する
- Step 3のプロンプトで、登場キャラの外見テキストを毎回埋め込む
- `(MUST match the character in attached '{カタカナ名}.png')` と記載し、どのキャラ画像を参照するか明示する

**注意:** `--reference-image` はスタイル抽出用（YAML分析→メタプロンプト生成）であり、キャラクター一貫性には使えない。`--attach-image` を使うこと。

---

## Step 1: ストーリー構成案の作成（書籍特化版）

### 最初に必ずやること

**ユーザーに原稿/文章の添付を求める。**

```
書籍を漫画化します。まず原稿（テキストまたはファイル）を添付してください。
各章を解析し、重要ポイントを抽出して漫画化します。
```

### 📚 書籍漫画化のストーリー構成ルール

1. **章ベースで構成**: `## 第N章` を検出し、各章を独立したシーンとして扱う
2. **各章3-5ページ**: 章の長さ・重要度に応じて3-5ページ（12-20コマ）で構成
3. **重要ポイント優先**: 章の主旨が伝わる重要な部分を抽出し、細部は省略してOK
4. **具体例を活用**: 数字・エピソード・実例など、インパクトのある部分を漫画化
5. **対話形式**: 解説役（先生）と学ぶ役（主人公）の会話で展開
6. **図解をコマに**: 原稿内の図解・データは漫画のコマとして視覚化

### 章ごとのページ配分ガイドライン

| 章の特徴 | ページ数 | 理由 |
|---------|---------|------|
| 導入章（第1章など） | 4-5ページ | 読者の共感を得る、世界観の提示が重要 |
| 具体例が多い章 | 5ページ | 実例・エピソードは漫画向き |
| 手順・ステップ系の章 | 3-4ページ | リスト形式は簡潔に |
| まとめ・結論の章 | 3ページ | 要点を凝縮 |

### 取捨選択の基準

**漫画化すべき内容（優先度高）:**
- 読者の悩み・共感ポイント
- 具体的な数字・報酬例
- 実績者のエピソード
- ビフォーアフターの対比
- 驚きや発見の瞬間

**省略してよい内容:**
- 細かい補足説明
- 繰り返しの内容
- 抽象的な理論
- 詳細なリスト（要点のみ抽出）

### コマ分割テクニック（必須遵守）

- **会話の1往復**（Aが話す→Bが話す）でページを分ける
- **3行以上の長ゼリフ**は、文節や句読点でページを分割する
- **「驚き」「沈黙」「強調」**などのリアクション単体で1ページ使う
- 場面転換、時間経過、視点変化でもページを分ける

### 📚 書籍漫画化の手順

1. **章構成の解析**
   - `## 第N章` のタイトルを抽出
   - 各章の小見出し（`### N.N`）も確認
   - 章ごとの文字数・内容量を把握

2. **重要ポイントの抽出**
   - 各章から、以下を優先的に抽出:
     - 読者の悩み・共感ポイント
     - 具体的な数字・報酬例
     - 実績者のエピソード
     - ビフォーアフター
     - 驚きや発見の瞬間
     - アクションステップ

3. **ページ配分の決定**
   - 全章数を確認
   - 各章3-5ページで配分
   - 重要な章は5ページ、まとめ章は3ページなど調整

4. **漫画シーンへの変換**
   - 抽出したポイントを漫画の「シーン」として構成
   - 対話形式で展開（主人公が学ぶ、先生が教える）
   - データや図解は漫画のコマとして視覚化

### 出力形式

`output/{slug}/story_structure.md` に保存:

```markdown
# 漫画ストーリー構成案（全{N}ページ）

タイトル：{書籍タイトル}

**原稿の章構成:**
- 第1章: {タイトル} → 漫画{X}ページ
- 第2章: {タイトル} → 漫画{Y}ページ
- 第3章: {タイトル} → 漫画{Z}ページ
...

**ページ配分の理由:**
{なぜこの配分にしたか、各章の重要度を簡潔に説明}

---

## シーン1：{第1章のタイトル}（ページ1〜{N}）

**原稿の要点:**
{第1章から抽出した重要ポイント}

**漫画化方針:**
{どのように漫画化するか。対話形式、ビフォーアフターなど}

場所：{場所}
登場人物：{キャラ名一覧}

**ページ1**
コマ1：{場面の詳細な描写。キャラの行動、表情、背景を具体的に記述。}
コマ2：{次のコマ。前のコマからの自然なつながりを明記。}
コマ3：{キャラ名}「{セリフ原文}」{キャラの動作や表情の補足}
コマ4：{リアクション。驚きの表情のアップなど。}「{セリフ}」

**ページ2**
...

## シーン2：{第2章のタイトル}（ページ{N+1}〜{M}）
...

（最後のページまで全て記述）
```

---

## Step 2: キャラクター設計画（個別シート方式）

### 概要

2回以上登場する**全キャラクター**について:
1. **キャラ1人につき1枚**のキャラクターシート画像を生成する
2. ファイル名は**カタカナ名**（例: `ケイコ.png`, `アカリ.png`）
3. **サイズは896x1200px**（漫画ページと同じサイズ）
4. 各キャラの外見プロンプトテキスト（英語）をDBとして保存する（Step 3で使用）
5. キャラクター名は毎回新規で考えること

### 個別キャラクターシート画像プロンプト

キャラクター1人につき1枚のシートを作成する。
内容: 全身の立ち姿で正面、側面、背面からみたキャラクター。キャラクターの足元に対応する名前（カタカナ）が記載されている。

```
({カタカナ名}): (best quality, masterpiece:1.2), anime style, character sheet,
multiple views, full body, front view, side view, back view,
white background, flat color, resolution 896x1200px,
{性別・年齢・外見詳細を英語で},
katakana name "{カタカナ名}" written at feet
```

**プロンプト例:**

```
(ケイコ): (best quality, masterpiece:1.2), anime style, character sheet,
multiple views, full body, front view, side view, back view,
white background, flat color, resolution 896x1200px,
1woman, Japanese, 49 years old, soft facial features, black hair in a low bun,
wearing a simple mint green cardigan over a white blouse, long brown skirt,
gentle and warm smile, modest housewife,
katakana name "ケイコ" written at feet
```

```
(アカリ): (best quality, masterpiece:1.2), anime style, character sheet,
multiple views, full body, front view, side view, back view,
white background, flat color, resolution 896x1200px,
1girl, Japanese, 20 years old, cheerful expression, shoulder-length brown hair with bangs,
wearing a casual hoodie and jeans, energetic and youthful appearance,
katakana name "アカリ" written at feet
```

### キャラクター外見プロンプトDB

各キャラの外見テキスト（英語）を `character_prompts.md` に保存する。
これがStep 3で毎回プロンプトに埋め込まれるマスターデータになる。

**注意: 以下はフォーマット例です。実際のキャラクターは書籍のテーマ・世界観に合わせて毎回新しく設計してください。前回のプロジェクトのキャラを引き継がないこと。**

```markdown
# キャラクター外見プロンプトDB

## ケイコ（主人公）
1woman, Japanese, 49 years old, soft facial features, black hair in a low bun,
wearing a simple mint green cardigan over a white blouse, long brown skirt,
gentle and warm smile, modest housewife
→ ファイル名: ケイコ.png

## アカリ（主人公の娘）
1girl, Japanese, 20 years old, cheerful expression, shoulder-length brown hair with bangs,
wearing a casual hoodie and jeans, energetic and youthful appearance
→ ファイル名: アカリ.png

## {マスコット名}（マスコット）
{テーマに合ったマスコットの外見。書籍の題材に関連するデザインにする}
→ ファイル名: {マスコット名}.png
```

### 画像生成（キャラごとに1回ずつ実行）

**重要：相対パスは `../../../` で開発フォルダのルートに戻ること。**
nanobanana-proは `開発1/.claude/skills/nanobanana-pro/` にあるので、`../../` だと `.claude/` で止まる。`../../../` で正しく `開発1/` に到達する。

**キャラごとに個別に実行する:**

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

# キャラ1: ケイコ
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{ケイコのキャラクターシートプロンプト}" \
  --output "../../../output/{slug}/characters/ケイコ.png" \
  --timeout 240

# キャラ2: アカリ
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{アカリのキャラクターシートプロンプト}" \
  --output "../../../output/{slug}/characters/アカリ.png" \
  --timeout 240

# ... 全キャラ分繰り返す
```

### リサイズ（生成後必須）

リサイズはファイルのある場所にcdしてから実行する（日本語パスの文字化け回避）。
**各キャラシートを896x1200pxにリサイズする。**

```bash
cd "{開発フォルダ}/output/{slug}/characters"

# キャラごとにリサイズ
for charfile in ケイコ.png アカリ.png; do
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
    "../../../.claude/skills/nanobanana-pro/.venv/Scripts/python.exe" -c "
from PIL import Image
img = Image.open('$charfile')
img = img.resize((896, 1200), Image.LANCZOS)
img.save('$charfile')
print('Resized $charfile to 896x1200')
"
done
```

---

## Step 3: ページ別プロンプト生成

### 概要

Step 1のストーリーを元に、各ページのNanoBanana用プロンプトを作成する。
プロンプトは**英語**で記述し、**セリフ・文字入れ部分のみ日本語**を含める。
**★ キャラの外見テキストはStep 2のDBから毎回同じものを埋め込む（一貫性確保の要）。**
**★ キャラ参照は個別シート画像を指定する（`MUST match the character in attached '{カタカナ名}.png'`）。**

**📚 書籍漫画化の重要ルール:**
- **全ページ分のプロンプトを必ず最後まで作成する**
- サンプルだけで終わらない（「残りも作成しますか？」と聞かない）
- Step 1で決めたページ数（15〜25ページ）すべてを完成させる
- 途中で確認を求めず、一気に全ページ分を出力する

全ページ分を `output/{slug}/page_prompts.md` に一括出力する。

### プロンプトテンプレート

```markdown
### Page {N}

**Page layout**
{ページ全体のシーン・感情の流れを英語で自然な文章で表現。
各コマがどのように展開・対比・連続しているかを簡潔かつ詳細にまとめる。}
**Reading order: Right-to-left (Japanese manga style)** ← 必須記載
Template: {テンプレ1〜10から選択}

---
重要: Panel番号は読む順番（1→2→3→4）。
横並びコマの場合、Panel1=右側、Panel2=左側。
---

**Panel1** ← 読む順番の1番目（横並びなら右側のコマ）
**Description** {シーンの説明を英語で}
**panel shape and size** {horizontal-large / vertical-medium / square-small 等}
**panel position** {top / middle-right / middle-left / bottom 等、コマの位置を明記}
**Character name & details** {キャラ名} — {★Step 2のDBの外見テキストをそのまま埋め込む}, (MUST match the character in attached '{カタカナ名}.png')
**Character expression** {表情を英語で}
**Character facing** {facing left / facing right / front}
**Character pose** {ポーズを英語で}
**Background** {背景を英語で}
**speech bubble** 「{日本語セリフそのまま}」
  ⚠️  1コマに複数の吹き出しがある場合の順序（厳守）:
  - 右側の吹き出しが最初（speech bubble 1）
  - 左側の吹き出しが次（speech bubble 2）
  - 例: speech bubble 1 (right side): 「右のセリフ」, speech bubble 2 (left side): 「左のセリフ」
  - 2人の会話の場合: 右側のキャラのセリフ → 左側のキャラのセリフ
**camera angle** {eye-level / top-down / low-angle / side view}
**art style** anime-style, modern manga illustration, soft light and smooth shading, delicate linework, expressive eyes, clean and bright overall tone, --ar 3:4
**color theme** {配色を英語で}

**Panel2** ← 読む順番の2番目（横並びなら左側のコマ）
**panel position** {位置を明記}
...
```

**注意（縦長生成の保証 — 必須）:**
- プロンプトの**先頭**に以下のブロックを必ず挿入すること：
  ```
  --ar 3:4 MUST generate in PORTRAIT orientation (taller than wide, 3:4 ratio). DO NOT use landscape.
  ```
- プロンプトの**末尾**にも `--ar 3:4` を含めること（二重保証）

**注意（キャラクター一貫性 + アートスタイル統一の保証 — 必須）:**
- プロンプトの**先頭**（`--ar 3:4` の直後）に以下のブロックを必ず挿入すること：
  ```
  CRITICAL CHARACTER REFERENCE: The attached images are the official character reference sheets. You MUST faithfully reproduce each character's appearance exactly as shown in their respective reference sheet.

  ART STYLE CONSISTENCY: You MUST also match the art style, color palette, line quality, shading technique, and overall visual touch of the attached character sheets. All panels must look like they belong to the same manga series with the same illustrator.
  ```
- 各コマの `**Character name & details**` フィールドで `(MUST match the character in attached '{カタカナ名}.png')` を記載し、どのキャラ画像を参照するか明示する
- プロンプトの**末尾**に以下を追加する：
  ```
  anime-style, modern manga illustration, soft light and smooth shading, delicate linework, expressive eyes, clean and bright overall tone, full color manga page

  IMPORTANT: All characters MUST exactly match their appearance in the attached character reference sheets. The art style, line quality, coloring, and shading must also match the attached references. --ar 3:4
  ```

### コマ割りテンプレート選択ルール

**1コマ:**
- テンプレ1: ページ全体を使った1コマ（見開き・クライマックス・タイトル）

**2コマ:**
- テンプレ2: 上下2分割（上段→下段）（会話・対比）
- テンプレ3: 上下2分割（上段小→下段大）（導入→メイン）
- テンプレ4: 上下2分割（上段大→下段小）（メイン→リアクション）

**3コマ:**
- テンプレ5: 上・中・下の3段構成（テンポのよい展開）
  ```
  ┌─────────┐
  │ Panel1  │ ← 上段
  ├─────────┤
  │ Panel2  │ ← 中段
  ├─────────┤
  │ Panel3  │ ← 下段
  └─────────┘
  ```

- テンプレ6: 上段1コマ+下段左右2コマ
  ```
  ┌───────────────┐
  │    Panel1     │ ← 上段
  ├────────┬──────┤
  │ Panel3 │Panel2│ ← 下段: 右(Panel2)→左(Panel3)
  └────────┴──────┘
  ```

- テンプレ7: 上段左右2コマ+下段1コマ
  ```
  ┌────────┬──────┐
  │ Panel2 │Panel1│ ← 上段: 右(Panel1)→左(Panel2)
  ├───────────────┤
  │    Panel3     │ ← 下段
  └───────────────┘
  ```

**4コマ:**
- テンプレ8: 上段横長+中段左右+下段横長
  ```
  ┌───────────────┐
  │    Panel1     │ ← 上段
  ├────────┬──────┤
  │ Panel3 │Panel2│ ← 中段: 右(Panel2)→左(Panel3)
  ├───────────────┤
  │    Panel4     │ ← 下段
  └───────────────┘
  ```

- テンプレ9: 上段横長+下段右縦長+左上下分割
  ```
  ┌────────────────┐
  │    Panel1      │ ← 上段
  ├─────┬──────────┤
  │Panel4│ Panel2   │ ← 下段: 右(Panel2)→左上(Panel3)→左下(Panel4)
  │─────│          │
  │Panel3│          │
  └─────┴──────────┘
  ```

- テンプレ10: 上段横長+下段左縦長+右上下分割
  ```
  ┌────────────────┐
  │    Panel1      │ ← 上段
  ├──────────┬─────┤
  │          │Panel2│ ← 下段: 右上(Panel2)→右下(Panel3)→左(Panel4)
  │  Panel4  │─────│
  │          │Panel3│
  └──────────┴─────┘
  ```

### テンプレートバリエーション強制ルール（必須遵守）

```
┌─────────────────────────────────────────────────────────────────────┐
│  同じテンプレを3ページ連続で使用することは絶対禁止                  │
│  全体で最低4種類以上のテンプレートを使い分けること                  │
└─────────────────────────────────────────────────────────────────────┘
```

**ルール1: 連続使用制限**
- 同じテンプレートは**最大2ページ連続**まで。3ページ連続は禁止
- テンプレ8を3ページ連続で使いたい場合、間に別テンプレを1つ挟む

**ルール2: 最低バリエーション数**
- 全体ページ数に応じた最低テンプレ種類数:

| 総ページ数 | 最低テンプレ種類数 |
|-----------|------------------|
| 5-10ページ | 3種類以上 |
| 11-15ページ | 4種類以上 |
| 16-20ページ | 5種類以上 |
| 21ページ以上 | 6種類以上 |

**ルール3: シーン別テンプレ推奨マッピング**

| シーンの内容 | 推奨テンプレ | 理由 |
|-------------|------------|------|
| 章の冒頭・導入 | テンプレ3（上小+下大）| 小さい導入→大きいメインの流れ |
| 会話が中心 | テンプレ5（3段）/ テンプレ7（2+1）| テンポよく会話を展開 |
| 説明・解説シーン | テンプレ8（4コマ）/ テンプレ6（1+2）| 情報量を確保 |
| 驚き・衝撃の瞬間 | テンプレ1（全面1コマ）/ テンプレ4（大+小）| インパクト最大化 |
| クライマックス | テンプレ1（全面）/ テンプレ9 / テンプレ10 | 変則レイアウトで緊張感 |
| まとめ・振り返り | テンプレ2（上下均等）/ テンプレ5（3段）| 落ち着いた構成 |
| 感動・余韻 | テンプレ4（上大+下小）/ テンプレ1 | 余白で感情を表現 |

**ルール4: ページ配分の目安（19ページの場合）**
```
テンプレ1（1コマ）: 1-2ページ（冒頭タイトルやクライマックス）
テンプレ2-4（2コマ）: 3-4ページ（導入・対比・リアクション）
テンプレ5-7（3コマ）: 4-5ページ（会話・テンポ重視）
テンプレ8-10（4コマ）: 8-10ページ（情報量が多いシーン）
```

### 読み順ルール（厳守）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️  重要: すべての漫画は右→左読み（日本式）で作成すること        │
└─────────────────────────────────────────────────────────────────────┘
```

**基本ルール:**
- **日本の漫画形式**: 右上から左下へ
- **横並びのコマ**: 必ず「右側」が先、「左側」が後
- **Panel番号**: 読む順番を示す（Panel1=最初に読む、Panel2=次に読む）
- **位置と番号は別**: Panel1が左側にあることもある（読む順番が1番目という意味）
- **1コマ内の吹き出し順序**: 複数の吹き出しがある場合、右側の吹き出しが最初、左側の吹き出しが次
  - 例: 1コマに2人が会話 → 右側キャラのセリフが先、左側キャラのセリフが後

**具体例（テンプレ8の場合）:**
```
┌─────────────────────────┐
│   Panel1（上段横長）      │  ← 最初に読む
├───────────┬─────────────┤
│  Panel3   │   Panel2    │  ← Panel2（右）を先に読み、次にPanel3（左）
│ (中段左)  │  (中段右)   │
├─────────────────────────┤
│   Panel4（下段横長）      │  ← 最後に読む
└─────────────────────────┘

読み順: Panel1 → Panel2（右） → Panel3（左） → Panel4
```

**Page layoutに必須記載:**
- すべてのページのPage layout説明に「Right-to-left reading order (Japanese manga style)」を含めること

### 絶対遵守ルール

1. **セリフ完全維持**: 原稿のセリフは一文字も要約・省略・変更しない
2. **サイズ**: 896x1200px
3. **必ずフルカラー**: 白黒漫画は絶対に禁止
4. **（）の中の言葉**は吹き出しに記載しない
5. **同じ言葉を二回以上**吹き出しに記載しない
6. **1コマ内の吹き出し順序**: 右側の吹き出しが1番目、左側の吹き出しが2番目（右→左読み）

### オノマトペ（活用する）

ぱぁっ / パァァ / ビクッ / ギクッ / キュン / イライラ / じーっ / ガーン / むすっ / テクテク / ダダダダ / ガチャ / チラッ / カタカタ / シーン / ドキドキ / ザワザワ / キラキラ / パチパチ / ゴゴゴ

### 背景パターン（30+種類から選択）

水玉模様 / 半円 / ドット模様 / フラッシュエフェクト / ストライプ / グラデーション / 幾何学模様 / 集中線 / 放射線 / 斜線ハッチング / 花びら散り / 泡エフェクト / 暗転 / 白飛び / ぼかし背景 / 都市風景 / 室内 / 自然風景 / ハートパターン / 星パターン / 雷エフェクト / 炎エフェクト / パステルグラデーション / モノクロ反転 / セピア調 / 夕焼け色 / 雨粒エフェクト / 雪結晶 / 桜吹雪 / 紅葉 / デジタルエフェクト / 回路パターン / 光の粒子

---

## 画像生成

### 生成方法

各ページのプロンプトをnanobanana-proに送信する。
そのページに登場するキャラの個別シート画像 + テンプレート画像を `--attach-image` で添付する。
**複数画像はバッチアップロードされる（1回のファイル選択ダイアログで全画像を一括送信）。**

**重要：相対パスは `../../../` でプロジェクトルートに戻ること。**

**キャラが1人 + テンプレート画像:**
```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{ページNのプロンプト全文}" \
  --attach-image "../../../output/{slug}/characters/ケイコ.png" \
  --attach-image "../../../.claude/shared/manga-templates/テンプレ{N}.jpg" \
  --output "../../../output/{slug}/panels/page_NNN.png" \
  --timeout 240
```

**キャラが複数人 + テンプレート画像（--attach-imageを複数回指定）:**
```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{ページNのプロンプト全文}" \
  --attach-image "../../../output/{slug}/characters/ケイコ.png" \
  --attach-image "../../../output/{slug}/characters/アカリ.png" \
  --attach-image "../../../.claude/shared/manga-templates/テンプレ{N}.jpg" \
  --output "../../../output/{slug}/panels/page_NNN.png" \
  --timeout 240
```

**ルール:**
- そのページに登場するキャラの個別シート画像のみを添付する（登場しないキャラの画像は添付しない）
- テンプレート画像はStep 3で各ページに指定したものを添付する（レイアウト精度向上）
- `--attach-image` はキャラ数 + テンプレート1枚で繰り返す
- 添付画像は合計4〜5枚まで（バッチアップロードで一括送信される）

### 生成後の検証（必須）

生成された画像が**縦長（portrait）**であることを必ず検証する。
横長で出力された場合はリサイズせず、**再生成する**。

```bash
cd "{開発フォルダ}/output/{slug}/panels"

PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  "../../../.claude/skills/nanobanana-pro/.venv/Scripts/python.exe" -c "
from PIL import Image
img = Image.open('page_NNN.png')
w, h = img.size
print(f'Size: {w}x{h}')
if w > h:
    print('ERROR: LANDSCAPE detected. Must regenerate this page.')
elif (w, h) != (896, 1200):
    img = img.resize((896, 1200), Image.LANCZOS)
    img.save('page_NNN.png')
    print('Resized to 896x1200')
else:
    print('OK: Already 896x1200')
"
```

**ルール:**
- 横長（width > height）→ **リサイズ禁止、再生成する**
- 縦長だがサイズが違う（例: 765x1024）→ 896x1200にリサイズOK
- すでに896x1200 → そのまま

### 出力ファイル名

- `panels/page_001.png`, `panels/page_002.png`, ... `panels/page_NNN.png`

### バッチ生成

全ページを順次生成。10枚ごとに進捗報告。
中断後はまだ生成されていないページから再開可能。
横長で出力されたページは自動検出し、再生成キューに追加する。

---

## Step 4: 表紙作成（cover-master-ss 連携）

### 概要

漫画ページの画像一括生成が完了した後、**表紙作成**に進む。
個別キャラクターシート画像を参照画像として活用し、
キャラクターの外見を表紙にも一貫して反映する。

**個別シート版の強み**: キャラごとに独立した高品質シートがあるため、
cover-master-ss のStep 2（参照画像の確認）でメインキャラのシートを直接渡せる。
これにより、表紙のキャラクター再現度が最も高くなる。

### 手順

#### 1. ユーザーに表紙作成を確認

漫画ページ生成完了後、以下を確認する:

```
漫画ページの生成が完了しました！

続けて表紙を作成しますか？
漫画のキャラクターを活かした表紙を cover-master-ss で作ります。
キャラ個別シートがあるので、高い再現度で表紙に反映できます。
```

AskUserQuestion で確認:
- 「表紙を作る」→ Step 4 を続行
- 「今はスキップ」→ Step 4 をスキップして完了

#### 2. cover-master-ss に引き継ぐ情報

cover-master-ss を呼び出す際に、以下の情報を自動的に提供する:

| 情報 | 引き継ぎ元 | cover-master-ss での用途 |
|------|-----------|------------------------|
| 書籍タイトル | Step 1 のストーリー構成案 | Step 1: ヒアリング（タイトル） |
| ジャンル・ターゲット | 元の電子書籍情報 | Step 1: ヒアリング |
| メインキャラ画像 | `characters/{メインキャラ名}.png` | Step 2: 参照画像（メイン） |
| サブキャラ画像 | `characters/{サブキャラ名}.png` | Step 2: 参照画像（サブ） |
| キャラクター外見テキスト | `character_prompts.md` | Step 2: キャラ描写 |
| **出来の良い漫画ページ** | `panels/page_NNN.png`（1-2枚選定） | **Step 2: アートスタイル参照** |
| 漫画の総ページ数 | panels/ 内のファイル数 | Step 3: コンテンツ量 |

#### 2.5 出来の良い漫画ページの選定

漫画ページ生成完了後、表紙の参照画像として**出来の良いページを1-2枚選定**する。

**選定基準（優先順）:**
1. メインキャラが大きく魅力的に描かれているページ
2. キャラクターの描写が正確で一貫しているページ
3. 構図やカラーパレットが表紙映えするページ
4. クライマックスや感動的なシーンのページ

**選定方法:**
- 全ページ画像を Read ツールで閲覧し、上記基準で1-2枚を選ぶ
- 選定したページパスを cover-master-ss に渡す

**活用方法:**
- 選定したページは `--attach-image` で表紙生成時にGeminiに添付する
- プロンプトに「The attached manga pages show the art style to match」と記載する
- これにより表紙と漫画本編のアートスタイルが統一される

#### 3. cover-master-ss の呼び出し

Skill ツールで `cover-master-ss` を呼び出し、以下を伝える:

```
cover-master-ss で表紙を作成します。

■ 書籍情報:
- タイトル: {書籍タイトル}
- ジャンル: {ジャンル}
- ターゲット: {ターゲット読者}

■ 参照画像（漫画から引き継ぎ — Step 8で全て --attach-image で添付）:
- メインキャラ: output/{slug}/characters/{メインキャラ名}.png
- サブキャラ: output/{slug}/characters/{サブキャラ名}.png
- 出来の良い漫画ページ: output/{slug}/panels/{選定ページ}.png（1-2枚）
  → キャラクターの外見とアートスタイルを表紙にも忠実に反映してください

■ キャラクター外見:
{character_prompts.md の内容}

■ 漫画スタイルとの統一:
- 漫画ページと同じアートスタイル・色彩で表紙を作成
- 添付した漫画ページのアートスタイル・配色を表紙にも反映
- スタイルC（マンガ・アニメ型）を推奨
```

cover-master-ss のフローに従い、スタイル選択→カラーパレット→YAML生成→画像生成まで進める。

#### 4. 表紙画像の保存

cover-master-ss で生成された表紙画像は以下に保存する:

```
output/{slug}/
├── cover.png                   # 表紙画像（本文埋め込み用）
└── cover_prompt_amazon.md      # Amazon KDP提出用プロンプト
```

電子書籍と漫画は同じ `output/{slug}/` フォルダ内にあるため、
表紙画像（cover.png）は自動的に共有される。

---

## Step 5: DOCX統合（原稿+漫画ページの統合Word）

### 概要

**元の電子書籍の原稿テキストと漫画ページを統合した1つのWordファイル（DOCX）を作成する。**
漫画画像だけを並べるのではなく、各章の文章の後に対応する漫画ページを挿入し、
「テキストで学ぶ → 漫画で理解を深める」という構成の完成品を出力する。

### 前提条件

- 元の電子書籍原稿（`output/{slug}/manuscript.md`）が同じフォルダに存在すること
- Step 1の `story_structure.md` に章→漫画ページの対応が記載されていること
- 全漫画ページ画像が `panels/` フォルダに揃っていること（全ページ896x1200px）
- 図解画像が `images/` フォルダに揃っていること

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ 重要: manuscript.md と manuscript_raw.md の違い               │
│                                                                     │
│  manuscript.md     = 図解画像が ![](images/...) で埋め込み済み     │
│  manuscript_raw.md = HTMLコメント <!-- [INLINE_IMAGE] --> のまま    │
│                                                                     │
│  DOCX統合時は必ず manuscript.md を使用すること！                    │
│  manuscript_raw.md を使うと図解画像がWordに含まれない              │
└─────────────────────────────────────────────────────────────────────┘
```

### 手順

#### 0. 全パネル画像の一括リサイズ（Step 4完了後に必須実行）

Step 4で生成した全ページが896x1200pxかを確認し、リサイズする。

```python
# output/{slug}/panels/ で実行
from PIL import Image
import glob

files = sorted(glob.glob('page_*.png'))
for f in files:
    img = Image.open(f)
    w, h = img.size
    if w > h:
        print(f'ERROR: {f} is LANDSCAPE ({w}x{h}). Must regenerate.')
        continue
    if (w, h) != (896, 1200):
        resized = img.resize((896, 1200), Image.LANCZOS)
        resized.save(f, quality=95)
        print(f'Resized {f}: {w}x{h} -> 896x1200')
    else:
        print(f'{f}: OK (896x1200)')
print(f'Total: {len(files)} pages')
```

**ルール:**
- 横長（width > height）→ リサイズ禁止、再生成する
- 縦長だがサイズが違う（例: 765x1024）→ 896x1200にリサイズOK

#### 1. 章→漫画ページの対応表を作成

`story_structure.md` の「原稿の章構成」セクションから、各章に対応する漫画ページ番号を抽出する。

例:
```
第1章 → 漫画ページ 1〜4
第2章 → 漫画ページ 5〜7
第3章 → 漫画ページ 8〜11
第4章 → 漫画ページ 12〜16
第5章 → 漫画ページ 17〜19
```

#### 2. 統合Markdownファイルの生成（build_compiled.py）

**Pythonスクリプトで自動生成する（手動編集は禁止）。**
手動で原稿にページを差し込むとミスの原因になるため、必ずスクリプトで行う。

`output/{slug}/build_compiled.py` を作成して実行する:

```python
#!/usr/bin/env python3
"""Build manga_compiled.md by inserting manga pages after each chapter."""
import re

INPUT = "manuscript.md"     # ★ manuscript_raw.md は使用禁止
OUTPUT = "manga_compiled.md"

# Step 1 の対応表をここに記入（story_structure.md から抽出）
CHAPTER_PAGES = {
    1: [1, 2, 3, 4],       # 第1章 → ページ1-4
    2: [5, 6, 7],           # 第2章 → ページ5-7  ※ 実際の配分に合わせる
    3: [8, 9, 10, 11],
    4: [12, 13, 14, 15, 16],
    5: [17, 18, 19],
}

def make_manga_section(chapter_num, pages):
    lines = []
    lines.append("")
    lines.append("\\newpage")
    lines.append("")
    lines.append(f"### 第{chapter_num}章 まんがでわかる")
    lines.append("")
    for i, page_num in enumerate(pages):
        lines.append(f"![Page {page_num}](panels/page_{page_num:03d}.png){{ width=100% }}")
        lines.append("")
        if i < len(pages) - 1:
            lines.append("\\newpage")
            lines.append("")
    return "\n".join(lines)

with open(INPUT, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
result = []

# 表紙画像を冒頭に（images/cover.png がある場合）
# ※ 表紙パスはプロジェクトにより異なる。images/ 内か root直下か確認すること
result.append("![表紙](images/cover.png){ width=100% }")
result.append("")
result.append("\\newpage")
result.append("")

current_chapter = 0
chapter_pattern = re.compile(r"^## 第(\d+)章")
owari_pattern = re.compile(r"^## おわりに")

i = 0
while i < len(lines):
    line = lines[i]
    chapter_match = chapter_pattern.match(line)
    owari_match = owari_pattern.match(line)

    if chapter_match:
        new_chapter = int(chapter_match.group(1))
        if current_chapter > 0 and current_chapter in CHAPTER_PAGES:
            result.append(make_manga_section(current_chapter, CHAPTER_PAGES[current_chapter]))
            result.append("")
            result.append("\\newpage")
            result.append("")
        current_chapter = new_chapter
        result.append(line)
    elif owari_match:
        if current_chapter > 0 and current_chapter in CHAPTER_PAGES:
            result.append(make_manga_section(current_chapter, CHAPTER_PAGES[current_chapter]))
            result.append("")
            result.append("\\newpage")
            result.append("")
        current_chapter = 0
        result.append(line)
    elif line.strip() == "<!-- [COVER_IMAGE] -->":
        pass  # 表紙プレースホルダーはスキップ（冒頭で追加済み）
    else:
        result.append(line)
    i += 1

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print(f"Created {OUTPUT} ({len(result)} lines)")
```

実行:
```bash
cd "output/{slug}"
python build_compiled.py
```

**生成後の確認（必須）:**
```bash
grep -c "images/" manga_compiled.md    # 図解の参照数（images/ 内の画像数と一致すべき）
grep -c "panels/" manga_compiled.md    # 漫画パネルの参照数（全ページ数と一致すべき）
```

**統合ルール:**
- 表紙画像を最初に配置（パスは `images/cover.png` または `cover.png` を実態に合わせる）
- 元の原稿のテキスト構造（見出し・段落・箇条書き）を維持する
- 元の原稿に含まれる図解画像（`![](images/...)`）もそのまま維持する
- 各章の本文テキストの後に「### 第N章 まんがでわかる」の見出しを追加
- 見出しの後に対応する漫画ページを順番に挿入
- 各漫画ページの間に `\newpage`（改ページ）を挿入
- すべての画像に `{ width=100% }` を付与
- 画像行の前後に必ず空行1行ずつ
- 「はじめに」と「おわりに」には漫画を挿入しない

#### 3. DOCX変換（pypandoc + ASCIIパス変換）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ Windows + 日本語パスの問題                                     │
│                                                                     │
│  output/{slug}/ のパスに日本語（例: 開発1/）が含まれると           │
│  Pandoc がファイルを読めずに変換失敗する。                          │
│  必ず ASCII の一時ディレクトリにコピーしてから変換すること。        │
│                                                                     │
│  また pandoc コマンドは PATH に入っていないことが多い。             │
│  pypandoc 経由で呼び出すのが安全。                                 │
└─────────────────────────────────────────────────────────────────────┘
```

`output/{slug}/convert_to_docx.py` を作成して実行する:

```python
#!/usr/bin/env python3
"""Convert manga_compiled.md to final_book.docx using pypandoc."""
import os, sys, shutil, tempfile
import pypandoc

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
MD_FILE = os.path.join(SRC_DIR, "manga_compiled.md")
DOCX_FILE = os.path.join(SRC_DIR, "final_book.docx")

# ASCII一時ディレクトリにコピー（日本語パス回避）
TEMP_BASE = os.path.join(tempfile.gettempdir(), "pandoc_work")
os.makedirs(TEMP_BASE, exist_ok=True)
temp_dir = os.path.join(TEMP_BASE, "manga_build")
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

# Markdownファイルをコピー
shutil.copy2(MD_FILE, os.path.join(temp_dir, "manga_compiled.md"))

# panels/ と images/ をコピー
for folder in ["panels", "images"]:
    src = os.path.join(SRC_DIR, folder)
    dst = os.path.join(temp_dir, folder)
    if os.path.exists(src):
        shutil.copytree(src, dst)
        print(f"  Copied {folder}/ ({len(os.listdir(dst))} files)")

# pypandoc で変換
print("Converting to DOCX...")
temp_md = os.path.join(temp_dir, "manga_compiled.md")
temp_docx = os.path.join(temp_dir, "final_book.docx")

try:
    pypandoc.convert_file(
        temp_md, 'docx', format='markdown',
        outputfile=temp_docx,
        extra_args=[f'--resource-path={temp_dir}', '--standalone']
    )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# 結果をコピーバック
shutil.copy2(temp_docx, DOCX_FILE)
size_mb = os.path.getsize(DOCX_FILE) / (1024 * 1024)
print(f"Output: {DOCX_FILE} ({size_mb:.1f} MB)")

# 一時ディレクトリ削除
shutil.rmtree(temp_dir, ignore_errors=True)
print("Done!")
```

実行:
```bash
cd "output/{slug}"
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python convert_to_docx.py
```

#### 4. 出力検証（必須）

DOCX内に図解画像と漫画ページの両方が埋め込まれていることを検証する。

```python
# output/{slug}/ で実行
import zipfile

with zipfile.ZipFile('final_book.docx', 'r') as z:
    media = [f for f in z.namelist() if f.startswith('word/media/')]
    print(f'DOCX内の埋め込み画像数: {len(media)}')

    # 期待値: images/ 内の画像数 + panels/ 内のページ数
    import os
    expected_images = len(os.listdir('images'))
    expected_panels = len(os.listdir('panels'))
    expected_total = expected_images + expected_panels
    print(f'期待値: images/{expected_images} + panels/{expected_panels} = {expected_total}')

    if len(media) >= expected_total:
        print('OK: 全画像が埋め込まれています')
    else:
        print(f'WARNING: 画像が不足しています（{len(media)} < {expected_total}）')
        print('  → manuscript_raw.md を使っていないか確認してください')
```

**検証基準:**
- DOCX内の画像数 ≧ `images/` の画像数 + `panels/` の画像数
- ファイルサイズが20MB以上（図解+漫画で通常20-50MB）
- 不足している場合は `manga_compiled.md` 内の画像参照数を確認する

### 出力ファイル

```
output/{slug}/
├── build_compiled.py           # manga_compiled.md 生成スクリプト
├── convert_to_docx.py          # DOCX変換スクリプト（日本語パス対応）
├── manga_compiled.md           # 中間Markdown（原稿+図解+漫画統合済み）
└── final_book.docx             # ★ 最終成果物（原稿+図解+漫画の統合Word）
```

---

## 出力先

**電子書籍（ebook-creator-ss）と同じフォルダ（`output/{slug}/`）に漫画関連ファイルを追加する。**
1冊の書籍タイトルにつき1フォルダで、原稿・図解・漫画すべてを統合管理する。

```
output/{slug}/
│
│  ── 電子書籍スキル（ebook-creator-ss）が先に生成済み ──
├── manuscript.md             # 電子書籍原稿（Markdown）
├── manuscript_raw.md         # 中間ファイル
├── manuscript.docx           # 原稿+図解のみのWord（中間成果物）
├── research.md               # リサーチ結果
├── images/                   # 図解画像（40〜60枚）
│   ├── ch1_header.png
│   ├── ch1_img1.png
│   └── ...
│
│  ── 本スキル（manga-produce-kobetsu-ss）が追加するファイル ──
├── story_structure.md        # ストーリー構成案（全コマ詳細）
├── character_prompts.md      # キャラクター外見プロンプトDB
├── page_prompts.md           # 全ページのプロンプト
├── characters/               # キャラ個別シート画像（896x1200px）
│   ├── {キャラ名}.png
│   └── ...（キャラ数分）
├── panels/                   # 漫画ページ画像（896x1200px）
│   ├── page_001.png
│   ├── page_002.png
│   └── ...
├── cover.png                 # 漫画風表紙（Step 4で生成）
├── cover_prompt.md           # 表紙プロンプト Version A + B
├── cover_prompt_amazon.md    # Amazon KDP用プロンプト
├── manga_compiled.md         # 中間Markdown：原稿テキスト+漫画統合済み
├── final_book.docx           # ★ 最終成果物（原稿+図解+漫画の統合Word）
└── generate_panels.py        # バッチ生成スクリプト（オプション）
```

**最終成果物は `final_book.docx`**。
- 元の原稿テキスト + 図解画像 + 各章末尾に漫画ページを挿入した統合Word
- `manuscript.docx`（原稿+図解のみ）は中間成果物として残る

---

## 関連スキル

| スキル | 用途 |
|--------|------|
| `nanobanana-pro` | Gemini NanoBanana で画像生成 |
| `custom-character` | キャラクター設計パターン参考 |
| `nanobanana-prompts` | 画像プロンプト最適化の黄金ルール |
| `comicle-ss` | CSV出力版（同じ個別キャラシート方式） |
| `cover-master-ss` | Step 4: 表紙作成（キャラ個別シートを参照画像として連携） |
| `doc-convert-pandoc` | Step 5: Markdown → DOCX 変換 |
| `ebook-creator-ss` | 電子書籍作成（漫画化の前工程） |

## 使用例

```
# 電子書籍作成後に
「書籍を作った後に漫画作りたい」
「この電子書籍を漫画化して」
「各章を漫画で分かるようにして」

# ebook-creator-ss との連携
/ebook-creator-ss でテーマの書籍作成
  ↓
/manga-produce-v2-ss で書籍を漫画化
```

## 📖 書籍漫画化の実行例

```
ユーザー: 「書籍を作った後に漫画作りたい」

AI: manga-produce-kobetsu-ss スキルを起動
  1. 原稿ファイルを読み込む（manuscript.md）
  2. 章構成を解析（## 第1章、## 第2章...）
  3. 各章の重要ポイントを抽出
  4. 各章3-5ページの漫画ストーリーを構成（Step 1）
  5. キャラごとに個別シート画像を生成（Step 2）
  6. ページ別プロンプト生成（Step 3）
  7. 個別キャラシートを添付しながら画像一括生成
  8. cover-master-ss で表紙作成（Step 4）
     → キャラ個別シートを参照画像として自動連携
     → 漫画と統一感のある表紙を生成
  9. 原稿テキスト+漫画ページをDOCXに統合（Step 5）
     → 元の電子書籍原稿に各章の漫画ページを挿入
     → Pandocで原稿+漫画統合Word出力
```
