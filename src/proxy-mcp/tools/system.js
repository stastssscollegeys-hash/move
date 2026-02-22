"use strict";
/**
 * System Tools - Health check and system status
 *
 * P6: Enhanced with circuit breaker, rollout status, and recommendations
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.systemHealth = void 0;
const observability_1 = require("../observability");
const registry_1 = require("../internal/registry");
const circuit_breaker_1 = require("../internal/circuit-breaker");
const startTime = Date.now();
function systemHealth() {
    const uptime = Date.now() - startTime;
    // Get MCP status
    const allMcps = (0, registry_1.getAllMcps)();
    const enabledMcps = (0, registry_1.getEnabledMcps)();
    // Get rollout status
    const rolloutSummary = (0, registry_1.getRolloutSummary)();
    // Get circuit breaker status
    const circuitSummary = (0, circuit_breaker_1.getCircuitSummary)();
    const circuitStates = (0, circuit_breaker_1.getAllCircuitStates)();
    // Get observability metrics
    let metrics;
    try {
        metrics = (0, observability_1.getRecentEventsSummary)(100);
    }
    catch {
        metrics = null;
    }
    // Get recommendations from recent report
    let recommendations = [];
    try {
        const period = (0, observability_1.getLast24hPeriod)();
        const report = (0, observability_1.generateReport)(period);
        recommendations = report.recommendations;
    }
    catch {
        // Ignore report generation errors
    }
    // Determine overall health status
    let status = 'healthy';
    const issues = [];
    // Check circuit breaker status
    if (circuitSummary.open > 0) {
        status = 'degraded';
        issues.push(`${circuitSummary.open} MCP(s) circuit open`);
    }
    // Check success rate (only if there are events to evaluate)
    const totalEvents = metrics?.last24h?.successCount + metrics?.last24h?.failureCount || 0;
    if (totalEvents > 0) {
        if (metrics && metrics.last24h.successRate < 0.9) {
            status = 'unhealthy';
            issues.push(`Low success rate: ${Math.round(metrics.last24h.successRate * 100)}%`);
        }
        else if (metrics && metrics.last24h.successRate < 0.95) {
            if (status === 'healthy')
                status = 'degraded';
            issues.push(`Warning: success rate ${Math.round(metrics.last24h.successRate * 100)}%`);
        }
    }
    // Note: No events (cold start) is not considered unhealthy
    // Build per-MCP status
    const mcpStatus = enabledMcps.map((mcp) => {
        const circuitState = circuitStates.get(mcp.name) || 'closed';
        const rollout = rolloutSummary.mcps.find((r) => r.name === mcp.name);
        return {
            name: mcp.name,
            enabled: true,
            circuit: circuitState,
            rollout: rollout?.mode || 'full',
            canaryPercent: rollout?.canaryPercent,
        };
    });
    return {
        success: true,
        data: {
            status,
            issues: issues.length > 0 ? issues : undefined,
            uptime,
            version: '0.2.0',
            timestamp: new Date().toISOString(),
            mcps: {
                total: allMcps.length,
                enabled: enabledMcps.length,
                status: mcpStatus,
            },
            circuits: {
                total: circuitSummary.total,
                closed: circuitSummary.closed,
                open: circuitSummary.open,
                halfOpen: circuitSummary.halfOpen,
            },
            rollout: {
                overlayActive: rolloutSummary.overlayActive,
                mcps: rolloutSummary.mcps,
            },
            metrics: metrics
                ? {
                    totalEvents: metrics.total,
                    last24h: {
                        success: metrics.last24h.successCount,
                        failure: metrics.last24h.failureCount,
                        successRate: Math.round(metrics.last24h.successRate * 100) + '%',
                        avgDurationMs: metrics.last24h.avgDurationMs,
                    },
                    topErrors: metrics.topErrors,
                }
                : null,
            recommendations: recommendations.length > 0 ? recommendations : undefined,
        },
    };
}
exports.systemHealth = systemHealth;
