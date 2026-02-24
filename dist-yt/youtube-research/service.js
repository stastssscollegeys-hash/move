"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __rest = (this && this.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.YouTubeResearchService = void 0;
var sdk_1 = require("@anthropic-ai/sdk");
var prompts_1 = require("./prompts");
var YouTubeResearchService = /** @class */ (function () {
    function YouTubeResearchService(anthropicApiKey) {
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
    YouTubeResearchService.prototype.searchYouTube = function (query_1, filters_1, apiKey_1) {
        return __awaiter(this, arguments, void 0, function (query, filters, apiKey, maxResults) {
            var searchParams, regionLangMap, lang, now, dateMap, days, after, searchRes, err, searchData, videoIds, detailParams, detailRes, detailData, channelIds, channelSubs, chParams, chRes, chData, _i, _a, ch, allVideos, regionLangMap, mapping_1, filtered, result;
            if (maxResults === void 0) { maxResults = 20; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        searchParams = new URLSearchParams({
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
                            regionLangMap = {
                                JP: 'ja', US: 'en', KR: 'ko', TW: 'zh-Hant', CN: 'zh-Hans',
                                GB: 'en', DE: 'de', FR: 'fr', IN: 'hi', BR: 'pt',
                            };
                            lang = regionLangMap[filters.regionCode];
                            if (lang)
                                searchParams.set('relevanceLanguage', lang);
                        }
                        // Upload date filter
                        if (filters.uploadPeriod !== 'all') {
                            now = new Date();
                            dateMap = { week: 7, month: 30, '3months': 90, year: 365 };
                            days = dateMap[filters.uploadPeriod] || 0;
                            if (days > 0) {
                                after = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
                                searchParams.set('publishedAfter', after.toISOString());
                            }
                        }
                        return [4 /*yield*/, fetch("https://www.googleapis.com/youtube/v3/search?".concat(searchParams))];
                    case 1:
                        searchRes = _b.sent();
                        if (!!searchRes.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, searchRes.text()];
                    case 2:
                        err = _b.sent();
                        throw new Error("YouTube Search API error: ".concat(searchRes.status, " ").concat(err));
                    case 3: return [4 /*yield*/, searchRes.json()];
                    case 4:
                        searchData = _b.sent();
                        videoIds = (searchData.items || []).map(function (item) { return item.id.videoId; }).filter(Boolean);
                        if (videoIds.length === 0)
                            return [2 /*return*/, []];
                        detailParams = new URLSearchParams({
                            part: 'snippet,statistics,contentDetails',
                            id: videoIds.join(','),
                            key: apiKey,
                        });
                        return [4 /*yield*/, fetch("https://www.googleapis.com/youtube/v3/videos?".concat(detailParams))];
                    case 5:
                        detailRes = _b.sent();
                        if (!detailRes.ok)
                            throw new Error("YouTube Videos API error: ".concat(detailRes.status));
                        return [4 /*yield*/, detailRes.json()];
                    case 6:
                        detailData = _b.sent();
                        channelIds = __spreadArray([], new Set((detailData.items || []).map(function (item) { return item.snippet.channelId; })), true);
                        channelSubs = {};
                        if (!(channelIds.length > 0)) return [3 /*break*/, 9];
                        chParams = new URLSearchParams({
                            part: 'statistics',
                            id: channelIds.join(','),
                            key: apiKey,
                        });
                        return [4 /*yield*/, fetch("https://www.googleapis.com/youtube/v3/channels?".concat(chParams))];
                    case 7:
                        chRes = _b.sent();
                        if (!chRes.ok) return [3 /*break*/, 9];
                        return [4 /*yield*/, chRes.json()];
                    case 8:
                        chData = _b.sent();
                        for (_i = 0, _a = chData.items || []; _i < _a.length; _i++) {
                            ch = _a[_i];
                            channelSubs[ch.id] = parseInt(ch.statistics.subscriberCount || '0', 10);
                        }
                        _b.label = 9;
                    case 9:
                        allVideos = (detailData.items || []).map(function (item) {
                            var _a, _b, _c, _d, _e;
                            var stats = item.statistics || {};
                            var snippet = item.snippet || {};
                            return {
                                id: item.id,
                                title: snippet.title || '',
                                channel: snippet.channelTitle || '',
                                subscribers: channelSubs[snippet.channelId] || null,
                                views: parseInt(stats.viewCount || '0', 10),
                                likes: parseInt(stats.likeCount || '0', 10),
                                uploadDate: snippet.publishedAt || null,
                                duration: ((_a = item.contentDetails) === null || _a === void 0 ? void 0 : _a.duration) || null,
                                description: snippet.description || '',
                                tags: Array.isArray(snippet.tags) ? snippet.tags : [],
                                transcriptOrSummary: '',
                                url: "https://youtube.com/watch?v=".concat(item.id),
                                thumbnail: ((_c = (_b = snippet.thumbnails) === null || _b === void 0 ? void 0 : _b.medium) === null || _c === void 0 ? void 0 : _c.url) || ((_e = (_d = snippet.thumbnails) === null || _d === void 0 ? void 0 : _d.default) === null || _e === void 0 ? void 0 : _e.url) || '',
                                _lang: snippet.defaultAudioLanguage || snippet.defaultLanguage || '',
                            };
                        });
                        // Step 5: Post-filter by language if region is specified
                        if (filters.regionCode && filters.regionCode !== 'all') {
                            regionLangMap = {
                                JP: { lang: 'ja', script: /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/ },
                                KR: { lang: 'ko', script: /[\uAC00-\uD7AF\u1100-\u11FF]/ },
                                TW: { lang: 'zh', script: /[\u4E00-\u9FFF]/ },
                                CN: { lang: 'zh', script: /[\u4E00-\u9FFF]/ },
                            };
                            mapping_1 = regionLangMap[filters.regionCode];
                            if (mapping_1) {
                                filtered = allVideos.filter(function (v) {
                                    // 1. API言語フィールドが一致
                                    if (v._lang && v._lang.startsWith(mapping_1.lang))
                                        return true;
                                    // 2. 言語フィールド未設定 → タイトルの文字種で判定
                                    if (!v._lang && mapping_1.script.test(v.title))
                                        return true;
                                    return false;
                                });
                                result = filtered.length >= 3 ? filtered : allVideos;
                                return [2 /*return*/, result.map(function (_a) {
                                        var _lang = _a._lang, rest = __rest(_a, ["_lang"]);
                                        return rest;
                                    })];
                            }
                        }
                        return [2 /*return*/, allVideos.map(function (_a) {
                                var _lang = _a._lang, rest = __rest(_a, ["_lang"]);
                                return rest;
                            })];
                }
            });
        });
    };
    // Step 1: YouTube検索 + バズ比率算出（Claude不要・高速）
    YouTubeResearchService.prototype.searchWithBuzz = function (request) {
        return __awaiter(this, void 0, void 0, function () {
            var videos, buzzRanking, err_1, message;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, this.searchYouTube(request.query, request.filters, request.youtubeApiKey, request.maxResults || 20)];
                    case 1:
                        videos = _a.sent();
                        if (videos.length === 0) {
                            return [2 /*return*/, { success: false, error: '動画が見つかりませんでした。キーワードを変えてみてください。' }];
                        }
                        buzzRanking = videos.map(function (video) {
                            var buzzRatio = null;
                            var buzzLevel = 'unknown';
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
                            return { video: video, buzzRatio: buzzRatio, buzzLevel: buzzLevel };
                        });
                        buzzRanking.sort(function (a, b) {
                            if (a.buzzRatio === null)
                                return 1;
                            if (b.buzzRatio === null)
                                return -1;
                            return b.buzzRatio - a.buzzRatio;
                        });
                        return [2 /*return*/, {
                                success: true,
                                data: {
                                    query: request.query,
                                    videoCount: videos.length,
                                    videos: videos,
                                    buzzRanking: buzzRanking,
                                    audience: undefined,
                                    keywords: [],
                                    recommendations: [],
                                    fullReport: '',
                                }
                            }];
                    case 2:
                        err_1 = _a.sent();
                        message = err_1 instanceof Error ? err_1.message : 'Unknown error';
                        return [2 /*return*/, { success: false, error: message }];
                    case 3: return [2 /*return*/];
                }
            });
        });
    };
    // Step 2: 選択した動画に対してターゲット＆キーワード＆レポート生成（Claude使用）
    YouTubeResearchService.prototype.analyzeSelected = function (videos) {
        return __awaiter(this, void 0, void 0, function () {
            var audience, keywords, recsRaw, recommendations, parsed, fullReport, err_2, message;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 4, , 5]);
                        if (!this.client) {
                            return [2 /*return*/, { success: false, error: 'Anthropic APIキーが設定されていません' }];
                        }
                        return [4 /*yield*/, this.analyzeAudience(videos)];
                    case 1:
                        audience = _a.sent();
                        return [4 /*yield*/, this.extractKeywords(videos)];
                    case 2:
                        keywords = _a.sent();
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildRecommendationsPrompt)('バズ動画の共通パターン分析', '', JSON.stringify(audience.demographics), keywords.slice(0, 5).map(function (k) { return k.keyword; }).join(', ')))];
                    case 3:
                        recsRaw = _a.sent();
                        recommendations = [];
                        try {
                            parsed = JSON.parse(recsRaw);
                            recommendations = parsed.recommendations || [];
                        }
                        catch (e) {
                            console.error('[analyzeSelected] Recommendations JSON parse failed:', recsRaw.slice(0, 300));
                            recommendations = ['分析データを元にコンテンツ企画を検討してください'];
                        }
                        fullReport = this.buildReport(videos, [], [], audience, keywords, recommendations, { lengthCategory: 'all', uploadPeriod: 'all' });
                        return [2 /*return*/, { success: true, data: { audience: audience, keywords: keywords, recommendations: recommendations, fullReport: fullReport } }];
                    case 4:
                        err_2 = _a.sent();
                        message = err_2 instanceof Error ? err_2.message : 'Unknown error';
                        console.error('[analyzeSelected] Error:', message);
                        return [2 /*return*/, { success: false, error: message }];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    // --- Phase 2: Metadata ---
    YouTubeResearchService.prototype.fetchVideoMetadata = function (inputs) {
        return __awaiter(this, void 0, void 0, function () {
            var _this = this;
            return __generator(this, function (_a) {
                return [2 /*return*/, inputs.map(function (input, i) {
                        var isUrl = input.inputType === 'url' || input.rawText.match(/youtube\.com|youtu\.be/);
                        return {
                            id: "video_".concat(String(i + 1).padStart(3, '0')),
                            title: isUrl ? _this.extractFromText(input.rawText, 'title') : "\u52D5\u753B ".concat(i + 1),
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
                    })];
            });
        });
    };
    YouTubeResearchService.prototype.extractFromText = function (text, _field) {
        // URL from text
        var urlMatch = text.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
        return urlMatch ? "YouTube Video (".concat(urlMatch[1], ")") : 'Unknown';
    };
    // --- Phase 3: Buzz Detection ---
    YouTubeResearchService.prototype.detectBuzz = function (videos) {
        return __awaiter(this, void 0, void 0, function () {
            var ranking, buzzVideos, commonPatterns, videoData;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        ranking = videos.map(function (video) {
                            var buzzRatio = null;
                            var buzzLevel = 'unknown';
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
                            return { video: video, buzzRatio: buzzRatio, buzzLevel: buzzLevel };
                        });
                        // Sort by buzz ratio descending (unknowns at end)
                        ranking.sort(function (a, b) {
                            if (a.buzzRatio === null)
                                return 1;
                            if (b.buzzRatio === null)
                                return -1;
                            return b.buzzRatio - a.buzzRatio;
                        });
                        buzzVideos = ranking.filter(function (r) { return r.buzzLevel === 'super-buzz' || r.buzzLevel === 'buzz' || r.buzzLevel === 'good'; });
                        commonPatterns = '';
                        if (!(buzzVideos.length > 0)) return [3 /*break*/, 2];
                        videoData = buzzVideos.map(function (r) { return ({
                            title: r.video.title,
                            description: r.video.description || r.video.transcriptOrSummary.slice(0, 500),
                            channel: r.video.channel
                        }); });
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildBuzzAnalysisPrompt)(videoData))];
                    case 1:
                        commonPatterns = _a.sent();
                        _a.label = 2;
                    case 2: return [2 /*return*/, { success: true, data: { ranking: ranking, commonPatterns: commonPatterns } }];
                }
            });
        });
    };
    // --- Phase 4: Trend Check ---
    YouTubeResearchService.prototype.checkTrend = function (titles) {
        return __awaiter(this, void 0, void 0, function () {
            var results, _i, titles_1, title, prompt_1, raw, parsed, summary;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        results = [];
                        _i = 0, titles_1 = titles;
                        _a.label = 1;
                    case 1:
                        if (!(_i < titles_1.length)) return [3 /*break*/, 4];
                        title = titles_1[_i];
                        prompt_1 = (0, prompts_1.buildTrendCheckPrompt)(title);
                        return [4 /*yield*/, this.callClaude(prompt_1)];
                    case 2:
                        raw = _a.sent();
                        try {
                            parsed = JSON.parse(raw);
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
                        catch (_b) {
                            results.push({
                                originalTitle: title,
                                topic: title,
                                googleTrends: 'unknown',
                                youtubeSearch: 'unknown',
                                competition: 'unknown',
                                verdict: 'unknown'
                            });
                        }
                        _a.label = 3;
                    case 3:
                        _i++;
                        return [3 /*break*/, 1];
                    case 4:
                        summary = results
                            .map(function (r) { return "".concat(r.topic, ": ").concat(_this.verdictLabel(r.verdict)).concat(r.reasoning ? '（' + r.reasoning + '）' : ''); })
                            .join('\n');
                        return [2 /*return*/, { success: true, data: { results: results, summary: summary } }];
                }
            });
        });
    };
    // --- Phase 5: Audience Analysis ---
    YouTubeResearchService.prototype.analyzeAudience = function (videos) {
        return __awaiter(this, void 0, void 0, function () {
            var content, raw;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        content = videos
                            .map(function (v) {
                            var lines = [
                                "\u30BF\u30A4\u30C8\u30EB: ".concat(v.title),
                                "\u30C1\u30E3\u30F3\u30CD\u30EB: ".concat(v.channel),
                                v.views !== null ? "\u518D\u751F\u6570: ".concat(v.views.toLocaleString(), "\u56DE") : null,
                                v.subscribers !== null ? "\u30C1\u30E3\u30F3\u30CD\u30EB\u767B\u9332\u8005\u6570: ".concat(v.subscribers.toLocaleString(), "\u4EBA") : null,
                                v.likes !== null ? "\u9AD8\u8A55\u4FA1\u6570: ".concat(v.likes.toLocaleString()) : null,
                                "\u8AAC\u660E\u6587: ".concat(v.description),
                                v.tags && v.tags.length > 0 ? "\u30BF\u30B0: ".concat(v.tags.join(', ')) : null,
                            ];
                            return lines.filter(Boolean).join('\n');
                        })
                            .join('\n---\n');
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildAudiencePrompt)(content))];
                    case 1:
                        raw = _a.sent();
                        try {
                            return [2 /*return*/, JSON.parse(raw)];
                        }
                        catch (e) {
                            console.error('[analyzeAudience] JSON parse failed. Raw response:', raw.slice(0, 500));
                            console.error('[analyzeAudience] Parse error:', e instanceof Error ? e.message : e);
                            return [2 /*return*/, {
                                    demographics: { ageRange: '分析失敗', gender: '分析失敗', occupation: '分析失敗' },
                                    psychographics: { interests: ['JSON解析エラー - APIレスポンスを確認してください'], values: [], lifestyle: '' },
                                    painPoints: [],
                                    viewingMotivation: [],
                                    purchaseBehavior: [],
                                    relatedMedia: []
                                }];
                        }
                        return [2 /*return*/];
                }
            });
        });
    };
    // --- Phase 6: Keyword Extraction ---
    YouTubeResearchService.prototype.extractKeywords = function (videos) {
        return __awaiter(this, void 0, void 0, function () {
            var content, raw, parsed;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        content = videos
                            .map(function (v) {
                            var lines = [
                                "\u30BF\u30A4\u30C8\u30EB: ".concat(v.title),
                                "\u30C1\u30E3\u30F3\u30CD\u30EB: ".concat(v.channel),
                                v.views !== null ? "\u518D\u751F\u6570: ".concat(v.views.toLocaleString(), "\u56DE") : null,
                                v.subscribers !== null ? "\u30C1\u30E3\u30F3\u30CD\u30EB\u767B\u9332\u8005\u6570: ".concat(v.subscribers.toLocaleString(), "\u4EBA") : null,
                                "\u8AAC\u660E\u6587: ".concat(v.description),
                                v.tags && v.tags.length > 0 ? "\u30BF\u30B0: ".concat(v.tags.join(', ')) : null,
                            ];
                            return lines.filter(Boolean).join('\n');
                        })
                            .join('\n---\n');
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildKeywordPrompt)(content))];
                    case 1:
                        raw = _a.sent();
                        try {
                            parsed = JSON.parse(raw);
                            return [2 /*return*/, parsed.keywords || []];
                        }
                        catch (e) {
                            console.error('[extractKeywords] JSON parse failed. Raw response:', raw.slice(0, 500));
                            console.error('[extractKeywords] Parse error:', e instanceof Error ? e.message : e);
                            return [2 /*return*/, []];
                        }
                        return [2 /*return*/];
                }
            });
        });
    };
    // --- Phase 7: Full Analysis ---
    YouTubeResearchService.prototype.fullAnalysis = function (request) {
        return __awaiter(this, void 0, void 0, function () {
            var videos, buzzResult, buzzRanking, topKeywords, trendResult, _a, trendCheck, audience, keywords, recsRaw, recommendations, parsed, fullReport, err_3, message;
            var _b, _c, _d, _e;
            return __generator(this, function (_f) {
                switch (_f.label) {
                    case 0:
                        _f.trys.push([0, 9, , 10]);
                        return [4 /*yield*/, this.fetchVideoMetadata(request.videos)];
                    case 1:
                        videos = _f.sent();
                        return [4 /*yield*/, this.detectBuzz(videos)];
                    case 2:
                        buzzResult = _f.sent();
                        buzzRanking = ((_b = buzzResult.data) === null || _b === void 0 ? void 0 : _b.ranking) || [];
                        topKeywords = videos
                            .slice(0, 5)
                            .map(function (v) { return v.title; })
                            .filter(function (t) { return t && t !== 'Unknown'; });
                        if (!(topKeywords.length > 0)) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.checkTrend(topKeywords.slice(0, 3))];
                    case 3:
                        _a = _f.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        _a = { success: true, data: { results: [], summary: '' } };
                        _f.label = 5;
                    case 5:
                        trendResult = _a;
                        trendCheck = ((_c = trendResult.data) === null || _c === void 0 ? void 0 : _c.results) || [];
                        return [4 /*yield*/, this.analyzeAudience(videos)];
                    case 6:
                        audience = _f.sent();
                        return [4 /*yield*/, this.extractKeywords(videos)];
                    case 7:
                        keywords = _f.sent();
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildRecommendationsPrompt)(((_d = buzzResult.data) === null || _d === void 0 ? void 0 : _d.commonPatterns) || 'バズ分析データなし', ((_e = trendResult.data) === null || _e === void 0 ? void 0 : _e.summary) || 'トレンドデータなし', JSON.stringify(audience.demographics), keywords.slice(0, 5).map(function (k) { return k.keyword; }).join(', ')))];
                    case 8:
                        recsRaw = _f.sent();
                        recommendations = [];
                        try {
                            parsed = JSON.parse(recsRaw);
                            recommendations = parsed.recommendations || [];
                        }
                        catch (_g) {
                            recommendations = ['分析データを元に動画企画を検討してください'];
                        }
                        fullReport = this.buildReport(videos, buzzRanking, trendCheck, audience, keywords, recommendations, request.filters);
                        return [2 /*return*/, {
                                success: true,
                                data: {
                                    videoCount: videos.length,
                                    videos: videos,
                                    buzzRanking: buzzRanking,
                                    trendCheck: trendCheck,
                                    audience: audience,
                                    keywords: keywords,
                                    recommendations: recommendations,
                                    fullReport: fullReport
                                }
                            }];
                    case 9:
                        err_3 = _f.sent();
                        message = err_3 instanceof Error ? err_3.message : 'Unknown error';
                        return [2 /*return*/, { success: false, error: message }];
                    case 10: return [2 /*return*/];
                }
            });
        });
    };
    // --- Helpers ---
    YouTubeResearchService.prototype.callClaude = function (userPrompt) {
        return __awaiter(this, void 0, void 0, function () {
            var response, block, raw;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.client) {
                            throw new Error('Anthropic APIキーが設定されていません');
                        }
                        return [4 /*yield*/, this.client.messages.create({
                                model: this.model,
                                max_tokens: 4096,
                                system: prompts_1.SYSTEM_PROMPT,
                                messages: [{ role: 'user', content: userPrompt }]
                            })];
                    case 1:
                        response = _a.sent();
                        block = response.content[0];
                        raw = block.type === 'text' ? block.text : '';
                        return [2 /*return*/, this.extractJson(raw)];
                }
            });
        });
    };
    /** Strip markdown code fences and extract JSON from Claude response */
    YouTubeResearchService.prototype.extractJson = function (raw) {
        var text = raw.trim();
        // Remove ```json ... ``` or ``` ... ``` fences
        var fenceMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/);
        if (fenceMatch) {
            text = fenceMatch[1].trim();
        }
        // If still not starting with { or [, try to find JSON object/array
        if (!text.startsWith('{') && !text.startsWith('[')) {
            var jsonStart = text.search(/[\{\\[]/);
            if (jsonStart >= 0) {
                text = text.slice(jsonStart);
                // Find matching closing bracket
                var opener_1 = text[0];
                var closer = opener_1 === '{' ? '}' : ']';
                var depth = 0;
                for (var i = 0; i < text.length; i++) {
                    if (text[i] === opener_1)
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
    };
    YouTubeResearchService.prototype.verdictLabel = function (verdict) {
        var labels = {
            'go-now': '今すぐ出すべき！',
            'chance-but-competitive': 'チャンスだが競争激しい',
            'first-mover': '先行者優位を取れる',
            'niche-stable': 'ニッチで安定的に狙える',
            'too-late': 'タイミング遅い',
            'unknown': '判定不可'
        };
        return labels[verdict] || verdict;
    };
    YouTubeResearchService.prototype.buildReport = function (videos, buzzRanking, trendCheck, audience, keywords, recommendations, filters) {
        var _this = this;
        var date = new Date().toISOString().split('T')[0];
        var filterStr = [
            filters.keyword && "\u30AD\u30FC\u30EF\u30FC\u30C9: ".concat(filters.keyword),
            filters.genre && "\u30B8\u30E3\u30F3\u30EB: ".concat(filters.genre),
            "\u52D5\u753B\u9577: ".concat(filters.lengthCategory),
            "\u671F\u9593: ".concat(filters.uploadPeriod)
        ].filter(Boolean).join(' / ');
        var buzzTable = buzzRanking
            .map(function (r, i) { var _a, _b, _c, _d; return "| ".concat(i + 1, " | ").concat(r.video.title, " | ").concat(r.video.channel || '-', " | ").concat((_a = r.video.views) !== null && _a !== void 0 ? _a : '-', " | ").concat((_b = r.video.subscribers) !== null && _b !== void 0 ? _b : '-', " | ").concat((_d = (_c = r.buzzRatio) === null || _c === void 0 ? void 0 : _c.toFixed(1)) !== null && _d !== void 0 ? _d : '-', " | ").concat(_this.buzzLabel(r.buzzLevel), " |"); })
            .join('\n');
        var trendTable = trendCheck
            .map(function (r) { return "| ".concat(r.topic, " | ").concat(_this.trendArrow(r.googleTrends), " | ").concat(_this.trendArrow(r.youtubeSearch), " | ").concat(_this.compLabel(r.competition), " | ").concat(_this.verdictLabel(r.verdict), " |"); })
            .join('\n');
        var kwTable = keywords
            .slice(0, 20)
            .map(function (k) { return "| ".concat(k.keyword, " | ").concat(k.category, " | ").concat(k.estimatedVolume, " | ").concat(k.competition, " | ").concat(k.suggestedUse.join(', '), " |"); })
            .join('\n');
        var recsStr = recommendations.map(function (r, i) { return "".concat(i + 1, ". ").concat(r); }).join('\n');
        return "# YouTube\u52D5\u753B\u30EA\u30B5\u30FC\u30C1\u30EC\u30DD\u30FC\u30C8\n\n## \u5206\u6790\u6982\u8981\n- \u5206\u6790\u65E5: ".concat(date, "\n- \u5BFE\u8C61\u52D5\u753B\u6570: ").concat(videos.length, "\n- \u30D5\u30A3\u30EB\u30BF\u30FC\u6761\u4EF6: ").concat(filterStr, "\n\n## \u30D0\u30BA\u52D5\u753B\u30E9\u30F3\u30AD\u30F3\u30B0\n| \u9806\u4F4D | \u30BF\u30A4\u30C8\u30EB | \u30C1\u30E3\u30F3\u30CD\u30EB | \u518D\u751F\u6570 | \u767B\u9332\u8005\u6570 | \u30D0\u30BA\u6BD4\u7387 | \u5224\u5B9A |\n|------|---------|-----------|--------|---------|---------|------|\n").concat(buzzTable, "\n\n## \u30C8\u30EC\u30F3\u30C9\u5224\u5B9A\n| \u30AD\u30FC\u30EF\u30FC\u30C9 | Google Trends | YouTube\u691C\u7D22 | \u7AF6\u5408\u5EA6 | \u7DCF\u5408\u5224\u5B9A |\n|-----------|-------------|------------|--------|---------|\n").concat(trendTable, "\n\n## \u30BF\u30FC\u30B2\u30C3\u30C8\u30AA\u30FC\u30C7\u30A3\u30A8\u30F3\u30B9\n### \u30C7\u30E2\u30B0\u30E9\u30D5\u30A3\u30C3\u30AF\n- \u5E74\u9F62\u5C64: ").concat(audience.demographics.ageRange, "\n- \u6027\u5225: ").concat(audience.demographics.gender, "\n- \u8077\u696D: ").concat(audience.demographics.occupation, "\n\n### \u8208\u5473\u95A2\u5FC3\n").concat(audience.psychographics.interests.map(function (i) { return "- ".concat(i); }).join('\n'), "\n\n### \u8AB2\u984C\u30FB\u60A9\u307F\n").concat(audience.painPoints.map(function (p) { return "- ".concat(p); }).join('\n'), "\n\n### \u8996\u8074\u52D5\u6A5F\n").concat(audience.viewingMotivation.map(function (m) { return "- ".concat(m); }).join('\n'), "\n\n## \u30AD\u30FC\u30EF\u30FC\u30C9\u5206\u6790\n| \u30AD\u30FC\u30EF\u30FC\u30C9 | \u30AB\u30C6\u30B4\u30EA | \u30DC\u30EA\u30E5\u30FC\u30E0 | \u7AF6\u5408\u5EA6 | \u7528\u9014 |\n|-----------|---------|-----------|--------|------|\n").concat(kwTable, "\n\n## \u63A8\u5968\u30A2\u30AF\u30B7\u30E7\u30F3\n").concat(recsStr, "\n");
    };
    YouTubeResearchService.prototype.buzzLabel = function (level) {
        var labels = {
            'super-buzz': '超バズ',
            'buzz': 'バズ',
            'good': '好調',
            'average': '平均',
            'low': '低調',
            'unknown': '-'
        };
        return labels[level] || level;
    };
    YouTubeResearchService.prototype.trendArrow = function (trend) {
        var arrows = {
            'rising': '↑上昇',
            'stable': '→横ばい',
            'declining': '↓下降',
            'unknown': '?'
        };
        return arrows[trend] || trend;
    };
    YouTubeResearchService.prototype.compLabel = function (comp) {
        var labels = {
            'low': '少○',
            'medium': '普通△',
            'high': '多×',
            'unknown': '?'
        };
        return labels[comp] || comp;
    };
    return YouTubeResearchService;
}());
exports.YouTubeResearchService = YouTubeResearchService;
