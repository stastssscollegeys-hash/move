"use strict";
// ===== LP NanoBanana SS - Routes =====
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.lpNanoBananaRouter = void 0;
const express_1 = require("express");
const path_1 = __importDefault(require("path"));
const controller_1 = require("./controller");
const router = (0, express_1.Router)();
exports.lpNanoBananaRouter = router;
// Serve the main HTML page
router.get('/', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'lp-nanobanana.html'));
});
// API key setup guides
router.get('/claude-api-guide', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'anthropic-api-guide.html'));
});
router.get('/gemini-api-guide', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'gemini-api-guide.html'));
});
// API endpoints
router.post('/api/generate', controller_1.handleGenerate);
router.post('/api/retry-section', controller_1.handleRetrySection);
router.post('/api/parse-input', controller_1.handleParseInput);
router.post('/api/test-keys', controller_1.handleTestKeys);
router.get('/api/health', controller_1.handleHealth);
