// ===== LP NanoBanana SS - Routes =====

import { Router, Request, Response } from 'express';
import path from 'path';
import { handleGenerate, handleRetrySection, handleHealth, handleParseInput, handleTestKeys } from './controller';

const router = Router();

// Serve the main HTML page
router.get('/', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'lp-nanobanana.html'));
});

// API key setup guides
router.get('/claude-api-guide', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'anthropic-api-guide.html'));
});
router.get('/gemini-api-guide', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'gemini-api-guide.html'));
});

// API endpoints
router.post('/api/generate', handleGenerate as any);
router.post('/api/retry-section', handleRetrySection as any);
router.post('/api/parse-input', handleParseInput as any);
router.post('/api/test-keys', handleTestKeys as any);
router.get('/api/health', handleHealth);

export { router as lpNanoBananaRouter };
