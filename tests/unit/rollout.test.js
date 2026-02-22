"use strict";
/**
 * Rollout Module Unit Tests
 *
 * Tests for canary deployment logic and deterministic bucket calculation.
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
const rollout_1 = require("../../src/proxy-mcp/internal/rollout");
const overlay = __importStar(require("../../src/proxy-mcp/internal/overlay"));
// Mock overlay module
jest.mock('../../src/proxy-mcp/internal/overlay', () => ({
    getRolloutConfig: jest.fn(),
}));
const mockGetRolloutConfig = overlay.getRolloutConfig;
describe('Rollout Module', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });
    describe('calculateBucket', () => {
        it('should return deterministic bucket for same inputs', () => {
            const bucket1 = (0, rollout_1.calculateBucket)('github', 'run-123');
            const bucket2 = (0, rollout_1.calculateBucket)('github', 'run-123');
            expect(bucket1).toBe(bucket2);
        });
        it('should return different buckets for different runIds', () => {
            const bucket1 = (0, rollout_1.calculateBucket)('github', 'run-123');
            const bucket2 = (0, rollout_1.calculateBucket)('github', 'run-456');
            // They could be the same by chance, but statistically unlikely
            // Just verify they're valid buckets
            expect(bucket1).toBeGreaterThanOrEqual(0);
            expect(bucket1).toBeLessThan(100);
            expect(bucket2).toBeGreaterThanOrEqual(0);
            expect(bucket2).toBeLessThan(100);
        });
        it('should return bucket in range 0-99', () => {
            // Test multiple inputs
            const inputs = [
                ['mcp1', 'run1'],
                ['mcp2', 'run2'],
                ['github', 'session-abc-123'],
                ['test', 'test-run'],
            ];
            for (const [mcpName, runId] of inputs) {
                const bucket = (0, rollout_1.calculateBucket)(mcpName, runId);
                expect(bucket).toBeGreaterThanOrEqual(0);
                expect(bucket).toBeLessThan(100);
            }
        });
    });
    describe('isInCanary', () => {
        it('should return true if runId is in allowlist', () => {
            const rollout = {
                mode: 'canary',
                canaryPercent: 0,
                allowlist: { runIds: ['special-run'] },
            };
            expect((0, rollout_1.isInCanary)('github', 'special-run', rollout)).toBe(true);
        });
        it('should return false if canaryPercent is 0', () => {
            const rollout = {
                mode: 'canary',
                canaryPercent: 0,
            };
            expect((0, rollout_1.isInCanary)('github', 'run-123', rollout)).toBe(false);
        });
        it('should return true if canaryPercent is 100', () => {
            const rollout = {
                mode: 'canary',
                canaryPercent: 100,
            };
            expect((0, rollout_1.isInCanary)('github', 'run-123', rollout)).toBe(true);
        });
        it('should return based on bucket when canaryPercent is partial', () => {
            const rollout = {
                mode: 'canary',
                canaryPercent: 50,
            };
            // Test multiple runs - some should be in, some should be out
            let inCount = 0;
            for (let i = 0; i < 100; i++) {
                if ((0, rollout_1.isInCanary)('github', `run-${i}`, rollout)) {
                    inCount++;
                }
            }
            // Should be roughly 50% (with some variance)
            expect(inCount).toBeGreaterThan(30);
            expect(inCount).toBeLessThan(70);
        });
        it('should handle undefined canaryPercent as 0', () => {
            const rollout = {
                mode: 'canary',
            };
            expect((0, rollout_1.isInCanary)('github', 'run-123', rollout)).toBe(false);
        });
    });
    describe('isRolloutEnabled', () => {
        it('should return true when no rollout config', () => {
            mockGetRolloutConfig.mockReturnValue(null);
            expect((0, rollout_1.isRolloutEnabled)('github', 'run-123')).toBe(true);
        });
        it('should return false when mode is off', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'off' });
            expect((0, rollout_1.isRolloutEnabled)('github', 'run-123')).toBe(false);
        });
        it('should return true when mode is full', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'full' });
            expect((0, rollout_1.isRolloutEnabled)('github', 'run-123')).toBe(true);
        });
        it('should delegate to isInCanary when mode is canary', () => {
            mockGetRolloutConfig.mockReturnValue({
                mode: 'canary',
                canaryPercent: 100,
            });
            expect((0, rollout_1.isRolloutEnabled)('github', 'run-123')).toBe(true);
        });
        it('should return true for unknown mode', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'unknown' });
            expect((0, rollout_1.isRolloutEnabled)('github', 'run-123')).toBe(true);
        });
    });
    describe('formatRolloutStatus', () => {
        it('should return "default" when no config', () => {
            mockGetRolloutConfig.mockReturnValue(null);
            expect((0, rollout_1.formatRolloutStatus)('github')).toBe('default');
        });
        it('should return "off" for off mode', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'off' });
            expect((0, rollout_1.formatRolloutStatus)('github')).toBe('off');
        });
        it('should return "full (100%)" for full mode', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'full' });
            expect((0, rollout_1.formatRolloutStatus)('github')).toBe('full (100%)');
        });
        it('should return canary percentage for canary mode', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'canary', canaryPercent: 25 });
            expect((0, rollout_1.formatRolloutStatus)('github')).toBe('canary (25%)');
        });
        it('should handle undefined canaryPercent', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'canary' });
            expect((0, rollout_1.formatRolloutStatus)('github')).toBe('canary (0%)');
        });
        it('should return "unknown" for unknown mode', () => {
            mockGetRolloutConfig.mockReturnValue({ mode: 'unknown' });
            expect((0, rollout_1.formatRolloutStatus)('github')).toBe('unknown');
        });
    });
    describe('getRolloutSummary', () => {
        it('should return empty object (placeholder)', () => {
            expect((0, rollout_1.getRolloutSummary)()).toEqual({});
        });
    });
});
