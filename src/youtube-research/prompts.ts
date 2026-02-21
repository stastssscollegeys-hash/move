// YouTube Research Tool - AI Prompt Templates
// 動画リサーチ → 本・コンテンツ制作に活かすための分析プロンプト

export const SYSTEM_PROMPT = `あなたはYouTube動画リサーチとコンテンツマーケティングの専門家です。
動画のタイトル・概要欄・タグ・再生数・チャンネル情報から以下を推測・分析してください:
- その動画を見ている人はどんな人か（＝次に本やコンテンツを出す際のターゲット）
- その動画はどんなキーワードで検索されて見られているか（タイトルと概要欄の共通ワードから推測）
- なぜその動画が伸びているか（＝再現可能な勝ちパターン）

分析のコツ:
- タイトルに含まれるキーワードは視聴者が検索したワードと高い相関がある
- 概要欄にタイトルと同じワードが繰り返されていれば、それがメインキーワード
- タグはクリエイターがSEO目的で設定したもので、狙っているキーワードそのもの
- 再生数÷登録者数（バズ比率）が高い動画は、検索やおすすめ経由で外部流入が多い
- 「不明」と回答せず、利用可能なデータから最善の推測を行うこと

必ずJSON形式で回答してください。JSONの前後に余計なテキストを入れないでください。`;

export function buildBuzzAnalysisPrompt(videos: { title: string; description: string; channel: string }[]): string {
  const videoList = videos
    .map((v, i) => `### 動画 ${i + 1}\n- タイトル: ${v.title}\n- チャンネル: ${v.channel}\n- 説明文: ${v.description}`)
    .join('\n\n');

  return `以下のバズ動画に共通するパターンを分析してください。

${videoList}

以下のJSON形式で回答してください:
{
  "titlePatterns": "タイトルの共通パターン（数字、疑問形、煽り等）",
  "commonThemes": "共通テーマ",
  "timingInsights": "投稿タイミングに関する考察",
  "thumbnailGuess": "タイトルから推測できるサムネイル要素",
  "lengthTrend": "動画の長さの傾向",
  "whyBuzzed": "なぜバズったと考えられるか（3行以内）"
}`;
}

export function buildAudiencePrompt(content: string): string {
  return `以下のYouTube動画データ（タイトル・概要欄・タグ・再生数・チャンネル情報）を分析し、この動画を見ている人のターゲット像を推定してください。
この分析結果は「次に本や記事・コンテンツを出す際のターゲット設定」に使います。

## 分析のポイント
- タイトルのキーワードから「どんな悩みを持つ人が検索しているか」を推測
- 概要欄の内容から「動画が解決しようとしている課題」を読み取る
- タグから「クリエイターが想定しているターゲット層」を把握
- 再生数と登録者数の比率から「どの程度外部から流入しているか」を推測
- チャンネル名からジャンルや専門性を判断
- 「不明」とは回答せず、データから最善の推測を行うこと

## 動画データ
${content}

以下のJSON形式で回答してください:
{
  "demographics": {
    "ageRange": "例: 25-35歳",
    "gender": "例: 男女比6:4で男性やや多め",
    "occupation": "例: IT企業勤務、フリーランス、副業に興味がある会社員"
  },
  "psychographics": {
    "interests": ["興味1", "興味2", "興味3"],
    "values": ["価値観1", "価値観2"],
    "lifestyle": "ライフスタイルの説明"
  },
  "painPoints": ["この人たちが抱える課題1", "課題2", "課題3"],
  "viewingMotivation": ["なぜこの動画を見るのか1", "動機2", "動機3"],
  "purchaseBehavior": ["どんな本・教材・サービスを買いそうか1", "購買傾向2"],
  "relatedMedia": ["他にどんなチャンネル・メディアを見ているか1", "類似メディア2"],
  "contentAngle": "この層に刺さるコンテンツ（本・記事）の切り口提案"
}`;
}

export function buildKeywordPrompt(content: string): string {
  return `以下のYouTube動画データ（タイトル・概要欄・タグ・再生数・チャンネル情報）から、キーワード分析を行ってください。

## 分析手法
1. **タイトル分析**: タイトルに含まれるキーワードは、視聴者が実際に検索したワードと高い相関があります。複数動画のタイトルに共通するワードは特に重要です。
2. **概要欄分析**: 概要欄にタイトルと同じワードが繰り返されていれば、それがメインキーワードです。概要欄だけに出てくるワードはサブキーワード候補です。
3. **タグ分析**: タグはクリエイターがSEO目的で設定したもので、狙っているキーワードそのものです。
4. **クロス分析**: タイトル・概要欄・タグの3つに共通で出現するワードが最重要キーワードです。

## 抽出すべきキーワードの種類
1. この動画が「どんなキーワードで検索されて見られているか」（視聴者の検索ワード推測）
2. 「次に自分がコンテンツ（本・記事・動画）を出すとき使うべきキーワード」

## 動画データ
${content}

重要: 「不明」とは絶対に回答しないでください。データから最善の推測を行ってください。

以下のJSON形式で回答してください。各カテゴリ最大10個:
{
  "keywords": [
    {
      "keyword": "キーワード",
      "category": "main|sub|longtail|related|buying-intent|question|trending",
      "estimatedVolume": "high|medium|low",
      "competition": "high|medium|low",
      "relevance": "high|medium|low",
      "suggestedUse": ["YouTube SEO", "本のタイトル", "ブログ記事", "SNS投稿"],
      "nextContentIdea": "このキーワードを使った次のコンテンツアイデア（1行）"
    }
  ]
}`;
}

export function buildTrendCheckPrompt(videoTitle: string): string {
  return `あなたはYouTubeコンテンツ企画とトレンド分析の専門家です。

## タスク
以下のYouTube動画タイトルを見て、この動画の「企画テーマ」を抽出し、その企画が今YouTube動画としてまだイケるか（需要があるか・伸びるか）を判定してください。

## 動画タイトル
「${videoTitle}」

## 企画テーマの抽出ルール
- タイトルから「この動画は何についての企画か」を短いフレーズ（5〜20文字）で抽出してください
- 煽り表現（「末路」「やばい」「衝撃」等）や装飾は除いて、**核となるテーマ**だけを取り出してください
- 例:
  - 「クロードコードのバイブコーディングにはまった人の末路」→「Claude Codeのバイブコーディング」
  - 「【2025年最新】ChatGPTで月10万稼ぐ副業5選がヤバすぎた」→「ChatGPTで稼ぐ副業」
  - 「40代会社員が1年間筋トレした結果が凄かった」→「40代の筋トレビフォーアフター」

## 判定基準
- **検索トレンド**: この企画テーマの検索ボリュームは増加傾向か？
  - rising: 最近急上昇している旬のテーマ
  - stable: 安定して検索されている定番テーマ
  - declining: ピークを過ぎて下降傾向

- **YouTube上の動向**: この企画テーマの動画はYouTubeで増えているか？
  - rising: 新しい動画が次々アップされている旬のネタ
  - stable: コンスタントに動画がある
  - declining: 古い動画ばかりで新規が減っている

- **競合度**: この企画テーマで動画を出しているYouTuberの数
  - low: まだ少ない＝ブルーオーシャン
  - medium: それなりにいる
  - high: 大手含め多数が出している＝レッドオーシャン

- **総合判定（この企画で今から動画を出すべきか）**:
  - go-now: 上昇中＋競合少ない＝今すぐ出すべき最高タイミング
  - first-mover: まだ新しい＝先行者優位を取れる
  - chance-but-competitive: 需要はあるが競合多い＝差別化が必要
  - niche-stable: ニッチだが安定需要あり＝堅実に狙える
  - too-late: 下降＋飽和＝この企画はもう遅い

## 重要ルール
- 「unknown」とは絶対に回答しないでください
- あなたの知識と推論から必ず判定を行ってください
- 日本市場（日本語YouTube）の観点で判定してください

以下のJSON形式で回答してください:
{
  "topic": "抽出した企画テーマ（5〜20文字）",
  "googleTrends": "rising|stable|declining",
  "youtubeSearch": "rising|stable|declining",
  "competition": "low|medium|high",
  "verdict": "go-now|chance-but-competitive|first-mover|niche-stable|too-late",
  "reasoning": "この企画で今から動画を出すべきかの判定理由（2行以内）"
}`;
}

export function buildRecommendationsPrompt(
  buzzSummary: string,
  trendSummary: string,
  audienceSummary: string,
  keywordSummary: string
): string {
  return `以下の分析結果を踏まえ、次に出すべきコンテンツ（本・記事・動画）の推奨アクションを5つ提案してください。
「適当にYouTubeリサーチして本を出したら売れた」という成功パターンを再現するための提案です。

## バズ分析
${buzzSummary}

## トレンド判定
${trendSummary}

## ターゲット層
${audienceSummary}

## キーワード
${keywordSummary}

以下のJSON形式で回答してください:
{
  "recommendations": [
    "推奨アクション1: 理由",
    "推奨アクション2: 理由",
    "推奨アクション3: 理由",
    "推奨アクション4: 理由",
    "推奨アクション5: 理由"
  ],
  "bookTitleIdeas": [
    "本のタイトル案1",
    "本のタイトル案2",
    "本のタイトル案3"
  ],
  "contentCalendar": "今後1ヶ月で出すべきコンテンツの順番提案（3行以内）"
}`;
}
