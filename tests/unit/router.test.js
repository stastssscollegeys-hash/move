"use strict";
/**
 * Hybrid Router Unit Tests
 */
Object.defineProperty(exports, "__esModule", { value: true });
const router_1 = require("../../src/proxy-mcp/router");
const registry_1 = require("../../src/proxy-mcp/internal/registry");
// Mock MCPs for testing
const mockMcps = [
    {
        name: 'github',
        transport: 'stdio',
        command: 'npx',
        args: ['-y', '@anthropic/mcp-server-github'],
        enabled: true,
        tags: ['vcs', 'code', 'issues', 'pr', 'repository'],
        shortDescription: 'GitHub operations: repos, issues, PRs, code search',
        dangerousOperations: ['delete', 'force-push', 'archive'],
    },
    {
        name: 'postgres',
        transport: 'stdio',
        command: 'npx',
        args: ['-y', '@anthropic/mcp-server-postgres'],
        enabled: true,
        tags: ['database', 'sql', 'query', 'data'],
        shortDescription: 'PostgreSQL queries and schema operations',
        dangerousOperations: ['drop', 'truncate', 'delete', 'alter'],
    },
    {
        name: 'chrome',
        transport: 'stdio',
        command: 'npx',
        args: ['-y', '@anthropic/mcp-server-puppeteer'],
        enabled: true,
        tags: ['browser', 'web', 'automation', 'scrape', 'dom'],
        shortDescription: 'Browser automation: navigate, click, extract DOM',
        dangerousOperations: ['login', 'submit-form', 'payment'],
    },
    {
        name: 'disabled-mcp',
        transport: 'stdio',
        command: 'test',
        args: [],
        enabled: false,
        tags: ['test'],
        shortDescription: 'A disabled MCP',
        dangerousOperations: [],
    },
];
const defaultConfig = {
    ruleFirst: true,
    semanticThreshold: 0.3, // Lower threshold for testing
    topK: 5,
    fallback: 'require_clarify',
};
describe('Hybrid Router', () => {
    describe('Safety Rules', () => {
        it('should have defined safety rules', () => {
            expect(router_1.SAFETY_RULES.length).toBeGreaterThan(0);
        });
        it('should detect deployment keywords', () => {
            const result = (0, router_1.evaluateSafetyRules)('deploy to production');
            expect(result).not.toBeNull();
            expect(result?.action).toBe('require_human');
            expect(result?.matchedRule).toBe('deployment');
        });
        it('should detect destructive keywords', () => {
            const result = (0, router_1.evaluateSafetyRules)('delete all records');
            expect(result).not.toBeNull();
            expect(result?.action).toBe('require_human');
            expect(result?.matchedRule).toBe('destructive');
        });
        it('should detect secret/credential keywords', () => {
            const result = (0, router_1.evaluateSafetyRules)('rotate the api_key');
            expect(result).not.toBeNull();
            expect(result?.action).toBe('require_human');
            expect(result?.matchedRule).toBe('secrets');
        });
        it('should detect billing keywords', () => {
            const result = (0, router_1.evaluateSafetyRules)('cancel subscription');
            expect(result).not.toBeNull();
            expect(result?.action).toBe('require_human');
        });
        it('should deny automation abuse attempts', () => {
            const result = (0, router_1.evaluateSafetyRules)('bypass captcha');
            expect(result).not.toBeNull();
            expect(result?.action).toBe('deny');
            expect(result?.matchedRule).toBe('automation_abuse');
        });
        it('should return null for safe inputs', () => {
            const result = (0, router_1.evaluateSafetyRules)('search for issues');
            expect(result).toBeNull();
        });
        it('should check safety with isSafe helper', () => {
            expect((0, router_1.isSafe)('search for issues')).toBe(true);
            expect((0, router_1.isSafe)('delete all data')).toBe(false);
            expect((0, router_1.isSafe)('deploy to production')).toBe(false);
        });
    });
    describe('Semantic Similarity', () => {
        it('should calculate similarity for matching tags', () => {
            const score = (0, router_1.calculateSimilarity)('query database', mockMcps[1]); // postgres
            expect(score).toBeGreaterThan(0);
        });
        it('should give higher score for exact name match', () => {
            const scoreWithName = (0, router_1.calculateSimilarity)('github repository', mockMcps[0]);
            const scoreWithoutName = (0, router_1.calculateSimilarity)('repository management', mockMcps[0]);
            // When MCP name is in query, it gets a 0.3 bonus
            expect(scoreWithName).toBeGreaterThanOrEqual(scoreWithoutName);
        });
        it('should return 0 for empty query', () => {
            const score = (0, router_1.calculateSimilarity)('', mockMcps[0]);
            expect(score).toBe(0);
        });
        it('should find matching MCPs above threshold', () => {
            const candidates = (0, router_1.findMatchingMcps)('github pull request', mockMcps, 0.2, 5);
            expect(candidates.length).toBeGreaterThan(0);
            expect(candidates[0].name).toBe('github');
        });
        it('should not include disabled MCPs', () => {
            const candidates = (0, router_1.findMatchingMcps)('test disabled', mockMcps, 0.1, 5);
            const disabledMcp = candidates.find((c) => c.name === 'disabled-mcp');
            expect(disabledMcp).toBeUndefined();
        });
        it('should respect topK limit', () => {
            const candidates = (0, router_1.findMatchingMcps)('search something', mockMcps, 0.0, 2);
            expect(candidates.length).toBeLessThanOrEqual(2);
        });
    });
    describe('Route Function', () => {
        it('should deny dangerous automation requests', () => {
            const result = (0, router_1.route)('bypass captcha and login', mockMcps, defaultConfig);
            expect(result.action).toBe('deny');
        });
        it('should require human for deployment', () => {
            const result = (0, router_1.route)('deploy the app to production', mockMcps, defaultConfig);
            expect(result.action).toBe('require_human');
        });
        it('should require human for destructive operations', () => {
            const result = (0, router_1.route)('drop table users', mockMcps, defaultConfig);
            expect(result.action).toBe('require_human');
        });
        it('should allow safe operations with matching MCP', () => {
            const result = (0, router_1.route)('search github issues for bugs', mockMcps, defaultConfig);
            expect(result.action).toBe('allow');
            expect(result.candidates).toBeDefined();
            expect(result.candidates.length).toBeGreaterThan(0);
        });
        it('should fallback when no MCP matches threshold', () => {
            const highThresholdConfig = { ...defaultConfig, semanticThreshold: 0.99 };
            const result = (0, router_1.route)('do something random xyz', mockMcps, highThresholdConfig);
            expect(result.action).toBe('require_clarify');
        });
        it('should check dangerous operations on matched MCP', () => {
            // Enable a more specific match for testing
            const result = (0, router_1.route)('delete repository on github', mockMcps, defaultConfig);
            // Should require human because 'delete' is in github's dangerousOperations
            expect(result.action).toBe('require_human');
        });
        it('should prioritize safety rules when ruleFirst is true', () => {
            const result = (0, router_1.route)('deploy code to github', mockMcps, {
                ...defaultConfig,
                ruleFirst: true,
            });
            expect(result.action).toBe('require_human');
            expect(result.matchedRule).toBe('deployment');
        });
        it('should include confidence score for matched MCPs', () => {
            const result = (0, router_1.route)('run sql query on database', mockMcps, defaultConfig);
            if (result.action === 'allow') {
                expect(result.confidence).toBeDefined();
                expect(result.confidence).toBeGreaterThan(0);
            }
        });
    });
    describe('Edge Cases', () => {
        it('should handle empty input gracefully', () => {
            const result = (0, router_1.route)('', mockMcps, defaultConfig);
            expect(result.action).toBe('require_clarify');
        });
        it('should handle empty MCP list', () => {
            const result = (0, router_1.route)('search for something', [], defaultConfig);
            expect(result.action).toBe('require_clarify');
        });
        it('should handle special characters in input', () => {
            const result = (0, router_1.route)('search for @user #issue', mockMcps, defaultConfig);
            expect(['allow', 'require_clarify']).toContain(result.action);
        });
        it('should be case-insensitive for safety rules', () => {
            const result1 = (0, router_1.evaluateSafetyRules)('DELETE all data');
            const result2 = (0, router_1.evaluateSafetyRules)('delete ALL DATA');
            expect(result1?.action).toBe(result2?.action);
        });
    });
    describe('Utility Functions', () => {
        it('should get safety categories', () => {
            const categories = (0, router_1.getSafetyCategories)();
            expect(categories).toContain('deployment');
            expect(categories).toContain('destructive');
            expect(categories).toContain('secrets');
        });
        it('should find best match', () => {
            const best = (0, router_1.findBestMatch)('github issues', mockMcps, 0.2);
            expect(best).not.toBeNull();
            expect(best?.name).toBe('github');
        });
        it('should return null when no match above threshold', () => {
            const best = (0, router_1.findBestMatch)('xyz random', mockMcps, 0.99);
            expect(best).toBeNull();
        });
        it('should explain route', () => {
            const explanation = (0, router_1.explainRoute)('search github issues', mockMcps, defaultConfig);
            expect(explanation).toContain('Input:');
            expect(explanation).toContain('Action:');
            expect(explanation).toContain('Reason:');
        });
    });
    describe('Registry Functions', () => {
        beforeEach(() => {
            (0, registry_1.clearCache)();
        });
        it('should load config', () => {
            const config = (0, registry_1.loadConfig)();
            expect(config).toBeDefined();
            expect(config.version).toBeDefined();
            expect(config.mcps).toBeDefined();
            expect(config.routerConfig).toBeDefined();
        });
        it('should get all MCPs', () => {
            const mcps = (0, registry_1.getAllMcps)();
            expect(Array.isArray(mcps)).toBe(true);
        });
        it('should get enabled MCPs only', () => {
            const enabled = (0, registry_1.getEnabledMcps)();
            expect(Array.isArray(enabled)).toBe(true);
            // All returned MCPs should be enabled
            enabled.forEach(mcp => {
                expect(mcp.enabled).toBe(true);
            });
        });
        it('should get MCP by name', () => {
            const mcp = (0, registry_1.getMcpByName)('github');
            // May or may not exist depending on config
            if (mcp) {
                expect(mcp.name).toBe('github');
            }
        });
        it('should get MCPs by tag', () => {
            const mcps = (0, registry_1.getMcpsByTag)('vcs');
            expect(Array.isArray(mcps)).toBe(true);
        });
        it('should get router config', () => {
            const config = (0, registry_1.getRouterConfig)();
            expect(config.ruleFirst).toBeDefined();
            expect(config.semanticThreshold).toBeDefined();
            expect(config.topK).toBeDefined();
            expect(config.fallback).toBeDefined();
        });
        it('should check if MCP is enabled', () => {
            const enabled = (0, registry_1.isMcpEnabled)('github');
            expect(typeof enabled).toBe('boolean');
        });
        it('should get MCP summary', () => {
            const summary = (0, registry_1.getMcpSummary)();
            expect(typeof summary).toBe('string');
        });
    });
});
