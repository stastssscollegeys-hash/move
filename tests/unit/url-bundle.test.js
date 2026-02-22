"use strict";
/**
 * URL Bundle Unit Tests
 *
 * Tests for URL normalization, deduplication, and grouping.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
const url_bundle_1 = require("../../src/proxy-mcp/browser/url-bundle");
const memoryTools = __importStar(require("../../src/proxy-mcp/tools/memory"));
// Mock memory tools
jest.mock('../../src/proxy-mcp/tools/memory');
jest.mock('../../src/proxy-mcp/observability', () => ({
    recordEvent: jest.fn(),
}));
const mockMemoryGetContent = memoryTools.memoryGetContent;
const mockMemoryAdd = memoryTools.memoryAdd;
describe('URL Bundle Module', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });
    describe('normalizeUrl', () => {
        const config = url_bundle_1.DEFAULT_URL_BUNDLE_CONFIG;
        it('should normalize a simple URL', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/page', config);
            expect(result).not.toBeNull();
            expect(result?.url).toBe('https://example.com/page');
            expect(result?.domain).toBe('example.com');
        });
        it('should remove UTM parameters', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/page?utm_source=twitter&utm_medium=social&id=123', config);
            expect(result?.url).toBe('https://example.com/page?id=123');
        });
        it('should remove all tracking parameters', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/page?fbclid=abc&gclid=def&ref=home', config);
            expect(result?.url).toBe('https://example.com/page');
        });
        it('should normalize trailing slashes', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/page/', config);
            expect(result?.url).toBe('https://example.com/page');
        });
        it('should keep root trailing slash', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/', config);
            expect(result?.url).toBe('https://example.com/');
        });
        it('should trim whitespace', () => {
            const result = (0, url_bundle_1.normalizeUrl)('  https://example.com/page  ', config);
            expect(result?.url).toBe('https://example.com/page');
        });
        it('should return null for invalid URLs', () => {
            expect((0, url_bundle_1.normalizeUrl)('not a url', config)).toBeNull();
            expect((0, url_bundle_1.normalizeUrl)('', config)).toBeNull();
            expect((0, url_bundle_1.normalizeUrl)('   ', config)).toBeNull();
        });
        it('should track original URL when modified', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/page?utm_source=test', config);
            expect(result?.url).toBe('https://example.com/page');
            expect(result?.originalUrl).toBe('https://example.com/page?utm_source=test');
        });
        it('should not track original URL when unchanged', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/page', config);
            expect(result?.originalUrl).toBeUndefined();
        });
        it('should preserve necessary query parameters', () => {
            const result = (0, url_bundle_1.normalizeUrl)('https://example.com/search?q=test&page=2', config);
            expect(result?.url).toBe('https://example.com/search?q=test&page=2');
        });
    });
    describe('parseUrlList', () => {
        it('should parse JSON array of strings', () => {
            const input = JSON.stringify([
                'https://example.com/1',
                'https://example.com/2',
            ]);
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
            ]);
        });
        it('should parse JSON array of URL objects', () => {
            const input = JSON.stringify([
                { url: 'https://example.com/1', title: 'Page 1' },
                { url: 'https://example.com/2', title: 'Page 2' },
            ]);
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
            ]);
        });
        it('should parse JSON array of href objects', () => {
            const input = JSON.stringify([
                { href: 'https://example.com/1', text: 'Link 1' },
                { href: 'https://example.com/2', text: 'Link 2' },
            ]);
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
            ]);
        });
        it('should parse JSON object with urls array', () => {
            const input = JSON.stringify({
                urls: ['https://example.com/1', 'https://example.com/2'],
            });
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
            ]);
        });
        it('should parse JSON object with tabs array', () => {
            const input = JSON.stringify({
                tabs: [
                    { url: 'https://example.com/1' },
                    { url: 'https://example.com/2' },
                ],
            });
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
            ]);
        });
        it('should parse newline-separated URLs', () => {
            const input = `https://example.com/1
https://example.com/2
https://example.com/3`;
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
                'https://example.com/3',
            ]);
        });
        it('should parse comma-separated URLs', () => {
            const input = 'https://example.com/1, https://example.com/2, https://example.com/3';
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
                'https://example.com/3',
            ]);
        });
        it('should filter non-URL lines', () => {
            const input = `Some text
https://example.com/1
Another text line
https://example.com/2`;
            const result = (0, url_bundle_1.parseUrlList)(input);
            expect(result).toEqual([
                'https://example.com/1',
                'https://example.com/2',
            ]);
        });
        it('should handle empty input', () => {
            expect((0, url_bundle_1.parseUrlList)('')).toEqual([]);
            expect((0, url_bundle_1.parseUrlList)('no urls here')).toEqual([]);
        });
    });
    describe('normalizeUrlBundle', () => {
        it('should normalize URL bundle from memory', async () => {
            const inputUrls = [
                'https://example.com/page1?utm_source=test',
                'https://example.com/page2/',
                'https://example.com/page1?utm_source=other', // duplicate after normalization
                'https://other.com/page',
            ];
            mockMemoryGetContent.mockResolvedValue({
                success: true,
                data: { id: 'ref-input-123', content: JSON.stringify(inputUrls), contentLength: 100 },
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-output-123',
            });
            const result = await (0, url_bundle_1.normalizeUrlBundle)('ref-input-123');
            expect(result.success).toBe(true);
            expect(result.outputRefId).toBe('ref-output-123');
            expect(result.data?.inputCount).toBe(4);
            expect(result.data?.outputCount).toBe(3); // 1 duplicate removed
            expect(result.data?.duplicatesRemoved).toBe(1);
        });
        it('should apply maxUrls limit', async () => {
            const inputUrls = Array.from({ length: 300 }, (_, i) => `https://example.com/page${i}`);
            mockMemoryGetContent.mockResolvedValue({
                success: true,
                data: { id: 'ref-input-456', content: JSON.stringify(inputUrls), contentLength: 10000 },
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-output-456',
            });
            const result = await (0, url_bundle_1.normalizeUrlBundle)('ref-input-456', { maxUrls: 100 });
            expect(result.success).toBe(true);
            expect(result.data?.outputCount).toBe(100);
        });
        it('should group URLs by domain', async () => {
            const inputUrls = [
                'https://example.com/1',
                'https://example.com/2',
                'https://other.com/1',
            ];
            mockMemoryGetContent.mockResolvedValue({
                success: true,
                data: { id: 'ref-input-789', content: JSON.stringify(inputUrls), contentLength: 100 },
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-output-789',
            });
            const result = await (0, url_bundle_1.normalizeUrlBundle)('ref-input-789');
            expect(result.success).toBe(true);
            expect(result.data?.domainGroups).toEqual({
                'example.com': 2,
                'other.com': 1,
            });
        });
        it('should return error when input refId not found', async () => {
            mockMemoryGetContent.mockResolvedValue({
                success: false,
                error: 'Memory entry not found: ref-not-found',
            });
            const result = await (0, url_bundle_1.normalizeUrlBundle)('ref-not-found');
            expect(result.success).toBe(false);
            expect(result.error).toContain('Failed to find URL bundle');
        });
        it('should return error when no valid URLs found', async () => {
            mockMemoryGetContent.mockResolvedValue({
                success: true,
                data: { id: 'ref-no-urls', content: 'no urls here', contentLength: 12 },
            });
            const result = await (0, url_bundle_1.normalizeUrlBundle)('ref-no-urls');
            expect(result.success).toBe(false);
            expect(result.error).toContain('No valid URLs found');
        });
        it('should return error when memory store fails', async () => {
            mockMemoryGetContent.mockResolvedValue({
                success: true,
                data: { id: 'ref-store-fail', content: JSON.stringify(['https://example.com']), contentLength: 50 },
            });
            mockMemoryAdd.mockResolvedValue({
                success: false,
                error: 'Storage error',
            });
            const result = await (0, url_bundle_1.normalizeUrlBundle)('ref-store-fail');
            expect(result.success).toBe(false);
            expect(result.error).toContain('Failed to store');
        });
    });
    describe('getUrlBundleStats', () => {
        it('should return URL statistics', async () => {
            const inputUrls = [
                'https://example.com/1',
                'https://example.com/2',
                'https://other.com/1',
                'https://third.org/page',
            ];
            mockMemoryGetContent.mockResolvedValue({
                success: true,
                data: { id: 'ref-stats-123', content: JSON.stringify(inputUrls), contentLength: 100 },
            });
            const result = await (0, url_bundle_1.getUrlBundleStats)('ref-stats-123');
            expect(result.success).toBe(true);
            expect(result.stats?.totalUrls).toBe(4);
            expect(result.stats?.uniqueDomains).toBe(3);
            expect(result.stats?.topDomains).toContainEqual({
                domain: 'example.com',
                count: 2,
            });
        });
        it('should return error when refId not found', async () => {
            mockMemoryGetContent.mockResolvedValue({
                success: false,
                error: 'Memory entry not found: ref-not-found',
            });
            const result = await (0, url_bundle_1.getUrlBundleStats)('ref-not-found');
            expect(result.success).toBe(false);
            expect(result.error).toContain('Failed to find');
        });
    });
});
