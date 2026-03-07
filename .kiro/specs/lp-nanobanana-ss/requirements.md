# Requirements: lp-nanobanana-ss

> NanoBanana（Gemini画像生成）を活用し、ナレッジプロンプトに基づくコピーライティングと参考LPのデザインリサーチを組み合わせて、LPのセクション画像を自動生成するClaude Codeスキル及びWebシステム。

## 1. 目的（Purpose）
- LP制作の全工程（コピーライティング、デザインリサーチ、画像生成）をClaude Code上で一気通貫で完結させ、手作業ゼロでLP画像を完成させること
- 個人起業家がコピーライティング未経験でも、ナレッジプロンプトの専門知識により反応率の高いLP文章と画像を得られるようにすること

## 2. 概要（Executive Summary）
- **Who**: LP制作を行う個人起業家、マーケター、清水昴（開発者兼ユーザー）
- **What**: ナレッジプロンプトからLPコピーを生成し、参考LPのデザインをリサーチした上で、NanoBananaでLPセクション画像を順次自動生成するシステム（Claude Codeスキル及びWeb UI）
- **Why**: LP制作の全工程をClaude Code上で一気通貫で完結させ、手作業ゼロでLPを完成させるため

## 3. 背景 & Context
- 現状、LP制作はコピーライティング、デザイン、画像生成、コーディングと複数ステップに分かれ、各ステップで手作業が発生する
- Web版Claude、Manus、GenSparkでもLPコピーは作れるが、画像生成まで一括で行えない
- Claude CodeからNanoBanana（Geminiブラウザ操作）を動かすことで、コピーからプロンプト、画像生成を一気通貫で実行できる
- 既存の`manga-creator-ss`スキルでNanoBananaブラウザ操作の実績がある（`scripts/run.py`経由）
- 既存の`src/lp-creator-ss/`にClaude API経由のLP生成コードがあるが、今回ゼロから再設計する
- Stage 1はClaude Codeスキルとしてブラウザ版NanoBananaで動作確認し、Stage 2でAPI版に移行してWeb UIで動作するシステムにする

## 4. スコープ
### 4.1 In Scope

**Stage 1: Claude Codeスキル版（最優先）**
- ナレッジプロンプト（後日提供）を用いたLPコピーライティング生成
- 参考LPのURLからスクリーンショット取得とデザイン分析
- 分析結果とコピーからNanoBanana用画像生成プロンプト生成（セクションごと）
- NanoBanana（`scripts/run.py`経由のブラウザ操作）でLP画像を順次生成
- 生成画像の`output/`フォルダへの保存
- `.claude/skills/lp-nanobanana-ss/SKILL.md`としてスキル定義

**Stage 2: Web UI + API版（Stage 1完成後）**
- `src/lp-creator-ss/`を上書きしてWeb UIを構築
- 入力フォーム（商品情報、参考URL）
- NanoBanana API経由での画像生成（ブラウザ操作からの移行）
- 生成画像をUI上に順番に表示
- 生成結果のダウンロード機能

### 4.2 Out of Scope（重要）
- LP公開後のA/Bテスト機能
- メール配信、MA連携
- ユーザー認証、課金機能（Stage 2時点では不要）
- 動画埋め込みの自動生成
- 多言語対応（日本語のみ）
- HTMLコーディングの自動生成（画像ベースのLP）
- ナレッジプロンプト自体の作成（ユーザーが提供する）

## 5. 用語集 / Glossary
| 用語 | 定義 |
|------|------|
| LP | ランディングページ。商品やサービスの販売や問い合わせ獲得を目的とした縦長の単一ページ |
| NanoBanana | Gemini画像生成をブラウザ操作（patchright）で実行するPythonツール。`scripts/run.py`経由で起動する |
| ナレッジプロンプト | LPコピーライティングの品質を担保するための専門知識が埋め込まれたプロンプトテンプレート。ユーザーが提供する |
| セクション | LPを構成する各ブロック（ファーストビュー、問題提起、解決策、ベネフィット、お客様の声、特典、CTA） |
| CTA | Call To Action。ユーザーに行動を促すボタンやリンク |
| デザインリサーチ | 参考LPのスクリーンショットを取得し、配色、レイアウト、フォント使い等を分析すること |
| ファーストビュー | LPの最上部。スクロールせずに見える領域。キャッチコピーとCTAを配置する |
| Stage 1 | Claude Codeスキル版。ブラウザ版NanoBananaでLP画像を生成する |
| Stage 2 | Web UI + API版。NanoBanana APIを使いWeb上でLP画像を生成する |

## 6. ステークホルダー & 役割
| Role | 権限/責務 |
|------|----------|
| プロダクトオーナー（清水昴） | 要件決定、ナレッジプロンプト提供、参考LP選定、品質判定 |
| 開発者（AIエージェント + 清水） | 設計、実装、テスト |
| エンドユーザー（個人起業家） | Stage 2のWeb UIを使用してLPを生成する利用者 |

## 7. 前提/仮定（Assumptions）
- ナレッジプロンプトはユーザーが後日提供する。提供されるまでStage 1のコピーライティング部分はプレースホルダーとする
- NanoBananaの`scripts/run.py`がWindows環境（`C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro\`）で動作する
- Geminiへのログイン認証はユーザーが手動で行う（スキル実行前に認証済みであること）
- 参考LPのURLは公開ページであり、スクリーンショット取得がHTTPステータス200で成功する
- 1つのLPは7セクション（ファーストビュー、問題提起、解決策、ベネフィット、お客様の声、特典、CTA）で構成する（固定構成）
- Stage 2のNanoBanana API（Gemini Imagen API）の仕様とコストはStage 2着手時に調査する
- Stage 2のWeb UIは既存の開発1のExpressサーバー（`src/app.ts`）にルートを追加する形で実装する

## 8. 制約（Constraints）
- **技術（Stage 1）**: Claude Codeスキルとして`.claude/skills/lp-nanobanana-ss/`に配置する
- **技術（Stage 1）**: NanoBananaのブラウザ操作は`manga-creator-ss`と同じ`scripts/run.py`経由で実行する
- **技術（Stage 1）**: 画像生成のタイムアウトは1枚あたり240秒とする
- **技術（Stage 2）**: `src/lp-creator-ss/`を上書きして実装する（既存コードは破棄）
- **技術（Stage 2）**: フロントエンドは`public/lp-creator.html`として単一HTMLファイルで提供する
- **環境**: Windows 11、Python実行時は`PYTHONIOENCODING=utf-8 PYTHONUTF8=1`を付与する
- **環境**: 画像出力先は`output/lp-{slug}/`ディレクトリとする
- **運用**: 開発者は清水1名 + AIエージェント。専任運用チームなし
- **コスト**: Stage 1はGemini無料枠（ブラウザ操作）で動作する。Stage 2はAPI課金が発生する

## 9. 成功条件（Success Metrics）
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Stage 1: LPセクション画像生成成功率 | 生成指示した全セクションのうち80%以上が画像として出力される | 生成指示数に対する`output/lp-{slug}/sections/`内のPNGファイル数の比率 |
| Stage 1: 1セクション画像生成時間 | 240秒以内 | NanoBanana `scripts/run.py`のプロセス開始から終了までの経過秒数 |
| Stage 1: デザインリサーチ成功率 | 参考URLのスクリーンショットが取得できる割合が90%以上 | スクリーンショット取得試行数に対する成功数の比率 |
| Stage 2: LP全体生成時間 | 入力完了から全セクション画像表示まで1800秒（30分）以内 | フロントエンドのタイムスタンプ計測 |
| Stage 2: UI表示 | 各セクション画像が生成完了順にUI上に表示される | 生成完了イベント発火後2秒以内に画像がDOM上に表示されることを確認 |

## 10. 機能要件（Functional Requirements）

### REQ-001: ナレッジプロンプトによるLPコピー生成
- 種別: EARS-イベント駆動
- 優先度: MUST
- 要件文(EARS): ユーザーが商品情報（商品名、ターゲット、強み、価格、詳細説明）を入力したとき、システムはナレッジプロンプトに基づいてLPの全7セクション（ファーストビュー、問題提起、解決策、ベネフィット、お客様の声、特典、CTA）のコピーライティングテキストを生成し`output/lp-{slug}/copy.md`に保存しなければならない。
- 根拠/目的: LPの文章をナレッジプロンプトの専門知識で生成することで、コピーライティング未経験者でも反応率の高いLP文章を得るため
- 受入テスト(GWT):
  - AT-001: Given ナレッジプロンプトが`.claude/skills/lp-nanobanana-ss/knowledge/`に配置されている When ユーザーが商品名「AI活用セミナー」、ターゲット「個人起業家」、強み「ワンクリックでLP完成」を入力する Then `output/lp-ai-seminar/copy.md`にファーストビュー、問題提起、解決策、ベネフィット、お客様の声、特典、CTAの7セクション分のテキストが出力され、各セクションが50文字以上である
  - AT-002: Given ナレッジプロンプトが配置されていない When ユーザーが商品情報を入力する Then エラーメッセージ「ナレッジプロンプトが見つかりません。knowledge/ディレクトリにプロンプトファイルを配置してください。」を表示する
- 例外・エラー:
  - EH-001: If ナレッジプロンプトファイルが存在しない then the system shall エラーメッセージを表示し処理を中断する
  - EH-002: If 商品情報の必須項目（商品名、ターゲット、強み）のいずれかが空文字である then the system shall 「必須項目が入力されていません: {項目名}」というエラーメッセージを表示する
- 補足:
  - ナレッジプロンプトの内容はユーザーが後日提供する
  - 関連: REQ-003

### REQ-002: 参考LPのデザインリサーチ
- 種別: EARS-イベント駆動
- 優先度: MUST
- 要件文(EARS): ユーザーが参考LPのURLを1つ以上入力したとき、システムは各URLのページ全体をスクリーンショットとして取得しセクションごとに分割して`output/lp-{slug}/research/`に保存し、各セクションの配色（HEXコード3色以上）とレイアウト構造（カラム数、余白比率）とテキスト配置パターンを`output/lp-{slug}/research/analysis.json`に出力しなければならない。
- 根拠/目的: 参考LPのデザインを構造化データとして抽出し、NanoBanana画像生成プロンプトに反映するため
- 受入テスト(GWT):
  - AT-003: Given 公開されているLPのURL「https://example.com/lp」が存在する When ユーザーがそのURLを入力する Then `output/lp-{slug}/research/`にスクリーンショットPNGファイルが1枚以上保存され、`analysis.json`に`colors`（HEXコード3個以上の配列）と`layout`（構造情報）と`text_placement`（テキスト配置情報）が含まれる
  - AT-004: Given URLが404を返すページである When ユーザーがそのURLを入力する Then エラーメッセージ「URLにアクセスできません（HTTPステータス: 404）」を表示し、他のURLの処理は継続する
- 例外・エラー:
  - EH-003: If URLへのアクセスがHTTPステータス200以外を返した then the system shall そのURLをスキップしエラーログに記録する
  - EH-004: If スクリーンショット取得が60秒以内に完了しない then the system shall タイムアウトとしてそのURLをスキップする
- 補足:
  - スクリーンショット取得にはpatchright（NanoBananaのブラウザ）またはPlaywrightを使用する
  - 関連: REQ-003

### REQ-003: NanoBanana用画像生成プロンプト生成
- 種別: EARS-イベント駆動
- 優先度: MUST
- 要件文(EARS): REQ-001のコピーテキストとREQ-002のデザイン分析結果が揃ったとき、システムはLPの各セクションごとにNanoBanana用の画像生成プロンプト（テキスト配置、色指定、レイアウト指示を含む英語テキスト）を生成し`output/lp-{slug}/prompts/section_{NNN}.txt`として保存しなければならない。
- 根拠/目的: コピーとデザイン分析を統合し、NanoBananaが生成可能な形式のプロンプトに変換するため
- 受入テスト(GWT):
  - AT-005: Given `copy.md`に7セクション分のテキストが存在し`analysis.json`にデザイン分析結果が存在する When プロンプト生成を実行する Then `output/lp-{slug}/prompts/`に`section_001.txt`から`section_007.txt`の7ファイルが生成され各ファイルが100文字以上の英語テキストを含む
  - AT-006: Given `copy.md`にファーストビューセクションのテキスト「AI時代の新常識」が含まれる When プロンプト生成を実行する Then `section_001.txt`にそのテキストの英訳または原文が含まれ配色情報（HEXコード）が1つ以上含まれる
- 例外・エラー:
  - EH-005: If `copy.md`が存在しない then the system shall 「コピーテキストが生成されていません。先にREQ-001を実行してください。」というエラーメッセージを表示する
  - EH-006: If `analysis.json`が存在しない then the system shall デフォルトのデザイン設定（白背景#FFFFFF、アクセント色#2563EB、テキスト色#111827）を使用してプロンプトを生成する
- 補足:
  - プロンプトはcovermaster-ssやmanga-creator-ssで使用しているテキスト差し込み形式を参考にする
  - 日本語テキスト部分はプロンプト内にそのまま含める（NanoBananaが日本語テキスト描画に対応しているため）
  - 関連: REQ-001, REQ-002, REQ-004

### REQ-004: NanoBananaによるLP画像順次生成
- 種別: EARS-イベント駆動
- 優先度: MUST
- 要件文(EARS): REQ-003のプロンプトファイル群が生成されたとき、システムは`section_001.txt`から順番にNanoBanana（`scripts/run.py`経由）を実行し各セクションの画像を`output/lp-{slug}/sections/section_{NNN}.png`として保存しなければならない。
- 根拠/目的: プロンプトからLP画像を自動生成し、手作業なしでLPビジュアルを完成させるため
- 受入テスト(GWT):
  - AT-007: Given `prompts/section_001.txt`から`section_007.txt`が存在する When 画像生成を実行する Then `sections/section_001.png`から`sections/section_007.png`が生成され各ファイルのサイズが10KB以上である
  - AT-008: Given 7セクション分のプロンプトが存在する When 画像生成を実行する Then 3枚目の画像生成完了時点で「進捗: 3/7セクション完了」という形式の進捗メッセージが出力される
  - AT-009: Given 画像生成が4枚目で失敗した When 画像生成を再実行する Then 4枚目から再開され既に生成済みの1から3枚目は再生成されない
- 例外・エラー:
  - EH-007: If NanoBananaの`scripts/run.py`が240秒以内に完了しない then the system shall そのセクションをタイムアウトとして記録し次のセクションの生成に進む
  - EH-008: If Geminiへの認証が切れている（ブラウザがログイン画面を表示した） then the system shall 「Geminiの認証が切れています。ブラウザでログインしてから再実行してください。」というメッセージを表示し処理を中断する
  - EH-009: If 生成された画像ファイルが0バイトである then the system shall そのセクションを「生成失敗」として記録し次のセクションに進む
- 補足:
  - NanoBanana実行コマンド: `cd ".claude/skills/nanobanana-pro" && PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py --prompt "{プロンプト}" --output "../../../output/lp-{slug}/sections/section_{NNN}.png" --timeout 240`
  - 関連: REQ-003

### REQ-005: 生成結果レポート出力
- 種別: EARS-イベント駆動
- 優先度: MUST
- 要件文(EARS): 全セクションの画像生成が完了（成功、失敗、タイムアウト問わず）したとき、システムは各セクションの生成ステータス（成功/失敗/タイムアウト）とファイルパスと生成時間（秒）を含むレポートを`output/lp-{slug}/report.md`に出力しなければならない。
- 根拠/目的: 生成結果の全体像を把握し、再生成が必要なセクションを特定するため
- 受入テスト(GWT):
  - AT-010: Given 7セクション中5セクションが成功、1セクションが失敗、1セクションがタイムアウトした When 全セクションの処理が完了する Then `report.md`に7行のステータス表（セクション番号、ステータス、ファイルパス、生成時間）が出力される
- 例外・エラー:
  - EH-010: If `output/lp-{slug}/`ディレクトリへの書き込み権限がない then the system shall エラーメッセージ「出力ディレクトリへの書き込み権限がありません: {パス}」を表示する
- 補足:
  - 関連: REQ-004

### REQ-006: 参考URL未指定時のデフォルトデザイン適用
- 種別: EARS-状態駆動
- 優先度: SHOULD
- 要件文(EARS): 参考LPのURLが指定されていない場合、システムはデフォルトのデザイン設定（背景色: #FFFFFF、アクセント色: #2563EB、テキスト色: #111827、見出しフォントサイズ: 48px、本文フォントサイズ: 18px、上下余白: 60px、左右余白: 40px）を使用してプロンプトを生成しなければならない。
- 根拠/目的: 参考URLがなくてもLP画像を生成できるようにし、一定水準のデザイン品質を保証するため
- 受入テスト(GWT):
  - AT-011: Given 参考URLが未入力である When コピーテキストのみでプロンプト生成を実行する Then 生成されたプロンプトファイルにHEXコード`#2563EB`が含まれる
- 例外・エラー:
  - EH-011: If デフォルト設定ファイルが破損している then the system shall ハードコードされたフォールバック値（背景色: #FFFFFF、アクセント色: #2563EB、テキスト色: #111827）を使用する
- 補足:
  - 関連: REQ-002, REQ-003

### REQ-007: 画像リサイズ処理
- 種別: EARS-イベント駆動
- 優先度: MUST
- 要件文(EARS): NanoBananaが画像を生成したとき、システムは生成された画像を幅1080pxかつ元画像のアスペクト比を維持した高さにリサイズし元ファイルを上書き保存しなければならない。
- 根拠/目的: LP用画像のファイルサイズを削減しWeb表示に統一した幅で提供するため
- 受入テスト(GWT):
  - AT-012: Given NanoBananaが幅2048pxの画像を生成した When リサイズ処理が実行される Then 出力画像の幅が1080pxでありアスペクト比が元画像と同一（誤差1%以内）である
- 例外・エラー:
  - EH-012: If Pillowライブラリが利用できない then the system shall リサイズをスキップし警告メッセージ「Pillowが見つかりません。リサイズをスキップします。」を出力する
- 補足:
  - リサイズにはNanoBananaの`.venv`内のPillowを使用する
  - 関連: REQ-004

### REQ-008: Stage 2 Web UI入力フォーム
- 種別: EARS-イベント駆動
- 優先度: COULD
- 要件文(EARS): ユーザーがWeb UIの入力フォームに商品名、ターゲット、強み、参考URL（任意）を入力し「LP生成」ボタンをクリックしたとき、システムはバックエンドAPIにリクエストを送信し生成処理を開始しなければならない。
- 根拠/目的: Stage 2としてブラウザからLP生成を実行できるようにするため
- 受入テスト(GWT):
  - AT-013: Given Web UIが表示されている When ユーザーが商品名「AIセミナー」を入力し「LP生成」ボタンをクリックする Then APIエンドポイント`POST /api/lp-creator/generate`にリクエストが送信されHTTPステータス202が返却される
- 例外・エラー:
  - EH-013: If APIサーバーが5秒以内に応答しない then the system shall UI上に「サーバーに接続できません。しばらく待ってから再試行してください。」というメッセージを表示する
- 補足:
  - Stage 2での実装。Stage 1完了後に着手する
  - 関連: REQ-001

### REQ-009: Stage 2 生成画像のリアルタイム表示
- 種別: EARS-イベント駆動
- 優先度: COULD
- 要件文(EARS): バックエンドが1セクションの画像生成を完了したとき、システムはServer-Sent Events（SSE）を通じてフロントエンドに画像パスを送信しフロントエンドは受信から2秒以内にその画像をページ上に表示しなければならない。
- 根拠/目的: ユーザーが生成結果をリアルタイムで確認できるようにし全セクション完了を待たずに品質チェックを可能にするため
- 受入テスト(GWT):
  - AT-014: Given LP生成が進行中である When 3番目のセクション画像が生成完了する Then SSEイベントがフロントエンドに送信され2秒以内にページ上にその画像が表示される
- 例外・エラー:
  - EH-014: If SSE接続が切断された then the system shall フロントエンドで5秒間隔のポーリングにフォールバックし未表示のセクション画像を取得する
- 補足:
  - Stage 2での実装
  - 関連: REQ-004, REQ-008

### REQ-010: スキル定義ファイル作成
- 種別: EARS-普遍
- 優先度: MUST
- 要件文(EARS): システムは`.claude/skills/lp-nanobanana-ss/SKILL.md`にスキル名`lp-nanobanana-ss`と全体フローと使用例と関連スキル一覧を含むスキル定義を保持しなければならない。
- 根拠/目的: Claude Codeスキルとして正しく認識、起動されるために標準的なスキル定義ファイルが必要であるため
- 受入テスト(GWT):
  - AT-015: Given `.claude/skills/lp-nanobanana-ss/SKILL.md`が存在する When Claude Codeのスキル一覧を確認する Then `lp-nanobanana-ss`がスキルとして認識されている
  - AT-016: Given SKILL.mdの内容を確認する When 「When to Use This Skill」セクションを読む Then 「LPを作って」「ランディングページを生成」「LP画像を作成」のトリガーワードが記載されている
- 例外・エラー:
  - EH-015: If SKILL.mdの`name`または`description`フィールドが存在しない then the system shall スキルとして認識されないためフィールドの存在を検証しエラーを報告する
- 補足:
  - 全体フロー: 入力受付、コピー生成、デザインリサーチ、プロンプト生成、画像生成、レポート出力
  - 関連: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005

### REQ-011: 中断再開機能
- 種別: EARS-イベント駆動
- 優先度: SHOULD
- 要件文(EARS): 画像生成処理が中断された（タイムアウト、ユーザー中断、エラー）とき、システムは`output/lp-{slug}/progress.json`に完了済みセクション番号の一覧を保存し再実行時にそのファイルを読み込んで未完了セクションから処理を再開しなければならない。
- 根拠/目的: 7セクションの画像生成は合計で最大30分かかるため途中で中断しても最初からやり直す必要がないようにするため
- 受入テスト(GWT):
  - AT-017: Given 7セクション中3セクションまで生成完了し4セクション目でタイムアウトした When 画像生成を再実行する Then `progress.json`を読み込みセクション4から生成を再開する（セクション1から3は再生成しない）
  - AT-018: Given `progress.json`が存在しない When 画像生成を実行する Then セクション1から全セクションを生成する
- 例外・エラー:
  - EH-016: If `progress.json`が破損している（JSONパースエラー） then the system shall 警告メッセージ「進捗ファイルが破損しています。最初から生成します。」を表示しセクション1から全セクションを生成する
- 補足:
  - 関連: REQ-004

## 11. 非機能要件（Non-Functional Requirements）

### REQ-900: 画像生成タイムアウト
- 種別: EARS-普遍
- 優先度: MUST
- 要件文(EARS): システムはNanoBananaの各画像生成処理に240秒のタイムアウトを設定し240秒を超過した場合はプロセスを強制終了しなければならない。
- 根拠/目的: ブラウザ操作の無限待機を防止し次のセクション生成に進むため
- 受入テスト(GWT):
  - AT-019: Given NanoBananaが画像生成中である When 240秒経過しても完了しない Then プロセスが強制終了されタイムアウトログが出力される
- 例外・エラー:
  - EH-017: If プロセス強制終了に失敗した（OSError等） then the system shall 警告ログを出力しユーザーに手動終了を促すメッセージを表示する

### REQ-901: ファイルシステム出力構造
- 種別: EARS-普遍
- 優先度: MUST
- 要件文(EARS): システムは全ての生成物を`output/lp-{slug}/`配下の固定ディレクトリ構造（`copy.md`、`research/`、`prompts/`、`sections/`、`report.md`、`progress.json`）で出力しなければならない。
- 根拠/目的: 生成物の所在を予測可能にし中断再開や再利用の手順を統一するため
- 受入テスト(GWT):
  - AT-020: Given LP生成が完了した When `output/lp-{slug}/`の内容を確認する Then `copy.md`と`research/`と`prompts/`と`sections/`と`report.md`と`progress.json`が存在する
- 例外・エラー:
  - EH-018: If `output/`ディレクトリが存在しない then the system shall 自動的にディレクトリを作成する

### REQ-902: Windows環境互換性
- 種別: EARS-普遍
- 優先度: MUST
- 要件文(EARS): システムはWindows 11環境で動作し全てのPython実行時に環境変数`PYTHONIOENCODING=utf-8`と`PYTHONUTF8=1`を設定しなければならない。
- 根拠/目的: Windows環境のcp932エンコーディングによる日本語文字化けを防止するため
- 受入テスト(GWT):
  - AT-021: Given Windows 11環境である When スキルを実行する Then 全てのPythonプロセスの環境変数に`PYTHONIOENCODING=utf-8`と`PYTHONUTF8=1`が設定されている
- 例外・エラー:
  - EH-019: If 環境変数の設定に失敗した then the system shall コマンドライン引数`-X utf8`をPython実行時に追加する

## 12. セキュリティ/プライバシー要件
- ナレッジプロンプトは`.claude/skills/lp-nanobanana-ss/knowledge/`にローカル保存し外部に送信しない
- Geminiへの認証情報はpatchrightのブラウザプロファイルで管理しスキル内にハードコードしない
- 生成された画像はローカルの`output/`ディレクトリにのみ保存し自動アップロードは行わない
- Stage 2のWeb UIではAPIキーをサーバーサイドの環境変数（`.env`）で管理しフロントエンドに露出させない

## 13. ログ/監視/運用要件
- 各セクションの画像生成の開始、完了、失敗をコンソールに出力する（形式: `[LP-GEN] Section {N}/{Total}: {status} ({elapsed}s)`）
- 生成結果の全体レポートは`report.md`に出力する（REQ-005参照）
- 中断再開の状態は`progress.json`で管理する（REQ-011参照）

## 14. 未解決事項（Open Questions）
- なし

## 15. SLO/SLI/SLA（信頼性目標）

| Metric | Target | Measurement |
|--------|--------|-------------|
| 画像生成成功率 | 1回の実行で全セクションの80%以上が成功 | success_sections / total_sections |
| 1セクション生成時間 | 240秒以内 | NanoBananaプロセスの経過時間 |
| 中断再開成功率 | progress.jsonが存在する場合100%正しく再開 | 再開テストの成功/失敗 |

## 16. 関連ADR（技術決定記録）

| ADR ID | 決定内容 | Status |
|--------|---------|--------|
| ADR-001 | Stage 1はブラウザ版NanoBanana（scripts/run.py経由）を使用しStage 2でAPI版に移行する | Accepted |
| ADR-002 | 画像生成はセクション単位で順次実行する（並列実行はブラウザ制約により不可） | Accepted |
| ADR-003 | デザインリサーチはスクリーンショットとAI分析で行いHTML/CSSパースは行わない | Accepted |
| ADR-004 | LPセクション構成は固定7セクション（ファーストビュー、問題提起、解決策、ベネフィット、お客様の声、特典、CTA）とする | Accepted |

## 17. セキュリティ脅威と対策

| 脅威 | リスク | 緩和策 | 対応要件 |
|------|--------|--------|---------|
| ナレッジプロンプトの外部漏洩 | 中 | ローカルファイルとして保存、git管理外（.gitignore） | REQ-001 |
| 参考URLからの悪意あるコンテンツ取得 | 低 | スクリーンショットのみ取得（JS実行はブラウザサンドボックス内） | REQ-002 |

## 18. ガードレール（AI制約）

- 許可パス: `src/lp-creator-ss/`, `.claude/skills/lp-nanobanana-ss/`, `output/lp-*/`, `.kiro/specs/lp-nanobanana-ss/`
- 禁止パス: `.env*`, `secrets/`, `~/.ssh/`, `.claude/skills/nanobanana-pro/scripts/`（読み取りのみ許可、編集禁止）
- 承認が必要な操作: NanoBanana APIキーの設定（Stage 2）、本番デプロイ

## 19. 運用手順書参照

- NanoBanana認証切れ時: `auth_manager.py setup`を実行してGeminiに再ログイン
- 画像生成失敗時: `report.md`を確認し失敗セクションのみ再実行
- ナレッジプロンプト更新時: `knowledge/`ディレクトリ内のファイルを差し替え

## 20. 成熟度レベル

| Level | 名称 | 達成条件 | 現在 |
|-------|------|---------|------|
| L1 | Draft | requirements.md作成 | ✅ |
| L2 | Review Ready | C.U.T.E. >= 90 | ✅ (100/100) |
| L3 | Implementation Ready | C.U.T.E. >= 98, レビュー承認 | ✅ (100/100) |
| L4 | Production Ready | Stage 1実装完了, テスト完了 | ✅ SKILL.md + knowledge/ 完成 |
| L5 | Enterprise Ready | Stage 2実装完了, Web UI稼働 | - |
