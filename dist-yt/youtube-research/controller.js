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
exports.handleTrend = exports.handleAnalyzeSelected = exports.handleSearch = void 0;
var service_1 = require("./service");
// Step 1: YouTube検索 + バズ比率（高速・Claude不要）
function handleSearch(req, res) {
    return __awaiter(this, void 0, void 0, function () {
        var body, service, result, err_1, message;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    body = req.body;
                    if (!body.query || !body.query.trim()) {
                        res.status(400).json({ success: false, error: '検索キーワードを入力してください' });
                        return [2 /*return*/];
                    }
                    if (!body.youtubeApiKey) {
                        res.status(400).json({ success: false, error: 'YouTube APIキーを入力してください' });
                        return [2 /*return*/];
                    }
                    service = new service_1.YouTubeResearchService();
                    return [4 /*yield*/, service.searchWithBuzz({
                            query: body.query.trim(),
                            filters: body.filters || { lengthCategory: 'all', uploadPeriod: 'all' },
                            maxResults: body.maxResults || 20,
                            youtubeApiKey: body.youtubeApiKey,
                            anthropicApiKey: body.anthropicApiKey,
                        })];
                case 1:
                    result = _a.sent();
                    res.json(result);
                    return [3 /*break*/, 3];
                case 2:
                    err_1 = _a.sent();
                    message = err_1 instanceof Error ? err_1.message : 'Internal server error';
                    res.status(500).json({ success: false, error: message });
                    return [3 /*break*/, 3];
                case 3: return [2 /*return*/];
            }
        });
    });
}
exports.handleSearch = handleSearch;
// Step 2: 選択した動画でターゲット＆キーワード分析（Claude使用）
function handleAnalyzeSelected(req, res) {
    return __awaiter(this, void 0, void 0, function () {
        var body, service, result, err_2, message;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    body = req.body;
                    if (!body.videos || body.videos.length === 0) {
                        res.status(400).json({ success: false, error: '分析する動画を選択してください' });
                        return [2 /*return*/];
                    }
                    if (!body.anthropicApiKey) {
                        res.status(400).json({ success: false, error: 'Anthropic APIキーを入力してください' });
                        return [2 /*return*/];
                    }
                    service = new service_1.YouTubeResearchService(body.anthropicApiKey);
                    return [4 /*yield*/, service.analyzeSelected(body.videos)];
                case 1:
                    result = _a.sent();
                    res.json(result);
                    return [3 /*break*/, 3];
                case 2:
                    err_2 = _a.sent();
                    message = err_2 instanceof Error ? err_2.message : 'Internal server error';
                    res.status(500).json({ success: false, error: message });
                    return [3 /*break*/, 3];
                case 3: return [2 /*return*/];
            }
        });
    });
}
exports.handleAnalyzeSelected = handleAnalyzeSelected;
// Step 3: トレンド判定（Claude使用）
function handleTrend(req, res) {
    return __awaiter(this, void 0, void 0, function () {
        var body, service, result, err_3, message;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    body = req.body;
                    if (!body.titles || body.titles.length === 0) {
                        res.status(400).json({ success: false, error: '動画タイトルが必要です' });
                        return [2 /*return*/];
                    }
                    service = new service_1.YouTubeResearchService(body.anthropicApiKey);
                    return [4 /*yield*/, service.checkTrend(body.titles.slice(0, 10))];
                case 1:
                    result = _a.sent();
                    res.json(result);
                    return [3 /*break*/, 3];
                case 2:
                    err_3 = _a.sent();
                    message = err_3 instanceof Error ? err_3.message : 'Internal server error';
                    res.status(500).json({ success: false, error: message });
                    return [3 /*break*/, 3];
                case 3: return [2 /*return*/];
            }
        });
    });
}
exports.handleTrend = handleTrend;
