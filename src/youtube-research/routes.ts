import { Router, Request, Response } from 'express';
import path from 'path';
import { handleSearch, handleAnalyzeSelected, handleTrend } from './controller';

const router = Router();

// Serve the main HTML page
router.get('/', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'youtube-research.html'));
});

// API endpoints
router.post('/api/search', handleSearch as any);                    // 検索+バズ（高速）
router.post('/api/analyze-selected', handleAnalyzeSelected as any); // ターゲット+キーワード
router.post('/api/trend', handleTrend as any);                      // トレンド判定

// API Key Guide page
router.get('/api-key-guide', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'youtube-research-api-guide.html'));
});

// Health check
router.get('/api/health', (_req: Request, res: Response) => {
  res.json({ status: 'OK', service: 'youtube-research' });
});

export { router as youtubeResearchRouter };
