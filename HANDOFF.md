# OpenClaw Mac mini セットアップ — 引き継ぎメモ

**最終更新: 2026-02-23 17:45 JST**

---

## 現在の状況

### 1. Discord連携（完了）

**状態:** ボットがDiscordでメッセージに返答することを確認済み

**解決のために行った作業:**
- OpenClaw v2026.2.22-2 インストール済み
- Discord Developer Portalで「SubaClaw」ボット作成済み
- Discordプラグインインストール済み（`openclaw plugins install @openclaw/discord`）
- `openclaw configure` でDiscord設定完了（token, allowlist=#general）
- Gateway起動確認済み（Runtime: running, RPC probe: ok）
- `openclaw status` でDiscord Channel = ON / State = OK を確認
- MESSAGE CONTENT INTENT をDiscord Developer Portalでオンにした
- **`plugins.allow: ["discord"]` を openclaw.json に追加** ← これが主な原因だった
- **`groupPolicy` を `"allowlist"` → `"open"` に変更**（テスト用。本番では `"allowlist"` に戻すこと）
- **ペアリング承認**（`openclaw pairing approve discord SEE8S5YQ`）でユーザー shimizu307 を承認

**修正した設定（openclaw.json）:**
```json
"plugins": {
  "allow": ["discord"],   // ← 追加。これがないとプラグインが動作しない
  "installs": { ... }
}

"channels": {
  "discord": {
    "groupPolicy": "open",  // ← "allowlist"から変更（テスト用）
    ...
  }
}
```

**解決した問題まとめ（3つ）:**
1. `plugins.allow: ["discord"]` が未設定 → 追加で解決
2. ペアリング未承認 → `openclaw pairing approve discord SEE8S5YQ` で解決
3. `guilds` 設定のチャンネル名が `"general"`（英語）だが実際は「一般」（日本語） → `guilds` 設定を削除して解決

**残タスク:**
- `groupPolicy` を `"open"` → `"allowlist"` に戻す（セキュリティ上推奨。その際は `guilds` にチャンネルIDを指定すること。名前ではなくIDで指定する）
- Discord Developer PortalでBot Tokenをリセット（前回チャットに貼られたため）
- Discordプラグイン重複警告は残っているが動作に影響なし（手動インストール版を削除するとDiscordが動かなくなるので触らない）
- ボットは現在Administrator権限で招待されている。本番運用時は最小限の権限に絞ること

**手順書への反映:**
- `docs/OpenClaw_AWS_EC2_Setup_Guide.md` に `plugins.allow` 設定手順を Step 5.5 として追加済み
- 画面6の説明を更新済み（警告の重要性を明記）
- `guilds` 設定に関する注意事項を追記済み

**設定ファイル:** `/Users/shimizusubaru/.openclaw/openclaw.json`
**ログファイル:** `/tmp/openclaw/openclaw-2026-02-23.log`

---

### 2. 手順書の再構成（進行中）

**目的:** EC2ガイドとMac miniガイドが混ざっている状態を整理し、Mac mini主体の1ファイルに統一する

**現在のファイル:**
- `docs/OpenClaw_AWS_EC2_Setup_Guide.md` — 元のファイル（EC2+Mac mini混在、約2700行）。今回のセッションでDiscord設定画面の追記済み
- `hokan/OpenClaw_MacMini_Setup.docx` — 上記のWord変換版（古い、EC2混在）

**作成すべきファイル:**
- `docs/OpenClaw_MacMini_Setup_Guide.md` — Mac mini主体の新ガイド
- `hokan/OpenClaw_MacMini_Setup.docx` — 上記のWord変換版

**新しい構成:**
```
# OpenClaw × Mac mini セットアップ完全ガイド

1. この手順書について（Mac mini向け）
2. 全体像（Mac miniがサーバー、EC2ではない）
3. 用語集（Mac mini関連のみ。EC2用語は付録へ）
4. 事前に準備するもの（AWS不要）
STEP 1: Mac miniの初期セットアップ（旧STEP 0 全部）
STEP 2: OpenClawインストール・初期設定（旧STEP 4 全部 — 画面1〜20）
  + セキュリティ強化（旧0-5b）
  + セットアップ完了チェック（旧0-5c）
STEP 3: OpenClawの特徴を理解する（旧0-6, 0-6b 全部）
STEP 4: Discord連携（旧0-7 全部 + 今回追加した画面12〜17）
STEP 5: LINE公式アカウントを準備する（旧STEP 5 全部）
STEP 6: OpenClawとLINEを接続する（旧STEP 6 全部）
STEP 7: Mac mini常時稼働設定（旧0-8 全部）
セキュリティ注意事項（全部残す）
トラブルシューティング（EC2系はappendixへ）
料金の目安（API費用中心に）
おわりに

付録A: AWS EC2へのデプロイ（将来の拡張用）
  - EC2用語集
  - 旧STEP 1（AWSアカウント）
  - 旧STEP 2（IAM）
  - 旧STEP 3（AWS CLI）
  - 旧STEP 7（EC2構築）
  - 旧STEP 8（EC2にOpenClaw）
  - 旧STEP 9（ngrok HTTPS）
  - 旧STEP 10（Webhook）
  - 独自ドメイン設定
```

**重要ルール:**
- Mac miniの内容は一切削除・要約しない。全画面キャプチャ、全説明文をそのまま保持
- EC2の内容は付録に移動（削除ではない）
- 最終出力はWord（pandocで変換: `pandoc docs/OpenClaw_MacMini_Setup_Guide.md -o hokan/OpenClaw_MacMini_Setup.docx --from markdown --to docx`）

**元のEC2ガイドの復元:**
```bash
# git commitでFeb 19の状態に戻す（必要なら）
git show 6bf035b:docs/OpenClaw_AWS_EC2_Setup_Guide.md > docs/OpenClaw_AWS_EC2_Setup_Guide_original.md
```

---

### 3. 環境情報

- **マシン:** Mac mini (shimizusubarunoMac-mini)
- **Node.js:** v24.13.1 (nvm管理)
- **OpenClaw:** v2026.2.22-2
- **パス:**
  - OpenClaw設定: `~/.openclaw/openclaw.json`
  - OpenClaw拡張: `~/.openclaw/extensions/`
  - OpenClawログ: `/tmp/openclaw/openclaw-YYYY-MM-DD.log`
  - プロジェクト: `/Users/shimizusubaru/dev/kaihatu1/`
  - 手順書(MD): `docs/OpenClaw_AWS_EC2_Setup_Guide.md`
  - 手順書(Word): `hokan/OpenClaw_MacMini_Setup.docx`

---

### 4. Discord Bot情報

- **Bot名:** SubaClaw
- **Discord Developer Portal:** https://discord.com/developers/applications
- **Bot Token:** openclaw.jsonの`channels.discord.token`に保存済み
- **注意:** 前回セッションでトークンがチャットに貼られたため、セットアップ完了後にDiscord Developer Portalでリセット推奨
- **MESSAGE CONTENT INTENT:** オン（確認済み）
- **SERVER MEMBERS INTENT / PRESENCE INTENT:** 未確認（必要なら有効化）
