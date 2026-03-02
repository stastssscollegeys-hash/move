const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType } = require("docx");
const fs = require("fs");
const path = require("path");

function heading(text, level) {
  return new Paragraph({ heading: level, children: [new TextRun({ text, bold: true })] });
}
function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })] });
}
function bold(text) {
  return new Paragraph({ children: [new TextRun({ text, bold: true })] });
}
function bullet(text, level = 0) {
  return new Paragraph({ bullet: { level }, children: [new TextRun(text)] });
}
function code(text) {
  return new Paragraph({ children: [new TextRun({ text, font: "Courier New", size: 20 })] });
}
function spacer() {
  return new Paragraph({ children: [] });
}
function makeCell(text, opts = {}) {
  return new TableCell({
    children: [new Paragraph({ children: [new TextRun({ text, ...opts })] })],
    width: { size: opts.width || 2500, type: WidthType.DXA },
  });
}
function makeTable(headers, rows) {
  const headerRow = new TableRow({ children: headers.map(h => makeCell(h, { bold: true })) });
  const dataRows = rows.map(row => new TableRow({ children: row.map(cell => makeCell(cell)) }));
  return new Table({ rows: [headerRow, ...dataRows] });
}

const doc = new Document({
  sections: [{
    children: [
      heading("OpenClaw Mac mini セットアップ手順書", HeadingLevel.TITLE),
      p("実際の導入手順に基づく備忘録", { italics: true }),
      spacer(),

      // ========== 前提知識 ==========
      heading("前提知識：MacとWindowsの違い", HeadingLevel.HEADING_1),
      spacer(),
      bold("キーボード対応表"),
      makeTable(["Windows", "Mac", "場所"], [
        ["Ctrl", "Command（⌘）", "スペースバーのすぐ左右"],
        ["Alt", "Option（⌥）", "Commandの外側"],
        ["Shift", "Shift（⇧）", "同じ"],
        ["Enter", "Return", "同じ"],
      ]),
      spacer(),
      p("要するに：WindowsでCtrlを使っていた操作は、MacではCommandに置き換えるだけ。"),
      spacer(),
      bold("ターミナルの開き方（PowerShellに相当）"),
      bullet("Dock → Launchpad（ロケットアイコン）→ 検索欄に「ターミナル」→ クリック"),
      spacer(),
      bold("プライベートブラウズの開き方"),
      bullet("Safari: メニューバー「ファイル」→「新規プライベートウィンドウ」（暗い色になればOK）"),
      bullet("Chrome: メニューバー「ファイル」→「新しいシークレット ウィンドウ」（暗い色になればOK）"),
      bullet("ショートカット: Shift + Command + N（どちらも共通）"),
      spacer(),
      bold("ツールの認証でプライベートブラウズを使う手順（毎回この流れ）"),
      bullet("1. ツール（CursorやClaude Code）でログインボタンを押す"),
      bullet("2. ブラウザが自動で開く"),
      bullet("3. アドレスバーをクリック → Command+A → Command+C でURLをコピー"),
      bullet("4. そのブラウザを閉じる（左上の赤い丸ボタン）"),
      bullet("5. プライベートウィンドウを開く（「ファイル」→「新規プライベートウィンドウ」）"),
      bullet("6. アドレスバーに Command+V で貼り付け → Return"),
      bullet("7. Googleアカウントでログイン → 認証完了 → プライベートウィンドウを閉じる"),
      bullet("8. ツール側に戻ると認証が通っている"),
      p("※最初のセットアップ時だけ。一度通ればしばらく再認証不要。", { italics: true }),

      // ========== Step 1 ==========
      spacer(),
      heading("Step 1: Mac mini初期設定", HeadingLevel.HEADING_1),
      bullet("言語: 日本語 / 地域: 日本 / Wi-Fi: 接続"),
      bullet("Apple ID: 「あとで設定」でスキップ（ログインしない）"),
      bullet("その他の設定（ユーザー名・パスワード等）を進めて完了"),
      p("※App Storeは使えなくなるが、必要なツールは全てWebからダウンロードできるので問題なし", { italics: true }),

      // ========== Step 2 ==========
      spacer(),
      heading("Step 2: Cursorをインストール", HeadingLevel.HEADING_1),
      bullet("Safariで cursor.com →「Download」→ .dmgを開く → Applicationsにドラッグ"),
      bullet("起動 → 普段のCursorアカウントでログイン（エディタ設定しか入ってないので安全）"),
      bullet("「Googleで続ける」の場合 → プライベートブラウズで認証"),
      bullet("「Open Cursor from Terminal」→「Install」を押す"),

      // ========== Step 3 ==========
      spacer(),
      heading("Step 3: Git・Node.jsをインストール", HeadingLevel.HEADING_1),
      p("CursorのAIチャットに頼めば両方入れてくれます。"),
      bullet("「Gitをインストールしたい」→ AIが実行してくれる → 確認: git --version"),
      bullet("「Node.jsをインストールしたい」→ AIが実行してくれる → 確認: node --version"),
      p("※「command not found」→ ターミナルを閉じて開き直す", { italics: true }),

      // ========== Step 4 ==========
      spacer(),
      heading("Step 4: Claude Codeをインストール", HeadingLevel.HEADING_1),
      bullet("CursorのAIチャットに「Claude Codeをインストールしたい」と入力"),
      bullet("AIが npm install -g @anthropic-ai/claude-code を実行してくれる"),
      bullet("確認: claude --version → バージョン番号が出ればOK"),

      // ========== Step 5 ==========
      spacer(),
      heading("Step 5: Claude Codeにログイン", HeadingLevel.HEADING_1),
      bullet("Cursorのターミナルで claude → Return"),
      bullet("認証URLが表示される → ブラウザが自動で開く"),
      bullet("プライベートブラウズで認証（前提知識の手順通り）"),
      bullet("Cursorのターミナルに戻ると対話画面が表示される → 完了！"),

      // ========== Step 6 ==========
      spacer(),
      heading("Step 6: OpenClawをインストール", HeadingLevel.HEADING_1),
      bullet("Claude Codeに「OpenClawをインストールしたい」と頼む"),
      bullet("または: npm install -g openclaw@latest → openclaw onboard --install-daemon"),
      bullet("AIプロバイダー「Anthropic」を選択 → APIキーを入力"),
      spacer(),
      bold("Anthropic APIキーの取得手順:"),
      bullet("1. console.anthropic.com/settings/keys にアクセス"),
      bullet("2.「Create Key」でAPIキーを生成"),
      bullet("3. 表示されたキー（sk-ant-...）をコピー → OpenClawに入力"),
      spacer(),
      bold("料金プラン: Claude Max サブスクリプション（月額$100 or $200）を推奨"),
      bullet("月額固定なので、万が一APIキーが漏洩しても月額以上の請求は発生しない"),
      bullet("従量課金（pay-per-use）だと漏洩時に青天井で課金されるリスクがある"),
      bullet("APIキーはいつでもコンソールから無効化・再生成できる"),

      // ========== Step 7 ==========
      spacer(),
      heading("Step 7: OpenClaw専用Gmailの作成", HeadingLevel.HEADING_1),
      bold("7-1. 専用Gmailアカウントを作成"),
      bullet("accounts.google.com で新規作成（例: yourname-openclaw@gmail.com）"),
      spacer(),
      bold("7-2. 普段のGmailから転送設定"),
      bullet("普段のGmail → 歯車 →「すべての設定」→「メール転送とPOP/IMAP」→ 転送先に専用Gmailを追加"),
      spacer(),
      bold("7-3. Googleカレンダーの共有設定"),
      bullet("カレンダー →「設定と共有」→「特定のユーザーとの共有」→ 専用Gmailを追加"),

      // ========== Step 8 ==========
      spacer(),
      heading("Step 8: アカウント設定（Chrome・LINE・Discord等）", HeadingLevel.HEADING_1),
      bold("Google Chrome:"),
      bullet("Safariで google.com/chrome → ダウンロード → Googleアカウントでログインしない"),
      spacer(),
      bold("公式LINE連携（オプション）:"),
      bullet("LINE DevelopersでMessaging APIチャネル作成 → トークン発行 → OpenClawに設定"),
      spacer(),
      bold("Discord連携（オプション）:"),
      bullet("Discord Developer PortalでBot作成 → トークン取得 → OpenClawに設定"),

      // ========== Step 9 ==========
      spacer(),
      heading("Step 9: Mac miniの常時稼働設定", HeadingLevel.HEADING_1),
      bullet("システム設定 > エネルギー >「自動スリープを防ぐ」→ オン"),
      bullet("「ネットワークアクセスによるスリープ解除」→ オン"),
      bullet("「停電後に自動的に起動する」→ オン"),
      bullet("HDMIダミープラグを接続（ヘッドレス運用用、約1,000円）"),

      // ========== Step 10 ==========
      spacer(),
      heading("Step 10: セキュリティ強化", HeadingLevel.HEADING_1),
      bullet("FileVault: システム設定 > プライバシーとセキュリティ > FileVault > オン"),
      bullet("ファイアウォール: システム設定 > ネットワーク > ファイアウォール > オン"),
      bullet("自動ログイン無効化: システム設定 > ユーザとグループ > 自動ログイン > オフ"),
      spacer(),
      code("chmod 700 ~/.openclaw/"),
      code("chmod 600 ~/.openclaw/*"),

      // ========== プライベートモードの考え方 ==========
      spacer(),
      heading("プライベートモードの考え方（重要）", HeadingLevel.HEADING_1),
      p("プライベートモードが守るのは「ブラウザにログイン状態を残さない」ことだけ。"),
      spacer(),
      makeTable(["やること", "安全？", "理由"], [
        ["プライベートモードでGoogle認証 → 閉じる", "OK", "セッション消える"],
        ["プライベートモードでGmail開いて見る", "OK", "閉じればログイン消える"],
        ["Gmailの内容をコピー → Claude Codeに貼る", "OK", "Mac mini専用機なので問題なし"],
        ["プライベートモードでGitHub認証", "OK", "セッション消える"],
        ["通常ブラウザでChromeにGoogleログイン（同期ON）", "NG", "パスワード等が全部同期される"],
      ]),
      spacer(),
      p("要するに：プライベートモードは「ブラウザを汚さないための手段」。コピペでClaude Codeに渡すのはOK。", { bold: true }),

      // ========== GitHubログイン ==========
      spacer(),
      heading("GitHubへのログイン", HeadingLevel.HEADING_1),
      p("ブラウザ不要。ターミナルから認証できます。"),
      code("gh auth login"),
      bullet("「GitHub.com」→「HTTPS」→「Login with a web browser」→ プライベートモードで認証"),
      bullet("普段のGitHubアカウントでOK（コードしか入っていないので安全）"),
      bullet("一度認証すれば、以降ずっとターミナルからpush/pullできる"),

      // ========== WindowsとMac miniの使い分け ==========
      spacer(),
      heading("WindowsとMac miniの使い分け", HeadingLevel.HEADING_1),
      p("既存のリポジトリをMac miniでも使ってOK。漏れてまずい情報は入っていないので、利便性を優先する。"),
      spacer(),
      makeTable(["マシン", "役割", "やること"], [
        ["Windows PC", "メインの開発機", "コード書く、記事作る、pushする"],
        ["Mac mini", "OpenClawサーバー", "OpenClawを24時間動かす。必要時にpull"],
      ]),
      spacer(),
      bold("開発状況の共有方法:"),
      bullet("Windows PCで開発 → git push → Mac miniで git pull → 最新コードが反映される"),
      bullet("Mac miniで設定変更 → git push → Windows PCで git pull → 変更が反映される"),
      bullet("Gitのプッシュにブラウザは使わない。ターミナルで gh auth login を一度やればずっとOK"),
      spacer(),
      bold("注意:"),
      bullet("同じファイルを両方のマシンで同時に編集しない（コンフリクトが起きる）"),
      bullet("基本はWindows PCで開発、Mac miniはOpenClawのサーバーとして使うだけ"),

      // ========== ツール使い分け ==========
      spacer(),
      heading("ツール使い分け", HeadingLevel.HEADING_1),
      makeTable(["ツール", "用途", "アカウント"], [
        ["OpenClaw", "日常タスク自動化", "専用Gmail、公式LINE、Claude API"],
        ["Claude Code", "コーディング（CLI）", "普段のAnthropicアカウント"],
        ["Cursor", "コーディング（IDE）", "普段のアカウント"],
        ["GitHub", "ソースコード管理", "普段のアカウント"],
      ]),

      // ========== アカウント一覧 ==========
      spacer(),
      heading("アカウント一覧まとめ", HeadingLevel.HEADING_1),
      makeTable(["サービス", "個人アカウントOK？", "Mac miniに残る情報"], [
        ["Apple ID", "不要（スキップ）", "なし"],
        ["Google", "専用アカウントを作る", "セッション（プライベートブラウズなら残らない）"],
        ["GitHub", "OK", "認証トークン、コード"],
        ["Anthropic", "OK（Max推奨）", "APIキー（漏洩しても月額固定で安全）"],
        ["Claude Code", "OK（プライベートブラウズ）", "認証トークン"],
        ["Cursor", "OK", "エディタ設定"],
        ["LINE", "公式アカウントは新規", "チャンネルトークン"],
        ["Discord", "Bot作成のみ", "Botトークン"],
        ["ngrok", "新規作成", "AuthToken"],
      ]),

      // ========== GitHub Push通知 ==========
      spacer(),
      heading("GitHub Push通知の設定", HeadingLevel.HEADING_1),
      p("Mac miniから身に覚えのないpushがあった場合にすぐ気づけるよう、メール通知を設定する。"),
      spacer(),
      bold("仕組み: GitHub Actionsでpush時に自動メール送信"),
      bullet("リポジトリの .github/workflows/push-notify.yml にワークフローを配置済み"),
      bullet("pushが発生するたびにGmailに通知メールが届く"),
      bullet("メール内容: リポジトリ名、ブランチ、プッシュした人、コミットメッセージ"),
      spacer(),
      bold("必要な設定（GitHubのリポジトリ設定画面で）:"),
      bullet("1. GitHubのリポジトリ → Settings → Secrets and variables → Actions"),
      bullet("2.「New repository secret」で以下2つを登録:"),
      bullet("   GMAIL_USER → 自分のGmailアドレス", 1),
      bullet("   GMAIL_APP_PASSWORD → Gmailのアプリパスワード（16文字）", 1),
      spacer(),
      bold("Gmailアプリパスワードの取得:"),
      bullet("1. myaccount.google.com/apppasswords にアクセス"),
      bullet("2. アプリ名を入力（例: github-push-alert）→ 生成"),
      bullet("3. 表示された16文字のパスワードをコピー"),
      p("※ Googleアカウントの2段階認証が有効でないと作成できません", { italics: true }),

      // ========== チェックリスト ==========
      spacer(),
      heading("セットアップ完了チェックリスト", HeadingLevel.HEADING_1),
      bullet("□ Mac mini初期設定完了（Apple IDスキップ）"),
      bullet("□ Cursorインストール・ログイン完了"),
      bullet("□ Git インストール完了（git --version で確認）"),
      bullet("□ Node.js インストール完了（node --version で確認）"),
      bullet("□ Claude Code インストール完了（claude --version で確認）"),
      bullet("□ Claude Code 認証完了（プライベートブラウズで実施）"),
      bullet("□ OpenClaw インストール・初期設定完了"),
      bullet("□ OpenClaw専用Gmail作成・転送設定完了"),
      bullet("□ Google Chrome インストール（ログインしない）"),
      bullet("□ 公式LINE連携（オプション）"),
      bullet("□ Discord Bot連携（オプション）"),
      bullet("□ 常時稼働設定（スリープ防止等）"),
      bullet("□ セキュリティ強化（FileVault、ファイアウォール、パーミッション）"),
      bullet("□ GitHub Push通知設定完了（テストメール受信確認）"),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(path.join(__dirname, "OpenClaw_MacMini_Setup.docx"), buffer);
  console.log("Word file created: output/OpenClaw_MacMini_Setup.docx");
});
