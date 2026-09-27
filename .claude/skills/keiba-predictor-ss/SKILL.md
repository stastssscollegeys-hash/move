---
name: keiba-predictor-ss
description: JRA中央競馬予想 — 市場オッズ×λ-Harvilleを確率の土台に、実測で両関門を通った要素だけを掛け、前向き台帳で検証しながらSNS素材（X/Threads/note/画像）を生成する
type: skill
---

# 競馬予想スキル (keiba-predictor-ss) v4.0（2026-09-27 再設計）

> **v3.3（3,153行）は `SKILL_full_archive_20260927.md` に原本保存。** SNS文面テンプレ・20因子の採点表・
> 過去の全ガードはそこにある。本書は「今の1手順」「守ること」「台帳の場所」だけを書く。
> 再設計の根拠と実測: `docs/keiba_system_redesign_20260927.md`（正本）／ `DECISION_LOG.md`

## 0. この仕組みが立っている事実（2026-09-27・レース前records 523R）

| ◎の決め方 | 1着率 | 3着内率 | 単勝回収 |
|---|---|---|---|
| 総合指数1位（旧v3.3の◎） | 21.8% | 47.6% | 68.8%［53〜86%］ |
| **市場1番人気** | **36.5%** | **64.4%** | **86.1%** |

同じ人気帯の中で「指数1位」は他馬と差がない。**指数は市場に無い情報を持たない。**
確率を順位テーブル／人気帯から作ると期待値は控除率（≒80%）に固定される。
→ 妙味は「市場より正確な確率」からしか生まれない。だから、**市場を土台にして実測で通った要素だけ掛ける。**

## 1. 現行構成（v4.0）

| 部品 | 現行 | ファイル |
|---|---|---|
| 確率の土台 | 単勝オッズ→正規化→**λ-Harville(1.00/0.80/0.70)** | `prob_core.py` |
| 掛けてよい要素 | **両関門を2回連続で通った消しだけ**: 斤量有利70以上×0.94／馬体重-10kg以下×0.92 | `prob_core.KESHI` |
| 買い目ルール | **K1の1本**: lift＝p消し後/p市場のみ、EV_est＝払戻率×lift ≧1.0 の券だけ。無ければ見送り。予算1万・反比例・100円単位・Σ(1/配当)≦1 | `kaime_core.py` → `db/rule_k1_ledger.json` |
| 旧エンジン（並走） | `gen_kaime_v5.choose_pattern`（順位テーブル＋p/q妙味）。**変更しない**。前向き516R・86.3%［58〜125%］ | `weekly_forward_test.py` → `db/forward_test.json` |
| 公開に使う側 | 前向き成績が良いほう。**当面は旧エンジン**（K1は台帳のみ） | `gen_digest_sns.py` |
| 印 | 確率の順（◎○▲△△）。🔥＝消しの反射で市場より上がった8番人気以下。**印と買い目は同じpから出す** | `prob_core.marks` |
| 脚質補正 sc[8] | `{距離帯}|全ペース|{馬場}` の実測セル。**ペースは予測しない**（頭数からの予測44.3%＜常にM 45.6%） | `pace_factor.py` / `db/pace_style.json` |
| 候補の昇格経路 | `pdca_rounds.py` 両関門（全体\|z\|≥2＋後半\|z\|≥1.5同方向）を**2回連続** → `KESHI`へ。加点候補は前向き台帳を経てから | `db/pdca_rounds.json` / `db/sire_candidates.json` |
| 蓄積DB | 33,849頭・血統100%・ラップ48R〜・追い切り115頭〜 | `daily_pdca/db/` |

## 2. 守ること（禁止・必須）

### 分析
- 🔴 蓄積DBの `AI予測順位`・`独自指数`・F01〜F03は**結果リーク**（3着内93%が出る）。評価は**レース前records**（`engine_backtest.drop_leaky`）でのみ行う
- 🔴 新しい層（因子・補正・ガード）を足す前に `python index_audit_leakfree.py` で**市場1番人気に同条件で勝っているか**を測る。勝っていなければ足さない
- 🔴 在サンプルの発見はそのまま使わない。台帳に事前登録し、登録日以降のレースだけで判定（300帯スキャンはhold-outで全滅した）
- 🔴 週末1場12レース程度の偏り（枠・脚質）を一般則にしない。必ず全期間×人気条件付きで再現を確認する
- 🔴 「補正の幅が足りなかった」と上限を広げる前に、因子そのものが実測に合っているかを疑う（道悪±3→±8で3着馬を落とした）
- 🔴 型×買い方ROI・人気帯ROIは週で顔ぶれが変わる。**運用ルールにしない**。減点（消し）にだけ使う
- 予測パスに結果を混ぜたrecords（ファイル更新時刻＞レース日）は必ず除外

### 馬券・金額
- 🔴 **100円単位**。450円・620円は「買えない」ので絶対に書かない。25%上限に収まらない時は点数を変える
- 🔴 1レース上限10,000円（目安）。期待値マイナスならどう配分しても破産確率は1
- 🔴 3連単・3連複は実証できない券種（必要ベット2万）。検証は単勝・複勝・ワイド・馬連で行う
- 見送りも台帳に残す。見送ったレースにもSNS用の提示買い目は出す（ファイル名 `sns_kaime_*.json`）

### SNS（確立済み・変更禁止）
- 冒頭2行ヘッダー: `🏇【レース名 G1】YYYY年M月D日（曜）` ／ `━━ 競馬場 芝/ダXXXXm / XX頭 ━━` → リード文 → `─────` で挟んだ見出し
- 重賞は **X・Threads各4〜6投稿のスレッド**（①印一覧+消し+穴 ②◎ ③○ ④▲穴 ⑤△消し ⑥買い目）。1本長文への圧縮禁止
- X本文は**141字目で折りたたまれる**。言いたいことは親投稿の冒頭140字以内に。Threadsは1投稿500字以内（自動チェック必須）
- 🔴 印の直後に「（N番人気）」を書かない（人気は変わる）。理由の文中で触れるのは可
- 🔴 サイト名・インフルエンサー名・芸能人名・内部用語（PDCA・合算・sc[]・EV）を公開文に書かない。「EV」は「期待値」に開く
- 🔴 自己卑下（「指数が市場より当たる証拠はない」等）を公開文に書かない
- 時制: 前日投稿＝「明日発走」、投稿日のレース結果＝「本日の実測」
- note: 冒頭フック「こんにちは、アスメシ競馬予想です🍱＋明日の飯代を懸けて＋結論を先に言います」、マークダウン記号（# ** ）禁止、12セクション（原本アーカイブ参照）
- 投稿案は必ずdocxも出す。画像は印インフォグラフィック（9:16・七夕賞構図）とnoteヘッダー（`keiba-thumbnail-ss`）
- G1連載『AI指数 vs 1番人気』の6コーナー・カレンダーは `gen_g1_campaign.py`

## 3. 毎週の手順（この順で・省略禁止）

```
金〜土（前日）
  python collect_weekend_bigdata.py            # レース前records（素性＝ファイル更新時刻がレース前）
  python race_history.py <重賞名>               # 重賞の型データを自前集計
  外部照合（競馬ラボ／重賞ナビ／うましる追切）→ python oikiri_store.py --add DATE 場 R "馬名:S ..."
  インフルエンサー収集 → *_influencer.json → python influencer_ledger.py --add-week <dir> --date DATE
  python gen_digest_sns.py ...                 # SNS素材（X/Threads/note/docx）
土日 当日朝（必須・省略禁止）
  python odds_snapshot.py                      # 実オッズ
  python scratch_check.py                      # 出走取消
  python kaime_core.py --day DATE --register    # K1登録（見送り含む・台帳に残す）
  python gen_kaime_v5.py --odds-file ...        # 旧エンジンの当日再計算 → 公開はこちら
土日 終了後
  python fetch_payouts.py --dates DATE
  python weekly_forward_test.py --date DATE     # 旧エンジン前向き（リーク除外込み）
  python kaime_core.py --settle --report        # K1前向き
  python review_weekend.py --dates ...          # 公開買い目の答え合わせ
  python weekend_full_review.py --dates ...     # 全レースの決着傾向
  python fetch_margin_lap.py --date DATE --write
  python band_hitrate.py ; python band_tracker.py --update
  python pdca_rounds.py --rounds 100            # 消し候補の再検定（2回連続通過で KESHI へ）
  python oikiri_store.py --evaluate
  結果報告SNS（正直報告・収支明記）→ 来週狙い目SNS
月（新開催が貯まったら）
  python pace_style_audit.py ; python sire_condition_scan.py ; python backfill_bloodline_smartrc.py --write
```

## 4. 台帳・検証スクリプト（場所）

| 目的 | ファイル |
|---|---|
| 旧エンジン前向き（516R〜） | `db/forward_test.json` ← `weekly_forward_test.py` |
| K1前向き | `db/rule_k1_ledger.json` ← `kaime_core.py` |
| R1（◎○1〜3人気の馬連BOX3）前向き | `db/rule_r1_ledger.json` ← `rule_forward_ledger.py` |
| 人気帯の追跡（in-sample/forward分離） | `db/band_tracking.json` ← `band_tracker.py` |
| 消し候補の検定 | `db/pdca_rounds.json` ← `pdca_rounds.py` |
| 種牡馬×条件の候補（eval_from以降で判定） | `db/sire_candidates.json` ← `sire_condition_scan.py` |
| 指数が市場に勝っているか | `index_audit_leakfree.py` |
| 公開買い目の実測 | `review_weekend.py` ／ `db/roi_ledger.json` |
| 追い切り | `db/oikiri.json` ← `oikiri_store.py` |
| インフルエンサー | `db/influencer_ledger.json` ← `influencer_ledger.py`（重みは `influencer_weight.py`） |
| 脚質×距離×馬場 | `db/pace_style.json`（＋外部裏取り `pace_style_external.json`） |

## 5. 判定基準（事前登録・動かさない）

- ルール採用: 前向き累計の95%区間の**下限が100%超**
- ルール棄却: 買った100レース時点で**最高配当1レース除外の回収率 < 80%**
- 要素の昇格: pdca両関門を2回連続通過（加点方向は前向き台帳を経由）
- 帯の棄却: forward の95%区間が100%を下回りきったとき

## 6. 現在のフェーズ

SNSは集客、実際には買わない。予想は軽く出してSNSを回し、**検証はDBで積む**。
K1は2026-09-26〜27の48Rで1レースも買わなかった（lift最大1.050）＝今ある消しは控除率を超えない。
これは失敗ではなく現状の記述。次に前向き検証を通った要素が入ったときに初めて発火する。

## 7. 関連

- 原本（v3.3全文・SNSテンプレ・20因子表・旧ガード）: `SKILL_full_archive_20260927.md`
- 決定記録: `docs/keiba_system_redesign_20260927.md` ／ `docs/keiba_roi100_roadmap.md` ／ `DECISION_LOG.md`
- 関連スキル: `keiba-draw-complete-ss`（枠順確定後パッケージ）／ `keiba-thumbnail-ss`（noteヘッダー）／ `chatgpt-image-devtools-ss`（印画像）
- 一回限りスクリプトの置き場: `src/keiba-predictor/archive/`（新規に日付付きを作らず、汎用スクリプトに引数で渡す）
