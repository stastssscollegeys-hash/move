"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const path_1 = __importDefault(require("path"));
const helmet_1 = __importDefault(require("helmet"));
const cors_1 = __importDefault(require("cors"));
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const routes_1 = require("./youtube-research/routes");
const routes_2 = require("./lp-creator-ss/routes");
const routes_3 = __importDefault(require("./funnel-forge-ss/routes"));
const routes_4 = __importDefault(require("./enrolly-ss/routes"));
const app = (0, express_1.default)();
// Security: Helmet with CSP configured for YouTube thumbnails
app.use((0, helmet_1.default)({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            imgSrc: ["'self'", 'i.ytimg.com'],
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'", "'unsafe-inline'"],
            connectSrc: ["'self'"],
            frameSrc: ["'self'", "blob:"],
        },
    },
}));
// Security: CORS
app.use((0, cors_1.default)({
    origin: process.env.CORS_ORIGIN || '*',
    methods: ['GET', 'POST', 'PATCH', 'DELETE'],
}));
// Security: Rate limiting
const apiLimiter = (0, express_rate_limit_1.default)({
    windowMs: 15 * 60 * 1000, // 15 minutes
    limit: 100, // max 100 requests per window per IP
    standardHeaders: 'draft-7',
    legacyHeaders: false,
    message: { success: false, error: 'リクエスト数が上限に達しました。しばらくしてから再度お試しください。' },
});
app.use('/youtube-research/api/', apiLimiter);
// LP Creator: stricter rate limit (10 requests per 15 min — heavy Claude usage)
const lpCreatorLimiter = (0, express_rate_limit_1.default)({
    windowMs: 15 * 60 * 1000,
    limit: 10,
    standardHeaders: 'draft-7',
    legacyHeaders: false,
    message: { success: false, error: 'リクエスト数が上限に達しました。しばらくしてから再度お試しください。' },
});
app.use('/lp-creator/api/', lpCreatorLimiter);
// Stripe webhook needs raw body (before JSON parser)
app.post('/ff/api/stripe-webhook', express_1.default.raw({ type: 'application/json' }), async (req, res) => {
    const { handleWebhook } = require('./funnel-forge-ss/stripe-service');
    const signature = req.headers['stripe-signature'];
    const result = await handleWebhook(req.body.toString(), signature || '');
    res.status(result.success ? 200 : 400).json(result);
});
// Body parser with size limit
app.use(express_1.default.json({ limit: '1mb' }));
app.use(express_1.default.static(path_1.default.join(__dirname, '..', 'public')));
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'OK' });
});
app.use('/youtube-research', routes_1.youtubeResearchRouter);
app.use('/lp-creator', routes_2.lpCreatorRouter);
app.use('/ff', routes_3.default);
app.use('/enrolly', routes_4.default);
exports.default = app;
