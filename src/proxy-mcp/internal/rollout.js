"use strict";
/**
 * Rollout Logic for Canary Deployments
 *
 * Deterministic canary selection based on runId + mcpName hash
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
exports.formatRolloutStatus = exports.getRolloutSummary = exports.calculateBucket = exports.isInCanary = exports.isRolloutEnabled = void 0;
const crypto = __importStar(require("crypto"));
const overlay_1 = require("./overlay");
/**
 * Check if an MCP is enabled for a given runId based on rollout config
 *
 * @param mcpName - Name of the internal MCP
 * @param runId - Run ID for deterministic canary selection
 * @returns true if the MCP should be enabled for this runId
 */
function isRolloutEnabled(mcpName, runId) {
    const rollout = (0, overlay_1.getRolloutConfig)(mcpName);
    // No rollout config = use base enabled state
    if (!rollout) {
        return true;
    }
    switch (rollout.mode) {
        case 'off':
            return false;
        case 'full':
            return true;
        case 'canary':
            return isInCanary(mcpName, runId, rollout);
        default:
            return true;
    }
}
exports.isRolloutEnabled = isRolloutEnabled;
/**
 * Deterministic canary selection
 *
 * Uses sha256 hash of runId:mcpName to generate a bucket (0-99)
 * Returns true if bucket < canaryPercent
 */
function isInCanary(mcpName, runId, rollout) {
    // Check allowlist first
    if (rollout.allowlist?.runIds?.includes(runId)) {
        return true;
    }
    const canaryPercent = rollout.canaryPercent ?? 0;
    if (canaryPercent <= 0) {
        return false;
    }
    if (canaryPercent >= 100) {
        return true;
    }
    const bucket = calculateBucket(mcpName, runId);
    return bucket < canaryPercent;
}
exports.isInCanary = isInCanary;
/**
 * Calculate deterministic bucket (0-99) from mcpName and runId
 */
function calculateBucket(mcpName, runId) {
    const input = `${runId}:${mcpName}`;
    const hash = crypto.createHash('sha256').update(input).digest('hex');
    // Take first 8 hex chars and convert to number, then mod 100
    const hashValue = parseInt(hash.slice(0, 8), 16);
    return hashValue % 100;
}
exports.calculateBucket = calculateBucket;
/**
 * Get rollout status summary for all MCPs
 */
function getRolloutSummary() {
    // This would need to iterate over all MCPs, but for now return empty
    // as we don't have access to the full MCP list here
    return {};
}
exports.getRolloutSummary = getRolloutSummary;
/**
 * Format rollout status for display
 */
function formatRolloutStatus(mcpName) {
    const rollout = (0, overlay_1.getRolloutConfig)(mcpName);
    if (!rollout) {
        return 'default';
    }
    switch (rollout.mode) {
        case 'off':
            return 'off';
        case 'full':
            return 'full (100%)';
        case 'canary':
            return `canary (${rollout.canaryPercent ?? 0}%)`;
        default:
            return 'unknown';
    }
}
exports.formatRolloutStatus = formatRolloutStatus;
