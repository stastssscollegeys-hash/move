"use strict";
/**
 * Skillize Unit Tests (M5)
 *
 * Tests for URL→Skill generation with templates
 */
Object.defineProperty(exports, "__esModule", { value: true });
const templates_1 = require("../../src/proxy-mcp/skillize/templates");
const skill_1 = require("../../src/proxy-mcp/tools/skill");
const memory_1 = require("../../src/proxy-mcp/memory");
describe('Skillize', () => {
    describe('Templates', () => {
        describe('template definitions', () => {
            it('should have 3 templates available', () => {
                expect(templates_1.templates).toHaveLength(3);
            });
            it('should have docs template', () => {
                const template = (0, templates_1.getTemplate)('docs');
                expect(template).toBeDefined();
                expect(template?.type).toBe('docs');
                expect(template?.keywords).toContain('documentation');
            });
            it('should have ecommerce template', () => {
                const template = (0, templates_1.getTemplate)('ecommerce');
                expect(template).toBeDefined();
                expect(template?.type).toBe('ecommerce');
                expect(template?.keywords).toContain('product');
            });
            it('should have internal-tool template', () => {
                const template = (0, templates_1.getTemplate)('internal-tool');
                expect(template).toBeDefined();
                expect(template?.type).toBe('internal-tool');
                expect(template?.keywords).toContain('dashboard');
            });
            it('should return undefined for unknown template', () => {
                const template = (0, templates_1.getTemplate)('unknown');
                expect(template).toBeUndefined();
            });
        });
        describe('detectTemplate', () => {
            it('should detect docs template for documentation URLs', () => {
                const analysis = {
                    url: 'https://docs.example.com/api/reference',
                    title: 'API Documentation',
                    contentType: 'documentation',
                    hostname: 'docs.example.com',
                    path: '/api/reference',
                    sections: ['Getting Started', 'Installation'],
                    sampleContent: 'This is the API documentation for our library.',
                };
                const template = (0, templates_1.detectTemplate)(analysis);
                expect(template.type).toBe('docs');
            });
            it('should detect ecommerce template for product pages', () => {
                const analysis = {
                    url: 'https://shop.example.com/product/123',
                    title: 'Amazing Product',
                    contentType: 'product',
                    hostname: 'shop.example.com',
                    path: '/product/123',
                    sections: [],
                    sampleContent: 'Buy now for $99.99. Add to cart. Free shipping.',
                    productInfo: {
                        name: 'Amazing Product',
                        price: '$99.99',
                    },
                };
                const template = (0, templates_1.detectTemplate)(analysis);
                expect(template.type).toBe('ecommerce');
            });
            it('should detect internal-tool template for dashboard URLs', () => {
                const analysis = {
                    url: 'https://admin.example.com/dashboard',
                    title: 'Admin Dashboard',
                    contentType: 'tool',
                    hostname: 'admin.example.com',
                    path: '/dashboard',
                    sections: ['Settings', 'Configuration'],
                    sampleContent: 'Welcome to the admin dashboard. Configure your settings.',
                };
                const template = (0, templates_1.detectTemplate)(analysis);
                expect(template.type).toBe('internal-tool');
            });
            it('should default to docs for unknown content', () => {
                const analysis = {
                    url: 'https://example.com/page',
                    title: 'Some Page',
                    contentType: 'unknown',
                    hostname: 'example.com',
                    path: '/page',
                    sections: [],
                    sampleContent: 'Some random content here.',
                };
                const template = (0, templates_1.detectTemplate)(analysis);
                expect(template.type).toBe('docs');
            });
        });
        describe('template generation', () => {
            it('should generate docs skill content', () => {
                const analysis = {
                    url: 'https://docs.example.com/guide',
                    title: 'Example Guide',
                    contentType: 'documentation',
                    hostname: 'docs.example.com',
                    path: '/guide',
                    sections: ['Introduction', 'Getting Started', 'API Reference'],
                    sampleContent: 'Welcome to the Example Guide. This documentation covers...',
                };
                const template = (0, templates_1.getTemplate)('docs');
                const skill = template.generate(analysis);
                expect(skill.name).toBe('example-guide');
                expect(skill.template).toBe('docs');
                expect(skill.skillMd).toContain('Example Guide');
                expect(skill.skillMd).toContain('Introduction');
                expect(skill.skillMd).toContain('docs.example.com');
                expect(skill.usage).toContain('skill.run');
            });
            it('should generate ecommerce skill content', () => {
                const analysis = {
                    url: 'https://shop.example.com/product/widget',
                    title: 'Super Widget',
                    contentType: 'product',
                    hostname: 'shop.example.com',
                    path: '/product/widget',
                    sections: [],
                    sampleContent: 'The best widget ever made.',
                    productInfo: {
                        name: 'Super Widget',
                        price: '$49.99',
                        category: 'Widgets',
                    },
                };
                const template = (0, templates_1.getTemplate)('ecommerce');
                const skill = template.generate(analysis);
                expect(skill.name).toBe('super-widget');
                expect(skill.template).toBe('ecommerce');
                expect(skill.skillMd).toContain('Super Widget');
                expect(skill.skillMd).toContain('$49.99');
            });
            it('should generate internal-tool skill content', () => {
                const analysis = {
                    url: 'https://localhost:3000/admin',
                    title: 'Local Admin Panel',
                    contentType: 'tool',
                    hostname: 'localhost',
                    path: '/admin',
                    sections: ['Users', 'Settings', 'Logs'],
                    sampleContent: 'Admin panel for managing the application.',
                };
                const template = (0, templates_1.getTemplate)('internal-tool');
                const skill = template.generate(analysis);
                expect(skill.name).toBe('local-admin-panel');
                expect(skill.template).toBe('internal-tool');
                expect(skill.skillMd).toContain('Local Admin Panel');
                expect(skill.skillMd).toContain('Security Note');
            });
        });
    });
    describe('Skill Integration (sync check)', () => {
        describe('skillRun for skillize', () => {
            it('should require URL for skillize', () => {
                const result = (0, skill_1.skillRun)('skillize');
                expect(result.success).toBe(false);
                expect(result.error).toContain('URL is required');
            });
            it('should validate URL format', () => {
                const result = (0, skill_1.skillRun)('skillize', { url: 'not-a-valid-url' });
                expect(result.success).toBe(false);
                expect(result.error).toContain('Invalid URL');
            });
            it('should return ready status for valid URL (dry-run)', () => {
                const result = (0, skill_1.skillRun)('skillize', { url: 'https://docs.example.com' });
                expect(result.success).toBe(true);
                expect(result.data.asyncRequired).toBe(true);
                expect(result.data.status).toBe('ready');
                expect(result.data.confirmWrite).toBe(false);
                expect(result.data.message).toContain('dry-run');
            });
            it('should indicate write mode when confirmWrite=true', () => {
                const result = (0, skill_1.skillRun)('skillize', {
                    url: 'https://docs.example.com',
                    confirmWrite: true,
                });
                expect(result.success).toBe(true);
                expect(result.data.confirmWrite).toBe(true);
                expect(result.data.message).toContain('WRITE mode');
            });
        });
    });
    describe('Skill Integration (async execution)', () => {
        beforeEach(() => {
            memory_1.MemoryService.resetInstance();
        });
        describe('skillRunAsync for skillize', () => {
            it('should require URL', async () => {
                const result = await (0, skill_1.skillRunAsync)('skillize', {});
                expect(result.success).toBe(false);
                expect(result.error).toContain('URL is required');
            });
            // Note: Full async tests require chrome MCP or mocked web skills
            // These tests verify the integration structure works correctly
            it('should handle unknown skill', async () => {
                const result = await (0, skill_1.skillRunAsync)('unknown.skill', { url: 'https://example.com' });
                expect(result.success).toBe(false);
                expect(result.error).toContain('Unknown skill');
            });
        });
    });
    describe('Template URL Patterns', () => {
        it('should match docs patterns', () => {
            const template = (0, templates_1.getTemplate)('docs');
            expect(template.urlPatterns.some(p => p.test('https://docs.example.com'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('https://example.com/docs/'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('https://example.com/api/'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('https://example.io/docs'))).toBe(true);
        });
        it('should match ecommerce patterns', () => {
            const template = (0, templates_1.getTemplate)('ecommerce');
            expect(template.urlPatterns.some(p => p.test('https://example.com/product/123'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('https://example.com/shop/'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('https://amazon.com/dp/B123'))).toBe(true);
        });
        it('should match internal-tool patterns', () => {
            const template = (0, templates_1.getTemplate)('internal-tool');
            expect(template.urlPatterns.some(p => p.test('https://example.com/admin'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('https://example.com/dashboard'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('http://localhost:3000'))).toBe(true);
            expect(template.urlPatterns.some(p => p.test('http://127.0.0.1:8080'))).toBe(true);
        });
    });
});
