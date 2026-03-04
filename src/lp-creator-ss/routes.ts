// ===== LP Creator SS - Routes =====

import { Router, Request, Response } from 'express';
import path from 'path';
import { handleGenerate, handleGenerateDemo, handleHealth, handleGetSettings, handleSaveSettings } from './controller';

const router = Router();

// Serve the main HTML page
router.get('/', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'lp-creator.html'));
});

// Admin settings page
router.get('/settings', (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'lp-creator-settings.html'));
});

// API endpoints
router.post('/api/generate', handleGenerate as any);
router.post('/api/generate-demo', handleGenerateDemo as any);
router.get('/api/health', handleHealth);
router.get('/api/settings', handleGetSettings);
router.post('/api/settings', handleSaveSettings);

export { router as lpCreatorRouter };
