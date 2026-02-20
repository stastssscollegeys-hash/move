// YouTube Research Tool - AI Prompt Templates
// 動画リサーチ → 本・コンテンツ制作に活かすための分析プロンプト

export const SYSTEM_PROMPT = `あなたはYouTube動画リサーチとコンテンツマーケティングの専門家です。
動画データを分析し、以下を正確に抽出してください:
- その動画を見ている人はどんな人か（＝次に本やコンテンツを出す際のターゲット）
- その動画はどんなキーワードで見られているか（＝次のコンテンツに使うべきキーワード）
- なぜその動画が伸びているか（＝再現可能な勝ちパターン）
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
  return `以下のYouTube動画コンテンツを分析し、この動画を見ている人のターゲット像を推定してください。
この分析結果は「次に本や記事・コンテンツを出す際のターゲット設定」に使います。

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
  return `以下のYouTube動画コンテンツから2種類のキーワードを抽出してください:
1. この動画が「どんなキーワードで見られているか」（視聴者が検索しそうなワード）
2. 「次に自分がコンテンツ（本・記事・動画）を出すとき使うべきキーワード」

## 動画データ
${content}

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

export function buildTrendCheckPrompt(keyword: string, searchResults: string): string {
  return `以下の検索結果から「${keyword}」のトレンド状況を判定してください。

## 検索結果
${searchResults}

以下のJSON形式で回答してください:
{
  "googleTrends": "rising|stable|declining|unknown",
  "youtubeSearch": "rising|stable|declining|unknown",
  "competition": "low|medium|high|unknown",
  "verdict": "go-now|chance-but-competitive|first-mover|niche-stable|too-late|unknown",
  "reasoning": "判定理由（2行以内）"
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
