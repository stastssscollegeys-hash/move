"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const supertest_1 = __importDefault(require("supertest"));
const app_1 = __importDefault(require("../../src/app"));
// Mock Anthropic SDK
jest.mock('@anthropic-ai/sdk', () => {
    return jest.fn().mockImplementation(() => ({
        messages: {
            create: jest.fn().mockResolvedValue({
                content: [{ type: 'text', text: JSON.stringify({
                            demographics: { ageRange: '25-35', gender: '男性多め', occupation: 'IT' },
                            psychographics: { interests: ['AI'], values: ['効率'], lifestyle: 'テック好き' },
                            painPoints: ['時間がない'],
                            viewingMotivation: ['学びたい'],
                            purchaseBehavior: ['本を買う'],
                            relatedMedia: ['テック系YouTube'],
                            contentAngle: 'AI活用'
                        }) }]
            })
        }
    }));
});
describe('YouTube Research Routes', () => {
    describe('GET /youtube-research/api/health', () => {
        it('should return OK', async () => {
            const res = await (0, supertest_1.default)(app_1.default).get('/youtube-research/api/health');
            expect(res.status).toBe(200);
            expect(res.body.status).toBe('OK');
            expect(res.body.service).toBe('youtube-research');
        });
    });
    describe('POST /youtube-research/api/search', () => {
        it('should reject empty query', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/search')
                .send({ query: '', youtubeApiKey: 'test' });
            expect(res.status).toBe(400);
            expect(res.body.success).toBe(false);
        });
        it('should reject missing query', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/search')
                .send({ youtubeApiKey: 'test' });
            expect(res.status).toBe(400);
        });
        it('should reject missing YouTube API key', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/search')
                .send({ query: 'AI副業' });
            expect(res.status).toBe(400);
            expect(res.body.error).toContain('YouTube');
        });
    });
    describe('POST /youtube-research/api/analyze-selected', () => {
        it('should reject empty videos', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/analyze-selected')
                .send({ videos: [], anthropicApiKey: 'test' });
            expect(res.status).toBe(400);
            expect(res.body.success).toBe(false);
        });
        it('should reject missing Anthropic API key', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/analyze-selected')
                .send({ videos: [{ id: '1', title: 'test' }] });
            expect(res.status).toBe(400);
            expect(res.body.error).toContain('Anthropic');
        });
        it('should accept valid input', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/analyze-selected')
                .send({
                videos: [{
                        id: '1', title: 'AI副業', channel: 'test', subscribers: 1000,
                        views: 50000, likes: 100, uploadDate: null, duration: null,
                        description: 'テスト', transcriptOrSummary: 'テスト要約', url: null
                    }],
                anthropicApiKey: 'test-key'
            });
            expect(res.status).toBe(200);
            expect(res.body.success).toBe(true);
        });
    });
    describe('POST /youtube-research/api/trend', () => {
        it('should reject empty keywords', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/trend')
                .send({ keywords: [] });
            expect(res.status).toBe(400);
        });
        it('should accept valid keywords', async () => {
            const res = await (0, supertest_1.default)(app_1.default)
                .post('/youtube-research/api/trend')
                .send({ keywords: ['AI副業'], anthropicApiKey: 'test-key' });
            expect(res.status).toBe(200);
            expect(res.body.success).toBe(true);
        });
    });
    describe('GET /health (original)', () => {
        it('should still work', async () => {
            const res = await (0, supertest_1.default)(app_1.default).get('/health');
            expect(res.status).toBe(200);
            expect(res.body.status).toBe('OK');
        });
    });
});
