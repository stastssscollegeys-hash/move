import express from 'express';
import path from 'path';
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { youtubeResearchRouter } from './youtube-research/routes';
import { lpCreatorRouter } from './lp-creator-ss/routes';
import { lpNanoBananaRouter } from './lp-nanobanana-ss/routes';
import funnelForgeRouter from './funnel-forge-ss/routes';
import enrollyRouter from './enrolly-ss/routes';

const app = express();

// Security: Helmet with CSP configured for YouTube thumbnails
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      imgSrc: ["'self'", 'i.ytimg.com', 'data:'],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'", "'unsafe-inline'", 'cdnjs.cloudflare.com'],
      connectSrc: ["'self'"],
      frameSrc: ["'self'", "blob:"],
    },
  },
}));

// Security: CORS
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PATCH', 'DELETE'],
}));

// Security: Rate limiting
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  limit: 100, // max 100 requests per window per IP
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { success: false, error: 'リクエスト数が上限に達しました。しばらくしてから再度お試しください。' },
});
app.use('/youtube-research/api/', apiLimiter);

// LP Creator: stricter rate limit (10 requests per 15 min — heavy Claude usage)
const lpCreatorLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 10,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { success: false, error: 'リクエスト数が上限に達しました。しばらくしてから再度お試しください。' },
});
app.use('/lp-creator/api/', lpCreatorLimiter);

// LP NanoBanana: rate limit (100 requests per 15 min)
const lpNanoBananaLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 100,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { success: false, error: 'リクエスト数が上限に達しました。しばらくしてから再度お試しください。' },
});
app.use('/lp-nanobanana/api/', lpNanoBananaLimiter);

// Stripe webhook needs raw body (before JSON parser)
app.post('/ff/api/stripe-webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const { handleWebhook } = require('./funnel-forge-ss/stripe-service');
  const signature = req.headers['stripe-signature'] as string;
  const result = await handleWebhook(req.body.toString(), signature || '');
  res.status(result.success ? 200 : 400).json(result);
});

// Body parser with size limit
app.use(express.json({ limit: '1mb' }));

app.use(express.static(path.join(__dirname, '..', 'public')));

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

app.use('/youtube-research', youtubeResearchRouter);
app.use('/lp-creator', lpCreatorRouter);
app.use('/lp-nanobanana', lpNanoBananaRouter);
app.use('/ff', funnelForgeRouter);
app.use('/enrolly', enrollyRouter);

export default app;
