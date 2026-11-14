# 金曜の「枠順確定版」（前売り前）— 雛形一式（2026-11-13 武蔵野S・デイリー杯2歳Sで確立）

正本の手順は `.claude/skills/keiba-predictor-ss/SKILL.md` §3g と `docs/keiba_week_before_preview_playbook.md` §4b。
ここにあるのは 2026-11-14 の実物をそのまま置いた雛形。**`Desktop/競馬予想レポート/{日付}/research/` にコピーして、日付・レース・MANUAL・COND・ODDS・本文を書き換えて使う**（この場所で直接は動かさない）。

| ファイル | 役割 | 書き換える所 |
|---|---|---|
| `build_digest.py` | 蓄積DB（JRAのみ）から各馬の近5走・同コース成績・間隔・想定脚質 → `entry_digest_{レース}.json` | `RACES`（枠・馬番・馬名・性齢・斤量・騎手・厩舎）、`MANUAL`（DBに無い走り＝DB最終日より後・地方。収集メモから）、`RACE_DATE` |
| `score.py` | 独自採点100点（①近走40 ②型20 ③適性20 ④脚質10 ⑤状態10。2026-11-14 に配点を測り直した＝`index_weight_test.py`）→ `score_{レース}.json`・`draw_input_{レース}.json` | レースごとの配点関数（race_profile／course_profile に合わせる）、`COND`（最終追い切りの5段階）、`ODDS`（想定オッズ・出典と日付） |
| `mc_draw.py` | 100万回×3シナリオ（A素のまま／B不確かさ／C前有利・外枠） → `mc_draw_{レース}.json` | 引数にレース名。中身は変えない（指数を市場に混ぜる強さ K=0.1。0.4 には戻さない） |
| `build_draw_posts.py` | 見立てレポート md＋X3本・Threads6本（定型見出し・500字・禁止語・印記号の検査） | 本文の定数（CONC/PTS/WX/OIK/SIM/AX/RV/OTH/ANA/LOW）、`HEAD`、`NOTE` |
| `prompt_1_waku_example.txt` | 画像①（結論4バナー＋全頭の枠順）の指示文の例 | 【テーマ・配色】（レースごとに変える）、タイトル・キャッチ・バナー・枠順の行 |
| `prompt_2_sim_example.txt` | 画像②（3着内の確率ランキング）の指示文の例 | 同上＋7行の数字 |
| `images_batch_example.json` | `cdp_chatgpt.mjs batch` に渡す1件ぶん | promptFile／out／attachImages（①はレイアウト参照に前のレースの①＋キャラシート、②は自分の①＋キャラシート） |

落とし穴（SKILL §3g にも書いた）:
- `race_profile.py` は改称前の名前（例: 東京中日スポーツ杯武蔵野ステークス）や全角数字（デイリー杯２歳ステークス）で保存されている年がある。1回ぶんしか出ないときは `--alias` か表記を疑う
- DBの条件文字列は「特別 オープン ○○ステークス」。格の辞書に「オープン」が無いと OP特別が .45 になる
- 2歳馬は同名の旧馬の成績が混ざる → 2026-06 以降に絞る
- 画像生成は空きメモリ 700MB 以下でタブが固まる。デバッグChromeの余計なタブを閉じ、前面で1枚ずつ
