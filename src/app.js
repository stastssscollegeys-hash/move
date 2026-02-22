"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const path_1 = __importDefault(require("path"));
const routes_1 = require("./youtube-research/routes");
const app = (0, express_1.default)();
// Middleware
app.use(express_1.default.json({ limit: '10mb' }));
app.use(express_1.default.static(path_1.default.join(__dirname, '..', 'public')));
// Existing health check
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'OK' });
});
// YouTube Research Tool
app.use('/youtube-research', routes_1.youtubeResearchRouter);
exports.default = app;
