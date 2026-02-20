import Anthropic from '@anthropic-ai/sdk';
import {
  VideoInput, VideoMeta, FilterParams,
  BuzzResult, TrendResult, AudienceProfile, KeywordEntry,
  AnalyzeRequest, AnalyzeResponse, BuzzResponse, TrendResponse,
  SearchRequest, SearchResponse
} from './types';
import {
  SYSTEM_PROMPT,
  buildBuzzAnalysisPrompt,
  buildAudiencePrompt,
  buildKeywordPrompt,
  buildTrendCheckPrompt,
  buildRecommendationsPrompt
} from './prompts';

export class YouTubeResearchService {
  private client: Anthropic | null = null;
  private model = 'claude-sonnet-4-5-20250929';

  constructor(anthropicApiKey?: string) {
    if (anthropicApiKey) {
      this.client = new Anthropic({ apiKey: anthropicApiKey });
    } else if (process.env.ANTHROPIC_API_KEY) {
      this.client = new Anthropic();
    }
  }

  // --- YouTube Data API Search ---

  async searchYouTube(query: string, filters: FilterParams, apiKey: string, maxResults = 20): Promise<VideoMeta[]> {
    // Step 1: Search for videos
    const searchParams = new URLSearchParams({
      part: 'snippet',
      q: query,
      type: 'video',
      order: 'viewCount',
      maxResults: String(maxResults),
      key: apiKey,
    });

    // Video duration filter
    if (filters.lengthCategory === 'short') searchParams.set('videoDuration', 'short');
    else if (filters.lengthCategory === 'medium') searchParams.set('videoDuration', 'medium');
    else if (filters.lengthCategory === 'long') searchParams.set('videoDuration', 'long');

    // Upload date filter
    if (filters.uploadPeriod !== 'all') {
      const now = new Date();
      const dateMap: Record<string, number> = { week: 7, month: 30, '3months': 90, year: 365 };
      const days = dateMap[filters.uploadPeriod] || 0;
      if (days > 0) {
        const after = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
        searchParams.set('publishedAfter', after.toISOString());
      }
    }

    const searchRes = await fetch(`https://www.googleapis.com/youtube/v3/search?${searchParams}`);
    if (!searchRes.ok) {
      const err = await searchRes.text();
      throw new Error(`YouTube Search API error: ${searchRes.status} ${err}`);
    }
    const searchData = await searchRes.json();
    const videoIds = (searchData.items || []).map((item: any) => item.id.videoId).filter(Boolean);

    if (videoIds.length === 0) return [];

    // Step 2: Get video details (views, likes, duration)
    const detailParams = new URLSearchParams({
      part: 'snippet,statistics,contentDetails',
      id: videoIds.join(','),
      key: apiKey,
    });

    const detailRes = await fetch(`https://www.googleapis.com/youtube/v3/videos?${detailParams}`);
    if (!detailRes.ok) throw new Error(`YouTube Videos API error: ${detailRes.status}`);
    const detailData = await detailRes.json();

    // Step 3: Get channel subscriber counts
    const channelIds = [...new Set((detailData.items || []).map((item: any) => item.snippet.channelId))];
    let channelSubs: Record<string, number> = {};

    if (channelIds.length > 0) {
      const chParams = new URLSearchParams({
        part: 'statistics',
        id: (channelIds as string[]).join(','),
        key: apiKey,
      });
      const chRes = await fetch(`https://www.googleapis.com/youtube/v3/channels?${chParams}`);
      if (chRes.ok) {
        const chData = await chRes.json();
        for (const ch of chData.items || []) {
          channelSubs[ch.id] = parseInt(ch.statistics.subscriberCount || '0', 10);
        }
      }
    }

    // Step 4: Build VideoMeta array
    return (detailData.items || []).map((item: any, i: number) => {
      const stats = item.statistics || {};
      const snippet = item.snippet || {};
      return {
        id: item.id,
        title: snippet.title || '',
        channel: snippet.channelTitle || '',
        subscribers: channelSubs[snippet.channelId] || null,
        views: parseInt(stats.viewCount || '0', 10),
        likes: parseInt(stats.likeCount || '0', 10),
        uploadDate: snippet.publishedAt || null,
        duration: item.contentDetails?.duration || null,
        description: snippet.description || '',
        transcriptOrSummary: '',
        url: `https://youtube.com/watch?v=${item.id}`,
      };
    });
  }

  // Step 1: YouTube検索 + バズ比率算出（Claude不要・高速）
  async searchWithBuzz(request: SearchRequest): Promise<SearchResponse> {
    try {
      const videos = await this.searchYouTube(request.query, request.filters, request.youtubeApiKey, request.maxResults || 20);

      if (videos.length === 0) {
        return { success: false, error: '動画が見つかりませんでした。キーワードを変えてみてください。' };
      }

      // バズ比率は計算だけ（Claude不要）
      const buzzRanking: BuzzResult[] = videos.map(video => {
        let buzzRatio: number | null = null;
        let buzzLevel: BuzzResult['buzzLevel'] = 'unknown';
        if (video.views !== null && video.subscribers !== null && video.subscribers > 0) {
          buzzRatio = video.views / video.subscribers;
          if (buzzRatio >= 10) buzzLevel = 'super-buzz';
          else if (buzzRatio >= 5) buzzLevel = 'buzz';
          else if (buzzRatio >= 2) buzzLevel = 'good';
          else if (buzzRatio >= 1) buzzLevel = 'average';
          else buzzLevel = 'low';
        }
        return { video, buzzRatio, buzzLevel };
      });

      buzzRanking.sort((a, b) => {
        if (a.buzzRatio === null) return 1;
        if (b.buzzRatio === null) return -1;
        return b.buzzRatio - a.buzzRatio;
      });

      return {
        success: true,
        data: {
          query: request.query,
          videoCount: videos.length,
          videos,
          buzzRanking,
          audience: undefined as any,
          keywords: [],
          recommendations: [],
          fullReport: '',
        }
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, error: message };
    }
  }

  // Step 2: 選択した動画に対してターゲット＆キーワード＆レポート生成（Claude使用）
  async analyzeSelected(videos: VideoMeta[]): Promise<{
    success: boolean;
    data?: { audience: AudienceProfile; keywords: KeywordEntry[]; recommendations: string[]; fullReport: string };
    error?: string;
  }> {
    try {
      if (!this.client) {
        return { success: false, error: 'Anthropic APIキーが設定されていません' };
      }

      const audience = await this.analyzeAudience(videos);
      const keywords = await this.extractKeywords(videos);

      const recsRaw = await this.callClaude(buildRecommendationsPrompt(
        'バズ動画の共通パターン分析',
        '',
        JSON.stringify(audience.demographics),
        keywords.slice(0, 5).map(k => k.keyword).join(', ')
      ));

      let recommendations: string[] = [];
      try {
        const parsed = JSON.parse(recsRaw);
        recommendations = parsed.recommendations || [];
      } catch {
        recommendations = ['分析データを元にコンテンツ企画を検討してください'];
      }

      const fullReport = this.buildReport(videos, [], [], audience, keywords, recommendations, { lengthCategory: 'all', uploadPeriod: 'all' });

      return { success: true, data: { audience, keywords, recommendations, fullReport } };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, error: message };
    }
  }

  // --- Phase 2: Metadata ---

  async fetchVideoMetadata(inputs: VideoInput[]): Promise<VideoMeta[]> {
    return inputs.map((input, i) => {
      const isUrl = input.inputType === 'url' || input.rawText.match(/youtube\.com|youtu\.be/);
      return {
        id: `video_${String(i + 1).padStart(3, '0')}`,
        title: isUrl ? this.extractFromText(input.rawText, 'title') : `動画 ${i + 1}`,
        channel: '',
        subscribers: null,
        views: null,
        likes: null,
        uploadDate: null,
        duration: null,
        description: '',
        transcriptOrSummary: isUrl ? '' : input.rawText,
        url: isUrl ? input.rawText.trim() : null
      };
    });
  }

  private extractFromText(text: string, _field: string): string {
    // URL from text
    const urlMatch = text.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
    return urlMatch ? `YouTube Video (${urlMatch[1]})` : 'Unknown';
  }

  // --- Phase 3: Buzz Detection ---

  async detectBuzz(videos: VideoMeta[]): Promise<BuzzResponse> {
    const ranking: BuzzResult[] = videos.map(video => {
      let buzzRatio: number | null = null;
      let buzzLevel: BuzzResult['buzzLevel'] = 'unknown';

      if (video.views !== null && video.subscribers !== null && video.subscribers > 0) {
        buzzRatio = video.views / video.subscribers;
        if (buzzRatio >= 10) buzzLevel = 'super-buzz';
        else if (buzzRatio >= 5) buzzLevel = 'buzz';
        else if (buzzRatio >= 2) buzzLevel = 'good';
        else if (buzzRatio >= 1) buzzLevel = 'average';
        else buzzLevel = 'low';
      }

      return { video, buzzRatio, buzzLevel };
    });

    // Sort by buzz ratio descending (unknowns at end)
    ranking.sort((a, b) => {
      if (a.buzzRatio === null) return 1;
      if (b.buzzRatio === null) return -1;
      return b.buzzRatio - a.buzzRatio;
    });

    // AI analysis of common patterns in top buzz videos
    const buzzVideos = ranking.filter(r => r.buzzLevel === 'super-buzz' || r.buzzLevel === 'buzz' || r.buzzLevel === 'good');
    let commonPatterns = '';

    if (buzzVideos.length > 0) {
      const videoData = buzzVideos.map(r => ({
        title: r.video.title,
        description: r.video.description || r.video.transcriptOrSummary.slice(0, 500),
        channel: r.video.channel
      }));
      commonPatterns = await this.callClaude(buildBuzzAnalysisPrompt(videoData));
    }

    return { success: true, data: { ranking, commonPatterns } };
  }

  // --- Phase 4: Trend Check ---

  async checkTrend(keywords: string[]): Promise<TrendResponse> {
    const results: TrendResult[] = [];

    for (const keyword of keywords) {
      // Use AI to assess trend based on general knowledge
      const prompt = buildTrendCheckPrompt(keyword, `キーワード「${keyword}」について、現在のGoogle Trends、YouTube検索トレンド、競合状況を推定してください。`);
      const raw = await this.callClaude(prompt);

      try {
        const parsed = JSON.parse(raw);
        results.push({
          keyword,
          googleTrends: parsed.googleTrends || 'unknown',
          youtubeSearch: parsed.youtubeSearch || 'unknown',
          competition: parsed.competition || 'unknown',
          verdict: parsed.verdict || 'unknown'
        });
      } catch {
        results.push({
          keyword,
          googleTrends: 'unknown',
          youtubeSearch: 'unknown',
          competition: 'unknown',
          verdict: 'unknown'
        });
      }
    }

    const summary = results
      .map(r => `${r.keyword}: ${this.verdictLabel(r.verdict)}`)
      .join('\n');

    return { success: true, data: { results, summary } };
  }

  // --- Phase 5: Audience Analysis ---

  async analyzeAudience(videos: VideoMeta[]): Promise<AudienceProfile> {
    const content = videos
      .map(v => `タイトル: ${v.title}\nチャンネル: ${v.channel}\n説明: ${v.description}\n内容: ${v.transcriptOrSummary.slice(0, 2000)}`)
      .join('\n---\n');

    const raw = await this.callClaude(buildAudiencePrompt(content));

    try {
      return JSON.parse(raw);
    } catch {
      return {
        demographics: { ageRange: '不明', gender: '不明', occupation: '不明' },
        psychographics: { interests: [], values: [], lifestyle: '不明' },
        painPoints: [],
        viewingMotivation: [],
        purchaseBehavior: [],
        relatedMedia: []
      };
    }
  }

  // --- Phase 6: Keyword Extraction ---

  async extractKeywords(videos: VideoMeta[]): Promise<KeywordEntry[]> {
    const content = videos
      .map(v => `タイトル: ${v.title}\n説明: ${v.description}\n内容: ${v.transcriptOrSummary.slice(0, 2000)}`)
      .join('\n---\n');

    const raw = await this.callClaude(buildKeywordPrompt(content));

    try {
      const parsed = JSON.parse(raw);
      return parsed.keywords || [];
    } catch {
      return [];
    }
  }

  // --- Phase 7: Full Analysis ---

  async fullAnalysis(request: AnalyzeRequest): Promise<AnalyzeResponse> {
    try {
      // Phase 2
      const videos = await this.fetchVideoMetadata(request.videos);

      // Phase 3
      const buzzResult = await this.detectBuzz(videos);
      const buzzRanking = buzzResult.data?.ranking || [];

      // Phase 4: Extract keywords from top videos for trend check
      const topKeywords = videos
        .slice(0, 5)
        .map(v => v.title)
        .filter(t => t && t !== 'Unknown');
      const trendResult = topKeywords.length > 0
        ? await this.checkTrend(topKeywords.slice(0, 3))
        : { success: true, data: { results: [], summary: '' } };
      const trendCheck = trendResult.data?.results || [];

      // Phase 5
      const audience = await this.analyzeAudience(videos);

      // Phase 6
      const keywords = await this.extractKeywords(videos);

      // Phase 7: Recommendations
      const recsRaw = await this.callClaude(buildRecommendationsPrompt(
        buzzResult.data?.commonPatterns || 'バズ分析データなし',
        trendResult.data?.summary || 'トレンドデータなし',
        JSON.stringify(audience.demographics),
        keywords.slice(0, 5).map(k => k.keyword).join(', ')
      ));

      let recommendations: string[] = [];
      try {
        const parsed = JSON.parse(recsRaw);
        recommendations = parsed.recommendations || [];
      } catch {
        recommendations = ['分析データを元に動画企画を検討してください'];
      }

      // Build full report markdown
      const fullReport = this.buildReport(videos, buzzRanking, trendCheck, audience, keywords, recommendations, request.filters);

      return {
        success: true,
        data: {
          videoCount: videos.length,
          videos,
          buzzRanking,
          trendCheck,
          audience,
          keywords,
          recommendations,
          fullReport
        }
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, error: message };
    }
  }

  // --- Helpers ---

  private async callClaude(userPrompt: string): Promise<string> {
    if (!this.client) {
      throw new Error('Anthropic APIキーが設定されていません');
    }
    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: userPrompt }]
    });

    const block = response.content[0];
    return block.type === 'text' ? block.text : '';
  }

  private verdictLabel(verdict: string): string {
    const labels: Record<string, string> = {
      'go-now': '今すぐ出すべき！',
      'chance-but-competitive': 'チャンスだが競争激しい',
      'first-mover': '先行者優位を取れる',
      'niche-stable': 'ニッチで安定的に狙える',
      'too-late': 'タイミング遅い',
      'unknown': '判定不可'
    };
    return labels[verdict] || verdict;
  }

  private buildReport(
    videos: VideoMeta[],
    buzzRanking: BuzzResult[],
    trendCheck: TrendResult[],
    audience: AudienceProfile,
    keywords: KeywordEntry[],
    recommendations: string[],
    filters: FilterParams
  ): string {
    const date = new Date().toISOString().split('T')[0];
    const filterStr = [
      filters.keyword && `キーワード: ${filters.keyword}`,
      filters.genre && `ジャンル: ${filters.genre}`,
      `動画長: ${filters.lengthCategory}`,
      `期間: ${filters.uploadPeriod}`
    ].filter(Boolean).join(' / ');

    const buzzTable = buzzRanking
      .map((r, i) => `| ${i + 1} | ${r.video.title} | ${r.video.channel || '-'} | ${r.video.views ?? '-'} | ${r.video.subscribers ?? '-'} | ${r.buzzRatio?.toFixed(1) ?? '-'} | ${this.buzzLabel(r.buzzLevel)} |`)
      .join('\n');

    const trendTable = trendCheck
      .map(r => `| ${r.keyword} | ${this.trendArrow(r.googleTrends)} | ${this.trendArrow(r.youtubeSearch)} | ${this.compLabel(r.competition)} | ${this.verdictLabel(r.verdict)} |`)
      .join('\n');

    const kwTable = keywords
      .slice(0, 20)
      .map(k => `| ${k.keyword} | ${k.category} | ${k.estimatedVolume} | ${k.competition} | ${k.suggestedUse.join(', ')} |`)
      .join('\n');

    const recsStr = recommendations.map((r, i) => `${i + 1}. ${r}`).join('\n');

    return `# YouTube動画リサーチレポート

## 分析概要
- 分析日: ${date}
- 対象動画数: ${videos.length}
- フィルター条件: ${filterStr}

## バズ動画ランキング
| 順位 | タイトル | チャンネル | 再生数 | 登録者数 | バズ比率 | 判定 |
|------|---------|-----------|--------|---------|---------|------|
${buzzTable}

## トレンド判定
| キーワード | Google Trends | YouTube検索 | 競合度 | 総合判定 |
|-----------|-------------|------------|--------|---------|
${trendTable}

## ターゲットオーディエンス
### デモグラフィック
- 年齢層: ${audience.demographics.ageRange}
- 性別: ${audience.demographics.gender}
- 職業: ${audience.demographics.occupation}

### 興味関心
${audience.psychographics.interests.map(i => `- ${i}`).join('\n')}

### 課題・悩み
${audience.painPoints.map(p => `- ${p}`).join('\n')}

### 視聴動機
${audience.viewingMotivation.map(m => `- ${m}`).join('\n')}

## キーワード分析
| キーワード | カテゴリ | ボリューム | 競合度 | 用途 |
|-----------|---------|-----------|--------|------|
${kwTable}

## 推奨アクション
${recsStr}
`;
  }

  private buzzLabel(level: string): string {
    const labels: Record<string, string> = {
      'super-buzz': '超バズ',
      'buzz': 'バズ',
      'good': '好調',
      'average': '平均',
      'low': '低調',
      'unknown': '-'
    };
    return labels[level] || level;
  }

  private trendArrow(trend: string): string {
    const arrows: Record<string, string> = {
      'rising': '↑上昇',
      'stable': '→横ばい',
      'declining': '↓下降',
      'unknown': '?'
    };
    return arrows[trend] || trend;
  }

  private compLabel(comp: string): string {
    const labels: Record<string, string> = {
      'low': '少○',
      'medium': '普通△',
      'high': '多×',
      'unknown': '?'
    };
    return labels[comp] || comp;
  }
}
