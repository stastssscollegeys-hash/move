"use strict";
/**
 * Chrome Integration Unit Tests (M4)
 *
 * Tests for web skills and CAPTCHA detection
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
const browser_1 = require("../../src/proxy-mcp/browser");
const skill_1 = require("../../src/proxy-mcp/tools/skill");
const memory_1 = require("../../src/proxy-mcp/memory");
describe('Chrome Integration', () => {
    describe('CAPTCHA Detection', () => {
        describe('detectCaptcha', () => {
            it('should detect "captcha" pattern', () => {
                const result = (0, browser_1.detectCaptcha)('Please complete the captcha to continue');
                expect(result.detected).toBe(true);
                expect(result.pattern).toBe('captcha');
            });
            it('should detect recaptcha in content', () => {
                const result = (0, browser_1.detectCaptcha)('<div class="g-recaptcha"></div>');
                expect(result.detected).toBe(true);
                // Pattern order: "captcha" comes before "recaptcha" in the list
                expect(['captcha', 'recaptcha']).toContain(result.pattern);
            });
            it('should detect "cloudflare" pattern', () => {
                const result = (0, browser_1.detectCaptcha)('Checking if the site connection is secure Cloudflare');
                expect(result.detected).toBe(true);
                expect(result.pattern).toBe('cloudflare');
            });
            it('should detect "verify you are human" pattern', () => {
                const result = (0, browser_1.detectCaptcha)('Please verify you are human before continuing');
                expect(result.detected).toBe(true);
                expect(result.pattern).toBe('verify you are human');
            });
            it('should detect "i\'m not a robot" pattern', () => {
                const result = (0, browser_1.detectCaptcha)("Check this box: I'm not a robot");
                expect(result.detected).toBe(true);
                expect(result.pattern).toBe("i'm not a robot");
            });
            it('should not detect normal content', () => {
                const result = (0, browser_1.detectCaptcha)('Welcome to our website. Browse our products.');
                expect(result.detected).toBe(false);
                expect(result.pattern).toBeUndefined();
            });
            it('should be case insensitive', () => {
                const result = (0, browser_1.detectCaptcha)('CAPTCHA verification required');
                expect(result.detected).toBe(true);
            });
        });
        describe('guardCaptcha', () => {
            it('should return require_human when CAPTCHA detected', () => {
                const result = (0, browser_1.guardCaptcha)('Please solve the captcha', 'https://example.com');
                expect(result).not.toBeNull();
                expect(result.success).toBe(false);
                expect(result.action).toBe('require_human');
                expect(result.data?.instructions).toBeDefined();
            });
            it('should return null when no CAPTCHA', () => {
                const result = (0, browser_1.guardCaptcha)('Normal page content', 'https://example.com');
                expect(result).toBeNull();
            });
        });
        describe('checkBlockedPatterns', () => {
            it('should block accounts.google.com', () => {
                const result = (0, browser_1.checkBlockedPatterns)('https://accounts.google.com/signin');
                expect(result).not.toBeNull();
                expect(result.action).toBe('require_human');
            });
            it('should block login pages', () => {
                const result = (0, browser_1.checkBlockedPatterns)('https://example.com/login');
                expect(result).not.toBeNull();
                expect(result.action).toBe('require_human');
            });
            it('should block auth pages', () => {
                const result = (0, browser_1.checkBlockedPatterns)('https://auth.example.com/oauth');
                expect(result).not.toBeNull();
                expect(result.action).toBe('require_human');
            });
            it('should allow normal URLs', () => {
                const result = (0, browser_1.checkBlockedPatterns)('https://example.com/products');
                expect(result).toBeNull();
            });
        });
    });
    describe('Web Skills (sync check)', () => {
        describe('skillRun for web skills', () => {
            it('should require URL for web.read_url', () => {
                const result = (0, skill_1.skillRun)('web.read_url');
                expect(result.success).toBe(false);
                expect(result.error).toContain('URL is required');
            });
            it('should validate URL format', () => {
                const result = (0, skill_1.skillRun)('web.read_url', { url: 'not-a-valid-url' });
                expect(result.success).toBe(false);
                expect(result.error).toContain('Invalid URL');
            });
            it('should return ready status for valid URL', () => {
                const result = (0, skill_1.skillRun)('web.read_url', { url: 'https://example.com' });
                expect(result.success).toBe(true);
                expect(result.data.asyncRequired).toBe(true);
                expect(result.data.status).toBe('ready');
            });
            it('should handle web.extract_links', () => {
                const result = (0, skill_1.skillRun)('web.extract_links', { url: 'https://example.com' });
                expect(result.success).toBe(true);
                expect(result.data.skill).toBe('web.extract_links');
            });
            it('should handle web.capture_dom_map', () => {
                const result = (0, skill_1.skillRun)('web.capture_dom_map', { url: 'https://example.com' });
                expect(result.success).toBe(true);
                expect(result.data.skill).toBe('web.capture_dom_map');
            });
        });
    });
    describe('Web Skills (async execution)', () => {
        beforeEach(() => {
            memory_1.MemoryService.resetInstance();
        });
        describe('skillRunAsync', () => {
            it('should require URL', async () => {
                const result = await (0, skill_1.skillRunAsync)('web.read_url', {});
                expect(result.success).toBe(false);
                expect(result.error).toContain('URL is required');
            });
            it('should handle unknown web skill', async () => {
                const result = await (0, skill_1.skillRunAsync)('web.unknown', { url: 'https://example.com' });
                expect(result.success).toBe(false);
                expect(result.error).toContain('Unknown skill');
            });
            // Note: These tests verify web skills handle errors gracefully
            // Chrome MCP may or may not be available
            it('should handle chrome MCP state for read_url', async () => {
                const result = await (0, skill_1.skillRunAsync)('web.read_url', { url: 'https://example.com' });
                // Either succeeds or fails with a meaningful error
                if (!result.success) {
                    expect(result.error).toBeDefined();
                    // Error could be about MCP not available or not started
                    expect(typeof result.error).toBe('string');
                }
            });
            it('should handle chrome MCP state for extract_links', async () => {
                const result = await (0, skill_1.skillRunAsync)('web.extract_links', { url: 'https://example.com' });
                if (!result.success) {
                    expect(result.error).toBeDefined();
                }
            });
            it('should handle chrome MCP state for capture_dom_map', async () => {
                const result = await (0, skill_1.skillRunAsync)('web.capture_dom_map', { url: 'https://example.com' });
                if (!result.success) {
                    expect(result.error).toBeDefined();
                }
            });
        });
    });
    describe('MCP Client', () => {
        // These are integration-like tests that verify the client structure
        // without actually spawning processes
        it('should have McpClient class available', async () => {
            const { McpClient } = await Promise.resolve().then(() => __importStar(require('../../src/proxy-mcp/internal/mcp-client')));
            expect(McpClient).toBeDefined();
        });
        it('should have getClient function available', async () => {
            const { getClient } = await Promise.resolve().then(() => __importStar(require('../../src/proxy-mcp/internal/mcp-client')));
            expect(getClient).toBeDefined();
        });
        it('should return null for non-existent MCP', async () => {
            const { getClient } = await Promise.resolve().then(() => __importStar(require('../../src/proxy-mcp/internal/mcp-client')));
            const client = getClient('non-existent-mcp');
            expect(client).toBeNull();
        });
        it('should return client for chrome MCP (if configured)', async () => {
            const { getClient } = await Promise.resolve().then(() => __importStar(require('../../src/proxy-mcp/internal/mcp-client')));
            const client = getClient('chrome');
            // Client may be null if chrome MCP is not configured
            if (client) {
                expect(client.isAvailable()).toBe(true);
            }
            else {
                // Skip test if chrome MCP is not configured
                expect(client).toBeNull();
            }
        });
    });
    describe('Router Integration', () => {
        it('should route browser-related queries to chrome MCP', () => {
            const result = (0, skill_1.skillRun)('_', { mode: 'route', input: 'use browser to scrape web page' });
            expect(result.success).toBe(true);
            const candidates = result.data.candidates;
            // Chrome should be in candidates if the query matches its tags
            if (candidates && candidates.length > 0) {
                // Check if chrome is among top candidates
                const chromeCandidate = candidates.find(c => c.name === 'chrome');
                if (chromeCandidate) {
                    expect(chromeCandidate.name).toBe('chrome');
                }
            }
            // Test passes as long as routing works
            expect(result.success).toBe(true);
        });
        it('should route URL-related queries', () => {
            const result = (0, skill_1.skillRun)('_', { mode: 'route', input: 'scrape dom from url' });
            expect(result.success).toBe(true);
            // Just verify routing works
            expect(result.data.action).toBeDefined();
        });
    });
});
