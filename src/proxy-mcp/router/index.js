"use strict";
/**
 * Hybrid Router - Combines rule-based and semantic routing
 *
 * Priority:
 * 1. Safety rules (deny/require_human)
 * 2. Semantic matching (find best MCP)
 * 3. Fallback (require_human_or_clarify)
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
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.calculateSimilarity = exports.findBestMatch = exports.findMatchingMcps = exports.SAFETY_RULES = exports.getSafetyCategories = exports.evaluateSafetyRules = exports.explainRoute = exports.isSafe = exports.route = void 0;
const rules_1 = require("./rules");
const semantic_1 = require("./semantic");
const DEFAULT_CONFIG = {
    ruleFirst: true,
    semanticThreshold: 0.7,
    topK: 5,
    fallback: 'require_clarify',
};
/**
 * Main routing function
 * Returns routing decision for a given input
 */
function route(input, mcps, config = {}) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    // Step 1: Check safety rules first (if ruleFirst is enabled)
    if (cfg.ruleFirst) {
        const safetyResult = (0, rules_1.evaluateSafetyRules)(input);
        if (safetyResult) {
            return safetyResult;
        }
    }
    // Step 2: Find matching MCPs using semantic similarity
    const candidates = (0, semantic_1.findMatchingMcps)(input, mcps, cfg.semanticThreshold, cfg.topK);
    if (candidates.length === 0) {
        // No matches above threshold
        return {
            action: cfg.fallback,
            reason: `No MCP matched with confidence >= ${cfg.semanticThreshold}. Please clarify or confirm the intended action.`,
            candidates: [],
            confidence: 0,
        };
    }
    const bestMatch = candidates[0];
    // Step 3: Check if the best match involves dangerous operations
    const matchedMcp = mcps.find((m) => m.name === bestMatch.name);
    if (matchedMcp && matchedMcp.dangerousOperations.length > 0) {
        const hasDangerousOp = (0, rules_1.isDangerousOperation)(matchedMcp.name, input, matchedMcp.dangerousOperations);
        if (hasDangerousOp) {
            return {
                action: 'require_human',
                reason: `Operation may involve dangerous action for ${matchedMcp.name}. Human confirmation required.`,
                matchedRule: 'dangerous_operation',
                candidates,
                confidence: bestMatch.score,
            };
        }
    }
    // Step 4: Return the best match
    return {
        action: 'allow',
        reason: `Matched ${bestMatch.name} with confidence ${(bestMatch.score * 100).toFixed(1)}%`,
        candidates,
        confidence: bestMatch.score,
    };
}
exports.route = route;
/**
 * Quick check if input is safe (no safety rules triggered)
 */
function isSafe(input) {
    const result = (0, rules_1.evaluateSafetyRules)(input);
    return result === null;
}
exports.isSafe = isSafe;
/**
 * Get routing explanation (for debugging/logging)
 */
function explainRoute(input, mcps, config = {}) {
    const result = route(input, mcps, config);
    let explanation = `Input: "${input.slice(0, 50)}${input.length > 50 ? '...' : ''}"\n`;
    explanation += `Action: ${result.action}\n`;
    explanation += `Reason: ${result.reason}\n`;
    if (result.candidates && result.candidates.length > 0) {
        explanation += `Candidates:\n`;
        for (const candidate of result.candidates) {
            explanation += `  - ${candidate.name}: ${(candidate.score * 100).toFixed(1)}% [${candidate.tags.join(', ')}]\n`;
        }
    }
    if (result.matchedRule) {
        explanation += `Matched Rule: ${result.matchedRule}\n`;
    }
    return explanation;
}
exports.explainRoute = explainRoute;
// Re-export types and utilities
__exportStar(require("./types"), exports);
var rules_2 = require("./rules");
Object.defineProperty(exports, "evaluateSafetyRules", { enumerable: true, get: function () { return rules_2.evaluateSafetyRules; } });
Object.defineProperty(exports, "getSafetyCategories", { enumerable: true, get: function () { return rules_2.getSafetyCategories; } });
Object.defineProperty(exports, "SAFETY_RULES", { enumerable: true, get: function () { return rules_2.SAFETY_RULES; } });
var semantic_2 = require("./semantic");
Object.defineProperty(exports, "findMatchingMcps", { enumerable: true, get: function () { return semantic_2.findMatchingMcps; } });
Object.defineProperty(exports, "findBestMatch", { enumerable: true, get: function () { return semantic_2.findBestMatch; } });
Object.defineProperty(exports, "calculateSimilarity", { enumerable: true, get: function () { return semantic_2.calculateSimilarity; } });
