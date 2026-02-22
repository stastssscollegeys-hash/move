"use strict";
/**
 * Circuit Breaker Unit Tests - P6
 */
Object.defineProperty(exports, "__esModule", { value: true });
const circuit_breaker_1 = require("../../src/proxy-mcp/internal/circuit-breaker");
describe('Circuit Breaker', () => {
    beforeEach(() => {
        (0, circuit_breaker_1.resetAllCircuits)();
    });
    describe('initial state', () => {
        it('should start in closed state', () => {
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('closed');
        });
        it('should allow calls in closed state', () => {
            expect((0, circuit_breaker_1.isCallAllowed)('test-mcp')).toBe(true);
        });
    });
    describe('state transitions', () => {
        it('should transition to open after failure threshold', () => {
            const config = { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, failureThreshold: 3 };
            // Record 3 failures
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('closed');
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('open');
        });
        it('should block calls in open state', () => {
            const config = { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, failureThreshold: 1 };
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('open');
            expect((0, circuit_breaker_1.isCallAllowed)('test-mcp', config)).toBe(false);
        });
        it('should reset failure count on success', () => {
            const config = { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, failureThreshold: 3 };
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            (0, circuit_breaker_1.recordSuccess)('test-mcp', config);
            // One more failure should not open circuit (counter was reset)
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('closed');
        });
    });
    describe('half-open state', () => {
        it('should transition to half-open after cooldown', async () => {
            const config = {
                ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG,
                failureThreshold: 1,
                cooldownMs: 10, // Short cooldown for test
            };
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('open');
            // Wait for cooldown
            await new Promise((resolve) => setTimeout(resolve, 20));
            // Check should transition to half-open
            expect((0, circuit_breaker_1.isCallAllowed)('test-mcp', config)).toBe(true);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('half-open');
        });
        it('should close after successful calls in half-open', async () => {
            const config = {
                ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG,
                failureThreshold: 1,
                cooldownMs: 10,
                successThreshold: 2,
            };
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            await new Promise((resolve) => setTimeout(resolve, 20));
            // Transition to half-open
            (0, circuit_breaker_1.isCallAllowed)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('half-open');
            // Record successes
            (0, circuit_breaker_1.recordSuccess)('test-mcp', config);
            (0, circuit_breaker_1.recordSuccess)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('closed');
        });
        it('should reopen on failure in half-open', async () => {
            const config = {
                ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG,
                failureThreshold: 1,
                cooldownMs: 10,
            };
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            await new Promise((resolve) => setTimeout(resolve, 20));
            // Transition to half-open
            (0, circuit_breaker_1.isCallAllowed)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('half-open');
            // Failure in half-open should reopen
            (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('open');
        });
    });
    describe('disabled circuit', () => {
        it('should always allow calls when disabled', () => {
            const config = { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, enabled: false };
            // Record many failures
            for (let i = 0; i < 10; i++) {
                (0, circuit_breaker_1.recordFailure)('test-mcp', config);
            }
            expect((0, circuit_breaker_1.isCallAllowed)('test-mcp', config)).toBe(true);
        });
    });
    describe('circuit summary', () => {
        it('should return correct summary', () => {
            const config = { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, failureThreshold: 1 };
            // Create circuits in different states
            (0, circuit_breaker_1.isCallAllowed)('mcp-1'); // closed
            (0, circuit_breaker_1.isCallAllowed)('mcp-2'); // closed
            (0, circuit_breaker_1.recordFailure)('mcp-3', config);
            const summary = (0, circuit_breaker_1.getCircuitSummary)();
            expect(summary.total).toBe(3);
            expect(summary.closed).toBe(2);
            expect(summary.open).toBe(1);
            expect(summary.halfOpen).toBe(0);
        });
    });
    describe('reset', () => {
        it('should reset individual circuit', () => {
            (0, circuit_breaker_1.recordFailure)('test-mcp', { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, failureThreshold: 1 });
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('open');
            (0, circuit_breaker_1.resetCircuit)('test-mcp');
            expect((0, circuit_breaker_1.getCircuitState)('test-mcp')).toBe('closed');
        });
        it('should reset all circuits', () => {
            const config = { ...circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG, failureThreshold: 1 };
            (0, circuit_breaker_1.recordFailure)('mcp-1', config);
            (0, circuit_breaker_1.recordFailure)('mcp-2', config);
            (0, circuit_breaker_1.resetAllCircuits)();
            expect((0, circuit_breaker_1.getCircuitSummary)().total).toBe(0);
        });
    });
});
