import express from 'express';
import path from 'path';
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { youtubeResearchRouter } from './youtube-research/routes';
import { lpCreatorRouter } from './lp-creator-ss/routes';

const app = express();

// Security: Helmet with CSP configured for YouTube thumbnails
app.use(helmet({
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
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST'],
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

// Body parser with size limit
app.use(express.json({ limit: '1mb' }));

app.use(express.static(path.join(__dirname, '..', 'public')));

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

app.use('/youtube-research', youtubeResearchRouter);
app.use('/lp-creator', lpCreatorRouter);

export default app;
