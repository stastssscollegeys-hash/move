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

describe('YouTube Research - Security Middleware', () => {
  describe('Helmet Headers', () => {
    it('should set X-Content-Type-Options: nosniff', async () => {
      const res = await request(app).get('/youtube-research/api/health');
      expect(res.headers['x-content-type-options']).toBe('nosniff');
    });
  });

  describe('Body Size Limit', () => {
    it('should reject oversized JSON body', async () => {
      // Create a body that exceeds 1MB limit
      const largeBody = { data: 'x'.repeat(2 * 1024 * 1024) };
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send(largeBody);
      // Should return 413 (Payload Too Large) or 400-level error
      expect(res.status).toBeGreaterThanOrEqual(400);
    });
  });

  describe('API Health', () => {
    it('should return health status from youtube-research endpoint', async () => {
      const res = await request(app).get('/youtube-research/api/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('OK');
    });

    it('should return root health check', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('OK');
    });
  });

  describe('Input Validation Integration', () => {
    it('should reject empty query with proper error message', async () => {
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ query: '   ', youtubeApiKey: 'AIzaSyA12345678901234567890123456789012' });
      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should sanitize error responses (no stack traces)', async () => {
      const res = await request(app)
        .post('/youtube-research/api/search')
        .send({ query: 'test', youtubeApiKey: 'AIzaSyA12345678901234567890123456789012' });
      // Even on error, should not expose internal paths
      if (res.body.error) {
        expect(res.body.error).not.toContain(__dirname);
      }
    });
  });
});
