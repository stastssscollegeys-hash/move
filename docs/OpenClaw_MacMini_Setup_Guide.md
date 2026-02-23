# OpenClaw × Mac mini セットアップ完全ガイド
## 〜超初心者でもできる！AIエージェントをMac miniに構築する手順書〜

**最終更新: 2026年2月**

---

## 目次

1. [この手順書について](#1-この手順書について)
2. [全体像 - 何を作るのか](#2-全体像---何を作るのか)
3. [用語集 - 最初に知っておきたい言葉](#3-用語集---最初に知っておきたい言葉)
4. [事前に準備するもの](#4-事前に準備するもの)
5. [STEP 1: Mac miniの初期セットアップ](#step-1-mac-miniの初期セットアップ)
6. [STEP 2: OpenClawインストール・初期設定](#step-2-openclawインストール初期設定)
7. [STEP 3: OpenClawの特徴を理解する](#step-3-openclawの特徴を理解する)
8. [STEP 4: Discord連携（スマホからAIに話しかける）](#step-4-discord連携スマホからaiに話しかける)
9. [STEP 5: LINE公式アカウントを準備する](#step-5-line公式アカウントを準備する)
10. [STEP 6: OpenClawとLINEを接続する](#step-6-openclawとlineを接続する)
11. [STEP 7: Mac mini常時稼働設定](#step-7-mac-mini常時稼働設定)
12. [セキュリティ注意事項（Mac mini運用）](#セキュリティ注意事項mac-mini運用)
13. [トラブルシューティング](#トラブルシューティング)
14. [料金の目安](#料金の目安)
15. [おわりに](#おわりに)
16. [付録A: AWS EC2へのデプロイ](#付録a-aws-ec2へのデプロイ)

---

## 1. この手順書について

この手順書は、**コーディングやサーバーの知識がゼロ**の方でも、AIエージェント「OpenClaw」をMac miniに構築し、LINE公式アカウントやDiscordと連携できるようにするためのガイドです。

**ゴール:** LINEやDiscordでメッセージを送ると、Mac mini上のAIが24時間自動で返答してくれる仕組みを作る

**所要時間の目安:** 2〜4時間（初めての場合）

---

## 2. 全体像 - 何を作るのか

完成すると、以下のような仕組みが動きます：

```
あなた（スマホ）
  │
  │ LINEでメッセージ送信
  ▼
LINE公式アカウント
  │
  │ Webhook（自動転送）
  ▼
Mac mini（自宅サーバー）
  │
  │ OpenClawが受信
  ▼
OpenClaw（AIエージェント）
  │
  │ Claude Opus 4.5/4.6 が考えて返答
  ▼
LINE公式アカウント
  │
  │ 自動返信
  ▼
あなた（スマホ）に返事が届く！
```

**ポイント:**
- Mac miniが24時間動き続けるので、自分のスマホやパソコンを閉じていてもOK
- LINEだけでなく、Discord・Slack・Telegramなどとも連携可能
- OpenClawの裏側ではClaude（AI）が動いているので、高度な会話や作業指示が可能

---

## 3. 用語集 - 最初に知っておきたい言葉

難しい言葉がたくさん出てくるので、先に覚えておきましょう。

| 用語 | 分かりやすく言うと | 例え |
|------|-------------------|------|
| **ngrok** | ローカル環境を一時的に外部公開するツール | 「仮設の玄関」 |
| **HTTPS** | 暗号化された安全な通信 | 「鍵付きの手紙」 |
| **HTTP** | 暗号化されていない通信 | 「普通のハガキ」 |
| **Webhook** | あるイベントが起きたら自動で通知する仕組み | 「自動転送設定」 |
| **API** | ソフトウェア同士が通信するための窓口 | 「注文カウンター」 |
| **APIキー** | APIを使うための認証コード | 「会員証・パスワード」 |
| **OpenClaw** | オープンソースのAIエージェント基盤 | 「AI秘書の体」 |
| **Claude** | Anthropic社のAI | 「AI秘書の脳みそ」 |
| **CLI** | コマンドライン（文字入力）で操作するツール | 「テキスト版リモコン」 |
| **ターミナル** | コマンドを入力する画面 | 「黒い画面」 |
| **デーモン** | バックグラウンドで常時動くプログラム | 「24時間勤務のスタッフ」 |
| **ポート** | 通信の入り口の番号 | 「玄関（22番）、裏口（80番）など」 |

> **AWS/EC2関連の用語**は、[付録A: AWS EC2へのデプロイ](#付録a-aws-ec2へのデプロイ) を参照してください。

---

## 4. 事前に準備するもの

以下を先に用意してください：

- [ ] **Mac mini**（Apple Silicon搭載モデル推奨）
- [ ] **インターネット接続**
- [ ] **LINEアカウント**（公式アカウント作成用）
- [ ] **Discordアカウント**（Discord連携用。既存のものでOK）
- [ ] **Anthropic（Claude）のアカウント**（APIキー取得用。https://console.anthropic.com/）

---

## STEP 1: Mac miniの初期セットアップ

Mac miniをOpenClawサーバーとして使うための初期セットアップです。
**Apple ID不要、Googleアカウント不要で全ツールインストールできます。**

---

### 前提知識：MacとWindowsの違い（Windowsユーザー向け）

#### キーボードの対応表

| Windows | Mac | キーの場所 |
|---------|-----|-----------|
| `Ctrl` | `Command（⌘）` | スペースバーのすぐ左右にあるキー |
| `Alt` | `Option（⌥）` | Commandキーの外側にあるキー |
| `Shift` | `Shift（⇧）` | 同じ（左右にある上向き矢印のキー） |
| `Enter` | `Return` | 同じ位置 |
| `Backspace` | `Delete` | 同じ位置 |

**要するに：** Windowsで `Ctrl` を使っていた操作は、Macでは `Command` に置き換えるだけです。

| 操作 | Windows | Mac |
|------|---------|-----|
| コピー | `Ctrl + C` | `Command + C` |
| 貼り付け | `Ctrl + V` | `Command + V` |
| 全選択 | `Ctrl + A` | `Command + A` |
| 元に戻す | `Ctrl + Z` | `Command + Z` |

#### ターミナルの開き方

Windowsの「PowerShell」に相当するのがMacの「**ターミナル**」です。

**Launchpadから開く方法：**
1. 画面下のDock（アイコンが並んでいるバー）にあるロケットのアイコン「**Launchpad**」をクリック
2. 上部の検索欄に「**ターミナル**」と入力
3. 黒い画面のアイコン「ターミナル」をクリック

> **Windowsとの主な違い：**
> - `dir` → Macでは `ls`
> - パスの区切り: `\` → Macでは `/`
> - 例: Windows `C:\Users\名前\` → Mac `/Users/名前/`

#### プライベートブラウズの開き方

CursorやClaude CodeのログインでGoogleアカウントを使うとき、
**プライベートブラウズで認証する**のがルールです。

**Safariの場合：**
1. Safariを開く（Dockにあるコンパスのアイコン）
2. 画面一番上のメニューバーで「**ファイル**」をクリック
3. 「**新規プライベートウィンドウ**」をクリック
4. アドレスバーの周囲が**暗い色**になっていればOK

**Chromeの場合：**
1. Chromeを開く
2. 画面一番上のメニューバーで「**ファイル**」をクリック
3. 「**新しいシークレット ウィンドウ**」をクリック
4. 画面全体が**暗い色**になっていればOK

> キーボードショートカット: どちらも `Shift + Command + N` で開けます。

#### ツールの認証でプライベートブラウズを使う手順

CursorやClaude Codeのログイン時、毎回この流れです。

1. ツール（CursorやClaude Code）でログインボタンを押す
2. ブラウザが自動で開く
3. そのブラウザの**アドレスバー**（URL欄）をクリック → `Command + A`（全選択）→ `Command + C`（コピー）
4. そのブラウザを閉じる（左上の赤い丸ボタン）
5. SafariまたはChromeで**プライベートウィンドウ**を開く（「ファイル」→「新規プライベートウィンドウ」）
6. アドレスバーをクリック → `Command + V`（貼り付け）→ `Return`
7. Googleアカウントでログイン
8. 認証完了 → プライベートウィンドウを閉じる
9. ツール側に戻ると認証が通っている

> 最初のセットアップ時だけの作業です。一度通ればしばらく再認証不要です。

---

### 1-1. Cursorをインストール

1. Safariを開く（Dockにあるコンパスのアイコン）
2. アドレスバーに **cursor.com** と入力して `Return`
3. 「Download」をクリック
4. ダウンロードされた `.dmg` ファイルを開く
5. Cursorのアイコンを「Applications」フォルダにドラッグ
6. Cursorを起動する（LaunchpadまたはApplicationsフォルダから）

**初回起動時のログイン：**

7. Cursorアカウントへのログインを求められる
8. **普段使っているCursorアカウントでOK**（エディタ設定とサブスクリプション情報しか入っていないので安全）
9. 「Googleで続ける」を選ぶ場合 → **前提知識の「プライベートブラウズで認証する手順」の通りにやる**

**「Open Cursor from Terminal」のインストール：**

10. Cursorの設定画面に「Open Cursor from Terminal」という項目と「Install」ボタンがある
11. **「Install」を押す**（ターミナルから `cursor` コマンドでCursorを起動できるようになる）

---

### 1-2. GitとNode.jsをインストール

CursorのAIチャットに頼めば両方入れてくれます。

**Gitのインストール：**
1. CursorのAIチャット（画面右側）に「**Gitをインストールしたい**」と入力
2. AIが必要なコマンドを提案・実行してくれる
3. 指示に従って進めれば完了
4. **確認：** ターミナルで `git --version` → `git version 2.x.x` と出ればOK

**Node.jsのインストール：**
1. CursorのAIチャットに「**Node.jsをインストールしたい**」と入力
2. AIの指示に従って進めれば完了
3. **確認：** ターミナルで `node --version` → `v22.x.x` と出ればOK

> 「command not found」と出たら、ターミナルを一度閉じて開き直してから再度試してください。

**自分でコマンドを打つ場合（参考）：**
```
xcode-select --install    # Git（ポップアップが出たら「インストール」）
```
Node.jsは nodejs.org から「LTS」版をダウンロード → `.pkg` をダブルクリック → インストーラーに従う

---

### 1-3. Claude Codeをインストール

Git・Node.jsと同じく、CursorのAIに頼めばインストールできます。

1. CursorのAIチャットに「**Claude Codeをインストールしたい**」と入力
2. AIが `npm install -g @anthropic-ai/claude-code` を実行してくれる
3. 完了

**確認：** ターミナルで `claude --version` → バージョン番号が出ればOK

---

### 1-4. Claude Codeにログイン

1. Cursorのターミナルで `claude` と入力して `Return`
2. 認証URLが表示される → ブラウザが自動で開く
3. **プライベートブラウズで認証する**（前提知識の手順通り）：
   - 自動で開いたブラウザのURLをコピー → 閉じる → プライベートウィンドウで開き直す → 認証 → 閉じる
4. Cursorのターミナルに戻ると、Claude Codeの対話画面が表示される

**ここまで来ればClaude Codeが使える状態です！**

---

### 1-5. OpenClawをインストール

Claude Codeが使えるようになったので、Claude Codeに頼んでインストールできます。

Cursorのターミナルで `claude` を起動した状態で：
```
OpenClawをインストールしたい
```
と入力すれば、Claude Codeが手順を案内してくれます。

**または自分でやる場合：**
```
npm install -g openclaw@latest
```
インストール後の初期セットアップ：
```
openclaw onboard --install-daemon
```

詳しい設定は [STEP 2: OpenClawインストール・初期設定](#step-2-openclawインストール初期設定) を参照。

---

### セットアップ完了チェックリスト

| 手順 | やったこと | 確認方法 |
|------|-----------|---------|
| 1-1 | Cursor | Cursorが開ける・ログイン済み |
| 1-2 | Git・Node.js | `git --version` / `node --version` が表示される |
| 1-3 | Claude Code | `claude --version` が表示される |
| 1-4 | Claude Code認証 | `claude` で対話画面が表示される |
| 1-5 | OpenClaw | `openclaw status` で稼働確認 |

---


## STEP 2: OpenClawインストール・初期設定

Mac miniにOpenClawをインストールして初期設定を行います。

### 前提条件

**Node.js 22以上** が必要です。まだの方は先にインストール：
- https://nodejs.org/ から「LTS」版をダウンロードしてインストール

**確認方法:**
```bash
node --version
```
`v22.x.x` 以上が表示されればOK。

### OpenClawのインストール

**Mac / Linux / WSL2の場合：**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

**Windows（PowerShell）の場合：**
```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

**または、npmを使う方法：**
```bash
npm install -g openclaw@latest
```

### OpenClawの初期セットアップ（オンボーディング）

```bash
openclaw onboard --install-daemon
```

> **注意:** このコマンドは単独で実行してください。他のコマンドと同じ行に入力するとエラーになります。

対話形式で画面が進んでいきます。以下の通りに選択してください。

---

#### 画面1: バージョン表示とセキュリティ警告

```
🦞 OpenClaw 2026.2.22-2 (45febec)

┌─ Security Notice ──────────────────────────────────────────────────┐
│  This bot can read files and run actions if tools are enabled.     │
│  A bad prompt can trick it into doing unsafe things.               │
│                                                                    │
│  If you're not comfortable with basic security and access control, │
│  don't run OpenClaw.                                               │
│                                                                    │
│  Recommended baseline:                                             │
│  - Pairing/allowlists + mention gating.                            │
│  - Sandbox + least-privilege tools.                                │
│  - Keep secrets out of the agent's reachable filesystem.           │
│  - Use the strongest model for inboxes.                            │
│                                                                    │
│  Run regularly:                                                    │
│  openclaw security audit --deep                                    │
│  openclaw security audit --fix                                     │
│                                                                    │
│  Must read: https://docs.openclaw.ai/gateway/security              │
└────────────────────────────────────────────────────────────────────╯
│
◇  I understand this is powerful and inherently risky
│  Yes ← Yesを選択
```

> **これは何？:** OpenClawはAIがファイルを読んだりアクションを実行できる強力なツールです。
> 悪意のあるプロンプトで危険な操作をさせられる可能性があるため、
> セキュリティのリスクを理解していますか？と聞いています。
> → **Yes** を選んで進めてOKです。

---

#### 画面2: Onboarding mode（セットアップモード選択）

```
◆  Onboarding mode
│  ● QuickStart (Configure details later via openclaw configure.)
│  ○ Manual
```

→ **`QuickStart`** を選択

> **QuickStart vs Manual の違い:**
> - **QuickStart**: 最低限の設定だけして素早く始められる。細かい設定は後から `openclaw configure` で変更可能
> - **Manual**: 全設定項目を1つずつ確認しながら進める。上級者向け
> → 初めての場合は QuickStart で十分です。

---

#### 画面3: QuickStart設定の確認

```
◇  QuickStart
│  Defaults applied:
│  Port: 3000 (gateway: 18789)
│  Data dir: ~/.openclaw
│  Auth: pairing (code-on-first-DM v0.1)
│  Gateway auth: Token (default)
│  Tailscale exposure: Off
│  Direct to chat channels.
```

→ 確認だけ。自動で次に進みます。

> **各設定の意味:**
> - **Port: 3000**: OpenClawが使うポート番号（LINE等のWebhook受信用）
> - **gateway: 18789**: 管理画面（ダッシュボード）のポート番号
> - **Data dir: ~/.openclaw**: 設定やデータの保存先（ホームディレクトリ直下）
> - **Auth: pairing**: 初回DM時にペアリングコードで認証する方式
> - **Gateway auth: Token**: 管理画面のログインにトークン認証を使用
> - **Tailscale exposure: Off**: VPN公開はオフ（後から設定可能）

---

#### 画面4: Model/auth provider（AIプロバイダー選択）

```
◆  Model/auth provider
│  ○ OpenAI (Codex OAuth + API key)  ← ChatGPT / GPT-4（OpenAI社）
│  ● Anthropic                       ← Claude（Anthropic社） ★これを選択
│  ○ Chutes                          ← Chutes AI
│  ○ vLLM                            ← 自前サーバーでAIモデルを動かす（上級者向け）
│  ○ MiniMax                         ← MiniMax社のモデル
│  ○ Moonshot AI (Kimi K2.5)         ← Kimi（中国発AIモデル）
│  ○ Google                          ← Google Gemini
│  ○ xAI (Grok)                      ← X（旧Twitter）のGrok
│  ○ Mistral AI                      ← Mistral AI（フランス発）
│  ○ Volcano Engine                  ← ByteDance（TikTok親会社）のAI基盤
│  ○ BytePlus                        ← ByteDance海外版
│  ○ OpenRouter                      ← 複数AIの統合ゲートウェイ（1つのAPIキーで複数モデル）
│  ○ Qwen                            ← Alibaba（アリババ）のAIモデル
│  ○ Z.AI                            ← ZAI
│  ○ Qianfan                         ← Baidu（百度）のAI基盤
│  ○ Copilot                         ← GitHub Copilot
│  ○ Vercel AI Gateway               ← Vercel AI Gateway
│  ○ OpenCode Zen                    ← OpenCode
│  ○ Xiaomi                          ← Xiaomi（シャオミ）のAI
│  ○ Synthetic                       ← Synthetic AI
│  ○ Together AI                     ← オープンソースAIモデルのホスティング
│  ○ Hugging Face                    ← オープンソースAIのハブ
│  ○ Venice AI                       ← プライバシー重視AI
│  ○ LiteLLM                         ← 複数AIモデルの統合プロキシ（自前サーバー用）
│  ○ Cloudflare AI Gateway           ← Cloudflare経由のAIゲートウェイ
│  ○ Custom Provider                 ← カスタム（自分で接続先を指定）
│  ○ Skip for now                    ← スキップ（後で設定）
```

→ **`Anthropic`** を選択

> **なぜ Anthropic か:**
> - OpenClawの裏側で動くAIとしてClaude（Anthropic社）を使うため
> - Claude Code と同じAnthropicアカウント・APIキーが使える
> - Claude Opus 4.6 / Sonnet 4.6 など最新モデルが選べる

---

#### 画面5: Anthropic auth method（Anthropic認証方法の選択）

```
◆  Anthropic auth method
│  ● Anthropic token (paste setup-token)  ← Claude MAXサブスク利用者はこちら ★これを選択
│  ○ Anthropic API key                    ← APIキーを直接入力（従量課金）
│  ○ Back                                 ← 前の画面に戻る
```

→ **`Anthropic token (paste setup-token)`** を選択

> **2つの認証方法の違い:**
> - **Anthropic token（setup-token）**: Claude MAXなどのサブスクリプションで使う方法。
>   月額定額でAPIコストを気にせず使える。`claude setup-token` コマンドでトークンを取得して貼り付ける
> - **Anthropic API key**: Anthropicダッシュボード（https://console.anthropic.com/）でAPIキーを発行して入力。
>   従量課金（使った分だけ請求）。サブスクリプションなしでも使える

---

#### 画面5-b: トークンの貼り付け

```
◆  Paste Anthropic setup-token
│  _
```

この画面が出たら、トークンを貼り付けて Enter を押します。
トークンの取得方法は以下の通りです。

---

**【トークン取得手順】**

**1. 別のターミナルウィンドウを開く**
- Dock のターミナルアイコンを右クリック →「新規ウィンドウ」
- または `Command + N`（ターミナルがアクティブな状態で）

**2. 別ターミナルで `claude setup-token` を実行**
```bash
claude setup-token
```

**3. プライベートブラウズで認証**
- ブラウザが自動で開く
- 自動で開いたブラウザの**アドレスバーのURL**をコピー（`Command + A` → `Command + C`）
- そのブラウザを閉じる
- Safari またはChromeで**プライベートウィンドウ**を開く（`Shift + Command + N`）
- URLを貼り付けて `Return`
- Anthropicアカウント（Claude MAX）でログイン → 「承認する」をクリック
- プライベートウィンドウを閉じる

**4. 表示されたトークンをコピーしてOpenClaw画面に貼り付け**
- `claude setup-token` を実行したターミナルにトークン（長い文字列）が表示される
- トークンをマウスで選択 → `Command + C` でコピー
- OpenClawのオンボーディング画面（`Paste Anthropic setup-token` の画面）に戻る
- `Command + V` で貼り付け → `Return`

---

#### 画面5-c: Token name（トークン名の設定）

```
◆  Token name (blank = default)
│  default
```

→ **そのまま Enter**（`default` のまま）

> トークンに名前をつけるかどうかの設定です。
> 複数のトークンを使い分ける場合に名前を変えますが、
> 通常は1つだけなので `default` で問題ありません。

---

#### 画面6: Default model（デフォルトモデルの選択）

```
◆  Default model
│  ○ Keep current (anthropic/claude-sonnet-4-6)  ← 現在の初期値（sonnet）
│  ○ Enter model manually                        ← モデル名を手入力
│  ○ anthropic/claude-haiku-4-5-20251001
│  ○ anthropic/claude-haiku-4-5
│  ○ anthropic/claude-opus-4-20250514
│  ○ anthropic/claude-opus-4-0
│  ○ anthropic/claude-opus-4-1-20250805
│  ○ anthropic/claude-opus-4-1
│  ○ anthropic/claude-opus-4-5-20251101
│  ○ anthropic/claude-opus-4-5
│  ● anthropic/claude-opus-4-6                    ← ★これを選択（最新最強）
│  ○ anthropic/claude-sonnet-4-20250514
│  ○ anthropic/claude-sonnet-4-0
│  ○ anthropic/claude-sonnet-4-5-20250929
│  ○ anthropic/claude-sonnet-4-5
│  ○ anthropic/claude-sonnet-4-6
```

→ **`anthropic/claude-opus-4-6`** を選択

> **モデルの選び方ガイド:**
>
> | モデル | 性能 | 速度 | 用途 |
> |--------|------|------|------|
> | **claude-opus-4-6** | 最高 | 普通 | 複雑な推論・長文・コード生成。最も賢い ★おすすめ |
> | **claude-sonnet-4-6** | 高い | 速い | バランス型。日常的なタスクに十分 |
> | **claude-haiku-4-5** | 普通 | 最速 | 簡単なタスク。応答が速い |
>
> - 末尾の数字が大きいほど新しいバージョン（4-6 > 4-5 > 4-1 > 4-0）
> - 日付付き（例: `-20250514`）は特定日のスナップショット。日付なしが最新
> - 後から `openclaw configure` で変更可能

---

#### 画面7: Select channel（チャットチャンネルの選択）

```
◆  Select channel (QuickStart)
│  ○ Telegram (Bot API)                 ← Telegramボット
│  ○ WhatsApp (QR link)                 ← WhatsApp連携
│  ○ Discord (Bot API)                  ← Discordボット
│  ○ IRC (Server + Nick)                ← IRC（古いチャット）
│  ○ Google Chat (Chat API)             ← Google Chat
│  ○ Slack (Socket Mode)                ← Slack連携
│  ○ Signal (signal-cli)                ← Signal（暗号化メッセンジャー）
│  ○ iMessage (imsg)                    ← iMessage（Apple）
│  ○ Feishu/Lark (飞书)                 ← 飛書/Lark（中国版Slack）
│  ○ Nostr (NIP-04 DMs)                 ← Nostr（分散型SNS）
│  ○ Microsoft Teams (Bot Framework)    ← Microsoft Teams
│  ○ Mattermost (plugin)                ← Mattermost（自前チャット）
│  ○ Nextcloud Talk (self-hosted)       ← Nextcloud Talk
│  ○ Matrix (plugin)                    ← Matrix（分散型チャット）
│  ○ BlueBubbles (macOS app)            ← BlueBubbles（Mac用iMessage）
│  ○ LINE (Messaging API)               ← LINE公式アカウント連携
│  ○ Zalo (Bot API)                     ← Zalo（ベトナムのメッセンジャー）
│  ○ Zalo (Personal Account)            ← Zalo個人アカウント
│  ○ Synology Chat (Webhook)            ← Synology NASのチャット
│  ○ Tlon (Urbit)                       ← Urbitネットワーク
│  ● Skip for now                       ← スキップ（後で設定） ★これを選択
```

→ **`Skip for now`** を選択

> **なぜスキップ？:**
> - チャンネル連携は後から `openclaw configure` や `openclaw plugins install` で設定できる
> - まずはOpenClaw本体の動作確認を先にするのが安全
> - LINE連携が必要な場合は、後で「LINE (Messaging API)」を設定する（STEP 5〜6 参照）

#### 画面8: 設定ファイル・ディレクトリの自動作成

```
Updated ~/.openclaw/openclaw.json          ← 設定ファイルが作成された
Workspace OK: ~/.openclaw/workspace        ← ワークスペースディレクトリ
Sessions OK: ~/.openclaw/agents/main/sessions  ← セッション保存先
```

→ 自動で進みます（操作不要）

> **作成されたもの:**
> - `~/.openclaw/openclaw.json` — OpenClawのメイン設定ファイル
> - `~/.openclaw/workspace/` — 作業ディレクトリ
> - `~/.openclaw/agents/main/sessions/` — AIエージェントの会話セッション保存先
> すべて `~/.openclaw/` の中（kaihatu1やDEVには影響なし）

---

#### 画面9: Skills status / Configure skills（スキルの設定）

```
◇  Skills status ─────────────╮
│                             │
│  Eligible: 6                │  ← 使えるスキル: 6個
│  Missing requirements: 45   │  ← 必要条件が足りないスキル: 45個（後から追加可能）
│  Unsupported on this OS: 0  │  ← このOSで非対応: 0個
│  Blocked by allowlist: 0    │  ← 許可リストでブロック: 0個
│                             │
├─────────────────────────────╯
│
◆  Configure skills now? (recommended)
│  ● Yes / ○ No
```

→ **`Yes`** を選択

> **スキルとは？:**
> OpenClawに追加できる機能のこと。例えばWeb検索、ファイル操作、コード実行など。
> - **Eligible: 6** — 今すぐ使えるスキルが6つある
> - **Missing requirements: 45** — 追加のツールやAPIキーが必要なスキルが45個ある（後から設定可能）
> - 後から `openclaw skills` コマンドで管理できる

#### 画面10: Install missing skill dependencies（スキルの依存関係インストール）

```
◆  Install missing skill dependencies
│  ◼ Skip for now (Continue without installing dependencies)  ★これにチェック
│  ◻ 🔐 1password          ← パスワード管理
│  ◻ 📝 apple-notes        ← Apple メモ連携
│  ◻ ⏰ apple-reminders    ← Apple リマインダー連携
│  ◻ 🐻 bear-notes         ← Bear（メモアプリ）連携
│  ◻ 📰 blogwatcher        ← ブログ監視
│  ◻ 🫐 blucli             ← Bluetooth操作
│  ◻ 📸 camsnap            ← カメラ撮影
│  ◻ 🧩 clawhub            ← OpenClawスキルハブ
│  ◻ 🎛️ eightctl           ← Elgato Stream Deck操作
│  ◻ ♊️ gemini             ← Google Gemini連携
│  ◻ 🧲 gifgrep            ← GIF検索
│  ◻ 🎮 gog                ← GOGゲーム管理
│  ◻ 📍 goplaces           ← 場所検索
│  ◻ 📧 himalaya           ← メールクライアント
│  ◻ 📨 imsg               ← iMessage連携
│  ◻ 📦 mcporter           ← MCPサーバー管理
│  ◻ 📊 model-usage        ← AIモデル使用量表示
│  ◻ 🍌 nano-banana-pro    ← 画像生成
│  ◻ 📄 nano-pdf           ← PDF操作
│  ◻ 💎 obsidian           ← Obsidian（ノートアプリ）連携
│  ◻ 🎙️ openai-whisper     ← 音声文字起こし
│  ◻ 💡 openhue            ← Philips Hue照明操作
│  ◻ 🧿 oracle             ← AI占い
│  ◻ 🛵 ordercli           ← 注文管理
│  ◻ 👀 peekaboo           ← スクリーン監視
│  ◻ 🗣️ sag                ← 音声合成
│  ◻ 🌊 songsee            ← 楽曲検索
│  ◻ 🔊 sonoscli           ← Sonosスピーカー操作
│  ◻ 🧾 summarize          ← 要約
│  ...他
```

→ **`Skip for now`** にチェックを入れて Enter

> **これは何？:**
> 各スキルが動くために必要な追加ツールをインストールするかどうかの画面です。
> 例えば `apple-notes` を使うにはAppleのメモアプリとの連携ツールが必要、など。
> 今は全部スキップして大丈夫。後から必要なスキルだけ個別にインストールできます：
> ```bash
> openclaw skills install スキル名
> ```

#### 画面11: APIキーの設定（各種スキル用）

この後、スキルごとにAPIキーを設定するか聞かれます。
**すべて `No` でOK**です（後から設定可能）。

```
◆  Set GOOGLE_PLACES_API_KEY for goplaces?
│  ○ Yes / ● No                              ★ No を選択
```

> **Tips:** この後も同様に「〇〇のAPIキーを設定しますか？」と聞かれる場合があります。
> すべて **No** で進めてください。必要になったら後から `openclaw configure` で設定できます。

> **注意:** チェックボックス画面でスペースキーが反応しない場合は、
> **`英数`キー**（スペースバーの左）を押して日本語入力をオフにしてからスペースを押してください。

#### 画面12: APIキー設定の連続質問

以下のAPIキー設定が順番に表示されます。**すべて `No` を選択して Enter** でOKです：

```
Set GEMINI_API_KEY for nano-banana-pro?     → No
Set NOTION_API_KEY for notion?              → No
Set OPENAI_API_KEY for openai-image-gen?    → No
Set OPENAI_API_KEY for openai-whisper-api?  → No
Set ELEVENLABS_API_KEY for sag?             → No
```

> これらは画像生成・音声合成・ノート連携などのスキル用APIキーです。
> 今は不要。必要になったら後から `openclaw configure` で設定できます。

---

#### 画面13: Hooks（フック）の設定

```
◇  Hooks ──────────────────────────────────────────────────────────╮
│                                                                  │
│  Hooks let you automate actions when agent commands are issued.  │
│  Example: Save session context to memory when you issue          │
│  /new or /reset.                                                 │
│                                                                  │
│  Learn more: https://docs.openclaw.ai/automation/hooks           │
│                                                                  │
├──────────────────────────────────────────────────────────────────╯
│
◆  Enable hooks?
│  ◼ Skip for now                    ★ これにチェック
│  ◻ 🚀 boot-md                     ← 起動時にmdファイルを読み込む
│  ◻ 📎 bootstrap-extra-files       ← セッション開始時に追加ファイルを読む
│  ◻ 📝 command-logger              ← コマンドの実行ログを記録
│  ◻ 💾 session-memory              ← セッション終了時にメモリに保存
```

→ **`Skip for now`** にスペースでチェック → Enter

> **Hooksとは？:**
> エージェントのコマンド実行時に自動で追加アクションを行う仕組みです。
> 例えば `/new`（新規セッション）実行時に自動でコンテキストを保存する、など。
> 後から設定できるので今はスキップで問題ありません。

#### ポップアップ: Node.js ネットワークアクセス許可

```
┌──────────────────────────────────────────────────────────┐
│  "node.js" により、アプリによる、ネットワーク上の          │
│  デバイスからのデータの検索、接続、および収集が            │
│  許可されます。                                           │
│                                                          │
│            [許可しない]    [許可]                          │
└──────────────────────────────────────────────────────────┘
```

→ **「許可」** をクリック

> **なぜ許可が必要？:**
> OpenClawはNode.jsで動いており、以下の通信を行うため許可が必要です：
> - LINEやDiscordなど外部サービスとの通信（Webhook受信）
> - ダッシュボード（管理画面）の表示（http://127.0.0.1:18789/）
> - Anthropic APIへのリクエスト送信
> 「許可しない」を選ぶとOpenClawが正常に動作しません。

#### 画面14: Gateway サービスのインストール（自動）

```
Gateway service runtime ────────────────────────────────────────────╮
│  QuickStart uses Node for the Gateway service (stable + supported). │
├───────────────────────────────────────────────────────────────────╯

Installing Gateway service…..
Installed LaunchAgent: ~/Library/LaunchAgents/ai.openclaw.gateway.plist
Logs: ~/.openclaw/logs/gateway.log

◇  Gateway service installed.
```

→ 自動で進みます（操作不要）

> **何が起きたか:**
> - **Gateway（ゲートウェイ）サービス**がインストールされた
> - macOSの **LaunchAgent** として登録された → Mac起動時に自動で動く（デーモン化完了）
> - ログは `~/.openclaw/logs/gateway.log` に保存される

---

#### 画面15: エージェント・セッション情報（自動）

```
Agents: main (default)
Heartbeat interval: 1h (main)
Session store (main): ~/.openclaw/agents/main/sessions/sessions.json (0 entries)
```

→ 自動で進みます（操作不要）

> **表示内容:**
> - **Agents: main** — メインエージェントが作成された
> - **Heartbeat interval: 1h** — 1時間ごとに生存確認
> - **Session store: 0 entries** — まだ会話セッションはない（これから始める）

---

#### 画面16: Optional apps（オプションアプリ）

```
◇  Optional apps ────────────────────────╮
│  Add nodes for extra features:         │
│  - macOS app (system + notifications)  │
│  - iOS app (camera/canvas)             │
│  - Android app (camera/canvas)         │
├────────────────────────────────────────╯
```

→ 自動で進みます（操作不要）。後からアプリを追加できます。

---

#### 画面17: Control UI（管理画面の情報）

```
◇  Control UI ──────────────────────────────────────────────────────╮
│  http://127.0.0.1:18789/#token=xxxxxxxxxxxxxxxxxxxxxx             │
│  Gateway WS: ws://127.0.0.1:18789                                 │
│  Gateway: reachable                                               │
│  Docs: https://docs.openclaw.ai/web/control-ui                    │
├───────────────────────────────────────────────────────────────────╯
```

→ 自動で進みます（操作不要）

> **表示内容:**
> - **Control UI**: ブラウザで開ける管理画面のURL（トークン付き）
> - **Gateway: reachable** — ゲートウェイが正常に動いている
> - このURLはいつでも `openclaw dashboard` コマンドで開ける

---

#### 画面18: Token情報（参考表示）

```
◇  Token ──────────────────────────────────────────────────────────╮
│  Gateway token: shared auth for the Gateway + Control UI.        │
│  Stored in: ~/.openclaw/openclaw.json                            │
│  View token: openclaw config get gateway.auth.token              │
│  Generate token: openclaw doctor --generate-gateway-token        │
│  Open the dashboard anytime: openclaw dashboard --no-open        │
├──────────────────────────────────────────────────────────────────╯
```

→ 自動で進みます（操作不要）

> **管理画面関連のコマンド（後で使える）:**
> ```bash
> openclaw dashboard              # ブラウザで管理画面を開く
> openclaw dashboard --no-open    # URLだけ表示（ブラウザは開かない）
> openclaw config get gateway.auth.token  # ゲートウェイトークンを確認
> ```

---

#### 画面19: How do you want to hatch your bot?（ボットの起動方法）

```
◆  How do you want to hatch your bot?
│  ● Hatch in TUI (recommended)  ← ターミナルで対話画面を開く ★これを選択
│  ○ Open the Web UI             ← ブラウザで管理画面を開く
│  ○ Do this later               ← 後でやる
```

→ **`Hatch in TUI (recommended)`** を選択

> **選択肢の意味:**
> - **Hatch in TUI**: ターミナル上でOpenClawの対話画面（TUI = Terminal User Interface）が開く。
>   ここでAIと会話してボットの性格や名前を設定する。**推奨**
> - **Open the Web UI**: ブラウザの管理画面（http://127.0.0.1:18789/）で設定する
> - **Do this later**: スキップして後でやる

#### 画面20: TUI起動 — ボットとの初回対話

```
openclaw tui - ws://127.0.0.1:18789 - agent main - session main

session agent:main:main

 Wake up, my friend!

 Hey. I just came online — fresh out of the box, no memories, no name, nothing.
 Just me and a blinking cursor.

 So... who are you? And more importantly — who am I?
 Got a name in mind for me, or should we figure that out together?

 connected | idle
 agent main | session main (openclaw-tui) | anthropic/claude-opus-4-6 | think low | tokens ?/200k
```

→ **ボットに名前をつけて、日本語で話すように指示する**

> **これは何？:**
> OpenClawのAIボットが初めて起動しました。名前も性格もまだ何もない状態です。
> ここで名前や言語を設定します。

**入力例：**
```
名前は「Claw」にして。日本語で話して。
```

> **画面下部の情報:**
> - **connected | idle** — 正常に接続・待機中
> - **agent main** — メインエージェント
> - **anthropic/claude-opus-4-6** — 使用中のAIモデル
> - **tokens ?/200k** — コンテキストウィンドウ（最大200kトークン）

> **TUIの操作方法:**
> - メッセージを入力して `Return` で送信
> - `Ctrl + C` で終了（TUIを閉じる）
> - TUIを閉じてもOpenClawのデーモンはバックグラウンドで動き続ける

### 2-1. セキュリティ強化（インストール直後に必ず実行）

OpenClawの設定ファイルにはAPIキーやトークンが含まれるため、
インストール直後にアクセス権限を制限します。

**ターミナルで実行：**
```bash
find ~/.openclaw -type d -exec chmod 700 {} \;
find ~/.openclaw -type f -exec chmod 600 {} \;
```

> **コマンドの意味:**
> - 1行目: `~/.openclaw/` 内の**全ディレクトリ**を `700`（自分だけアクセス可能）にする
> - 2行目: `~/.openclaw/` 内の**全ファイル**を `600`（自分だけ読み書き可能）にする
>
> **注意:** `chmod 700 ~/.openclaw/` と `chmod 600 ~/.openclaw/*` だけだと、
> サブディレクトリ内の権限が足りずOpenClawが `EACCES: permission denied` エラーになります。
> 必ず上記の `find` コマンドを使ってください。

> **Claude Codeで自動実行も可能:**
> Claude Code上で作業している場合、このコマンドはClaude Codeが代わりに実行してくれます。
> 「セキュリティ強化して」と伝えればOKです。

**確認方法：**
```bash
ls -la ~/.openclaw/
```

以下のように `drwx------`（ディレクトリ）、`-rw-------`（ファイル）になっていればOK：
```
drwx------  11 ユーザー名  staff   352  .
-rw-------   1 ユーザー名  staff  1490  openclaw.json
-rw-------   1 ユーザー名  staff  1329  openclaw.json.bak
```

> **これは何をしている？:**
> - `chmod 700` — ディレクトリの中身を自分だけが見られるようにする
> - `chmod 600` — ファイルを自分だけが読み書きできるようにする
> - 他のユーザーがMac miniを使っても、APIキーやトークンは見えない

### 2-2. セットアップ完了チェック

ここまでで OpenClaw のインストールとセキュリティ設定が完了しました。

**確認コマンド：**
```bash
openclaw --version    # バージョン表示
openclaw status       # 稼働状態の確認
openclaw dashboard    # ブラウザで管理画面を開く
ls -la ~/.openclaw/   # 設定ファイルの権限確認
```

**TUIを再度開く場合：**
```bash
openclaw tui
```

---

---

## STEP 3: OpenClawの特徴を理解する

#### そもそもOpenClawって何が嬉しいの？（Claude Codeとの違い）

「Claude Codeで十分じゃない？」と思うかもしれません。
コーディングだけならClaude Codeで十分です。
OpenClawは**「AIを秘書として常駐させる」**ためのツールです。

| 機能 | Claude Code | OpenClaw |
|------|-------------|----------|
| **コーディング** | 得意 | できる |
| **常駐（24時間稼働）** | 使う時だけ起動 | **バックグラウンドでずっと動く** |
| **スマホから使える** | 不可 | **LINE・Discord・Telegramから話しかけられる** |
| **記憶の継続** | 毎回リセット | **セッションをまたいで覚えている** |
| **定期タスク（Cron）** | 不可 | **勝手にチェック・報告してくれる** |
| **ブラウザ自動化** | 不可 | **Webサイトを操作できる** |
| **マルチエージェント** | 不可 | **複数のAIを並列で走らせられる** |

**OpenClawの活用イメージ：**
- スマホのDiscordから「この記事のリサーチまとめて」と投げる
- 毎朝、定期タスクで今日の予定とニュースをまとめて通知してくれる
- SNSの反応を定期チェックして報告してくれる
- スクールの受講生からの質問を自動整理してくれる

> **つまり:** Claude Codeは「ツール」、OpenClawは「秘書」。
> 常駐させて、スマホから指示を出して、自動で仕事してもらう — それがOpenClawの世界です。

#### 定期タスクってどこに届くの？

定期タスク（Cron）の結果は、**連携したチャンネルに届きます**。
つまり、LINE・Discord・Telegramなどを先に連携しないと通知先がありません。

```
定期タスクの例: 毎朝8時に天気を教えて
    ↓
OpenClawが自動で実行
    ↓
結果をDiscord/LINE/Telegramに送信 ← ここにチャンネル連携が必要
```

なので、**まずDiscordかLINEを連携するのが次のステップ**です。

#### どのチャンネルを連携すべき？（Discord vs LINE）

| 項目 | Discord | LINE |
|------|---------|------|
| **セットアップの簡単さ** | **簡単（5分）** | やや面倒（20〜30分） |
| **接続方式** | WebSocket（直接接続） | Webhook（HTTPS必須） |
| **ngrok必要？** | **不要** | 必要（HTTPS化のため） |
| **やること** | Bot作成→トークン貼るだけ | 公式アカウント作成→Webhook→ngrok設定 |
| **スマホから使える？** | Discordアプリ | LINEアプリ |
| **日常使い** | 普段Discord使うなら便利 | 普段LINE使うなら便利 |

→ **まずはDiscordで連携するのがおすすめ**（圧倒的に簡単）

#### なぜDiscordはそのまま繋がるのに、LINEはngrokが必要なの？

接続の**方向**が逆だからです。

```
【Discordの場合】ボットが外に出ていく

  Mac mini（OpenClaw）  ──→  Discordサーバー
        ボットが          「メッセージありますか？」
        聞きに行く         と聞きに行く

  → 自分から出ていくだけなので、普通のインターネット接続でOK
```

```
【LINEの場合】LINEが訪ねてくる

  スマホ（LINE）  ──→  インターネット  ──→  Mac mini（OpenClaw）
   メッセージ送信        LINEサーバーが       「お届けに来ました」
                        Mac miniに届けに来る

  → 外からMac miniに入ってくる必要がある
  → でもMac miniは普通の家庭のネット回線なので「住所」がない
  → ngrokが「仮の住所（HTTPS URL）」を作ってくれる
```

**たとえ話：**
- **Discord** = ボットが郵便局に手紙を取りに行く（自分から出かけるだけ）
- **LINE** = 配達員が家に届けに来る（家の住所が必要 → ngrokが住所を作る）

> **ngrok（エヌグロック）とは？:**
> Mac miniのような家庭のパソコンを、一時的にインターネットに公開するツール。
> LINEは「HTTPS」という暗号化された安全な通信でしか接続できないため、
> ngrokがHTTPS化も同時にやってくれます。
> 無料プランがあるので、テスト用途ならコストゼロで使えます。

#### セキュリティは大丈夫？（既存アカウントで平気？）

**Discord — 既存の個人アカウントでOK：**
```
あなたのDiscordアカウント（管理者としてログイン）
  → Developer PortalでBot（ロボット）を作る ← Botは別人格
    → Botトークン（長い文字列）だけがMac miniに保存される
```
- あなたのDM・フレンドリスト・パスワードはMac miniに入らない
- Botは完全に別のアカウント。あなたの名前では発言しない
- 気に入らなければBotを消すだけ

**LINE — 既存の個人LINEでOK（管理者ログインのみ）：**
```
あなたの個人LINE（管理者としてログイン）
  → LINE公式アカウント（ビジネス用）を新しく作る ← 公式は別アカウント
    → チャンネルトークンとシークレットだけがMac miniに保存される
```
- 個人LINEのトーク履歴・友だちリストはMac miniに入らない
- お客さんが見るのはLINE公式アカウントの情報だけ
- あなたの個人LINEは管理画面にログインするためだけに使う
→ LINEは後から追加できます

---

### 3-1. OpenClawを触ってみる

#### TUIで話しかける

```bash
openclaw tui
```

**試してみること：**
```
自己紹介して。何ができるの？
簡単な自己紹介を書いて
Pythonでじゃんけんプログラムを作って
```

#### 管理画面（ダッシュボード）

```bash
openclaw dashboard
```

ブラウザで管理画面が開きます。チャンネル連携後に活きる画面です：
- ボットの会話履歴を確認
- スキルの追加・設定
- 稼働状態の監視

> **今の段階では:** TUIで動作確認できればOK。
> ダッシュボードはDiscord/LINE連携後の方が見る価値があります。

#### よく使うコマンド一覧

| コマンド | 説明 |
|----------|------|
| `openclaw tui` | ターミナルで対話画面を開く |
| `openclaw dashboard` | ブラウザで管理画面を開く |
| `openclaw status` | 稼働状態を確認 |
| `openclaw doctor` | 設定に問題がないかチェック |
| `openclaw skills` | 使えるスキル一覧 |
| `openclaw configure` | 設定を変更する |
| `openclaw logs` | ログを表示 |

#### 動作確認

```bash
openclaw doctor    # 設定に問題がないかチェック
openclaw status    # 起動状態を確認
```

TUIで話しかけてAIが返答すれば成功！

> **次のステップ:**
> Discordを連携して、スマホからOpenClawに話しかけられるようにしましょう。

---

---

## STEP 4: Discord連携（スマホからAIに話しかける）

DiscordにBotを作って、OpenClawと接続します。
これにより、スマホのDiscordアプリからAIに話しかけられるようになります。

> **所要時間:** 約5〜10分
> **必要なもの:** Discordアカウント（既存のものでOK）

#### Google Chromeのインストール（まだの場合）

Discord Developer Portalなどの管理画面操作にはブラウザが必要です。
Safariでも可能ですが、Chromeがおすすめです。

1. Safariで **google.com/chrome** にアクセス
2. 「Chromeをダウンロード」→ `.dmg` を開く → Applicationsにドラッグ
3. **ChromeにはGoogleアカウントでログインしない**（聞かれたらスキップ）

#### 注意: プライベートブラウズで作業する

Discordログイン時にGoogleやメールのセッションがブラウザに残る可能性があります。
**必ずプライベートブラウズで作業してください。**

1. Safari: `Shift + Command + N` → プライベートウィンドウが開く
2. Chrome: `Shift + Command + N` → シークレットウィンドウが開く

---

#### Step 1: Discord Developer PortalでBotを作成

1. プライベートブラウズで **https://discord.com/developers/applications** を開く
2. Discordアカウントでログイン。方法は3つ：
   - **QRコード**（おすすめ）: スマホのDiscordアプリでQRを読み取る → 「確認」をタップ
   - **メールアドレス + パスワード**: 登録済みのメール・パスワードを入力
   - **Googleアカウント**: 「Googleで続ける」を選択
3. 右上の **「New Application」** をクリック
4. 名前を入力（例：`SubaClaw`）→ チェックボックスに同意 → **「Create」**

---

#### Step 2: Botを有効化してトークンを取得

1. 左メニューの **「Bot」** をクリック
2. **「Reset Token」** をクリック
3. 確認画面が出たら **「Yes, do it!」** をクリック
4. トークン（長い文字列）が表示される → **コピー**（`Command + C`）

> **超重要:** このトークンは**この画面でしか確認できません**。
> ページを離れると二度と表示されないので、必ずコピーしてください。
> メモ帳に一時保存してもOKですが、**設定が終わったらメモは消してください**。
> もしコピーし忘れた場合は、もう一度「Reset Token」すれば新しいトークンが発行されます。

---

#### Step 3: Botの権限を設定（Message Content Intent）

1. 同じ「Bot」ページを**下にスクロール**する
2. **「Privileged Gateway Intents」** というセクションを探す
3. **「Message Content Intent」** のトグルを **オン**（青色）にする
4. 画面下部に緑色のバーで **「Save Changes」** が表示される → **クリック**

> **これは何？:**
> Botがユーザーのメッセージの中身を読めるようにする権限です。
> これがオフだと、Botはメッセージが来たことは分かるけど内容が読めません。

---

#### Step 4: BotをDiscordサーバーに招待

**4-1. 招待URLを作る**

1. 左メニューの **「OAuth2」** をクリック
2. その下に表示されるサブメニューの **「URL Generator」** をクリック

3. 画面に **「SCOPES」** セクションが表示される（チェックボックスがたくさん並んでいる）

> **SCOPESの並び順（実際の画面）:**
> ```
> identify, email, connections, guilds, guilds.join, ...
> ```
> この中にはチェック不要なものが大量にあります。**`bot` だけにチェック**してください。
> `bot` は中段あたり、`webhook.incoming` の近くにあります。

4. **`bot`** にチェックを入れる

5. チェックを入れると、下に **「BOT PERMISSIONS」** セクションが表示される
   3つのカテゴリに分かれています：

> **BOT PERMISSIONSの並び順（実際の画面）:**
>
> **General Permissions（一般権限）** — ここはチェック不要
> ```
> Administrator, View Audit Log, Manage Server, Manage Roles, ...
> ```
>
> **Text Permissions（テキスト権限）** — ★ここに3つある
> ```
> Send Messages          ← ★チェック
> Create Public Threads, Create Private Threads,
> Send Messages in Threads, Send TTS Messages,
> Manage Messages, Pin Messages, Manage Threads,
> Embed Links, Attach Files, Mention Everyone,
> Use External Emojis, Use External Stickers,
> Add Reactions, Use Slash Commands, ...
> Read Message History   ← ★チェック（この並びの中にある）
> ```
>
> **Voice Permissions（音声権限）** — ここはチェック不要
> ```
> Connect, Speak, Video, ...
> ```

6. 以下の3つにチェック（Text Permissions内にあります）：
   - **`Send Messages`**（メッセージ送信） — Text Permissionsの一番上
   - **`Read Message History`**（メッセージ履歴の読み取り） — Text Permissionsの中段
   - **`View Channels`**（チャンネルの閲覧） — General Permissionsの中にある

7. ページ一番下に **「GENERATED URL」** が表示される
8. 右の **「Copy」** ボタンをクリック（またはURLを選択して`Command + C`）

**4-2. BotをサーバーにBotを追加する**

1. コピーしたURLを、**プライベートブラウズの新しいタブ**に貼り付けて開く
2. 「このBotをどのサーバーに追加しますか？」と聞かれる
3. Botを追加したい**Discordサーバーを選択**（ドロップダウンから選ぶ）
4. **「認証」（Authorize）** をクリック
5. 「認証しました」「Authorized」と表示されたらOK

> **Discordサーバーを持っていない場合：**
> スマホのDiscordアプリで「＋」ボタン →「サーバーを作成」から新しいサーバーを作ってください。
> テスト用なので名前は何でもOK（例：「AI テスト」）。
> サーバーを作ってから、もう一度この手順をやり直してください。

---

#### Step 5: OpenClawにBotトークンを設定

ターミナルに戻って以下を実行：

```bash
openclaw configure
```

対話形式で設定画面が進みます。

**画面1: 既存設定の確認**
```
◇  Existing config detected ─────────╮
│  workspace: ~/.openclaw/workspace  │
│  model: anthropic/claude-opus-4-6  │
│  gateway.mode: local               │
│  gateway.port: 18789               │
│  gateway.bind: loopback            │
├────────────────────────────────────╯
```
→ 確認だけ（操作不要）

**画面2: Gateway の場所**
```
◆  Where will the Gateway run?
│  ● Local (this machine)   ★ これを選択
│  ○ Remote (info-only)
```
→ **Local (this machine)** を選択（Mac mini上で動かすので）

**画面3: 設定セクションの選択**
```
◆  Select sections to configure
│  ○ Workspace
│  ○ Model
│  ○ Web tools
│  ○ Gateway
│  ○ Daemon
│  ● Channels       ★ これを選択
│  ○ Skills
│  ○ Health check
│  ○ Continue
```
→ **Channels** を選択

**画面4: チャンネル設定モード**
```
◆  Channels
│  ● Configure/link    ★ これを選択
│  ○ Remove channel config
```
→ **Configure/link** を選択

**画面5: チャンネル選択**
```
◆  Select a channel
│  ○ Telegram (Bot API)
│  ● Discord (Bot API)   ★ これを選択（↓キーで移動）
│  ○ WhatsApp (QR link)
│  ...
│  ○ LINE (Messaging API)
│  ...
│  ○ Finished
```
→ **Discord (Bot API)** を選択

> **「discord plugin not available」と表示された場合：**
> Discordプラグインがまだインストールされていません。
> `Ctrl + C` で設定画面を閉じて、以下のコマンドを実行してください：
> ```bash
> openclaw plugins install @openclaw/discord
> openclaw gateway restart
> openclaw configure
> ```
> インストール後、もう一度 configure → Channels → Configure/link → Discord の順で進めてください。

**画面6: プラグインの警告（自動表示）**
```
[plugins] plugins.allow is empty; discovered non-bundled plugins may auto-load: discord
[plugins] discord: loaded without install/load-path provenance;
  treat as untracked local code and pin trust via plugins.allow
  or install records
```
→ 自動で進みます（操作不要）。プラグインの信頼設定に関する警告です。
→ **この警告は重要です。** configure完了後に `plugins.allow` を設定する必要があります（Step 5.6で設定します）。

**画面7: Discord Bot トークンの手順表示**
```
◇  Discord bot token ──────────────────────────────────────────────╮
│                                                                  │
│  1) Discord Developer Portal → Applications → New Application   │
│  2) Bot → Add Bot → Reset Token → copy token                    │
│  3) OAuth2 → URL Generator → bot scope → invite                 │
│  Intents → Message Content Intent)                               │
│  Docs: discord                                                   │
│                                                                  │
├──────────────────────────────────────────────────────────────────╯
```
→ 手順の説明表示。これは既にStep 1〜4で完了済み。

**画面8: トークン入力**
```
◆  Enter Discord bot token
│  _
```
→ Step 2でコピーしたBotトークンを **貼り付け**（`Command + V`）→ **Enter**

> **セキュリティ注意:**
> トークンをチャットやメッセージに貼り付けて他人に見られた場合は、
> Developer Portal → Bot → Reset Token でトークンを再発行し、
> `openclaw configure` で再設定してください。

**画面9: チャンネルアクセスの設定**
```
◆  Configure Discord channels access?
│  ● Yes / ○ No
```
→ **Yes** を選択

> Botがどのチャンネルで反応するか制御するための設定です。

**画面10: アクセスモードの選択**
```
◆  Discord channels access
│  ● Allowlist (recommended)   ★ これを選択（おすすめ）
│  ○ Open (allow all channels)
│  ○ Disabled (block all channels)
```
→ **Allowlist (recommended)** を選択

> **選択肢の意味:**
> - **Allowlist（おすすめ）**: 指定したチャンネルだけでBotが反応する。セキュリティ上安全
> - **Open**: サーバー内の全チャンネルでBotが反応する。テスト用には楽だが、意図しない場所で動く可能性
> - **Disabled**: 全チャンネルでBotが反応しない（設定だけして後で有効化する場合）

**画面11: 許可チャンネルの指定**
```
◆  Discord channels allowlist (comma-separated)
│  My Server/#general, guildId/channelId, #support
```
→ Botを使いたいチャンネル名を入力。例：

```
#general
```

> **入力形式:**
> - `#チャンネル名` — チャンネル名だけで指定（例: `#general`）
> - `サーバー名/#チャンネル名` — サーバーを明示して指定（例: `My Server/#general`）
> - 複数指定する場合はカンマ区切り（例: `#general, #bot-test`）
> - まずは `#general` だけで十分。後から `openclaw configure` で追加できます

**画面12: チャンネル解決結果**
```
Discord channels ─────────────────────╮
│                                      │
│  Unresolved (kept as typed): #general│
```
→ 「Unresolved」と表示されても問題なし。チャンネル名がDiscord APIで解決できなかっただけで、入力した名前でそのまま保持されます。そのまま進めてOK。

**画面13: 次のチャンネル選択**
```
◆  Select a channel
│  ○ Telegram (Bot API)
│  ● WhatsApp (QR link) (not configured)
│  ○ Discord (Bot API)
│  ○ IRC (Server + Nick)
│  ○ Google Chat (Chat API)
│  ○ Slack (Socket Mode)
│  ○ Signal (signal-cli)
│  ○ iMessage (imsg)
│  ○ Feishu/Lark (飞书)
│  ○ Nostr (NIP-04 DMs)
│  ○ Microsoft Teams (Bot Framework)
│  ○ Mattermost (plugin)
│  ○ Nextcloud Talk (self-hosted)
│  ○ Matrix (plugin)
│  ○ BlueBubbles (macOS app)
│  ○ LINE (Messaging API)
│  ○ Zalo (Bot API)
│  ○ Zalo (Personal Account)
│  ○ Synology Chat (Webhook)
│  ○ Tlon (Urbit)
│  ○ Finished
```

> **各選択肢の意味:**
> これはDiscord以外にも追加で連携したいチャンネルがあるか聞かれています。
> - **Telegram / WhatsApp / Discord / IRC / Google Chat / Slack / Signal** — 各種メッセージングサービス
> - **iMessage** — Apple iMessage連携
> - **Feishu/Lark** — 中国系ビジネスチャット（飞书）
> - **Nostr** — 分散型SNSプロトコル
> - **Microsoft Teams / Mattermost / Matrix** — ビジネスチャット
> - **LINE (Messaging API)** — LINE公式アカウント連携（後でSTEP 5〜6で設定）
> - **Zalo** — ベトナムのメッセージングアプリ
> - **Synology Chat** — Synology NAS付属のチャット
> - **Tlon (Urbit)** — 分散型コンピューティングプラットフォーム
> - **Finished** — ★ これ以上チャンネルを追加しない場合に選択

→ **↓キーで「Finished」に移動して Enter**（Discordだけでまずは十分です）

> **もし「Discord already configured」と表示された場合:**
> 前回のセッション等で既にDiscordを設定済みの場合、以下の画面が出ます：
> ```
> ◆  Discord already configured. What do you want to do?
> │  ● Modify settings
> │  ○ Disable (keeps config)
> │  ○ Delete config
> │  ○ Skip (leave as-is)
> ```
> - **Modify settings** — 設定を変更する（トークンやチャンネルを変えたい場合）
> - **Disable (keeps config)** — 一時的に無効化する（設定は残るので再度有効化できる）
> - **Delete config** — 設定を完全に削除する
> - **Skip (leave as-is)** — ★ 何も変えずにそのまま進む
>
> → **「Skip (leave as-is)」を選んで Enter**

**画面14: Finishedを選択**

再び「Select a channel」画面が出たら、↓キーで一番下の **「Finished」** を選んで Enter。

**画面15: DM（ダイレクトメッセージ）アクセスポリシー**
```
◆  Configure DM access policies now? (default: pairing)
│  ○ Yes / ● No
```
→ **「No」のまま Enter**

> **解説:**
> - DMアクセスポリシーとは、ボットにDMで直接話しかけたときの認証方式です
> - デフォルトは「pairing」（初回にペアリングコードで認証する方式）
> - セキュリティ上問題ないので、デフォルトのままでOK
> - 後から `openclaw configure` で変更できます

**画面16: 設定保存 → メインメニューに戻る**
```
Config warnings:
- plugins.entries.discord: plugin discord: duplicate plugin id detected...

Config overwrite: /Users/shimizusubaru/.openclaw/openclaw.json
(sha256 ... -> ..., backup=...openclaw.json.bak)
Updated ~/.openclaw/openclaw.json
│
◆  Select sections to configure
│  ● Workspace (Set workspace + sessions)
│  ○ Model
│  ○ Web tools
│  ○ Gateway
│  ○ Daemon
│  ○ Channels
│  ○ Skills
│  ○ Health check
│  ○ Continue
```

> **警告について:**
> - 「duplicate plugin id detected」→ Discordプラグインが重複して登録されている警告。動作に問題なし
> - 「Config overwrite」→ 設定ファイルが新しい内容で上書きされた。バックアップ（`.bak`）も自動作成される

→ **↓キーで「Continue」に移動して Enter**（他のセクションは変更不要）

**画面17: 設定完了**
```
◇  Control UI ────────────────────────────────────╮
│                                                 │
│  Web UI: http://127.0.0.1:18789/                │
│  Gateway WS: ws://127.0.0.1:18789               │
│  Gateway: reachable                             │
│  Docs: https://docs.openclaw.ai/web/control-ui  │
│                                                 │
├─────────────────────────────────────────────────╯
│
└  Configure complete.
```

> **表示内容の意味:**
> - **Web UI** — ブラウザでOpenClawの管理画面を見るアドレス（ローカルのみ）
> - **Gateway WS** — WebSocket接続先（内部通信用）
> - **Gateway: reachable** — Gatewayが正常に動いている
> - **Configure complete.** — 設定保存完了！

#### Step 5.5: plugins.allow の設定（重要）

`openclaw configure` が完了したら、Discordプラグインを明示的に許可する設定が必要です。
これを設定しないと、ボットがメッセージに反応しません。

設定ファイルを開きます：
```bash
nano ~/.openclaw/openclaw.json
```

ファイルの中にある `"plugins"` セクションを探し、`"allow": ["discord"]` を追加します：

```json
"plugins": {
  "allow": ["discord"],    ← この行を追加
  "installs": {
    "discord": {
      ...
    }
  }
}
```

> **なぜこの設定が必要？**
> - OpenClawはセキュリティのため、外部プラグインを自動的には信頼しません
> - `plugins.allow` にプラグイン名を明示的に追加することで、そのプラグインの実行を許可します
> - この設定がないと、Discordプラグインが正しく動作せず、ボットがメッセージに応答しません

> **nanoエディタの使い方（初めての方向け）：**
> 1. 矢印キーで移動して編集位置へ
> 2. 文字を入力して編集
> 3. `Ctrl + O` → `Enter` で保存
> 4. `Ctrl + X` で終了

#### Step 5.6: Gatewayを再起動して設定を反映

設定を変更したら、Gatewayを再起動する必要があります：

```bash
openclaw gateway restart
```

> **なぜ再起動が必要？**
> - OpenClawのGatewayは常駐プロセス（バックグラウンドで動いているサービス）
> - 設定ファイルを変更しただけでは反映されない
> - `gateway restart` でプロセスが再起動され、新しい設定（Discord連携）が読み込まれる

実行結果：
```
Restarted LaunchAgent: gui/501/ai.openclaw.gateway
```
→ この表示が出れば再起動成功！

---

#### Step 6: プライベートブラウズを閉じる

Bot作成とサーバー招待が終わったら：
1. プライベートブラウズのウィンドウを**すべて閉じる**
2. これでGoogleアカウントのセッションも消える

---

#### Step 7: スマホから話しかけてテスト

1. スマホにDiscordアプリをインストール（まだの場合）
2. Botを追加したサーバーを開く
3. テキストチャンネルでBotにメンション（`@SubaClaw こんにちは`）
4. AIが返答すれば成功！

> **ペアリングコードが表示された場合：**
> 初回はセキュリティのため、ペアリングコードが表示されることがあります。
> ターミナルで以下を実行して承認してください：
> ```bash
> openclaw pairing list discord
> openclaw pairing approve discord コード番号
> ```

> **グループチャンネルで返答が来ない場合：**
> `openclaw configure` で設定した `guilds` のチャンネル名が、実際のDiscordチャンネル名と一致していない可能性があります。
> 日本語のDiscordサーバーでは、デフォルトチャンネルが「一般」（日本語）になっていますが、
> 設定では英語の「general」で登録されることがあります。
>
> **対処法:** `~/.openclaw/openclaw.json` を開き、`guilds` セクションを削除してください：
> ```json
> "channels": {
>   "discord": {
>     "enabled": true,
>     "groupPolicy": "open",
>     "streaming": "off"
>     // ← guilds セクションを削除（または正しいチャンネルIDに変更）
>   }
> }
> ```
> 変更後、`openclaw gateway restart` で再起動してください。

---

---

## STEP 5: LINE公式アカウントを準備する

### 5-1. LINE公式アカウントを作成

1. **https://www.linebiz.com/jp/** にアクセス
2. **「LINE公式アカウントを作成」** をクリック
3. LINEアカウントまたはメールアドレスでログイン
4. アカウント名を入力（例：「AIテスト」）
5. 業種を選択（テスト用なら何でもOK）
6. 作成完了

### 5-2. Messaging APIを有効にする

1. LINE公式アカウントの管理画面（LINE Official Account Manager）を開く
2. **「設定」** → **「Messaging API」** をクリック
3. **「Messaging APIを利用する」** をクリック
4. プロバイダーを選択または新規作成
5. 利用規約に同意して有効化

### 5-3. 必要な情報をメモする

**チャンネルシークレット:**
1. LINE Official Account Managerの **「設定」** → **「Messaging API」**
2. **「チャンネルシークレット」** の値をコピー

**チャンネルアクセストークン:**
1. **LINE Developers** （https://developers.line.biz/console/）にログイン
2. 該当のチャンネルを選択
3. **「Messaging API」** タブを開く
4. 一番下の **「チャンネルアクセストークン（長期）」** → **「発行」** をクリック
5. 表示されたトークンをコピー

> **メモしておく値（2つ）：**
> - チャンネルシークレット
> - チャンネルアクセストークン

---

## STEP 6: OpenClawとLINEを接続する

### 6-1. LINEプラグインをインストール

```bash
openclaw plugins install @openclaw/line
```

### 6-2. LINEの認証情報を設定

OpenClawに「公式LINEと紐付けたい」と伝えると、チャンネルアクセストークンとチャンネルシークレットを聞かれます。STEP 5でメモした値を入力してください。

**または手動で設定する場合：**

OpenClawの設定ファイル（`openclaw.json`）に以下を追加：
```json
{
  "channels": {
    "line": {
      "enabled": true,
      "channelAccessToken": "ここにチャンネルアクセストークンを貼る",
      "channelSecret": "ここにチャンネルシークレットを貼る",
      "dmPolicy": "pairing"
    }
  }
}
```

### 6-3. ngrokでHTTPS化（ローカルテスト用）

LINE公式アカウントのWebhookは **HTTPS** が必須です。
自分のパソコンは通常HTTPなので、ngrokを使ってHTTPS化します。

**ngrokのインストール:**

1. https://ngrok.com/ でアカウント作成（無料）
2. ダッシュボードからAuthToken（認証トークン）を取得
3. ngrokをインストール：

**Windows（PowerShell）：**
```powershell
choco install ngrok
# またはダウンロードページからZIPをダウンロードして展開
```

**Mac：**
```bash
brew install ngrok
```

**認証トークンを設定：**
```bash
ngrok config add-authtoken あなたのAuthToken
```

**HTTPSトンネルを開始：**
```bash
ngrok http 3000
```
（OpenClawのポート番号に合わせてください）

表示される `https://xxxxx.ngrok-free.app` のURLをコピー。

### 6-4. LINE Webhookを設定

1. **LINE Developers** のコンソールを開く
2. 該当チャンネルの **「Messaging API」** タブ
3. **「Webhook URL」** に以下の形式で入力：
   ```
   https://xxxxx.ngrok-free.app/line/webhook
   ```
4. **「Webhookの利用」** をオンにする
5. **「検証」** ボタンを押して「成功」と表示されればOK

### 6-5. 接続テスト

1. スマホでLINE公式アカウントを友達追加
2. 何かメッセージを送る（例：「こんにちは」）
3. **ペアリングコード** が表示される場合：
   ```bash
   openclaw pairing list line
   openclaw pairing approve line コード番号
   ```
4. もう一度メッセージを送ると、AIが返答する！

> **成功！** これでMac miniでOpenClawとLINEの接続ができました。
> Mac miniを常時稼働させるための設定は [STEP 7: Mac mini常時稼働設定](#step-7-mac-mini常時稼働設定) を参照してください。

---


---

## STEP 7: Mac mini常時稼働設定

> **いつやるか:** LINE連携などが完了し、OpenClawを24時間動かす段階になってからでOKです。
> 設定自体は5分で終わります。

Mac miniをサーバーとして24時間動かすための設定です。

**1. スリープを防ぐ**
1. 左上のAppleメニュー → 「システム設定」
2. 「エネルギー」をクリック
3. 「自動スリープを防ぐ」→ **オン**
4. 「ネットワークアクセスによるスリープ解除」→ **オン**
5. 「停電後に自動的に起動する」→ **オン**

**2. HDMIダミープラグの接続（ヘッドレス運用）**
- Mac miniにモニターを繋がずに使う場合、HDMIダミープラグ（Amazonで500〜1000円）を挿す
- これがないと画面解像度がおかしくなったり、リモートデスクトップが使いにくくなる

**3. その他のセキュリティ設定**
1. 「システム設定」→「プライバシーとセキュリティ」→ **FileVault → オン**（ディスク暗号化）
2. 「システム設定」→「ネットワーク」→ **ファイアウォール → オン**
3. 「システム設定」→「ユーザとグループ」→ **自動ログイン → オフ**

---

---

## セキュリティ注意事項（Mac mini運用）

Mac miniをサーバーとして常時稼働させる場合、**たくさんのアカウント**を使うことになります。
「これは個人アカウントでいいの？」「専用アカウントを作るべき？」を**全サービスごとに**整理しました。

---

### 大原則：「サーバーに個人情報を残さない」

Mac miniは24時間動き続けるサーバーです。普段使いのパソコンとは違います。

```
✅ サーバーに入れていいもの → 開発ツール、コード、APIキー
❌ サーバーに入れてはダメなもの → 個人のパスワード、メール、写真、連絡先
```

---

### 全アカウント一覧と判断ガイド

#### 1. Googleアカウント

| 項目 | 判断 |
|------|------|
| **新規作成が必要か？** | **推奨**（サーバー専用アカウントを1つ作る） |
| **個人アカウントを使っていいか？** | **NG** |
| **何に使うか** | Claude Code認証、将来的に必要になるかもしれないサービス用 |

**サーバー専用Googleアカウントの作り方：**
1. Safariのプライベートブラウズを開く（`⇧⌘N`）
2. **https://accounts.google.com/signup** にアクセス
3. 以下のように入力：
   - 名前: サーバー用の名前（本名でなくてOK）
   - メールアドレス: `自分の名前-server@gmail.com` のような分かりやすい名前
   - パスワード: 個人アカウントとは**別のパスワード**にする
4. 電話番号認証を完了
5. 作成したら**メールアドレスとパスワードを安全な場所にメモ**
6. プライベートブラウズを閉じる

> **このアカウントのルール：**
> - 個人のメール・ドライブ・写真とは完全に別
> - サーバー関連の認証にだけ使う
> - 重要なデータは入れない（使い捨てでOK）

---

#### 2. Apple ID / iCloud

| 項目 | 判断 |
|------|------|
| **個人のApple IDでログインしていいか？** | **NG（絶対ダメ）** |
| **サーバー専用Apple IDを作るべきか？** | **不要**（ログインしないのがベスト） |
| **Mac miniの初期設定で聞かれたら？** | **「あとで設定」「スキップ」を選ぶ** |

**なぜダメか：**
- iCloudにログインすると、写真・連絡先・メモ・キーチェーン（パスワード）が全部同期される
- Mac miniに自分の全データが入ってしまう
- サーバー用途にiCloudは不要

**もしMac mini初期設定でApple IDを求められたら：**
1. 「あとで設定」「スキップ」などの選択肢を探す
2. Apple IDなしでもMacは問題なく使える
3. App Storeは使えなくなるが、**OpenClawのセットアップにApp Storeは一切不要**

**「App Storeなしで大丈夫？」→ 大丈夫です。全ツールWebかターミナルで入ります：**

| ツール | インストール方法 | App Store |
|--------|-----------------|-----------|
| Google Chrome | google.com/chrome からダウンロード | 不要 |
| VS Code | code.visualstudio.com からダウンロード | 不要 |
| Cursor | cursor.com からダウンロード | 不要 |
| Git | ターミナルで `xcode-select --install` | 不要 |
| Node.js | nodejs.org からダウンロード | 不要 |
| Claude Code | ターミナルで `npm install -g @anthropic-ai/claude-code` | 不要 |
| ngrok | ngrok.com からダウンロード | 不要 |
| OpenClaw | ターミナルからインストール | 不要 |

> App Storeが必要になるのは、iMovieなどのApple純正アプリを使いたい場合だけです。
> サーバー用途では出番がないので、Apple IDログインは不要です。

**もしログインしてしまったら：**
1. 「システム設定」→「Apple ID」を開く
2. 一番下の「サインアウト」をクリック
3. 「iCloudデータのコピーを残しますか？」→ 「いいえ」
4. iCloudのデータがMac miniから削除される

---

#### 3. GitHub

| 項目 | 判断 |
|------|------|
| **個人アカウントを使っていいか？** | **OK（安全）** |
| **新規作成が必要か？** | 不要 |
| **何に使うか** | コードの管理、OpenClawのスキル管理 |

**なぜOKか：**
- GitHubにはコードしか入っていない（個人のパスワードや写真は含まれない）
- 既存のリポジトリにアクセスする必要がある
- 二重アカウントはGitHubの規約違反にもなりかねない

**ログイン方法（安全な手順）：**
```bash
# ターミナルで認証（ブラウザを使わない方法）
gh auth login
# → 「GitHub.com」を選択
# → 「HTTPS」を選択
# → 「Login with a web browser」を選択
# → 表示されるコードをメモし、ブラウザで認証
```

---

#### 4. Anthropic（Claude API）

| 項目 | 判断 |
|------|------|
| **個人アカウントを使っていいか？** | **OK（安全）** |
| **新規作成が必要か？** | 不要 |
| **何に使うか** | OpenClawのAIバックエンド、Claude Code |

**なぜOKか：**
- AnthropicアカウントにはAPI設定と課金情報しかない
- 個人情報の同期機能はない
- APIキーだけをMac miniに保存する

**注意点：**
- APIキーは環境変数（`.bashrc`）に保存する
- APIキーを他人に見せない・GitHubにプッシュしない
- 課金が心配なら、Anthropicのダッシュボードで利用上限を設定しておく

---

#### 5. Claude Code（Anthropic認証）

| 項目 | 判断 |
|------|------|
| **個人アカウントを使っていいか？** | **OK（ただしプライベートブラウズで認証）** |
| **新規作成が必要か？** | 不要 |
| **何に使うか** | ターミナルからAIを使う（Claude Code） |

**安全な認証手順（再掲）：**
1. ターミナルで `claude` を実行
2. 表示される認証URLをコピー
3. **自動で開いたブラウザは閉じる**
4. Safari → 「ファイル」→「新規プライベートウィンドウ」（`⇧⌘N`）
5. URLを貼り付けて認証
6. 認証後、プライベートウィンドウを閉じる

> Claude Codeの認証トークンはターミナル側（`~/.claude/`）に保存されます。
> ブラウザを閉じても認証は有効なままです。

---

#### 6. Cursor

| 項目 | 判断 |
|------|------|
| **個人アカウントを使っていいか？** | **OK（安全）** |
| **新規作成が必要か？** | サーバー専用アカウントを作ってもOK |
| **何に使うか** | コードエディタ（Claude Codeのインストールに使う） |

**なぜOKか：**
- Cursorアカウントにはエディタの設定しか入っていない
- 個人データの同期はない

**もし専用アカウントを作りたい場合：**
- サーバー専用Googleアカウントのメールアドレスで登録すればOK

---

#### 7. LINE（公式アカウント）

| 項目 | 判断 |
|------|------|
| **個人LINEアカウントを使っていいか？** | **管理者ログインのみOK** |
| **新規作成が必要か？** | **LINE公式アカウント（ビジネス用）は新規作成が必要** |
| **何に使うか** | OpenClawとLINEの接続 |

**仕組みの説明：**
```
個人LINE（あなたのスマホ）
  → LINE公式アカウント（ビジネス用）の管理者としてログイン
    → LINE公式アカウントとOpenClawを接続
```

**個人LINEアカウントが公開されることはない：**
- LINE公式アカウントは、個人アカウントとは完全に別物
- お客さんが見るのは「LINE公式アカウント」の情報だけ
- あなたの個人LINEの友だちリスト・トーク履歴は見えない

**Mac miniに入れる情報：**
- チャンネルアクセストークン（API用の長い文字列）
- チャンネルシークレット（API用の文字列）
- これらは個人情報ではなく、ビジネス用の接続キー

**安全に管理するコツ：**
- チャンネルアクセストークンとシークレットは環境変数に保存（`.env`ファイル）
- `.env`ファイルは**絶対にGitHubにプッシュしない**（`.gitignore`に追加）

---

#### 8. Discord

| 項目 | 判断 |
|------|------|
| **個人Discordアカウントを使っていいか？** | **Bot専用なのでOK（ただし注意あり）** |
| **新規作成が必要か？** | **Discord Botアカウントは新規作成が必要** |
| **何に使うか** | OpenClawとDiscordの接続 |

**仕組みの説明：**
```
あなたのDiscordアカウント（管理者）
  → Discord Developer Portal でBotを作成
    → Botトークンを取得
      → OpenClawにBotトークンを設定
```

**個人Discordアカウントの安全性：**
- Bot作成時にDiscordにログインする必要がある
- ただし、Mac miniに保存するのは**Botのトークン**だけ
- あなたのDiscordパスワードやDMはMac miniに入らない

**Discord Botの作り方：**
1. **https://discord.com/developers/applications** にアクセス
2. 「New Application」→ 名前を入力（例：「OpenClaw Bot」）
3. 左メニュー「Bot」→「Add Bot」
4. 「Token」の「Reset Token」→ トークンをコピー
5. このトークンをOpenClawに設定

**Mac miniに入れる情報：**
- Botトークン（長い文字列）
- これは個人情報ではなく、Botの接続キー

**安全に管理するコツ：**
- Botトークンは環境変数に保存（`.env`ファイル）
- `.env`ファイルは**絶対にGitHubにプッシュしない**
- Botトークンが漏洩したら、Discord Developer Portalで即座にリセットする

---

#### 9. AWS

| 項目 | 判断 |
|------|------|
| **個人アカウントを使っていいか？** | **OK（EC2を使う場合のみ）** |
| **新規作成が必要か？** | Mac miniだけで運用するなら不要 |
| **何に使うか** | EC2サーバー（Mac miniの代わりにクラウドを使う場合） |

**Mac mini運用の場合：**
- AWSアカウントは**不要**
- Mac mini自体がサーバーなので、EC2を借りる必要がない
- 将来的にEC2に移行したくなったら、その時に作ればOK

---

#### 10. ngrok

| 項目 | 判断 |
|------|------|
| **個人アカウントを使っていいか？** | **OK（安全）** |
| **新規作成が必要か？** | アカウント自体は新規作成が必要（無料） |
| **何に使うか** | Mac miniをインターネットに公開する（HTTPS化） |

**なぜ必要か：**
- LINEやDiscordのWebhookは、HTTPS（暗号化通信）が必須
- Mac miniは通常HTTPしか出せない
- ngrokが間に入ってHTTPS化してくれる

**アカウント作成：**
1. **https://ngrok.com/** にアクセス
2. サーバー専用Googleアカウントまたはメールで登録
3. ダッシュボードからAuthToken（認証トークン）を取得

---

### アカウント一覧まとめ

| サービス | 個人アカウントOK？ | 専用アカウント作る？ | Mac miniに残る情報 |
|---------|-------------------|--------------------|--------------------|
| **Google** | ❌ NG | ✅ サーバー専用を作る | 認証時のセッション（プライベートブラウズなら残らない） |
| **Apple ID** | ❌ 絶対NG | ❌ 不要（ログインしない） | なし |
| **GitHub** | ✅ OK | 不要 | 認証トークン、コード |
| **Anthropic** | ✅ OK | 不要 | APIキー |
| **Claude Code** | ✅ OK | 不要 | 認証トークン（`~/.claude/`） |
| **Cursor** | ✅ OK | どちらでも | エディタ設定 |
| **LINE** | ✅ 管理者のみ | LINE公式は新規 | チャンネルトークン・シークレット |
| **Discord** | ✅ Bot作成のみ | Bot自体は新規 | Botトークン |
| **AWS** | ✅ OK | Mac mini運用なら不要 | アクセスキー（EC2使用時のみ） |
| **ngrok** | ✅ OK | 新規作成 | AuthToken |

---

### トラブル対処法（間違えてログインしてしまったら）

#### Google アカウントをChromeでログインしてしまった

**深刻度: 中（パスワード・ブックマーク・履歴が同期される）**

1. Chrome右上のプロフィールアイコンをクリック
2. 「同期は有効です」→クリック
3. 「オフにする」を選択
4. 「閲覧データの削除」にチェックを入れてオフにする
5. 再度プロフィールアイコン → 「Googleアカウントの管理」の横の「ログアウト」

**確認方法：** Chrome右上がアイコンではなく「ログイン」ボタンになっていればOK

---

#### Apple IDでiCloudにログインしてしまった

**深刻度: 高（写真・連絡先・メモ・パスワードが全部同期される）**

1. 左上のAppleメニュー →「システム設定」
2. 一番上の「Apple ID」をクリック
3. 一番下までスクロール →「サインアウト」
4. 「iCloudデータのコピーをこのMacに残しますか？」→ **すべてのチェックを外して**「続ける」
5. Apple IDのパスワードを入力してサインアウト

**確認方法：** 「システム設定」の一番上が「Apple IDでサインイン」になっていればOK

---

#### SafariでGoogleにログインしたまま放置してしまった

**深刻度: 低〜中（Cookieにセッションが残る）**

1. Safari → メニューバー「Safari」→「設定」（または `⌘,`）
2. 「プライバシー」タブ
3. 「Webサイトデータを管理」をクリック
4. 検索欄に「google」と入力
5. 表示されたものをすべて選択 →「削除」
6. 「完了」

**確認方法：** google.com にアクセスして、右上が「ログイン」ボタンになっていればOK

---

#### Discordの個人アカウントでMac miniのブラウザにログインしてしまった

**深刻度: 低（DMは見えるが、Botトークンとは別管理）**

1. Discordの左下の歯車アイコン（ユーザー設定）
2. 一番下の「ログアウト」
3. ブラウザの閲覧データを削除（Cookie削除）

**ポイント：** Botトークンは Developer Portal で管理されるので、ブラウザのログアウトとは無関係。Botは動き続ける。

---

#### LINEの管理者ページにログインしたまま放置してしまった

**深刻度: 低（LINE公式アカウントの管理画面だけ）**

1. LINE Official Account Manager（https://manager.line.biz/）にアクセス
2. 右上のメニュー →「ログアウト」

**ポイント：** 個人LINEのトーク履歴がMac miniに入ることはない。管理画面だけの話。

---

#### APIキーやトークンが漏洩した（GitHubにプッシュしてしまった等）

**深刻度: 最高（即対応が必要）**

| サービス | リセット方法 |
|---------|-------------|
| **Anthropic APIキー** | https://console.anthropic.com/ → APIキー → 削除 → 新規作成 |
| **LINE チャンネルアクセストークン** | LINE Developers → チャンネル → Messaging API → トークン再発行 |
| **Discord Botトークン** | Discord Developer Portal → Bot → Reset Token |
| **ngrok AuthToken** | https://dashboard.ngrok.com/ → Auth Token → Reset |
| **AWS アクセスキー** | IAM → ユーザー → セキュリティ認証情報 → アクセスキー → 無効化 → 新規作成 |

**GitHubにプッシュしてしまった場合の追加手順：**
1. 上記でトークン/キーをリセット
2. `.env`ファイルを`.gitignore`に追加
3. GitHubの履歴からも削除する（コミット履歴に残っているため）：
```bash
# .envファイルをGitの履歴から完全削除
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
git push origin --force --all
```
4. **リセット前のキーは無効なので、悪用はできない**（ただし速やかにリセットすること）

---

## トラブルシューティング

### よくある問題と解決方法

#### Q: OpenClawが起動しない
```
原因1: Node.jsのバージョンが古い
→ node --version で確認。22以上が必要

原因2: APIキーが設定されていない
→ echo $ANTHROPIC_API_KEY で確認。空なら再設定

原因3: デーモンが停止している
→ openclaw status で確認 → openclaw onboard --install-daemon で再セットアップ
```
#### Q: LINEにメッセージを送っても反応がない
```
原因1: Webhook URLが間違っている
→ LINE Developersで確認。検証ボタンで「成功」になるか確認

原因2: ngrokが停止している
→ EC2でngrokを再起動

原因3: ペアリングが完了していない
→ openclaw pairing list line で確認

原因4: Webhook の利用がオフになっている
→ LINE Official Account Managerで「Webhookの利用」をオンにする
```

> **EC2関連のトラブルシューティング**は、[付録A: AWS EC2へのデプロイ](#付録a-aws-ec2へのデプロイ) を参照してください。

---

## 料金の目安

### 月額料金の合計イメージ（Mac mini運用）

| 項目 | 料金 | 必須/任意 |
|------|------|-----------|
| Mac mini本体 | 初期費用 約10〜20万円（ランニングコストは電気代のみ） | 必須 |
| 電気代 | 約300〜500円/月 | 必須 |
| ngrok（無料プラン） | 無料 | 必須（LINE連携時） |
| ngrok（有料プラン） | 月額約$8〜（固定URL） | 任意 |
| Anthropic API | 使用量による（Claude MAXサブスクの場合は月額定額） | 必須 |
| **合計（最小構成）** | **電気代 + API代のみ** | |

> **参考:** EC2（クラウドサーバー）で運用する場合は月額3,000円〜の維持費がかかります。
> Mac miniは初期費用がかかりますが、ランニングコストは電気代のみで済みます。
> EC2での運用方法は [付録A: AWS EC2へのデプロイ](#付録a-aws-ec2へのデプロイ) を参照してください。

---

## おわりに

お疲れ様でした！ここまでの手順で、以下が実現できたはずです：

1. Mac miniの初期セットアップ
2. OpenClaw（AIエージェント）のインストールと初期設定
3. Discord連携（スマホからAIに話しかける）
4. LINE公式アカウントとの連携
5. Mac miniの常時稼働設定（24時間AIチャットボット）

**次のステップ：**
- OpenClawのスキルやツールを追加してカスタマイズ
- Slack、Telegramなど他のサービスとも連携
- OpenClawに業務を自動化させる（見積もり、開発、レポート作成など）
- 必要に応じて [付録A: AWS EC2へのデプロイ](#付録a-aws-ec2へのデプロイ) でクラウドに移行

**困ったときは：**
- クロードコードに相談する（「OpenClawの〇〇がうまくいかない」）
- OpenClaw公式ドキュメント: https://docs.openclaw.ai/
- OpenClaw GitHub: https://github.com/openclaw/openclaw

---

## 付録A: AWS EC2へのデプロイ

Mac miniではなく、AWS EC2（クラウドの仮想サーバー）にOpenClawをデプロイしたい場合の手順です。
Mac miniが手元にない場合や、クラウドで24時間稼働させたい場合に参照してください。

---

### EC2関連の用語集

| 用語 | 分かりやすく言うと | 例え |
|------|-------------------|------|
| **AWS** | Amazonが提供するクラウドサービス | 「レンタルパソコン屋さん」 |
| **EC2** | AWSの中の仮想サーバー | 「借りたパソコン本体」 |
| **VPC** | AWS内の自分専用ネットワーク | 「自分だけの土地」 |
| **サブネット** | VPCの中を区切ったエリア | 「土地の中の区画（庭・駐車場・家）」 |
| **セキュリティグループ** | 通信の許可/拒否ルール | 「門番・ガードマン」 |
| **キーペア** | EC2に入るための鍵 | 「家の鍵」 |
| **SSH** | リモートでサーバーに接続する仕組み | 「遠隔操作リモコン」 |
| **DNS** | ドメイン名とIPアドレスを紐付ける仕組み | 「電話帳」 |
| **Route 53** | AWSのDNSサービス | 「AWS専用の電話帳」 |
| **ALB** | 通信を振り分ける装置 | 「受付カウンター」 |
| **IAM** | AWSのユーザー管理サービス | 「社員証発行システム」 |
| **Elastic IP** | EC2に固定で割り当てるIPアドレス | 「変わらない住所」 |
| **リージョン** | AWSのサーバーがある地域 | 「データセンターの場所」 |

---

### A-1. AWSアカウントを作る

### 1-1. AWSの公式サイトにアクセス

1. ブラウザで **https://aws.amazon.com/** を開く
2. 右上の **「アカウントを作成」** をクリック

### 1-2. アカウント情報を入力

1. **メールアドレス** を入力
2. **AWSアカウント名** を入力（何でもOK。例：「myaws-account」）
3. **「メールアドレスを確認」** をクリック
4. メールに届いた **確認コード** を入力
5. **パスワード** を設定（8文字以上、大文字・小文字・数字・記号のうち3種類以上）

### 1-3. アカウントタイプを選択

- **「個人」** を選択（ビジネスでも機能は同じ）
- 連絡先情報（名前・住所・電話番号）を入力

### 1-4. 支払い方法を登録

- クレジットカードまたはデビットカードの情報を入力
- **無料枠内なら課金されません**が、登録自体は必要です

### 1-5. 本人確認

- 電話番号を入力
- SMSまたは音声通話で確認コードを受け取る
- コードを入力して確認

### 1-6. サポートプランを選択

- **「ベーシック（無料）」** を選択
- これで十分です

### 1-7. 完了！

- 「サインアップ完了」と表示されたらOK
- 通常数分でアカウントが使えるようになります（最大24時間かかる場合あり）

> **重要:** 2025年7月15日以降に作成したアカウントは新制度が適用されます。
> - $100のクレジットが付与（追加で最大$100獲得可能）
> - 無料期間は**6ヶ月間**（旧制度の12ヶ月から短縮）

### 1-8. MFA（多要素認証）を設定する【必須】

アカウントを乗っ取られないように、すぐにMFAを設定してください。

1. AWSマネジメントコンソールにログイン
2. 右上のアカウント名をクリック → **「セキュリティ認証情報」**
3. **「MFAデバイスの割り当て」** をクリック
4. **「認証アプリケーション」** を選択（Google Authenticatorなど）
5. QRコードをスマホのアプリでスキャン
6. 表示される6桁のコードを2回入力して完了

---

### A-2. IAMユーザーを作る（セキュリティ対策）

AWSでは「ルートユーザー」（最高権限）を普段使いしないのがルールです。
専用の「IAMユーザー」を作って、そちらで作業します。

### 2-1. IAMの画面を開く

1. AWSマネジメントコンソールにログイン
2. 上部の検索バーに **「IAM」** と入力してクリック

### 2-2. ユーザーを作成

1. 左メニューの **「ユーザー」** をクリック
2. **「ユーザーを作成」** をクリック
3. ユーザー名を入力（例：`admin-user`）
4. **「AWSマネジメントコンソールへのアクセスを提供」** にチェック
5. パスワードを設定

### 2-3. 権限を設定

1. **「ユーザーをグループに追加」** を選択
2. **「グループを作成」** をクリック
3. グループ名を入力（例：`Administrators`）
4. **`AdministratorAccess`** にチェックを入れる
5. **「ユーザーグループを作成」** → **「次へ」** → **「ユーザーを作成」**

### 2-4. アクセスキーを発行する

1. 作成したユーザーをクリック
2. **「セキュリティ認証情報」** タブを開く
3. **「アクセスキーを作成」** をクリック
4. 用途で **「コマンドラインインターフェイス（CLI）」** を選択
5. 表示される2つの値を**必ずメモ**してください：
   - **アクセスキーID**（例：`AKIAIOSFODNN7EXAMPLE`）
   - **シークレットアクセスキー**（例：`wJalrXUtnFEMI/K7MDENG/...`）

> **超重要:** シークレットアクセスキーは**この画面でしか確認できません**。
> 必ず安全な場所にメモしてください。忘れたら再発行が必要です。

---

### A-3. AWS CLIをパソコンにインストール

AWS CLIとは、ターミナル（黒い画面）からAWSを操作するためのツールです。
これがあると、クロードコードからAWSのサーバーを作ったりできるようになります。

### Windowsの場合

1. ブラウザで以下のURLを開く：
   **https://awscli.amazonaws.com/AWSCLIV2.msi**
2. ダウンロードされた `AWSCLIV2.msi` をダブルクリック
3. インストーラーの指示に従って「Next」→「Next」→「Install」
4. インストール完了

**確認方法:**
```
PowerShellまたはコマンドプロンプトを開いて入力：
aws --version
```
`aws-cli/2.x.x ...` と表示されればOK。

### Macの場合

1. ブラウザで以下のURLを開く：
   **https://awscli.amazonaws.com/AWSCLIV2.pkg**
2. ダウンロードされたファイルをダブルクリック
3. インストーラーの指示に従って進める

**または、ターミナルでHomebrewを使う場合：**
```bash
brew install awscli
```

**確認方法:**
```bash
aws --version
```

### AWS CLIの初期設定

ターミナル（PowerShell / コマンドプロンプト / Mac ターミナル）を開いて：

```
aws configure
```

聞かれる4つの値を順番に入力：

```
AWS Access Key ID: （STEP 2で取得したアクセスキーID）
AWS Secret Access Key: （STEP 2で取得したシークレットアクセスキー）
Default region name: ap-northeast-1
Default output format: json
```

> **ポイント:** `ap-northeast-1` は東京リージョンのことです。日本で使うならこれがベスト。

---

### A-4. EC2（仮想サーバー）を作る

いよいよ本番。AWSにEC2（仮想サーバー）を作ります。
これは「クラウド上に自分専用のパソコンを借りる」イメージです。

### 方法A: AWSコンソール（ブラウザ）から作る

#### 7-A-1. EC2の画面を開く

1. AWSマネジメントコンソールにログイン（IAMユーザーで）
2. 上部の検索バーに **「EC2」** と入力してクリック
3. **リージョンが「東京（ap-northeast-1）」** になっていることを確認（右上に表示）

#### 7-A-2. インスタンスを起動

1. **「インスタンスを起動」** をクリック
2. 以下の設定を行う：

**名前：**
```
openclaw-server （何でもOK。わかりやすい名前をつける）
```

**OS（AMI）：**
```
Ubuntu Server 22.04 LTS を選択（無料利用枠対象のマークがあるもの）
```

**インスタンスタイプ：**
```
t3.small を選択（2 vCPU、2GB RAM、月額約$20）
```

> **コスト比較:**
> | タイプ | スペック | 月額目安 |
> |--------|---------|---------|
> | t3.small | 2 vCPU / 2GB RAM | 約3,000円 |
> | t3.medium | 2 vCPU / 4GB RAM | 約4,700円 |
> | t2.small | 1 vCPU / 2GB RAM | 約3,300円 |

**キーペア（ログイン）：**
```
「新しいキーペアの作成」をクリック
- キーペア名: openclaw-key
- キーペアのタイプ: RSA
- ファイル形式: .pem（Macの場合）/ .ppk（PuTTYを使うWindowsの場合）
「キーペアを作成」をクリック → .pemファイルがダウンロードされる
```

> **超重要:** このキーペアファイル（.pem）は**絶対に失くさないでください**。
> これがEC2に入るための「家の鍵」です。再ダウンロードはできません。
> 安全なフォルダに保存し、他人に渡さないでください。

**ネットワーク設定（セキュリティグループ）：**
```
「編集」をクリックして以下を設定：

セキュリティグループ名: openclaw-sg

インバウンドルール:
- SSH (ポート22) → ソース: マイIP（自分のIPアドレスのみ）
- HTTP (ポート80) → ソース: 0.0.0.0/0（どこからでも）
- HTTPS (ポート443) → ソース: 0.0.0.0/0（どこからでも）
- カスタムTCP (ポート3000) → ソース: 0.0.0.0/0（OpenClaw用。ポートはOpenClawの設定による）
```

**ストレージ：**
```
20 GiB（gp3）に変更（デフォルトの8GiBでは足りない場合がある）
```

3. 設定を確認して **「インスタンスを起動」** をクリック
4. 「インスタンスが正常に起動しました」と表示されたらOK！

#### 7-A-3. Elastic IP（固定IPアドレス）を取得【推奨】

EC2を再起動するとIPアドレスが変わってしまうので、固定IPを割り当てます。

1. EC2の左メニュー → **「Elastic IP」**
2. **「Elastic IPアドレスの割り当て」** → **「割り当て」**
3. 割り当てられたIPアドレスを選択 → **「アクション」** → **「Elastic IPアドレスの関連付け」**
4. インスタンスで先ほど作った `openclaw-server` を選択
5. **「関連付ける」** をクリック

> **注意:** Elastic IPはEC2に関連付けている限り無料ですが、
> EC2を停止してElastic IPだけ残すと課金されます。

### 方法B: クロードコードから作る（上級者向け）

クロードコードに以下のように指示するだけで、EC2を自動構築してくれます：

```
EC2のサーバーを東京リージョンに立てて、
その中にOpenClawをインストールしたい。
インスタンスタイプはt3.smallで。
```

クロードコードがAWS CLIを使って自動的に構築してくれます。

---

### A-5. EC2にOpenClawをインストール

### 8-1. EC2にSSH接続する

EC2の「家の鍵」（.pemファイル）を使って、リモートで接続します。

**Windowsの場合（PowerShell）：**

```powershell
# 1. キーファイルの権限を設定（初回のみ）
# エクスプローラーで .pem ファイルを右クリック
# → プロパティ → セキュリティ → 詳細設定
# → 継承を無効にする → 継承されたアクセス許可を削除
# → 追加 → 自分のユーザーのみ「読み取り」権限を設定

# 2. SSH接続
ssh -i "C:\Users\あなたのユーザー名\Downloads\openclaw-key.pem" ubuntu@EC2のパブリックIPアドレス
```

**Macの場合：**
```bash
# 1. キーファイルの権限を設定（初回のみ）
chmod 400 ~/Downloads/openclaw-key.pem

# 2. SSH接続
ssh -i "~/Downloads/openclaw-key.pem" ubuntu@EC2のパブリックIPアドレス
```

> **EC2のパブリックIPアドレスの確認方法：**
> AWSコンソール → EC2 → インスタンス → 該当インスタンスをクリック
> → 「パブリック IPv4 アドレス」に表示されている数字（例：57.180.60.97）

初回接続時に「Are you sure you want to continue connecting?」と聞かれたら `yes` と入力。

### 8-2. EC2のセットアップ

SSH接続した状態で、以下のコマンドを順番に実行：

```bash
# 1. システムを最新にアップデート
sudo apt update && sudo apt upgrade -y

# 2. Node.js 22をインストール
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# 3. Node.jsのバージョン確認
node --version   # v22.x.x と表示されればOK
npm --version    # バージョンが表示されればOK

# 4. OpenClawをインストール
curl -fsSL https://openclaw.ai/install.sh | bash

# 5. OpenClawの初期セットアップ
openclaw onboard --install-daemon
```

セットアップ中の質問は、STEP 4と同じように答えてください。

### 8-3. APIキーを設定

```bash
# Anthropic APIキーを環境変数に設定
export ANTHROPIC_API_KEY="あなたのAPIキー"

# 永続化（再起動しても消えないように）
echo 'export ANTHROPIC_API_KEY="あなたのAPIキー"' >> ~/.bashrc
source ~/.bashrc
```

**または、`claude setup token` を使う方法：**
```bash
claude setup token
```
ただし、EC2ではブラウザが開けないため、表示されるURLを自分のパソコンのブラウザで開いて認証してください。

### 8-4. LINEプラグインをインストール

```bash
openclaw plugins install @openclaw/line
```

チャンネルアクセストークンとチャンネルシークレットを設定（STEP 5でメモした値）。

### 8-5. 動作確認

```bash
openclaw status    # 稼働中であることを確認
openclaw doctor    # 問題がないかチェック
```

---

### A-6. ngrokでHTTPS化する

EC2上のOpenClawをLINEと接続するには、HTTPS通信が必要です。
まずはngrokで簡単にHTTPS化しましょう（本番運用では独自ドメイン推奨）。

### 9-1. EC2にngrokをインストール

SSH接続した状態で：

```bash
# ngrokのリポジトリを追加
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list

# インストール
sudo apt update && sudo apt install ngrok

# 認証トークンを設定（ngrok.comのダッシュボードで取得）
ngrok config add-authtoken あなたのAuthToken
```

### 9-2. HTTPSトンネルを開始

```bash
# バックグラウンドで実行
nohup ngrok http 3000 &

# URLの確認
curl http://127.0.0.1:4040/api/tunnels
```

表示される `https://xxxxx.ngrok-free.app` のURLをメモしてください。

> **注意:** ngrok無料プランでは、再起動のたびにURLが変わります。
> 変わるたびにLINEのWebhook URLも更新する必要があります。
> 固定URLが必要な場合は、ngrok有料プラン（月$8〜）または独自ドメイン（後述）を検討してください。

---

### A-7. LINEのWebhookをEC2に向ける

### 10-1. Webhook URLを変更

1. **LINE Developers** コンソールを開く
2. 該当チャンネルの **「Messaging API」** タブ
3. **「Webhook URL」** を変更：
   ```
   https://xxxxx.ngrok-free.app/line/webhook
   ```
   （STEP 9で取得したngrokのURL + `/line/webhook`）
4. **「更新」** をクリック
5. **「検証」** をクリック → 「成功」と表示されればOK

### 10-2. 接続テスト

1. スマホのLINEで公式アカウントにメッセージを送る
2. ペアリングコードが表示されたら、EC2上で承認：
   ```bash
   openclaw pairing approve line コード番号
   ```
3. 再度メッセージを送る → AIが返答すれば成功！

### 10-3. 確認：EC2で動いているか確かめる

LINEで「あなたは今どこで動いていますか？」と聞いてみてください。

AIが「EC2インスタンスで稼働しています」のような返答をすれば、
クラウド上で動いていることが確認できます！

> **おめでとうございます！**
> これで、パソコンを閉じてもLINEからAIエージェントが使える状態になりました！

---


### A-8. （オプション）独自ドメインを設定する

ngrokの無料URLは再起動で変わってしまうため、本格運用するなら独自ドメインがおすすめです。

### Route 53でドメインを購入

1. AWSコンソール → **Route 53**
2. **「ドメインの登録」** → 希望のドメイン名を検索
3. 利用可能なドメインを選択して購入

> **ドメイン料金の目安:**
> - `.com` : 年間約$13（約2,000円）
> - `.net` : 年間約$11（約1,650円）
> - `.jp` : 年間約$90（約13,500円）

### Elastic IPとドメインを紐付ける

1. Route 53 → **「ホストゾーン」** → 購入したドメインを選択
2. **「レコードを作成」**
3. 設定：
   - レコードタイプ: **A**
   - 値: EC2の**Elastic IPアドレス**
   - TTL: 300
4. 「レコードを作成」

### ALB（ロードバランサー）でHTTPS化

独自ドメインの場合、SSL証明書（HTTPS化）にはALBを使います：

1. EC2 → **「ロードバランサー」** → **「ロードバランサーの作成」**
2. **「Application Load Balancer」** を選択
3. リスナーでHTTPS（ポート443）を設定
4. SSL証明書は **AWS Certificate Manager（ACM）** で無料取得可能
5. ターゲットグループにEC2インスタンスを登録
6. Route 53のAレコードをALBのDNS名に変更

> **ALBの料金:** 月額約$16〜$25（利用量による）
> 詳細な手順は別途リサーチが必要なため、クロードコードに
> 「ALBとACMを使ってHTTPS化したい」と相談するのがおすすめです。

---

---

### EC2関連のトラブルシューティング

#### Q: SSH接続できない
```
原因1: セキュリティグループでポート22が開いていない
→ EC2 → セキュリティグループ → インバウンドルールにSSH（ポート22）を追加

原因2: .pemファイルの権限が正しくない
→ Windows: プロパティで権限を修正 / Mac: chmod 400 xxxx.pem

原因3: IPアドレスが間違っている
→ EC2コンソールでパブリックIPアドレスを再確認

原因4: ユーザー名が間違っている
→ Ubuntu: ubuntu / Amazon Linux: ec2-user
```

#### Q: EC2を再起動したらLINEが反応しなくなった
```
原因: ngrokのURLが変わった
→ EC2でngrokを再起動 → 新しいURLをLINEのWebhookに設定

恒久対策: 独自ドメイン + Elastic IP を設定する（オプション参照）
```

#### Q: EC2が重い・固まった
```
対策1: インスタンスタイプを上げる（t3.small → t3.medium）
対策2: EC2を再起動（AWSコンソール → インスタンス → アクション → 再起動）
対策3: メモリを確認（SSH接続して free -m を実行）
```

---

### EC2運用時の料金の目安

| 項目 | 料金（月額） | 必須/任意 |
|------|-------------|-----------|
| EC2（t3.small） | 約3,000円 | 必須 |
| EBS（20GB ストレージ） | 約300円 | 必須 |
| Elastic IP | 無料（EC2稼働中） | 推奨 |
| ngrok（無料プラン） | 無料 | 必須（ドメインなしの場合） |
| Route 53（ドメイン） | 約200円/月 + ドメイン代 | 任意 |
| ALB（ロードバランサー） | 約2,500〜4,000円 | 任意（独自ドメイン時） |
| Anthropic API | 使用量による | 必須 |
| **合計（最小構成）** | **約3,300円 + API代** | |
| **合計（独自ドメイン構成）** | **約6,000〜7,500円 + API代** | |

#### 無料枠を活用する

2025年7月以降の新アカウントなら：
- $100のクレジットが付与される（約15,000円分）
- 追加で最大$100獲得可能
- **約3〜6ヶ月は実質無料で運用可能！**

---

*この手順書は2026年2月時点の情報に基づいています。*
*ソフトウェアのバージョンアップにより、手順が変わる場合があります。*
