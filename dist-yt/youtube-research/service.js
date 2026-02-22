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
Object.defineProperty(exports, "__esModule", { value: true });
exports.YouTubeResearchService = void 0;
var sdk_1 = require("@anthropic-ai/sdk");
var prompts_1 = require("./prompts");
var YouTubeResearchService = /** @class */ (function () {
    function YouTubeResearchService() {
        this.model = 'claude-sonnet-4-5-20250929';
        this.client = new sdk_1.default();
    }
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
    YouTubeResearchService.prototype.checkTrend = function (keywords) {
        return __awaiter(this, void 0, void 0, function () {
            var results, _i, keywords_1, keyword, prompt_1, raw, parsed, summary;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        results = [];
                        _i = 0, keywords_1 = keywords;
                        _a.label = 1;
                    case 1:
                        if (!(_i < keywords_1.length)) return [3 /*break*/, 4];
                        keyword = keywords_1[_i];
                        prompt_1 = (0, prompts_1.buildTrendCheckPrompt)(keyword, "\u30AD\u30FC\u30EF\u30FC\u30C9\u300C".concat(keyword, "\u300D\u306B\u3064\u3044\u3066\u3001\u73FE\u5728\u306EGoogle Trends\u3001YouTube\u691C\u7D22\u30C8\u30EC\u30F3\u30C9\u3001\u7AF6\u5408\u72B6\u6CC1\u3092\u63A8\u5B9A\u3057\u3066\u304F\u3060\u3055\u3044\u3002"));
                        return [4 /*yield*/, this.callClaude(prompt_1)];
                    case 2:
                        raw = _a.sent();
                        try {
                            parsed = JSON.parse(raw);
                            results.push({
                                keyword: keyword,
                                googleTrends: parsed.googleTrends || 'unknown',
                                youtubeSearch: parsed.youtubeSearch || 'unknown',
                                competition: parsed.competition || 'unknown',
                                verdict: parsed.verdict || 'unknown'
                            });
                        }
                        catch (_b) {
                            results.push({
                                keyword: keyword,
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
                            .map(function (r) { return "".concat(r.keyword, ": ").concat(_this.verdictLabel(r.verdict)); })
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
                            .map(function (v) { return "\u30BF\u30A4\u30C8\u30EB: ".concat(v.title, "\n\u30C1\u30E3\u30F3\u30CD\u30EB: ").concat(v.channel, "\n\u8AAC\u660E: ").concat(v.description, "\n\u5185\u5BB9: ").concat(v.transcriptOrSummary.slice(0, 2000)); })
                            .join('\n---\n');
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildAudiencePrompt)(content))];
                    case 1:
                        raw = _a.sent();
                        try {
                            return [2 /*return*/, JSON.parse(raw)];
                        }
                        catch (_b) {
                            return [2 /*return*/, {
                                    demographics: { ageRange: '不明', gender: '不明', occupation: '不明' },
                                    psychographics: { interests: [], values: [], lifestyle: '不明' },
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
                            .map(function (v) { return "\u30BF\u30A4\u30C8\u30EB: ".concat(v.title, "\n\u8AAC\u660E: ").concat(v.description, "\n\u5185\u5BB9: ").concat(v.transcriptOrSummary.slice(0, 2000)); })
                            .join('\n---\n');
                        return [4 /*yield*/, this.callClaude((0, prompts_1.buildKeywordPrompt)(content))];
                    case 1:
                        raw = _a.sent();
                        try {
                            parsed = JSON.parse(raw);
                            return [2 /*return*/, parsed.keywords || []];
                        }
                        catch (_b) {
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
            var videos, buzzResult, buzzRanking, topKeywords, trendResult, _a, trendCheck, audience, keywords, recsRaw, recommendations, parsed, fullReport, err_1, message;
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
                        err_1 = _f.sent();
                        message = err_1 instanceof Error ? err_1.message : 'Unknown error';
                        return [2 /*return*/, { success: false, error: message }];
                    case 10: return [2 /*return*/];
                }
            });
        });
    };
    // --- Helpers ---
    YouTubeResearchService.prototype.callClaude = function (userPrompt) {
        return __awaiter(this, void 0, void 0, function () {
            var response, block;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.client.messages.create({
                            model: this.model,
                            max_tokens: 4096,
                            system: prompts_1.SYSTEM_PROMPT,
                            messages: [{ role: 'user', content: userPrompt }]
                        })];
                    case 1:
                        response = _a.sent();
                        block = response.content[0];
                        return [2 /*return*/, block.type === 'text' ? block.text : ''];
                }
            });
        });
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
            .map(function (r) { return "| ".concat(r.keyword, " | ").concat(_this.trendArrow(r.googleTrends), " | ").concat(_this.trendArrow(r.youtubeSearch), " | ").concat(_this.compLabel(r.competition), " | ").concat(_this.verdictLabel(r.verdict), " |"); })
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
