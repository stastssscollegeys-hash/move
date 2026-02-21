import { Request, Response } from 'express';
import { YouTubeResearchService } from './service';
import { SearchRequest, TrendRequest, VideoMeta } from './types';

// Step 1: YouTube検索 + バズ比率（高速・Claude不要）
export async function handleSearch(req: Request, res: Response): Promise<void> {
  try {
    const body = req.body as SearchRequest;

    if (!body.query || !body.query.trim()) {
      res.status(400).json({ success: false, error: '検索キーワードを入力してください' });
      return;
    }
    if (!body.youtubeApiKey) {
      res.status(400).json({ success: false, error: 'YouTube APIキーを入力してください' });
      return;
    }

    const service = new YouTubeResearchService();
    const result = await service.searchWithBuzz({
      query: body.query.trim(),
      filters: body.filters || { lengthCategory: 'all', uploadPeriod: 'all' },
      maxResults: body.maxResults || 20,
      youtubeApiKey: body.youtubeApiKey,
      anthropicApiKey: body.anthropicApiKey,
    });

    res.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Internal server error';
    res.status(500).json({ success: false, error: message });
  }
}

// Step 2: 選択した動画でターゲット＆キーワード分析（Claude使用）
export async function handleAnalyzeSelected(req: Request, res: Response): Promise<void> {
  try {
    const body = req.body as { videos: VideoMeta[]; anthropicApiKey: string };

    if (!body.videos || body.videos.length === 0) {
      res.status(400).json({ success: false, error: '分析する動画を選択してください' });
      return;
    }
    if (!body.anthropicApiKey) {
      res.status(400).json({ success: false, error: 'Anthropic APIキーを入力してください' });
      return;
    }

    const service = new YouTubeResearchService(body.anthropicApiKey);
    const result = await service.analyzeSelected(body.videos);
    res.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Internal server error';
    res.status(500).json({ success: false, error: message });
  }
}

// Step 3: トレンド判定（Claude使用）
export async function handleTrend(req: Request, res: Response): Promise<void> {
  try {
    const body = req.body as TrendRequest & { anthropicApiKey?: string };

    if (!body.titles || body.titles.length === 0) {
      res.status(400).json({ success: false, error: '動画タイトルが必要です' });
      return;
    }

    const service = new YouTubeResearchService(body.anthropicApiKey);
    const result = await service.checkTrend(body.titles.slice(0, 10));
    res.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Internal server error';
    res.status(500).json({ success: false, error: message });
  }
}
