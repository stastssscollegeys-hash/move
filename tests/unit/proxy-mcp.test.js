"use strict";
/**
 * Proxy MCP Unit Tests
 */
Object.defineProperty(exports, "__esModule", { value: true });
const system_1 = require("../../src/proxy-mcp/tools/system");
const memory_1 = require("../../src/proxy-mcp/tools/memory");
const skill_1 = require("../../src/proxy-mcp/tools/skill");
const memory_2 = require("../../src/proxy-mcp/memory");
describe('Proxy MCP', () => {
    describe('system.health', () => {
        it('should return healthy status', () => {
            const result = (0, system_1.systemHealth)();
            expect(result.success).toBe(true);
            expect(result.data).toBeDefined();
            expect(['healthy', 'degraded', 'unhealthy']).toContain(result.data.status);
            expect(result.data.version).toBe('0.2.0');
            expect(result.data.uptime).toBeGreaterThanOrEqual(0);
            expect(result.data.timestamp).toBeDefined();
        });
        it('should include circuit breaker status', () => {
            const result = (0, system_1.systemHealth)();
            expect(result.data).toBeDefined();
            const data = result.data;
            expect(data.circuits).toBeDefined();
            expect(typeof data.circuits.total).toBe('number');
            expect(typeof data.circuits.closed).toBe('number');
            expect(typeof data.circuits.open).toBe('number');
            expect(typeof data.circuits.halfOpen).toBe('number');
        });
        it('should include rollout status', () => {
            const result = (0, system_1.systemHealth)();
            expect(result.data).toBeDefined();
            const data = result.data;
            expect(data.rollout).toBeDefined();
            expect(typeof data.rollout.overlayActive).toBe('boolean');
            expect(Array.isArray(data.rollout.mcps)).toBe(true);
        });
    });
    describe('memory tools', () => {
        beforeEach(async () => {
            // Reset singleton and clear all memory before each test
            memory_2.MemoryService.resetInstance();
            await (0, memory_1.memoryClearAll)();
        });
        describe('memory.add', () => {
            it('should store content and return reference ID', async () => {
                const result = await (0, memory_1.memoryAdd)('Test content', 'short-term');
                expect(result.success).toBe(true);
                expect(result.referenceId).toBeDefined();
                expect(typeof result.referenceId).toBe('string');
                expect(result.data.contentLength).toBe(12);
            });
            it('should store with metadata', async () => {
                const result = await (0, memory_1.memoryAdd)('Content with meta', 'long-term', { source: 'test' });
                expect(result.success).toBe(true);
                expect(result.referenceId).toBeDefined();
            });
            it('should return summary in response', async () => {
                const result = await (0, memory_1.memoryAdd)('Test content for summary generation', 'short-term');
                expect(result.success).toBe(true);
                expect(result.data.summary).toBeDefined();
            });
        });
        describe('memory.search', () => {
            it('should find content by ID', async () => {
                const addResult = await (0, memory_1.memoryAdd)('Searchable content', 'short-term');
                const id = addResult.referenceId;
                const searchResult = await (0, memory_1.memorySearch)(id);
                expect(searchResult.success).toBe(true);
                expect(searchResult.data.found).toBe(true);
                expect(searchResult.data.results.length).toBe(1);
            });
            it('should find content by keyword', async () => {
                await (0, memory_1.memoryAdd)('The quick brown fox', 'short-term');
                await (0, memory_1.memoryAdd)('Lazy dog sleeps', 'short-term');
                const result = await (0, memory_1.memorySearch)('fox');
                expect(result.success).toBe(true);
                expect(result.data.found).toBe(true);
                expect(result.data.results.length).toBeGreaterThanOrEqual(1);
            });
            it('should return empty results for non-matching query', async () => {
                await (0, memory_1.memoryAdd)('Some content', 'short-term');
                const result = await (0, memory_1.memorySearch)('nonexistent');
                expect(result.success).toBe(true);
                expect(result.data.found).toBe(false);
                expect(result.data.results.length).toBe(0);
            });
            it('should filter by namespace', async () => {
                await (0, memory_1.memoryAdd)('Short term content', 'short-term');
                await (0, memory_1.memoryAdd)('Long term content', 'long-term');
                const result = await (0, memory_1.memorySearch)('content', { namespace: 'short-term' });
                expect(result.success).toBe(true);
                expect(result.data.results.every(r => r.namespace === 'short-term')).toBe(true);
            });
        });
        describe('memory.stats', () => {
            it('should return memory statistics', async () => {
                await (0, memory_1.memoryAdd)('Short term 1', 'short-term');
                await (0, memory_1.memoryAdd)('Short term 2', 'short-term');
                await (0, memory_1.memoryAdd)('Long term 1', 'long-term');
                const result = await (0, memory_1.memoryStats)();
                expect(result.success).toBe(true);
                expect(result.data.total).toBe(3);
                expect(result.data.shortTerm).toBe(2);
                expect(result.data.longTerm).toBe(1);
            });
        });
        describe('memoryClearShortTerm', () => {
            it('should clear only short-term memory', async () => {
                await (0, memory_1.memoryAdd)('Short term', 'short-term');
                await (0, memory_1.memoryAdd)('Long term', 'long-term');
                const clearResult = await (0, memory_1.memoryClearShortTerm)();
                const statsResult = await (0, memory_1.memoryStats)();
                expect(clearResult.success).toBe(true);
                expect(clearResult.data.cleared).toBe(1);
                expect(statsResult.data.total).toBe(1);
                expect(statsResult.data.longTerm).toBe(1);
            });
        });
    });
    describe('skill tools', () => {
        describe('skill.search', () => {
            it('should return empty array when skills directory does not exist', () => {
                const result = (0, skill_1.skillSearch)('test');
                expect(result.success).toBe(true);
                expect(result.data.skills).toEqual([]);
            });
            it('should search with empty query', () => {
                const result = (0, skill_1.skillSearch)('');
                expect(result.success).toBe(true);
                expect(result.data).toBeDefined();
            });
        });
        describe('skill.run', () => {
            it('should return error for non-existent skill', () => {
                const result = (0, skill_1.skillRun)('nonexistent-skill');
                expect(result.success).toBe(false);
                expect(result.error).toContain('Skill not found');
            });
        });
    });
});
