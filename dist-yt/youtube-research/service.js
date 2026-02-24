"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.YouTubeResearchService = exports.calculateBuzzForVideo = exports.scoreGenreRelevance = void 0;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const prompts_1 = require("./prompts");
// Region to language mapping (shared across methods)
const REGION_LANG_MAP = {
    JP: 'ja', US: 'en', KR: 'ko', TW: 'zh-Hant', CN: 'zh-Hans',
    GB: 'en', DE: 'de', FR: 'fr', IN: 'hi', BR: 'pt',
};
// Region to script regex mapping (for post-filtering)
const REGION_SCRIPT_MAP = {
    JP: /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/,
    KR: /[\uAC00-\uD7AF\u1100-\u11FF]/,
    TW: /[\u4E00-\u9FFF]/,
    CN: /[\u4E00-\u9FFF]/,
};
// Genre keyword mapping for post-filtering (backend verification)
const GENRE_KEYWORDS = {
    education: ['教育', '学習', '勉強', '講座', '解説', '授業', 'スキルアップ', '資格', '学ぶ', '教える'],
    tech: ['テクノロジー', 'テック', 'プログラミング', 'AI', 'エンジニア', 'IT', '開発', 'ChatGPT', 'アプリ', 'コード', 'Python', 'JavaScript', 'プログラム'],
    business: ['ビジネス', '副業', '起業', '稼ぐ', 'マーケティング', 'フリーランス', '収益化', '投資', 'ノウハウ', 'コンサル', '物販', 'せどり', 'アフィリエイト', 'ネットビジネス', '経営', '営業', '転売'],
    lifestyle: ['ライフスタイル', '暮らし', 'ルーティン', '日常', 'Vlog', '生活', 'ミニマリスト', '丁寧な暮らし', 'モーニングルーティン', 'ナイトルーティン', '部屋'],
    entertainment: ['エンタメ', 'バラエティ', '面白い', 'やってみた', '検証', 'ドッキリ', 'チャレンジ', 'コント', '大食い', '爆笑', 'ネタ'],
    cooking: ['料理', 'レシピ', 'グルメ', '食べ', '作り方', 'クッキング', '簡単レシピ', '食レポ', 'お弁当', 'スイーツ', '手作り', '献立'],
    beauty: ['美容', 'コスメ', 'メイク', 'スキンケア', 'ヘアアレンジ', '垢抜け', '整形', 'ダイエット美容', 'プチプラ', 'ビューティー'],
    fitness: ['筋トレ', 'ダイエット', 'フィットネス', 'ワークアウト', 'エクササイズ', 'ストレッチ', 'ヨガ', '痩せる', 'ボディメイク', '宅トレ', 'トレーニング'],
    gaming: ['ゲーム', 'ゲーム実況', 'プレイ', '攻略', '配信', 'eスポーツ', 'マイクラ', 'フォートナイト', '原神', 'スプラ', 'ゲーミング', '実況'],
    music: ['音楽', '歌ってみた', 'MV', '弾いてみた', 'カバー', '作曲', 'ピアノ', 'ギター', 'DTM', 'オリジナル曲', '歌', '演奏'],
    travel: ['旅行', '旅', '観光', 'キャンプ', 'アウトドア', '絶景', '一人旅', '海外旅行', '温泉', '車中泊', 'バンライフ', '旅vlog'],
    pets: ['ペット', '犬', '猫', '動物', 'かわいい', '子犬', '子猫', '保護猫', '多頭飼い', '爬虫類', 'わんこ', 'にゃんこ'],
    parenting: ['子育て', '育児', 'ママ', 'パパ', '赤ちゃん', '知育', '離乳食', '幼児教育', '小学生', '受験', '出産', '妊娠'],
    spiritual: ['スピリチュアル', '引き寄せ', '潜在意識', '宇宙', '波動', '目覚め', '覚醒', 'ハイヤーセルフ', 'アセンション', 'ツインレイ'],
    fortune: ['占い', 'タロット', '星座', '数秘術', '四柱推命', '手相', '星読み', '運勢', '誕生日占い', 'オラクルカード', '鑑定'],
    healing: ['ヒーリング', '瞑想', '周波数', '睡眠', 'リラックス', 'ソルフェジオ', 'ASMR', '自然音', '528Hz', 'マインドフルネス'],
    mental: ['メンタルヘルス', 'HSP', '自己肯定感', 'うつ', '不安', '心理学', 'カウンセリング', 'アダルトチルドレン', '生きづらさ', '自分を変える', 'メンタル'],
};
/**
 * Score genre relevance for a video by checking title + description + tags.
 * Returns a score from 0 to 1.
 */
function scoreGenreRelevance(video, genre) {
    const keywords = GENRE_KEYWORDS[genre];
    if (!keywords)
        return 1; // Unknown genre = don't filter
    const titleLower = video.title.toLowerCase();
    const descLower = (video.description || '').toLowerCase();
    const tagsLower = (video.tags || []).map(t => t.toLowerCase());
    const allTags = tagsLower.join(' ');
    let score = 0;
    let titleHits = 0;
    let descHits = 0;
    let tagHits = 0;
    for (const kw of keywords) {
        const kwLower = kw.toLowerCase();
        if (titleLower.includes(kwLower))
            titleHits++;
        if (descLower.includes(kwLower))
            descHits++;
        if (allTags.includes(kwLower))
            tagHits++;
    }
    // Title match is most important (weight: 0.5), tags (0.3), description (0.2)
    const titleScore = Math.min(titleHits / 2, 1); // 2+ title hits = max
    const tagScore = Math.min(tagHits / 2, 1);
    const descScore = Math.min(descHits / 3, 1); // 3+ desc hits = max
    score = titleScore * 0.5 + tagScore * 0.3 + descScore * 0.2;
    return score;
}
exports.scoreGenreRelevance = scoreGenreRelevance;
/**
 * Calculate buzz ratio and level for a single video.
 * Centralized logic used by both searchWithBuzz() and detectBuzz().
 */
function calculateBuzzForVideo(video) {
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
}
exports.calculateBuzzForVideo = calculateBuzzForVideo;
/** Sort buzz results descending (unknowns at end) */
function sortBuzzRanking(ranking) {
    return ranking.sort((a, b) => {
        if (a.buzzRatio === null)
            return 1;
        if (b.buzzRatio === null)
            return -1;
        return b.buzzRatio - a.buzzRatio;
    });
}
class YouTubeResearchService {
    constructor(anthropicApiKey) {
        this.client = null;
        this.model = process.env.CLAUDE_MODEL || 'claude-sonnet-4-5-20250929';
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
            const lang = REGION_LANG_MAP[filters.regionCode];
            if (lang)
                searchParams.set('relevanceLanguage', lang);
        }
        // Upload date filter
        if (filters.uploadPeriod !== 'all') {
            const now = new Date();
            const dateMap = { week: 7, '2weeks': 14, month: 30, '3months': 90, '6months': 180, year: 365 };
            const days = dateMap[filters.uploadPeriod] || 0;
            if (days > 0) {
                const after = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
                searchParams.set('publishedAfter', after.toISOString());
            }
        }
        const searchRes = await fetch(`https://www.googleapis.com/youtube/v3/search?${searchParams}`);
        if (!searchRes.ok) {
            console.error(`[searchYouTube] YouTube Search API error: ${searchRes.status}`);
            if (searchRes.status === 403) {
                throw new Error('YouTube APIキーのクォータが上限に達したか、キーが無効です');
            }
            else if (searchRes.status === 400) {
                throw new Error('YouTube API リクエストが不正です。検索条件を確認してください');
            }
            throw new Error(`YouTube APIエラーが発生しました（ステータス: ${searchRes.status}）`);
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
        if (!detailRes.ok) {
            console.error(`[searchYouTube] YouTube Videos API error: ${detailRes.status}`);
            throw new Error(`YouTube APIエラーが発生しました（ステータス: ${detailRes.status}）`);
        }
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
            const script = REGION_SCRIPT_MAP[filters.regionCode];
            if (script) {
                // Strict filter: title OR description must contain regional script characters
                const filtered = rawVideos.filter((v) => script.test(v.title) || script.test(v.description || ''));
                if (filtered.length > 0) {
                    console.log(`[searchYouTube] Region filter "${filters.regionCode}": ${rawVideos.length} → ${filtered.length} videos`);
                    return filtered.map(({ _lang, ...rest }) => rest);
                }
                // Fallback: check _lang metadata from YouTube API
                const langFiltered = rawVideos.filter((v) => {
                    if (!v._lang)
                        return false;
                    const regionLang = REGION_LANG_MAP[filters.regionCode];
                    return regionLang && v._lang.startsWith(regionLang);
                });
                if (langFiltered.length > 0) {
                    console.log(`[searchYouTube] Region filter "${filters.regionCode}" (lang fallback): ${rawVideos.length} → ${langFiltered.length} videos`);
                    return langFiltered.map(({ _lang, ...rest }) => rest);
                }
                // Last resort: return all but log warning
                console.warn(`[searchYouTube] Region filter "${filters.regionCode}": no matches found, returning all ${rawVideos.length} videos`);
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
            // Genre post-filter: score and filter results by genre relevance
            let filteredVideos = videos;
            const genre = request.filters?.genre;
            if (genre && GENRE_KEYWORDS[genre]) {
                const scored = videos.map(v => ({
                    video: v,
                    genreScore: scoreGenreRelevance(v, genre),
                }));
                // Keep videos with score > 0 (at least 1 keyword match somewhere)
                const relevant = scored.filter(s => s.genreScore > 0);
                if (relevant.length > 0) {
                    // Sort by genre relevance (highest first), then use those videos
                    relevant.sort((a, b) => b.genreScore - a.genreScore);
                    filteredVideos = relevant.map(s => s.video);
                    console.log(`[searchWithBuzz] Genre filter "${genre}": ${videos.length} → ${filteredVideos.length} videos`);
                }
                else {
                    // No relevant videos found - return all with a note
                    console.log(`[searchWithBuzz] Genre filter "${genre}": no matches, returning all ${videos.length} videos`);
                }
            }
            const buzzRanking = sortBuzzRanking(filteredVideos.map(calculateBuzzForVideo));
            return {
                success: true,
                data: {
                    query: request.query,
                    videoCount: filteredVideos.length,
                    videos: filteredVideos,
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
            // Audience and Keywords are independent - run in parallel
            const [audience, keywords] = await Promise.all([
                this.analyzeAudience(videos),
                this.extractKeywords(videos),
            ]);
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
    // 未実装：現UIでは未使用。YouTube Data API検索（searchYouTube）を使用するため、
    // このメソッドはURL/テキスト入力ベースの旧フローの残存コード。
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
        const ranking = sortBuzzRanking(videos.map(calculateBuzzForVideo));
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
            const trendPromise = topKeywords.length > 0
                ? this.checkTrend(topKeywords.slice(0, 3))
                : Promise.resolve({ success: true, data: { results: [], summary: '' } });
            // Phase 5 & 6 are independent of Phase 4 - run in parallel
            const [trendResult, audience, keywords] = await Promise.all([
                trendPromise,
                this.analyzeAudience(videos),
                this.extractKeywords(videos),
            ]);
            const trendCheck = trendResult.data?.results || [];
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
            const jsonStart = text.search(/[{\[]/);
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
