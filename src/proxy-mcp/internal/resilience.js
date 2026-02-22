"use strict";
/**
 * Resilience Module - Timeout, Retry, and Circuit Breaker Integration
 *
 * Provides fault-tolerant execution for internal MCP calls
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getResilienceConfig = exports.executeWithResilience = exports.withRetry = exports.withTimeout = exports.ResilienceError = exports.DEFAULT_RESILIENCE_CONFIG = void 0;
const circuit_breaker_1 = require("./circuit-breaker");
const observability_1 = require("../observability");
exports.DEFAULT_RESILIENCE_CONFIG = {
    timeout: {
        spawnMs: 5000,
        toolCallMs: 15000,
    },
    retry: {
        maxAttempts: 2,
        backoffMs: 250,
        jitter: true,
    },
    circuit: circuit_breaker_1.DEFAULT_CIRCUIT_CONFIG,
};
/**
 * Error class for resilience failures
 */
class ResilienceError extends Error {
    constructor(message, type, mcpName, attempts = 0) {
        super(message);
        this.type = type;
        this.mcpName = mcpName;
        this.attempts = attempts;
        this.name = 'ResilienceError';
    }
}
exports.ResilienceError = ResilienceError;
/**
 * Calculate delay with optional jitter
 */
function calculateDelay(baseMs, attempt, jitter) {
    // Exponential backoff
    const delay = baseMs * Math.pow(2, attempt);
    if (jitter) {
        // Add random jitter (0-50% of delay)
        return delay + Math.random() * delay * 0.5;
    }
    return delay;
}
/**
 * Create a timeout promise
 */
function createTimeout(ms, message) {
    return new Promise((_, reject) => {
        setTimeout(() => reject(new Error(message)), ms);
    });
}
/**
 * Execute a function with timeout
 */
async function withTimeout(fn, timeoutMs, label = 'operation') {
    return Promise.race([fn(), createTimeout(timeoutMs, `${label} timed out after ${timeoutMs}ms`)]);
}
exports.withTimeout = withTimeout;
/**
 * Execute a function with retry logic
 */
async function withRetry(fn, config, mcpName) {
    let lastError;
    for (let attempt = 0; attempt < config.maxAttempts; attempt++) {
        try {
            return await fn();
        }
        catch (error) {
            lastError = error instanceof Error ? error : new Error(String(error));
            if (attempt < config.maxAttempts - 1) {
                const delay = calculateDelay(config.backoffMs, attempt, config.jitter);
                await new Promise((resolve) => setTimeout(resolve, delay));
                (0, observability_1.recordEvent)('internal_mcp_tool_call', mcpName, 'ok', {
                    metadata: { retry: true, attempt: attempt + 1 },
                });
            }
        }
    }
    throw new ResilienceError(`Max retries (${config.maxAttempts}) exceeded: ${lastError?.message}`, 'max_retries', mcpName, config.maxAttempts);
}
exports.withRetry = withRetry;
/**
 * Execute an internal MCP call with full resilience (timeout, retry, circuit breaker)
 */
async function executeWithResilience(mcpName, runId, fn, config = exports.DEFAULT_RESILIENCE_CONFIG) {
    const endTimer = (0, observability_1.startTimer)('internal_mcp_tool_call', runId, { mcpName });
    // Check circuit breaker first
    if (!(0, circuit_breaker_1.isCallAllowed)(mcpName, config.circuit)) {
        endTimer('fail', { errorType: 'circuit_open' });
        throw new ResilienceError(`Circuit breaker is open for ${mcpName}`, 'circuit_open', mcpName);
    }
    try {
        // Execute with timeout and retry
        const result = await withRetry(() => withTimeout(fn, config.timeout.toolCallMs, `${mcpName} call`), config.retry, mcpName);
        // Record success
        (0, circuit_breaker_1.recordSuccess)(mcpName, config.circuit);
        endTimer('ok');
        return result;
    }
    catch (error) {
        // Record failure
        (0, circuit_breaker_1.recordFailure)(mcpName, config.circuit);
        const errorMessage = error instanceof Error ? error.message : String(error);
        const errorType = error instanceof ResilienceError ? error.type : 'execution';
        endTimer('fail', { errorType, errorMessage });
        if (error instanceof ResilienceError) {
            throw error;
        }
        throw new ResilienceError(errorMessage, errorType, mcpName);
    }
}
exports.executeWithResilience = executeWithResilience;
/**
 * Get resilience config for a specific MCP (can be overridden in internal-mcps.json)
 */
function getResilienceConfig(mcpConfig) {
    if (!mcpConfig?.resilience) {
        return exports.DEFAULT_RESILIENCE_CONFIG;
    }
    return {
        timeout: {
            ...exports.DEFAULT_RESILIENCE_CONFIG.timeout,
            ...mcpConfig.resilience.timeout,
        },
        retry: {
            ...exports.DEFAULT_RESILIENCE_CONFIG.retry,
            ...mcpConfig.resilience.retry,
        },
        circuit: {
            ...exports.DEFAULT_RESILIENCE_CONFIG.circuit,
            ...mcpConfig.resilience.circuit,
        },
    };
}
exports.getResilienceConfig = getResilienceConfig;
