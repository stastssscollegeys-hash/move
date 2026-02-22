"use strict";
/**
 * Context Budget Monitor Tests
 */
Object.defineProperty(exports, "__esModule", { value: true });
const context_budget_1 = require("../../src/proxy-mcp/observability/context-budget");
describe('Context Budget Monitor', () => {
    beforeEach(() => {
        (0, context_budget_1.resetContextBudget)();
    });
    describe('initContextBudget', () => {
        it('should initialize with default model', () => {
            const session = (0, context_budget_1.initContextBudget)('test-session-1');
            expect(session.sessionId).toBe('test-session-1');
            expect(session.modelId).toBe('default');
            expect(session.contextLimit).toBe(context_budget_1.CONTEXT_LIMITS.default);
            expect(session.estimatedUsed).toBeGreaterThan(0);
            expect(session.level).toBe('ok');
            expect(session.operationCount).toBe(0);
        });
        it('should initialize with specific model', () => {
            const session = (0, context_budget_1.initContextBudget)('test-session-2', 'claude_opus_4_5');
            expect(session.modelId).toBe('claude_opus_4_5');
            expect(session.contextLimit).toBe(context_budget_1.CONTEXT_LIMITS.claude_opus_4_5);
        });
        it('should include system overhead in initial usage', () => {
            const session = (0, context_budget_1.initContextBudget)('test-session-3');
            const expectedOverhead = context_budget_1.OPERATION_TOKEN_ESTIMATES.system_prompt +
                context_budget_1.OPERATION_TOKEN_ESTIMATES.tool_definition * 30 +
                context_budget_1.OPERATION_TOKEN_ESTIMATES.mcp_server_overhead * 10;
            expect(session.estimatedUsed).toBe(expectedOverhead);
            expect(session.history.length).toBe(1);
            expect(session.history[0].description).toContain('System initialization');
        });
    });
    describe('recordContextUsage', () => {
        it('should record standard operation types', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            const initialUsage = (0, context_budget_1.getContextBudget)().estimatedUsed;
            (0, context_budget_1.recordContextUsage)('file_read_medium');
            const state = (0, context_budget_1.getContextBudget)();
            expect(state.estimatedUsed).toBe(initialUsage + context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_medium);
            expect(state.operationCount).toBe(1);
        });
        it('should record custom token amounts', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            const initialUsage = (0, context_budget_1.getContextBudget)().estimatedUsed;
            (0, context_budget_1.recordContextUsage)('custom', 5000, 'Large API response');
            const state = (0, context_budget_1.getContextBudget)();
            expect(state.estimatedUsed).toBe(initialUsage + 5000);
        });
        it('should auto-initialize session if not exists', () => {
            expect((0, context_budget_1.getContextBudget)()).toBeNull();
            (0, context_budget_1.recordContextUsage)('bash_simple');
            expect((0, context_budget_1.getContextBudget)()).not.toBeNull();
        });
        it('should return warning when threshold exceeded', () => {
            const session = (0, context_budget_1.initContextBudget)('test-session');
            // Use 85% of context
            const tokensToUse = session.contextLimit * 0.85 - session.estimatedUsed;
            const warning = (0, context_budget_1.recordContextUsage)('custom', tokensToUse, 'Large operation');
            expect(warning).not.toBeNull();
            expect(warning.level).toBe('warning');
            expect(warning.recommendations.length).toBeGreaterThan(0);
        });
        it('should return null when under threshold', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            const warning = (0, context_budget_1.recordContextUsage)('file_read_small');
            expect(warning).toBeNull();
        });
    });
    describe('estimateTokens', () => {
        it('should estimate tokens from string content', () => {
            const content = 'Hello world'; // 11 characters
            const tokens = (0, context_budget_1.estimateTokens)(content);
            // ~4 chars per token = ~3 tokens
            expect(tokens).toBeGreaterThanOrEqual(2);
            expect(tokens).toBeLessThanOrEqual(4);
        });
        it('should handle empty string', () => {
            expect((0, context_budget_1.estimateTokens)('')).toBe(0);
        });
        it('should handle large content', () => {
            const content = 'x'.repeat(10000);
            const tokens = (0, context_budget_1.estimateTokens)(content);
            // 10000 chars * 0.25 = 2500 tokens
            expect(tokens).toBe(2500);
        });
    });
    describe('estimateFileReadTokens', () => {
        it('should return small estimate for < 100 lines', () => {
            expect((0, context_budget_1.estimateFileReadTokens)(50)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_small);
            expect((0, context_budget_1.estimateFileReadTokens)(99)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_small);
        });
        it('should return medium estimate for 100-499 lines', () => {
            expect((0, context_budget_1.estimateFileReadTokens)(100)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_medium);
            expect((0, context_budget_1.estimateFileReadTokens)(499)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_medium);
        });
        it('should return large estimate for 500-1999 lines', () => {
            expect((0, context_budget_1.estimateFileReadTokens)(500)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_large);
            expect((0, context_budget_1.estimateFileReadTokens)(1999)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_large);
        });
        it('should return huge estimate for >= 2000 lines', () => {
            expect((0, context_budget_1.estimateFileReadTokens)(2000)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_huge);
            expect((0, context_budget_1.estimateFileReadTokens)(10000)).toBe(context_budget_1.OPERATION_TOKEN_ESTIMATES.file_read_huge);
        });
    });
    describe('getBudgetLevel', () => {
        it('should return ok for < 60%', () => {
            expect((0, context_budget_1.getBudgetLevel)(0.0)).toBe('ok');
            expect((0, context_budget_1.getBudgetLevel)(0.5)).toBe('ok');
            expect((0, context_budget_1.getBudgetLevel)(0.59)).toBe('ok');
        });
        it('should return info for 60-79%', () => {
            expect((0, context_budget_1.getBudgetLevel)(0.60)).toBe('info');
            expect((0, context_budget_1.getBudgetLevel)(0.70)).toBe('info');
            expect((0, context_budget_1.getBudgetLevel)(0.79)).toBe('info');
        });
        it('should return warning for 80-89%', () => {
            expect((0, context_budget_1.getBudgetLevel)(0.80)).toBe('warning');
            expect((0, context_budget_1.getBudgetLevel)(0.85)).toBe('warning');
            expect((0, context_budget_1.getBudgetLevel)(0.89)).toBe('warning');
        });
        it('should return critical for 90-94%', () => {
            expect((0, context_budget_1.getBudgetLevel)(0.90)).toBe('critical');
            expect((0, context_budget_1.getBudgetLevel)(0.92)).toBe('critical');
            expect((0, context_budget_1.getBudgetLevel)(0.94)).toBe('critical');
        });
        it('should return emergency for >= 95%', () => {
            expect((0, context_budget_1.getBudgetLevel)(0.95)).toBe('emergency');
            expect((0, context_budget_1.getBudgetLevel)(0.99)).toBe('emergency');
            expect((0, context_budget_1.getBudgetLevel)(1.0)).toBe('emergency');
        });
    });
    describe('getBudgetSummary', () => {
        it('should return message when no session', () => {
            const summary = (0, context_budget_1.getBudgetSummary)();
            expect(summary).toContain('No active context budget session');
        });
        it('should return formatted summary', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            const summary = (0, context_budget_1.getBudgetSummary)();
            expect(summary).toMatch(/🟢/); // ok level
            expect(summary).toContain('Context:');
            expect(summary).toContain('% used');
            expect(summary).toContain('remaining');
            expect(summary).toContain('operations');
        });
        it('should show correct level indicator', () => {
            const session = (0, context_budget_1.initContextBudget)('test-session');
            // Push to warning level
            const tokensToUse = session.contextLimit * 0.85 - session.estimatedUsed;
            (0, context_budget_1.recordContextUsage)('custom', tokensToUse);
            const summary = (0, context_budget_1.getBudgetSummary)();
            expect(summary).toMatch(/🟡/); // warning level
        });
    });
    describe('simulateCompaction', () => {
        it('should reduce usage by specified percentage', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            (0, context_budget_1.recordContextUsage)('custom', 100000); // Add significant usage
            const beforeState = (0, context_budget_1.getContextBudget)();
            const beforeUsed = beforeState.estimatedUsed;
            (0, context_budget_1.simulateCompaction)(50);
            const afterState = (0, context_budget_1.getContextBudget)();
            expect(afterState.estimatedUsed).toBe(beforeUsed * 0.5);
        });
        it('should update remaining and percentage', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            (0, context_budget_1.recordContextUsage)('custom', 100000);
            (0, context_budget_1.simulateCompaction)(50);
            const state = (0, context_budget_1.getContextBudget)();
            expect(state.estimatedRemaining).toBe(state.contextLimit - state.estimatedUsed);
            expect(state.usagePercent).toBe(state.estimatedUsed / state.contextLimit);
        });
        it('should add compaction to history', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            (0, context_budget_1.recordContextUsage)('custom', 50000);
            (0, context_budget_1.simulateCompaction)(40);
            const state = (0, context_budget_1.getContextBudget)();
            const lastHistory = state.history[state.history.length - 1];
            expect(lastHistory.description).toContain('Compaction');
            expect(lastHistory.estimatedTokens).toBeLessThan(0);
        });
    });
    describe('getTopConsumers', () => {
        it('should return empty array when no session', () => {
            expect((0, context_budget_1.getTopConsumers)()).toEqual([]);
        });
        it('should return top consumers sorted by total tokens', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            // Add various operations
            (0, context_budget_1.recordContextUsage)('file_read_large');
            (0, context_budget_1.recordContextUsage)('file_read_large');
            (0, context_budget_1.recordContextUsage)('file_read_small');
            (0, context_budget_1.recordContextUsage)('bash_simple');
            (0, context_budget_1.recordContextUsage)('bash_simple');
            (0, context_budget_1.recordContextUsage)('bash_simple');
            const consumers = (0, context_budget_1.getTopConsumers)(3);
            expect(consumers.length).toBeGreaterThan(0);
            // file_read_large should be at top (2 * 8000 = 16000)
            expect(consumers[0].type).toBe('file_read_large');
            expect(consumers[0].count).toBe(2);
        });
        it('should limit results', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            // Add many different operation types
            (0, context_budget_1.recordContextUsage)('file_read_small');
            (0, context_budget_1.recordContextUsage)('file_read_medium');
            (0, context_budget_1.recordContextUsage)('file_read_large');
            (0, context_budget_1.recordContextUsage)('bash_simple');
            (0, context_budget_1.recordContextUsage)('bash_medium');
            const consumers = (0, context_budget_1.getTopConsumers)(2);
            expect(consumers.length).toBeLessThanOrEqual(2);
        });
    });
    describe('withContextTracking', () => {
        it('should execute operation and track usage', async () => {
            (0, context_budget_1.initContextBudget)('test-session');
            const { result, warning } = await (0, context_budget_1.withContextTracking)('bash_simple', async () => 'test result');
            expect(result).toBe('test result');
            expect(warning).toBeNull();
            expect((0, context_budget_1.getContextBudget)().operationCount).toBe(1);
        });
        it('should propagate errors', async () => {
            (0, context_budget_1.initContextBudget)('test-session');
            await expect((0, context_budget_1.withContextTracking)('bash_simple', async () => {
                throw new Error('Test error');
            })).rejects.toThrow('Test error');
        });
    });
    describe('threshold constants', () => {
        it('should have correct threshold values', () => {
            expect(context_budget_1.BUDGET_THRESHOLDS.info).toBe(0.60);
            expect(context_budget_1.BUDGET_THRESHOLDS.warning).toBe(0.80);
            expect(context_budget_1.BUDGET_THRESHOLDS.critical).toBe(0.90);
            expect(context_budget_1.BUDGET_THRESHOLDS.emergency).toBe(0.95);
        });
    });
    describe('context limits', () => {
        it('should have reasonable context limits', () => {
            expect(context_budget_1.CONTEXT_LIMITS.default).toBeGreaterThanOrEqual(100000);
            expect(context_budget_1.CONTEXT_LIMITS.claude_opus_4_5).toBeGreaterThanOrEqual(100000);
        });
    });
    describe('history management', () => {
        it('should trim history when exceeding limit', () => {
            (0, context_budget_1.initContextBudget)('test-session');
            // Add many operations (more than MAX_HISTORY_ENTRIES = 100)
            for (let i = 0; i < 150; i++) {
                (0, context_budget_1.recordContextUsage)('bash_simple');
            }
            const state = (0, context_budget_1.getContextBudget)();
            expect(state.history.length).toBeLessThanOrEqual(100);
        });
    });
});
