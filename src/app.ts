import express from 'express';
import path from 'path';
import { youtubeResearchRouter } from './youtube-research/routes';

const app = express();

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, '..', 'public')));

// Existing health check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

// YouTube Research Tool
app.use('/youtube-research', youtubeResearchRouter);

export default app;
