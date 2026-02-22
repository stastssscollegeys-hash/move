"use strict";
/**
 * Rules Router - Pattern-based routing with safety rules
 *
 * Priority order:
 * 1. Deny rules (highest priority - block immediately)
 * 2. Require human rules (dangerous operations)
 * 3. Allow rules (explicitly permitted)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SAFETY_RULES = exports.getSafetyCategories = exports.isDangerousOperation = exports.evaluateSafetyRules = void 0;
/**
 * Safety rules for dangerous operations
 * These always take precedence over semantic routing
 */
const SAFETY_RULES = [
    {
        category: 'deployment',
        keywords: ['deploy', 'production', 'release', 'publish', 'rollout'],
        patterns: [/deploy\s+to\s+prod/i, /push\s+to\s+production/i, /release\s+v\d/i],
        action: 'require_human',
    },
    {
        category: 'destructive',
        keywords: ['delete', 'drop', 'truncate', 'remove', 'destroy', 'wipe'],
        patterns: [/drop\s+table/i, /delete\s+all/i, /rm\s+-rf/i, /truncate\s+table/i],
        action: 'require_human',
    },
    {
        category: 'secrets',
        keywords: ['secret', 'credential', 'password', 'token', 'api_key', 'private_key'],
        patterns: [/rotate\s+(secret|key|token)/i, /update\s+credential/i],
        action: 'require_human',
    },
    {
        category: 'billing',
        keywords: ['billing', 'payment', 'invoice', 'subscription', 'charge'],
        patterns: [/cancel\s+subscription/i, /change\s+plan/i, /update\s+billing/i],
        action: 'require_human',
    },
    {
        category: 'access_control',
        keywords: ['permission', 'role', 'access', 'admin', 'sudo', 'root'],
        patterns: [/grant\s+admin/i, /change\s+role/i, /elevate\s+privilege/i],
        action: 'require_human',
    },
    {
        category: 'automation_abuse',
        keywords: ['captcha', 'bypass', 'scrape', 'spam', 'flood'],
        patterns: [/bypass\s+captcha/i, /mass\s+scrape/i, /automated\s+login/i],
        action: 'deny',
    },
];
exports.SAFETY_RULES = SAFETY_RULES;
/**
 * Check if input matches any keyword
 */
function matchesKeywords(input, keywords) {
    const inputLower = input.toLowerCase();
    for (const keyword of keywords) {
        if (inputLower.includes(keyword.toLowerCase())) {
            return keyword;
        }
    }
    return null;
}
/**
 * Check if input matches any pattern
 */
function matchesPatterns(input, patterns) {
    for (const pattern of patterns) {
        if (pattern.test(input)) {
            return pattern;
        }
    }
    return null;
}
/**
 * Evaluate safety rules against input
 * Returns the most restrictive matching rule
 */
function evaluateSafetyRules(input) {
    let result = null;
    for (const rule of SAFETY_RULES) {
        // Check keywords
        const matchedKeyword = matchesKeywords(input, rule.keywords);
        if (matchedKeyword) {
            const newResult = {
                action: rule.action,
                reason: `Safety rule [${rule.category}]: matched keyword "${matchedKeyword}"`,
                matchedRule: rule.category,
            };
            // Deny takes precedence over require_human
            if (rule.action === 'deny') {
                return newResult;
            }
            // Keep the first require_human match
            if (!result) {
                result = newResult;
            }
        }
        // Check patterns
        const matchedPattern = matchesPatterns(input, rule.patterns);
        if (matchedPattern) {
            const newResult = {
                action: rule.action,
                reason: `Safety rule [${rule.category}]: matched pattern "${matchedPattern.source}"`,
                matchedRule: rule.category,
            };
            if (rule.action === 'deny') {
                return newResult;
            }
            if (!result) {
                result = newResult;
            }
        }
    }
    return result;
}
exports.evaluateSafetyRules = evaluateSafetyRules;
/**
 * Check if a specific MCP operation is dangerous
 */
function isDangerousOperation(mcpName, operation, dangerousOps) {
    const opLower = operation.toLowerCase();
    return dangerousOps.some((dangerousOp) => opLower.includes(dangerousOp.toLowerCase()));
}
exports.isDangerousOperation = isDangerousOperation;
/**
 * Get all safety rule categories
 */
function getSafetyCategories() {
    return SAFETY_RULES.map((rule) => rule.category);
}
exports.getSafetyCategories = getSafetyCategories;
