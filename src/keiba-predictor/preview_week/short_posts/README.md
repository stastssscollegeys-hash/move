# 水曜の短い投稿（1頭の物語＋データ1枚）の雛形

手順の正本は `.claude/skills/keiba-predictor-ss/SKILL.md` §3j。調査の根拠は `docs/keiba_sns_popular_posts_research_20261118.md`。

| ファイル | 役割 |
|---|---|
| `build_short_posts_20261118.py` | 文（定型見出し2行→テーマ1行→本文90〜120字（見出しとタグを入れた全体で160〜200字））と画像の指示を作る。2026-11-18（福島記念・マイルCS・東スポ杯2歳S）の版 |
| `gen.sh` | 画像を1枚ずつ生成（cdp_chatgpt.mjs batch）。正方形でなければ作り直す |

使い方: 2本を `Desktop/競馬予想レポート/{日曜の日付}/short_posts/` にコピー → R（見出し・配色・参照画像）と P（15本の文と画像の文字）をその週の数字に書き換え → `python build_short_posts_*.py` → `bash gen.sh`（前面で動かさず run_in_background。貼り付け作業と同時にしない）→ 15枚を目で確認 → X・Threads の下書きへ。
