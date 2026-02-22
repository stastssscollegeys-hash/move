"use strict";
/**
 * Circuit Breaker Implementation
 *
 * States:
 * - CLOSED: Normal operation, calls go through
 * - OPEN: Failures exceeded threshold, calls fail fast
 * - HALF_OPEN: Testing if service recovered
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.resetAllCircuits = exports.resetCircuit = exports.getCircuitSummary = exports.getAllCircuitStates = exports.getCircuitState = exports.recordFailure = exports.recordSuccess = exports.isCallAllowed = exports.DEFAULT_CIRCUIT_CONFIG = void 0;
const observability_1 = require("../observability");
exports.DEFAULT_CIRCUIT_CONFIG = {
    enabled: true,
    failureThreshold: 5,
    cooldownMs: 60000,
    halfOpenMaxCalls: 2,
    successThreshold: 2,
};
const circuits = new Map();
/**
 * Get or create circuit stats for an MCP
 */
function getCircuitStats(mcpName) {
    let stats = circuits.get(mcpName);
    if (!stats) {
        stats = {
            state: 'closed',
            failures: 0,
            successes: 0,
            lastFailureTime: 0,
            halfOpenCalls: 0,
            halfOpenSuccesses: 0,
        };
        circuits.set(mcpName, stats);
    }
    return stats;
}
/**
 * Check if a call is allowed through the circuit breaker
 */
function isCallAllowed(mcpName, config = exports.DEFAULT_CIRCUIT_CONFIG) {
    if (!config.enabled) {
        return true;
    }
    const stats = getCircuitStats(mcpName);
    switch (stats.state) {
        case 'closed':
            return true;
        case 'open': {
            // Check if cooldown has passed
            const now = Date.now();
            if (now - stats.lastFailureTime >= config.cooldownMs) {
                // Transition to half-open
                stats.state = 'half-open';
                stats.halfOpenCalls = 0;
                stats.halfOpenSuccesses = 0;
                (0, observability_1.recordEvent)('internal_mcp_tool_call', `circuit-${mcpName}`, 'ok', {
                    metadata: { circuit: 'half-open', mcp: mcpName },
                });
                return true;
            }
            return false;
        }
        case 'half-open': {
            // Allow limited calls in half-open state
            if (stats.halfOpenCalls < config.halfOpenMaxCalls) {
                return true;
            }
            return false;
        }
        default:
            return true;
    }
}
exports.isCallAllowed = isCallAllowed;
/**
 * Record a successful call
 */
function recordSuccess(mcpName, config = exports.DEFAULT_CIRCUIT_CONFIG) {
    if (!config.enabled)
        return;
    const stats = getCircuitStats(mcpName);
    switch (stats.state) {
        case 'closed':
            stats.successes++;
            // Reset failure count on success
            stats.failures = 0;
            break;
        case 'half-open':
            stats.halfOpenCalls++;
            stats.halfOpenSuccesses++;
            // Check if we've had enough successes to close
            if (stats.halfOpenSuccesses >= config.successThreshold) {
                stats.state = 'closed';
                stats.failures = 0;
                stats.successes = 0;
                (0, observability_1.recordEvent)('internal_mcp_tool_call', `circuit-${mcpName}`, 'ok', {
                    metadata: { circuit: 'closed', mcp: mcpName },
                });
            }
            break;
        case 'open':
            // Shouldn't happen, but handle it
            break;
    }
}
exports.recordSuccess = recordSuccess;
/**
 * Record a failed call
 */
function recordFailure(mcpName, config = exports.DEFAULT_CIRCUIT_CONFIG) {
    if (!config.enabled)
        return;
    const stats = getCircuitStats(mcpName);
    const now = Date.now();
    switch (stats.state) {
        case 'closed':
            stats.failures++;
            stats.lastFailureTime = now;
            // Check if we've exceeded the threshold
            if (stats.failures >= config.failureThreshold) {
                stats.state = 'open';
                (0, observability_1.recordEvent)('internal_mcp_tool_call', `circuit-${mcpName}`, 'fail', {
                    metadata: { circuit: 'open', mcp: mcpName, failures: stats.failures },
                });
            }
            break;
        case 'half-open':
            // Any failure in half-open goes back to open
            stats.state = 'open';
            stats.lastFailureTime = now;
            stats.halfOpenCalls = 0;
            stats.halfOpenSuccesses = 0;
            (0, observability_1.recordEvent)('internal_mcp_tool_call', `circuit-${mcpName}`, 'fail', {
                metadata: { circuit: 'open', mcp: mcpName, reason: 'half-open failure' },
            });
            break;
        case 'open':
            // Already open, just update last failure time
            stats.lastFailureTime = now;
            break;
    }
}
exports.recordFailure = recordFailure;
/**
 * Get current circuit state
 */
function getCircuitState(mcpName) {
    const stats = getCircuitStats(mcpName);
    return stats.state;
}
exports.getCircuitState = getCircuitState;
/**
 * Get all circuit states for monitoring
 */
function getAllCircuitStates() {
    const result = new Map();
    for (const [name, stats] of circuits.entries()) {
        result.set(name, stats.state);
    }
    return result;
}
exports.getAllCircuitStates = getAllCircuitStates;
/**
 * Get circuit stats summary
 */
function getCircuitSummary() {
    let closed = 0;
    let open = 0;
    let halfOpen = 0;
    for (const stats of circuits.values()) {
        switch (stats.state) {
            case 'closed':
                closed++;
                break;
            case 'open':
                open++;
                break;
            case 'half-open':
                halfOpen++;
                break;
        }
    }
    return {
        total: circuits.size,
        closed,
        open,
        halfOpen,
    };
}
exports.getCircuitSummary = getCircuitSummary;
/**
 * Reset circuit breaker (for testing)
 */
function resetCircuit(mcpName) {
    circuits.delete(mcpName);
}
exports.resetCircuit = resetCircuit;
/**
 * Reset all circuits (for testing)
 */
function resetAllCircuits() {
    circuits.clear();
}
exports.resetAllCircuits = resetAllCircuits;
