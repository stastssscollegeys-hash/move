"use strict";
/**
 * Internal MCP Registry - Manages internal MCP definitions
 *
 * P6 Update: Uses overlay system for production enablement
 * Priority: overlay > local > base
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
exports.getRolloutSummary = exports.getRolloutStatus = exports.isMcpEnabledForRun = exports.getMcpSummary = exports.isMcpEnabled = exports.getRouterConfig = exports.getMcpsByTag = exports.getMcpByName = exports.getEnabledMcps = exports.getAllMcps = exports.clearCache = exports.loadConfig = void 0;
const path = __importStar(require("path"));
const overlay_1 = require("./overlay");
const rollout_1 = require("./rollout");
const CONFIG_PATH = path.join(process.cwd(), 'config', 'proxy-mcp', 'internal-mcps.json');
let cachedConfig = null;
/**
 * Load internal MCPs config from file (uses overlay system)
 */
function loadConfig(_configPath = CONFIG_PATH) {
    if (cachedConfig) {
        return cachedConfig;
    }
    try {
        // Use overlay system for merged configuration
        const baseConfig = (0, overlay_1.loadBaseConfig)();
        const mergedMcps = (0, overlay_1.loadMergedConfig)();
        cachedConfig = {
            ...baseConfig,
            mcps: mergedMcps,
        };
        return cachedConfig;
    }
    catch (error) {
        console.error('[registry] Failed to load internal MCPs config:', error);
        return {
            version: '1.0.0',
            mcps: [],
            routerConfig: {
                ruleFirst: true,
                semanticThreshold: 0.7,
                topK: 5,
                fallback: 'require_clarify',
            },
        };
    }
}
exports.loadConfig = loadConfig;
/**
 * Clear cached config (for testing)
 */
function clearCache() {
    cachedConfig = null;
}
exports.clearCache = clearCache;
/**
 * Get all registered MCPs
 */
function getAllMcps() {
    const config = loadConfig();
    return config.mcps;
}
exports.getAllMcps = getAllMcps;
/**
 * Get enabled MCPs only
 */
function getEnabledMcps() {
    return getAllMcps().filter((mcp) => mcp.enabled);
}
exports.getEnabledMcps = getEnabledMcps;
/**
 * Get MCP by name
 */
function getMcpByName(name) {
    return getAllMcps().find((mcp) => mcp.name === name);
}
exports.getMcpByName = getMcpByName;
/**
 * Get MCPs by tag
 */
function getMcpsByTag(tag) {
    const tagLower = tag.toLowerCase();
    return getAllMcps().filter((mcp) => mcp.tags.some((t) => t.toLowerCase() === tagLower));
}
exports.getMcpsByTag = getMcpsByTag;
/**
 * Get router config
 */
function getRouterConfig() {
    const config = loadConfig();
    return config.routerConfig;
}
exports.getRouterConfig = getRouterConfig;
/**
 * Check if an MCP is enabled
 */
function isMcpEnabled(name) {
    const mcp = getMcpByName(name);
    return mcp?.enabled ?? false;
}
exports.isMcpEnabled = isMcpEnabled;
/**
 * Get MCP summary (for Claude context)
 */
function getMcpSummary() {
    const mcps = getAllMcps();
    if (mcps.length === 0) {
        return 'No internal MCPs registered.';
    }
    const lines = ['Available internal MCPs:'];
    for (const mcp of mcps) {
        const status = mcp.enabled ? 'enabled' : 'disabled';
        const rollout = (0, rollout_1.formatRolloutStatus)(mcp.name);
        lines.push(`  - ${mcp.name} [${status}] (${rollout}): ${mcp.shortDescription}`);
    }
    return lines.join('\n');
}
exports.getMcpSummary = getMcpSummary;
/**
 * Check if an MCP is enabled for a specific runId (considers rollout)
 */
function isMcpEnabledForRun(name, runId) {
    const mcp = getMcpByName(name);
    if (!mcp?.enabled) {
        return false;
    }
    // Check rollout status
    return (0, rollout_1.isRolloutEnabled)(name, runId);
}
exports.isMcpEnabledForRun = isMcpEnabledForRun;
/**
 * Get rollout status for all MCPs
 */
function getRolloutStatus() {
    const mcps = getAllMcps();
    return mcps.map((mcp) => ({
        name: mcp.name,
        enabled: mcp.enabled,
        rollout: (0, rollout_1.formatRolloutStatus)(mcp.name),
        rolloutConfig: (0, overlay_1.getRolloutConfig)(mcp.name),
    }));
}
exports.getRolloutStatus = getRolloutStatus;
/**
 * Get rollout summary for system_health
 */
function getRolloutSummary() {
    const mcps = getAllMcps();
    let enabled = 0;
    let canary = 0;
    let full = 0;
    let off = 0;
    const mcpStatuses = [];
    // Check if overlay is active
    const overlayPath = process.env.TAISUN_INTERNAL_MCPS_OVERLAY_PATH;
    const overlayActive = !!overlayPath;
    for (const mcp of mcps) {
        if (!mcp.enabled) {
            off++;
            mcpStatuses.push({ name: mcp.name, mode: 'off' });
            continue;
        }
        enabled++;
        const rollout = (0, overlay_1.getRolloutConfig)(mcp.name);
        if (!rollout || rollout.mode === 'full') {
            full++;
            mcpStatuses.push({ name: mcp.name, mode: 'full' });
        }
        else if (rollout.mode === 'canary') {
            canary++;
            mcpStatuses.push({ name: mcp.name, mode: 'canary', canaryPercent: rollout.canaryPercent });
        }
        else {
            off++;
            mcpStatuses.push({ name: mcp.name, mode: 'off' });
        }
    }
    return { total: mcps.length, enabled, canary, full, off, overlayActive, mcps: mcpStatuses };
}
exports.getRolloutSummary = getRolloutSummary;
