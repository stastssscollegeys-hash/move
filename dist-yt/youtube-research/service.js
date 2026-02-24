"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.YouTubeResearchService = void 0;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const prompts_1 = require("./prompts");
class YouTubeResearchService {
    constructor(anthropicApiKey) {
        this.client = null;
        this.model = 'claude-sonnet-4-5-20250929';
        if (anthropicApiKey) {
            this.client = new sdk_1.default({ apiKey: anthropicApiKey });
        }
        else if (process.env.ANTHROPIC_API_KEY) {
            this.client = new sdk_1.default();
        }
    }
    // --- YouTube Data API Search ---
    async searchYouTube(query, filters, apiKey, maxResults = 20) {
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
        if (filters.lengthCategory === 'short')
            searchParams.set('videoDuration', 'short');
        else if (filters.lengthCategory === 'medium')
            searchParams.set('videoDuration', 'medium');
        else if (filters.lengthCategory === 'long')
            searchParams.set('videoDuration', 'long');
        // Region + language filter
        if (filters.regionCode && filters.regionCode !== 'all') {
            searchParams.set('regionCode', filters.regionCode);
            // Map region to primary language for relevance filtering
            const regionLangMap = {
                JP: 'ja', US: 'en', KR: 'ko', TW: 'zh-Hant', CN: 'zh-Hans',
                GB: 'en', DE: 'de', FR: 'fr', IN: 'hi', BR: 'pt',
            };
            const lang = regionLangMap[filters.regionCode];
            if (lang)
                searchParams.set('relevanceLanguage', lang);
        }
        // Upload date filter
        if (filters.uploadPeriod !== 'all') {
            const now = new Date();
            const dateMap = { week: 7, month: 30, '3months': 90, year: 365 };
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
        const videoIds = (searchData.items || []).map((item) => item.id.videoId).filter(Boolean);
        if (videoIds.length === 0)
            return [];
        // Step 2: Get video details (views, likes, duration)
        const detailParams = new URLSearchParams({
            part: 'snippet,statistics,contentDetails',
            id: videoIds.join(','),
            key: apiKey,
        });
        const detailRes = await fetch(`https://www.googleapis.com/youtube/v3/videos?${detailParams}`);
        if (!detailRes.ok)
            throw new Error(`YouTube Videos API error: ${detailRes.status}`);
        const detailData = await detailRes.json();
        // Step 3: Get channel subscriber counts
        const channelIds = [...new Set((detailData.items || []).map((item) => item.snippet.channelId))];
        let channelSubs = {};
        if (channelIds.length > 0) {
            const chParams = new URLSearchParams({
                part: 'statistics',
                id: channelIds.join(','),
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
        const rawVideos = (detailData.items || []).map((item) => {
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
                tags: Array.isArray(snippet.tags) ? snippet.tags : [],
                transcriptOrSummary: '',
                url: `https://youtube.com/watch?v=${item.id}`,
                thumbnail: snippet.thumbnails?.medium?.url || snippet.thumbnails?.default?.url || '',
                _lang: snippet.defaultAudioLanguage || snippet.defaultLanguage || '',
            };
        });
        // Step 5: Post-filter by language if region is specified
        if (filters.regionCode && filters.regionCode !== 'all') {
            const regionLangMap = {
                JP: { lang: 'ja', script: /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/ },
                KR: { lang: 'ko', script: /[\uAC00-\uD7AF\u1100-\u11FF]/ },
                TW: { lang: 'zh', script: /[\u4E00-\u9FFF]/ },
                CN: { lang: 'zh', script: /[\u4E00-\u9FFF]/ },
            };
            const mapping = regionLangMap[filters.regionCode];
            if (mapping) {
                const filtered = rawVideos.filter((v) => {
                    // 1. API言語フィールドが一致
                    if (v._lang && v._lang.startsWith(mapping.lang))
                        return true;
                    // 2. タイトルにその言語の文字が含まれる
                    if (mapping.script.test(v.title))
                        return true;
                    return false;
                });
                // フィルタ後の結果が少なすぎる場合はフィルタ前を返す
                const result = filtered.length >= 3 ? filtered : rawVideos;
                return result.map(({ _lang, ...rest }) => rest);
            }
        }
        return rawVideos.map(({ _lang, ...rest }) => rest);
    }
    // Step 1: YouTube検索 + バズ比率算出（Claude不要・高速）
    async searchWithBuzz(request) {
        try {
            const videos = await this.searchYouTube(request.query, request.filters, request.youtubeApiKey, request.maxResults || 20);
            if (videos.length === 0) {
                return { success: false, error: '動画が見つかりませんでした。キーワードを変えてみてください。' };
            }
            // バズ比率は計算だけ（Claude不要）
            const buzzRanking = videos.map(video => {
                let buzzRatio = null;
                let buzzLevel = 'unknown';
                if (video.views !== null && video.subscribers !== null && video.subscribers > 0) {
                    buzzRatio = video.views / video.subscribers;
                    if (buzzRatio >= 10)
                        buzzLevel = 'super-buzz';
                    else if (buzzRatio >= 5)
                        buzzLevel = 'buzz';
                    else if (buzzRatio >= 2)
                        buzzLevel = 'good';
                    else if (buzzRatio >= 1)
                        buzzLevel = 'average';
                    else
                        buzzLevel = 'low';
                }
                return { video, buzzRatio, buzzLevel };
            });
            buzzRanking.sort((a, b) => {
                if (a.buzzRatio === null)
                    return 1;
                if (b.buzzRatio === null)
                    return -1;
                return b.buzzRatio - a.buzzRatio;
            });
            return {
                success: true,
                data: {
                    query: request.query,
                    videoCount: videos.length,
                    videos,
                    buzzRanking,
                    audience: undefined,
                    keywords: [],
                    recommendations: [],
                    fullReport: '',
                }
            };
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error';
            return { success: false, error: message };
        }
    }
    // Step 2: 選択した動画に対してターゲット＆キーワード＆レポート生成（Claude使用）
    async analyzeSelected(videos) {
        try {
            if (!this.client) {
                return { success: false, error: 'Anthropic APIキーが設定されていません' };
            }
            // タイトル+概要欄+タグから分析（字幕は使わない）
            const audience = await this.analyzeAudience(videos);
            const keywords = await this.extractKeywords(videos);
            const recsRaw = await this.callClaude((0, prompts_1.buildRecommendationsPrompt)('バズ動画の共通パターン分析', '', JSON.stringify(audience.demographics), keywords.slice(0, 5).map(k => k.keyword).join(', ')));
            let recommendations = [];
            try {
                const parsed = JSON.parse(recsRaw);
                recommendations = parsed.recommendations || [];
            }
            catch (e) {
                console.error('[analyzeSelected] Recommendations JSON parse failed:', recsRaw.slice(0, 300));
                recommendations = ['分析データを元にコンテンツ企画を検討してください'];
            }
            const fullReport = this.buildReport(videos, [], [], audience, keywords, recommendations, { lengthCategory: 'all', uploadPeriod: 'all' });
            return { success: true, data: { audience, keywords, recommendations, fullReport } };
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error';
            console.error('[analyzeSelected] Error:', message);
            return { success: false, error: message };
        }
    }
    // --- Phase 2: Metadata ---
    async fetchVideoMetadata(inputs) {
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
                tags: [],
                transcriptOrSummary: isUrl ? '' : input.rawText,
                url: isUrl ? input.rawText.trim() : null
            };
        });
    }
    extractFromText(text, _field) {
        // URL from text
        const urlMatch = text.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
        return urlMatch ? `YouTube Video (${urlMatch[1]})` : 'Unknown';
    }
    // --- Phase 3: Buzz Detection ---
    async detectBuzz(videos) {
        const ranking = videos.map(video => {
            let buzzRatio = null;
            let buzzLevel = 'unknown';
            if (video.views !== null && video.subscribers !== null && video.subscribers > 0) {
                buzzRatio = video.views / video.subscribers;
                if (buzzRatio >= 10)
                    buzzLevel = 'super-buzz';
                else if (buzzRatio >= 5)
                    buzzLevel = 'buzz';
                else if (buzzRatio >= 2)
                    buzzLevel = 'good';
                else if (buzzRatio >= 1)
                    buzzLevel = 'average';
                else
                    buzzLevel = 'low';
            }
            return { video, buzzRatio, buzzLevel };
        });
        // Sort by buzz ratio descending (unknowns at end)
        ranking.sort((a, b) => {
            if (a.buzzRatio === null)
                return 1;
            if (b.buzzRatio === null)
                return -1;
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
            commonPatterns = await this.callClaude((0, prompts_1.buildBuzzAnalysisPrompt)(videoData));
        }
        return { success: true, data: { ranking, commonPatterns } };
    }
    // --- Phase 4: Trend Check ---
    async checkTrend(titles) {
        const results = [];
        for (const title of titles) {
            const prompt = (0, prompts_1.buildTrendCheckPrompt)(title);
            const raw = await this.callClaude(prompt);
            try {
                const parsed = JSON.parse(raw);
                results.push({
                    originalTitle: title,
                    topic: parsed.topic || title,
                    googleTrends: parsed.googleTrends || 'stable',
                    youtubeSearch: parsed.youtubeSearch || 'stable',
                    competition: parsed.competition || 'medium',
                    verdict: parsed.verdict || 'niche-stable',
                    reasoning: parsed.reasoning || ''
                });
            }
            catch {
                results.push({
                    originalTitle: title,
                    topic: title,
                    googleTrends: 'unknown',
                    youtubeSearch: 'unknown',
                    competition: 'unknown',
                    verdict: 'unknown'
                });
            }
        }
        const summary = results
            .map(r => `${r.topic}: ${this.verdictLabel(r.verdict)}${r.reasoning ? '（' + r.reasoning + '）' : ''}`)
            .join('\n');
        return { success: true, data: { results, summary } };
    }
    // --- Phase 5: Audience Analysis ---
    async analyzeAudience(videos) {
        const content = videos
            .map(v => {
            const lines = [
                `タイトル: ${v.title}`,
                `チャンネル: ${v.channel}`,
                v.views !== null ? `再生数: ${v.views.toLocaleString()}回` : null,
                v.subscribers !== null ? `チャンネル登録者数: ${v.subscribers.toLocaleString()}人` : null,
                v.likes !== null ? `高評価数: ${v.likes.toLocaleString()}` : null,
                `説明文: ${v.description}`,
                v.tags && v.tags.length > 0 ? `タグ: ${v.tags.join(', ')}` : null,
            ];
            return lines.filter(Boolean).join('\n');
        })
            .join('\n---\n');
        const raw = await this.callClaude((0, prompts_1.buildAudiencePrompt)(content));
        try {
            return JSON.parse(raw);
        }
        catch (e) {
            console.error('[analyzeAudience] JSON parse failed. Raw response:', raw.slice(0, 500));
            console.error('[analyzeAudience] Parse error:', e instanceof Error ? e.message : e);
            return {
                demographics: { ageRange: '分析失敗', gender: '分析失敗', occupation: '分析失敗' },
                psychographics: { interests: ['JSON解析エラー - APIレスポンスを確認してください'], values: [], lifestyle: '' },
                painPoints: [],
                viewingMotivation: [],
                purchaseBehavior: [],
                relatedMedia: []
            };
        }
    }
    // --- Phase 6: Keyword Extraction ---
    async extractKeywords(videos) {
        const content = videos
            .map(v => {
            const lines = [
                `タイトル: ${v.title}`,
                `チャンネル: ${v.channel}`,
                v.views !== null ? `再生数: ${v.views.toLocaleString()}回` : null,
                v.subscribers !== null ? `チャンネル登録者数: ${v.subscribers.toLocaleString()}人` : null,
                `説明文: ${v.description}`,
                v.tags && v.tags.length > 0 ? `タグ: ${v.tags.join(', ')}` : null,
            ];
            return lines.filter(Boolean).join('\n');
        })
            .join('\n---\n');
        const raw = await this.callClaude((0, prompts_1.buildKeywordPrompt)(content));
        try {
            const parsed = JSON.parse(raw);
            return parsed.keywords || [];
        }
        catch (e) {
            console.error('[extractKeywords] JSON parse failed. Raw response:', raw.slice(0, 500));
            console.error('[extractKeywords] Parse error:', e instanceof Error ? e.message : e);
            return [];
        }
    }
    // --- Phase 7: Full Analysis ---
    async fullAnalysis(request) {
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
            const recsRaw = await this.callClaude((0, prompts_1.buildRecommendationsPrompt)(buzzResult.data?.commonPatterns || 'バズ分析データなし', trendResult.data?.summary || 'トレンドデータなし', JSON.stringify(audience.demographics), keywords.slice(0, 5).map(k => k.keyword).join(', ')));
            let recommendations = [];
            try {
                const parsed = JSON.parse(recsRaw);
                recommendations = parsed.recommendations || [];
            }
            catch {
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
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error';
            return { success: false, error: message };
        }
    }
    // --- Helpers ---
    async callClaude(userPrompt) {
        if (!this.client) {
            throw new Error('Anthropic APIキーが設定されていません');
        }
        const response = await this.client.messages.create({
            model: this.model,
            max_tokens: 4096,
            system: prompts_1.SYSTEM_PROMPT,
            messages: [{ role: 'user', content: userPrompt }]
        });
        const block = response.content[0];
        const raw = block.type === 'text' ? block.text : '';
        return this.extractJson(raw);
    }
    /** Strip markdown code fences and extract JSON from Claude response */
    extractJson(raw) {
        let text = raw.trim();
        // Remove ```json ... ``` or ``` ... ``` fences
        const fenceMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/);
        if (fenceMatch) {
            text = fenceMatch[1].trim();
        }
        // If still not starting with { or [, try to find JSON object/array
        if (!text.startsWith('{') && !text.startsWith('[')) {
            const jsonStart = text.search(/[\{\\[]/);
            if (jsonStart >= 0) {
                text = text.slice(jsonStart);
                // Find matching closing bracket
                const opener = text[0];
                const closer = opener === '{' ? '}' : ']';
                let depth = 0;
                for (let i = 0; i < text.length; i++) {
                    if (text[i] === opener)
                        depth++;
                    else if (text[i] === closer)
                        depth--;
                    if (depth === 0) {
                        text = text.slice(0, i + 1);
                        break;
                    }
                }
            }
        }
        return text;
    }
    verdictLabel(verdict) {
        const labels = {
            'go-now': '今すぐ出すべき！',
            'chance-but-competitive': 'チャンスだが競争激しい',
            'first-mover': '先行者優位を取れる',
            'niche-stable': 'ニッチで安定的に狙える',
            'too-late': 'タイミング遅い',
            'unknown': '判定不可'
        };
        return labels[verdict] || verdict;
    }
    buildReport(videos, buzzRanking, trendCheck, audience, keywords, recommendations, filters) {
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
            .map(r => `| ${r.topic} | ${this.trendArrow(r.googleTrends)} | ${this.trendArrow(r.youtubeSearch)} | ${this.compLabel(r.competition)} | ${this.verdictLabel(r.verdict)} |`)
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
    buzzLabel(level) {
        const labels = {
            'super-buzz': '超バズ',
            'buzz': 'バズ',
            'good': '好調',
            'average': '平均',
            'low': '低調',
            'unknown': '-'
        };
        return labels[level] || level;
    }
    trendArrow(trend) {
        const arrows = {
            'rising': '↑上昇',
            'stable': '→横ばい',
            'declining': '↓下降',
            'unknown': '?'
        };
        return arrows[trend] || trend;
    }
    compLabel(comp) {
        const labels = {
            'low': '少○',
            'medium': '普通△',
            'high': '多×',
            'unknown': '?'
        };
        return labels[comp] || comp;
    }
}
exports.YouTubeResearchService = YouTubeResearchService;
