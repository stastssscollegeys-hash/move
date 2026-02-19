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

## 全体フロー（3ステップ + 画像生成）

```
Step 1: ストーリー構成案の作成
   │  ユーザーから原稿/文章を受け取る（必須）
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

`output/manga-{slug}/story_structure.md` に保存:

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
  --output "../../../output/manga-{slug}/characters/ケイコ.png" \
  --timeout 240

# キャラ2: アカリ
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{アカリのキャラクターシートプロンプト}" \
  --output "../../../output/manga-{slug}/characters/アカリ.png" \
  --timeout 240

# ... 全キャラ分繰り返す
```

### リサイズ（生成後必須）

リサイズはファイルのある場所にcdしてから実行する（日本語パスの文字化け回避）。
**各キャラシートを896x1200pxにリサイズする。**

```bash
cd "{開発フォルダ}/output/manga-{slug}/characters"

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

全ページ分を `output/manga-{slug}/page_prompts.md` に一括出力する。

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
  --attach-image "../../../output/manga-{slug}/characters/ケイコ.png" \
  --attach-image "../../../.claude/shared/manga-templates/テンプレ{N}.jpg" \
  --output "../../../output/manga-{slug}/panels/page_NNN.png" \
  --timeout 240
```

**キャラが複数人 + テンプレート画像（--attach-imageを複数回指定）:**
```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{ページNのプロンプト全文}" \
  --attach-image "../../../output/manga-{slug}/characters/ケイコ.png" \
  --attach-image "../../../output/manga-{slug}/characters/アカリ.png" \
  --attach-image "../../../.claude/shared/manga-templates/テンプレ{N}.jpg" \
  --output "../../../output/manga-{slug}/panels/page_NNN.png" \
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
cd "{開発フォルダ}/output/manga-{slug}/panels"

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

## 出力先

```
output/manga-{slug}/
├── story_structure.md          # ストーリー構成案（全コマ詳細）
├── character_prompts.md        # キャラクター外見プロンプトDB
├── page_prompts.md             # 全ページのプロンプト（英語、セリフ部分のみ日本語）
├── characters/                 # キャラ個別シート画像（896x1200px）
│   ├── ケイコ.png
│   ├── アカリ.png
│   └── ...（キャラ数分）
├── panels/                     # 各ページ画像（896x1200px）
│   ├── page_001.png
│   ├── page_002.png
│   └── ...
└── generate_panels.py          # バッチ生成スクリプト（オプション）
```

---

## 関連スキル

| スキル | 用途 |
|--------|------|
| `nanobanana-pro` | Gemini NanoBanana で画像生成 |
| `custom-character` | キャラクター設計パターン参考 |
| `nanobanana-prompts` | 画像プロンプト最適化の黄金ルール |
| `comicle-ss` | CSV出力版（同じ個別キャラシート方式） |

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

AI: manga-produce-v2-ss スキルを起動
  1. 原稿ファイルを読み込む（manuscript.md）
  2. 章構成を解析（## 第1章、## 第2章...）
  3. 各章の重要ポイントを抽出
  4. 各章3-5ページの漫画ストーリーを構成（Step 1）
  5. キャラごとに個別シート画像を生成（Step 2）
  6. ページ別プロンプト生成（Step 3）
  7. 個別キャラシートを添付しながら画像一括生成
```
