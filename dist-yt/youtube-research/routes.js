"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.youtubeResearchRouter = void 0;
var express_1 = require("express");
var path_1 = require("path");
var controller_1 = require("./controller");
var router = (0, express_1.Router)();
exports.youtubeResearchRouter = router;
// Serve the main HTML page
router.get('/', function (_req, res) {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'youtube-research.html'));
});
// API endpoints
router.post('/api/search', controller_1.handleSearch); // 検索+バズ（高速）
router.post('/api/analyze-selected', controller_1.handleAnalyzeSelected); // ターゲット+キーワード
router.post('/api/trend', controller_1.handleTrend); // トレンド判定
// API Key Guide page
router.get('/api-key-guide', function (_req, res) {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'youtube-research-api-guide.html'));
});
// Health check
router.get('/api/health', function (_req, res) {
    res.json({ status: 'OK', service: 'youtube-research' });
});
