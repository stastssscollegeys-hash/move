import { Request, Response } from 'express';
import { YouTubeResearchService } from './service';
import { SearchRequest, TrendRequest, VideoMeta } from './types';

// Validation helpers
function isValidYouTubeApiKey(key: string): boolean {
  return /^AIza[0-9A-Za-z_-]{35}$/.test(key);
}

function isValidAnthropicApiKey(key: string): boolean {
  // Support both old (sk-ant-api03-...) and new (sk-ant-..., sk-...) key formats
  return /^sk-[0-9A-Za-z_-]{20,}$/.test(key);
}

function clampMaxResults(value: unknown): number {
  const num = typeof value === 'number' ? value : parseInt(String(value), 10);
  if (isNaN(num) || num < 1) return 20;
  return Math.min(num, 50);
}

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
    if (!isValidYouTubeApiKey(body.youtubeApiKey)) {
      res.status(400).json({ success: false, error: 'YouTube APIキーのフォーマットが不正です' });
      return;
    }

    const maxResults = clampMaxResults(body.maxResults);

    const service = new YouTubeResearchService();
    const result = await service.searchWithBuzz({
      query: body.query.trim(),
      filters: body.filters || { lengthCategory: 'all', uploadPeriod: 'all' },
      maxResults,
      youtubeApiKey: body.youtubeApiKey,
      anthropicApiKey: body.anthropicApiKey,
    });

    res.json(result);
  } catch (err) {
    console.error('[handleSearch] Error:', err);
    res.status(500).json({ success: false, error: 'サーバー内部エラーが発生しました' });
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
    if (!isValidAnthropicApiKey(body.anthropicApiKey)) {
      res.status(400).json({ success: false, error: 'Anthropic APIキーのフォーマットが不正です' });
      return;
    }

    const service = new YouTubeResearchService(body.anthropicApiKey);
    const result = await service.analyzeSelected(body.videos);
    res.json(result);
  } catch (err) {
    console.error('[handleAnalyzeSelected] Error:', err);
    res.status(500).json({ success: false, error: 'サーバー内部エラーが発生しました' });
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

    if (body.anthropicApiKey && !isValidAnthropicApiKey(body.anthropicApiKey)) {
      res.status(400).json({ success: false, error: 'Anthropic APIキーのフォーマットが不正です' });
      return;
    }

    const service = new YouTubeResearchService(body.anthropicApiKey);
    const result = await service.checkTrend(body.titles.slice(0, 10));
    res.json(result);
  } catch (err) {
    console.error('[handleTrend] Error:', err);
    res.status(500).json({ success: false, error: 'サーバー内部エラーが発生しました' });
  }
}
