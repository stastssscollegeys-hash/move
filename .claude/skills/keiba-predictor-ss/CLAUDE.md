# keiba-predictor v3.3 — JRA中央競馬 AI予想ツール

> **2026-08-19更新**: 現行構成はSKILL.md冒頭の「★現行バージョン一覧」が正本。
> 20因子v3.3.1（170点満点）／外部8サイト照合／調教3ソース合議／インフルエンサー合算v2／
> 買い目v5.5ガード／完全網羅チェックリスト（発行ゲート）。
> 予想・独自指数計算は必ずSKILL.mdの「★完全網羅チェックリスト」を通すこと。

このフォルダをClaude Codeで開くだけで競馬予想が使えます。

---

## MANDATORY: 初回セットアップ（必ず最初に実行）

**Claude Codeでこのプロジェクトを初めて開いたとき、以下を自動実行してください：**

```bash
pip install -r src/keiba-predictor/requirements.txt
pip install -r src/keiba-index/requirements.txt
```

エラーが出た場合は `python -m pip install ...` で再試行。
Python 3.10以上が必要です（`python --version` で確認）。

---

## 使い方（話しかけるだけ）

| ユーザーの言葉 | Claudeの動作 |
|-------------|------------|
| 「明日の予想して」 | 翌日レースを自動取得して全素材生成 |
| 「今日の予想して」 | 当日レースをオッズ込みで予想 |
| 「NHKマイルCの予想して」 | 特定レース指定で予想 |
| 「指数表を作って」 | Excel指数表を生成 |
| 「投稿もして」 | X・noteへ自動投稿（APIキー設定済みの場合） |

---

## 予想実行コマンド（内部参照）

```bash
# 作業ディレクトリはプロジェクトルート（このフォルダ）

# 翌日の重賞予想
python src/keiba-predictor/scripts/predict_and_report.py --tomorrow

# 当日レース（オッズ込み）
python src/keiba-predictor/scripts/predict_and_report.py --today

# レース名指定（例: NHKマイルC）
python src/keiba-predictor/scripts/predict_and_report.py \
  --date 20260510 --netkeiba --venue tokyo --race NHKマイルC

# 投稿文もプレビュー確認
python src/keiba-predictor/scripts/predict_and_report.py \
  --date 20260510 --netkeiba --venue tokyo --race NHKマイルC --dry-run

# X・note に自動投稿（.envのAPIキー設定済みの場合）
python src/keiba-predictor/scripts/predict_and_report.py \
  --date 20260510 --netkeiba --venue tokyo --race NHKマイルC --post-all

# Excel指数表
python src/keiba-index/run_index.py
```

---

## 自動判断ルール（トリガー → コマンド）

| ユーザーの発言 | 実行するコマンド |
|-------------|--------------|
| 「明日の予想して」 | `--tomorrow` |
| 「今日の予想して」 | `--today` |
| 「〇〇（レース名）の予想して」 | `--date YYYYMMDD --netkeiba --venue 会場 --race レース名` |
| 「投稿もして」 | `--post-all` を追加 |
| 「内容だけ見たい」 | `--dry-run` を追加 |

**日付・会場はユーザーの発言から推定するか、不明なら質問して確認する。**

---

## 会場コード一覧

| 会場 | コード |
|------|-------|
| 東京 | tokyo |
| 中山 | nakayama |
| 阪神 | hanshin |
| 京都 | kyoto |
| 中京 | chukyo |
| 小倉 | kokura |
| 新潟 | niigata |
| 福島 | fukushima |
| 札幌 | sapporo |
| 函館 | hakodate |

---

## 出力ファイル

| ファイル | 内容 |
|--------|------|
| `report_*.txt` | 全頭診断・予想印・買い目テキスト |
| `sns_*.md` | X/Threads/note 投稿文（そのままコピペ可） |
| `指数表_*.xlsx` | Excel指数表（色分け付き） |

---

## APIキー設定（X・note投稿機能を使う場合のみ）

```bash
cp .env.example .env   # Mac/Linux
copy .env.example .env  # Windows
```

`.env` をテキストエディタで開き、各値を入力してください。
**投稿機能を使わない場合は設定不要です。**

---

## 実測（2026-09-27 再検証・レース前records 523R）

- 総合指数1位の◎: 1着21.8%／3着内47.6%／単勝回収 **68.8%**［95%区間 53〜86%］
- 市場1番人気: 1着36.5%／3着内64.4%／単勝回収 86.1%
- 同じ人気帯の中で指数1位は他馬と差なし → **指数は市場に無い情報を持たない**
- 旧「複勝的中率69.7%／ROI273%」は結果リーク・in-sample を含む数字で、実績として使わない
- 詳細: `docs/keiba_system_redesign_20260927.md`

---

## スキル定義

詳細なスキル設定は `.claude/skills/keiba-predictor-ss/SKILL.md` を参照。
