"use strict";
/**
 * Safe JSON Parser Utility
 *
 * Provides protection against prototype pollution attacks when parsing JSON.
 * CWE-1321: Improperly Controlled Modification of Object Prototype Attributes
 *
 * Usage:
 *   import { safeJSONParse, sanitizeObject } from '../utils/safe-json';
 *   const data = safeJSONParse<MyType>(jsonString);
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.safeJSONParseWithValidation = exports.hasDangerousKeys = exports.safeJSONParseStrict = exports.safeJSONParse = exports.sanitizeObject = void 0;
/**
 * Dangerous property names that can lead to prototype pollution
 */
const DANGEROUS_KEYS = [
    '__proto__',
    'constructor',
    'prototype',
    '__defineGetter__',
    '__defineSetter__',
    '__lookupGetter__',
    '__lookupSetter__',
];
/**
 * Recursively remove dangerous properties from an object
 */
function sanitizeObject(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map((item) => sanitizeObject(item));
    }
    const sanitized = {};
    for (const [key, value] of Object.entries(obj)) {
        // Skip dangerous keys
        if (DANGEROUS_KEYS.includes(key)) {
            console.warn(`[Security] Removed dangerous key from JSON: ${key}`);
            continue;
        }
        // Recursively sanitize nested objects
        sanitized[key] = sanitizeObject(value);
    }
    return sanitized;
}
exports.sanitizeObject = sanitizeObject;
/**
 * Safely parse JSON with prototype pollution protection
 *
 * @param jsonString - The JSON string to parse
 * @param reviver - Optional reviver function (same as JSON.parse)
 * @returns Parsed and sanitized object, or null if parsing fails
 */
function safeJSONParse(jsonString, reviver) {
    try {
        const parsed = JSON.parse(jsonString, reviver);
        return sanitizeObject(parsed);
    }
    catch (error) {
        console.error('[Security] JSON parse error:', error);
        return null;
    }
}
exports.safeJSONParse = safeJSONParse;
/**
 * Safely parse JSON with strict validation
 * Throws an error instead of returning null
 *
 * @param jsonString - The JSON string to parse
 * @param context - Context string for error messages
 * @returns Parsed and sanitized object
 * @throws Error if parsing fails
 */
function safeJSONParseStrict(jsonString, context = 'unknown') {
    try {
        const parsed = JSON.parse(jsonString);
        return sanitizeObject(parsed);
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        throw new Error(`[Security] JSON parse failed in ${context}: ${message}`);
    }
}
exports.safeJSONParseStrict = safeJSONParseStrict;
/**
 * Check if an object contains dangerous prototype pollution keys
 */
function hasDangerousKeys(obj) {
    if (obj === null || typeof obj !== 'object') {
        return false;
    }
    if (Array.isArray(obj)) {
        return obj.some((item) => hasDangerousKeys(item));
    }
    for (const key of Object.keys(obj)) {
        if (DANGEROUS_KEYS.includes(key)) {
            return true;
        }
        const value = obj[key];
        if (hasDangerousKeys(value)) {
            return true;
        }
    }
    return false;
}
exports.hasDangerousKeys = hasDangerousKeys;
/**
 * Safely parse JSON with type validation
 *
 * @param jsonString - The JSON string to parse
 * @param validator - Type guard function to validate the parsed object
 * @returns Validated and typed object, or null if validation fails
 */
function safeJSONParseWithValidation(jsonString, validator) {
    const parsed = safeJSONParse(jsonString);
    if (parsed === null) {
        return null;
    }
    if (!validator(parsed)) {
        console.error('[Security] JSON validation failed: object did not match expected type');
        return null;
    }
    return parsed;
}
exports.safeJSONParseWithValidation = safeJSONParseWithValidation;
