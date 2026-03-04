"use strict";
// ===== LP Creator SS - Routes =====
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.lpCreatorRouter = void 0;
const express_1 = require("express");
const path_1 = __importDefault(require("path"));
const controller_1 = require("./controller");
const router = (0, express_1.Router)();
exports.lpCreatorRouter = router;
// Serve the main HTML page
router.get('/', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'lp-creator.html'));
});
// Admin settings page
router.get('/settings', (_req, res) => {
    res.sendFile(path_1.default.join(__dirname, '..', '..', 'public', 'lp-creator-settings.html'));
});
// API endpoints
router.post('/api/generate', controller_1.handleGenerate);
router.post('/api/generate-demo', controller_1.handleGenerateDemo);
router.get('/api/health', controller_1.handleHealth);
router.get('/api/settings', controller_1.handleGetSettings);
router.post('/api/settings', controller_1.handleSaveSettings);
