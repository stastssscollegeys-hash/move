import express from 'express';
import path from 'path';
import { youtubeResearchRouter } from './youtube-research/routes';

const app = express();

app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

app.use('/youtube-research', youtubeResearchRouter);

export default app;
