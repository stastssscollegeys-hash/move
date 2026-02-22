"use strict";
/**
 * Path Validator - Enforces absolute paths for file operations
 *
 * Based on Anthropic's SWE-bench best practices:
 * "Edit Tool requires absolute paths to prevent relative path mishandling"
 *
 * @see https://www.anthropic.com/engineering/swe-bench-sonnet
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.validatePaths = exports.getFileExtension = exports.isPathWithinDirectory = exports.toAbsolutePath = exports.enforceAbsolutePath = exports.normalizePath = exports.validatePath = exports.DEFAULT_PATH_CONFIG = void 0;
exports.DEFAULT_PATH_CONFIG = {
    allowRelative: false,
    allowedPrefixes: ['/', '/Users/', '/home/', '/tmp/', '/var/'],
    blockedPrefixes: ['/etc/passwd', '/etc/shadow', '/.ssh/', '/proc/', '/sys/'],
    maxDepth: 50,
};
/**
 * Validate and normalize a file path
 * Enforces absolute paths by default (SWE-bench best practice)
 */
function validatePath(path, config = exports.DEFAULT_PATH_CONFIG) {
    // Empty path check
    if (!path || path.trim() === '') {
        return {
            valid: false,
            normalizedPath: '',
            error: 'Path is empty',
            suggestion: 'Provide a valid absolute path starting with /',
        };
    }
    const trimmedPath = path.trim();
    // Relative path check (SWE-bench: absolute paths required)
    if (!config.allowRelative && !trimmedPath.startsWith('/')) {
        return {
            valid: false,
            normalizedPath: trimmedPath,
            error: `Relative path not allowed: ${trimmedPath}`,
            suggestion: `Use absolute path. Example: /Users/project/${trimmedPath}`,
        };
    }
    // Normalize path (remove .., //, trailing /)
    const normalizedPath = normalizePath(trimmedPath);
    // Path traversal attack prevention
    if (normalizedPath.includes('..')) {
        return {
            valid: false,
            normalizedPath,
            error: 'Path traversal detected: ".." not allowed in normalized path',
            suggestion: 'Use direct absolute path without relative navigation',
        };
    }
    // Blocked prefix check (security)
    for (const blocked of config.blockedPrefixes) {
        if (normalizedPath.startsWith(blocked) || normalizedPath.includes(blocked)) {
            return {
                valid: false,
                normalizedPath,
                error: `Access to ${blocked} is blocked for security`,
                suggestion: 'Choose a different path within allowed directories',
            };
        }
    }
    // Depth check (prevent infinite recursion)
    const depth = normalizedPath.split('/').filter(Boolean).length;
    if (depth > config.maxDepth) {
        return {
            valid: false,
            normalizedPath,
            error: `Path depth ${depth} exceeds maximum ${config.maxDepth}`,
            suggestion: 'Use a shallower directory structure',
        };
    }
    return {
        valid: true,
        normalizedPath,
    };
}
exports.validatePath = validatePath;
/**
 * Normalize a path by resolving . and .. and removing duplicate slashes
 */
function normalizePath(path) {
    // Handle empty or whitespace
    if (!path || path.trim() === '') {
        return '';
    }
    // Split by / and process
    const parts = path.split('/');
    const normalized = [];
    for (const part of parts) {
        if (part === '' || part === '.') {
            // Skip empty parts (from //) and current dir (.)
            continue;
        }
        else if (part === '..') {
            // Go up one level, but don't go above root
            if (normalized.length > 0 && normalized[normalized.length - 1] !== '..') {
                normalized.pop();
            }
            else if (!path.startsWith('/')) {
                // Only keep .. for relative paths
                normalized.push('..');
            }
        }
        else {
            normalized.push(part);
        }
    }
    // Reconstruct path
    const result = (path.startsWith('/') ? '/' : '') + normalized.join('/');
    return result || (path.startsWith('/') ? '/' : '.');
}
exports.normalizePath = normalizePath;
/**
 * Enforce absolute path - throws error if relative
 * Use this for strict enforcement in critical operations
 */
function enforceAbsolutePath(path, context) {
    const result = validatePath(path);
    if (!result.valid) {
        const contextMsg = context ? ` [${context}]` : '';
        throw new Error(`${result.error}${contextMsg}. ${result.suggestion || ''}`);
    }
    return result.normalizedPath;
}
exports.enforceAbsolutePath = enforceAbsolutePath;
/**
 * Convert relative path to absolute using base directory
 */
function toAbsolutePath(path, baseDir) {
    if (path.startsWith('/')) {
        return normalizePath(path);
    }
    // Ensure baseDir is absolute
    if (!baseDir.startsWith('/')) {
        throw new Error(`Base directory must be absolute: ${baseDir}`);
    }
    return normalizePath(`${baseDir}/${path}`);
}
exports.toAbsolutePath = toAbsolutePath;
/**
 * Check if path is within allowed directory (sandbox check)
 */
function isPathWithinDirectory(path, allowedDir) {
    const normalizedPath = normalizePath(path);
    const normalizedAllowed = normalizePath(allowedDir);
    return normalizedPath.startsWith(normalizedAllowed + '/') ||
        normalizedPath === normalizedAllowed;
}
exports.isPathWithinDirectory = isPathWithinDirectory;
/**
 * Extract file extension from path
 */
function getFileExtension(path) {
    const normalized = normalizePath(path);
    const lastPart = normalized.split('/').pop() || '';
    const dotIndex = lastPart.lastIndexOf('.');
    if (dotIndex === -1 || dotIndex === 0) {
        return '';
    }
    return lastPart.substring(dotIndex + 1).toLowerCase();
}
exports.getFileExtension = getFileExtension;
/**
 * Validate multiple paths at once
 */
function validatePaths(paths, config = exports.DEFAULT_PATH_CONFIG) {
    const valid = [];
    const invalid = [];
    for (const path of paths) {
        const result = validatePath(path, config);
        if (result.valid) {
            valid.push(result);
        }
        else {
            invalid.push(result);
        }
    }
    return { valid, invalid };
}
exports.validatePaths = validatePaths;
