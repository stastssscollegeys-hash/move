// Mock Anthropic SDK first
jest.mock('@anthropic-ai/sdk', () => ({
  __esModule: true,
  default: jest.fn().mockImplementation(() => ({
    messages: {
      create: jest.fn().mockResolvedValue({
        content: [{ type: 'text', text: '{}' }]
      })
    }
  }))
}));

import request from 'supertest';
import app from '../../src/app';

describe('YouTube Research Routes', () => {
  describe('GET /youtube-research/api/health', () => {
    it('should return OK', async () => {
      const res = await request(app).get('/youtube-research/api/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('OK');
      expect(res.body.service).toBe('youtube-research');
    });
  });

  describe('GET /health (root)', () => {
    it('should return OK', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('OK');
    });
  });

  describe('POST /youtube-research/api/search', () => {
    it('should reject empty query', async () => {
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ query: '', youtubeApiKey: 'AIzaSyA12345678901234567890123456789012' });
      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toContain('検索キーワード');
    });

    it('should reject missing query', async () => {
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ youtubeApiKey: 'AIzaSyA12345678901234567890123456789012' });
      expect(res.status).toBe(400);
    });

    it('should reject missing YouTube API key', async () => {
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ query: 'AI副業' });
      expect(res.status).toBe(400);
      expect(res.body.error).toContain('YouTube');
    });

    it('should reject invalid YouTube API key format', async () => {
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ query: 'test', youtubeApiKey: 'invalid-key' });
      expect(res.status).toBe(400);
      expect(res.body.error).toContain('フォーマットが不正');
    });

    it('should accept valid YouTube API key (AIza prefix + 35 chars)', async () => {
      // This will pass validation but may fail at actual YouTube API call
      // which returns a sanitized error, not a 400
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ query: 'test', youtubeApiKey: 'AIzaSyA12345678901234567890123456789012' });
      // Should pass validation (not 400 for format)
      expect(res.body.error).not.toContain('フォーマットが不正');
    });
  });

  describe('POST /youtube-research/api/analyze-selected', () => {
    it('should reject empty videos', async () => {
      const res = await request(app)
        .post('/youtube-research/api/analyze-selected')
        .send({ videos: [], anthropicApiKey: 'sk-ant-test-key-abcdefghijklmnop' });
      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should reject missing Anthropic API key', async () => {
      const res = await request(app)
        .post('/youtube-research/api/analyze-selected')
        .send({ videos: [{ id: '1', title: 'test' }] });
      expect(res.status).toBe(400);
      expect(res.body.error).toContain('Anthropic');
    });

    it('should reject invalid Anthropic API key format', async () => {
      const res = await request(app)
        .post('/youtube-research/api/analyze-selected')
        .send({ videos: [{ id: '1', title: 'test' }], anthropicApiKey: 'bad-key' });
      expect(res.status).toBe(400);
      expect(res.body.error).toContain('フォーマットが不正');
    });
  });

  describe('POST /youtube-research/api/trend', () => {
    it('should reject empty titles', async () => {
      const res = await request(app)
        .post('/youtube-research/api/trend')
        .send({ titles: [] });
      expect(res.status).toBe(400);
    });

    it('should reject missing titles', async () => {
      const res = await request(app)
        .post('/youtube-research/api/trend')
        .send({});
      expect(res.status).toBe(400);
    });

    it('should reject invalid Anthropic API key format', async () => {
      const res = await request(app)
        .post('/youtube-research/api/trend')
        .send({ titles: ['テスト'], anthropicApiKey: 'invalid' });
      expect(res.status).toBe(400);
      expect(res.body.error).toContain('フォーマットが不正');
    });
  });
});
