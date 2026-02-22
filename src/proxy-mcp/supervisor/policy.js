"use strict";
/**
 * Supervisor Policy - M6
 *
 * Policy checks for dangerous operations
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.validatePlan = exports.createPlanStep = exports.determineStepRisk = exports.analyzePlanRisk = exports.requiresApproval = exports.checkDangerousPatterns = void 0;
const types_1 = require("./types");
/**
 * Check if input contains dangerous patterns
 */
function checkDangerousPatterns(input) {
    const inputLower = input.toLowerCase();
    const matched = [];
    for (const pattern of types_1.DANGEROUS_PATTERNS) {
        // Handle patterns with dots/underscores
        const normalizedPattern = pattern.replace(/[._]/g, '[._]?');
        const regex = new RegExp(normalizedPattern, 'i');
        if (regex.test(inputLower)) {
            matched.push(pattern);
        }
    }
    return matched;
}
exports.checkDangerousPatterns = checkDangerousPatterns;
/**
 * Determine if approval is required based on input and route
 */
function requiresApproval(input, route) {
    // Check dangerous patterns in input
    const dangerousMatches = checkDangerousPatterns(input);
    if (dangerousMatches.length > 0) {
        return true;
    }
    // Check route decision
    if (route?.action === 'require_human') {
        return true;
    }
    // Check route's dangerous patterns
    if (route?.dangerousPatterns && route.dangerousPatterns.length > 0) {
        return true;
    }
    return false;
}
exports.requiresApproval = requiresApproval;
/**
 * Analyze execution plan for risk level
 */
function analyzePlanRisk(plan) {
    let maxRisk = 'low';
    const riskOrder = ['low', 'medium', 'high', 'critical'];
    for (const step of plan.steps) {
        const stepRiskIndex = riskOrder.indexOf(step.risk);
        const maxRiskIndex = riskOrder.indexOf(maxRisk);
        if (stepRiskIndex > maxRiskIndex) {
            maxRisk = step.risk;
        }
    }
    return maxRisk;
}
exports.analyzePlanRisk = analyzePlanRisk;
/**
 * Determine risk level for a single action
 */
function determineStepRisk(action, target) {
    const combined = `${action} ${target || ''}`.toLowerCase();
    const dangerousMatches = checkDangerousPatterns(combined);
    if (dangerousMatches.length === 0) {
        return 'low';
    }
    // Critical patterns
    const criticalPatterns = ['delete', 'drop', 'destroy', 'wipe', 'production', 'deploy'];
    const highPatterns = ['secret', 'credential', 'password', 'token', 'billing', 'payment'];
    const mediumPatterns = ['admin', 'role', 'permission', 'remove'];
    for (const pattern of criticalPatterns) {
        if (dangerousMatches.includes(pattern)) {
            return 'critical';
        }
    }
    for (const pattern of highPatterns) {
        if (dangerousMatches.includes(pattern)) {
            return 'high';
        }
    }
    for (const pattern of mediumPatterns) {
        if (dangerousMatches.includes(pattern)) {
            return 'medium';
        }
    }
    return 'medium';
}
exports.determineStepRisk = determineStepRisk;
/**
 * Create a plan step with risk assessment
 */
function createPlanStep(id, action, target, params) {
    return {
        id,
        action,
        target,
        params,
        risk: determineStepRisk(action, target),
    };
}
exports.createPlanStep = createPlanStep;
/**
 * Validate that a plan can be executed safely
 */
function validatePlan(plan, approved) {
    const risk = analyzePlanRisk(plan);
    // Critical and high risk always need approval
    if ((risk === 'critical' || risk === 'high') && !approved) {
        return {
            valid: false,
            reason: `Plan has ${risk} risk and requires approval`,
        };
    }
    // Medium risk needs approval if plan explicitly requires it
    if (risk === 'medium' && plan.requiresApproval && !approved) {
        return {
            valid: false,
            reason: 'Plan requires approval for medium-risk operations',
        };
    }
    return { valid: true };
}
exports.validatePlan = validatePlan;
