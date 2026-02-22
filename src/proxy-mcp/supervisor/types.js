"use strict";
/**
 * Supervisor Types - M6
 *
 * Types for LangGraph-based supervisor with human approval
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DANGEROUS_PATTERNS = void 0;
/**
 * Dangerous operation patterns that always require human approval
 */
exports.DANGEROUS_PATTERNS = [
    // Deployment
    'deploy',
    'production',
    'release',
    'publish',
    // Destructive
    'delete',
    'drop',
    'truncate',
    'remove',
    'destroy',
    'wipe',
    // Secrets
    'secret',
    'credential',
    'api.key',
    'api_key',
    'apikey',
    'password',
    'token',
    // Billing
    'billing',
    'payment',
    'subscription',
    'charge',
    'invoice',
    // Access control
    'role',
    'admin',
    'permission',
    'access.control',
    'access_control',
    'privilege',
    // Abuse
    'captcha',
    'bypass',
    'spam',
    'brute.force',
    'brute_force',
];
