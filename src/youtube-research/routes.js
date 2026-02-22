"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.youtubeResearchRouter = void 0;
const express_1 = require("express");
const path_1 = __importDefault(require("path"));
const controller_1 = require("./controller");
const router = (0, express_1.Router)();
exports.youtubeResearchRouter = router;
// Serve the main HTML page
router.get('/', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'youtube-research.html'));
});
// API endpoints
router.post('/api/search', controller_1.handleSearch); // 検索+バズ（高速）
router.post('/api/analyze-selected', controller_1.handleAnalyzeSelected); // ターゲット+キーワード
router.post('/api/trend', controller_1.handleTrend); // トレンド判定
// API Key Guide page
router.get('/api-key-guide', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'youtube-research-api-guide.html'));
});
// Health check
router.get('/api/health', (_req, res) => {
    res.json({ status: 'OK', service: 'youtube-research' });
});
