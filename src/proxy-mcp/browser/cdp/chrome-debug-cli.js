#!/usr/bin/env node
"use strict";
/* istanbul ignore file */
/**
 * Chrome Debug Mode CLI
 *
 * Starts Chrome in debug mode with CDP enabled for Playwright connection.
 * Uses a dedicated profile to avoid interfering with daily-use Chrome.
 *
 * Environment variables:
 * - CHROME_PATH: Path to Chrome executable
 * - CHROME_DEBUG_PORT: Debug port (default: 9222)
 * - CHROME_PROFILE_DIR: Profile directory (default: ~/.chrome-debug-profile)
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
const child_process_1 = require("child_process");
const net = __importStar(require("net"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
// Configuration
const DEFAULT_PORT = 9222;
const DEFAULT_PROFILE_DIR = path.join(os.homedir(), '.chrome-debug-profile');
// Security: Whitelist of allowed Chrome executable names
const ALLOWED_CHROME_BASENAMES = [
    'google chrome',
    'google-chrome',
    'google-chrome-stable',
    'chrome',
    'chrome.exe',
    'chromium',
    'chromium-browser',
];
// Security: Shell metacharacters that must not appear in paths
const DANGEROUS_CHARS = /[;&|`$(){}[\]<>!'"\\]/;
/**
 * Security: Validate Chrome path to prevent command injection
 * @throws Error if path is invalid or potentially dangerous
 */
function validateChromePath(chromePath) {
    // Check for empty path
    if (!chromePath || chromePath.trim() === '') {
        throw new Error('Security: Chrome path cannot be empty');
    }
    // Check for dangerous shell metacharacters
    if (DANGEROUS_CHARS.test(chromePath)) {
        throw new Error(`Security: Chrome path contains dangerous characters: ${chromePath}`);
    }
    // Must be absolute path
    if (!path.isAbsolute(chromePath)) {
        throw new Error(`Security: Chrome path must be absolute: ${chromePath}`);
    }
    // Check if file exists
    if (!fs.existsSync(chromePath)) {
        throw new Error(`Security: Chrome executable not found: ${chromePath}`);
    }
    // Resolve symlinks and get real path
    let realPath;
    try {
        realPath = fs.realpathSync(chromePath);
    }
    catch {
        throw new Error(`Security: Cannot resolve Chrome path: ${chromePath}`);
    }
    // Validate basename against whitelist
    const basename = path.basename(realPath).toLowerCase();
    if (!ALLOWED_CHROME_BASENAMES.includes(basename)) {
        throw new Error(`Security: Chrome executable name not in whitelist: ${basename}. ` +
            `Allowed: ${ALLOWED_CHROME_BASENAMES.join(', ')}`);
    }
    // Additional check: path should not contain path traversal
    if (chromePath.includes('..')) {
        throw new Error(`Security: Chrome path contains path traversal: ${chromePath}`);
    }
}
/**
 * Detect Chrome path based on OS
 */
function detectChromePath() {
    const platform = os.platform();
    if (platform === 'darwin') {
        // macOS
        const paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
        ];
        for (const p of paths) {
            if (fs.existsSync(p))
                return p;
        }
    }
    else if (platform === 'win32') {
        // Windows
        const paths = [
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
            path.join(os.homedir(), 'AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'),
        ];
        for (const p of paths) {
            if (fs.existsSync(p))
                return p;
        }
    }
    else {
        // Linux
        try {
            return (0, child_process_1.execSync)('which google-chrome || which chromium-browser || which chromium', {
                encoding: 'utf-8',
            }).trim();
        }
        catch {
            // Fall through to error
        }
    }
    throw new Error('Chrome not found. Set CHROME_PATH environment variable or install Chrome.');
}
/**
 * Check if a port is already in use
 */
async function isPortInUse(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                resolve(true);
            }
            else {
                resolve(false);
            }
        });
        server.once('listening', () => {
            server.close();
            resolve(false);
        });
        server.listen(port, '127.0.0.1');
    });
}
/**
 * Get configuration from environment variables
 */
function getConfig() {
    const chromePath = process.env.CHROME_PATH || detectChromePath();
    const port = parseInt(process.env.CHROME_DEBUG_PORT || String(DEFAULT_PORT), 10);
    const profileDir = process.env.CHROME_PROFILE_DIR || DEFAULT_PROFILE_DIR;
    // Security: Validate Chrome path before use
    validateChromePath(chromePath);
    return { chromePath, port, profileDir };
}
/**
 * Start Chrome in debug mode
 */
async function startChromeDebug() {
    const config = getConfig();
    console.log('Chrome Debug Mode CLI');
    console.log('=====================');
    console.log(`Chrome Path: ${config.chromePath}`);
    console.log(`Debug Port: ${config.port}`);
    console.log(`Profile Dir: ${config.profileDir}`);
    console.log('');
    // Check if port is already in use (Chrome might already be running)
    const portInUse = await isPortInUse(config.port);
    if (portInUse) {
        console.log(`Port ${config.port} is already in use.`);
        console.log('Chrome is likely already running in debug mode.');
        console.log(`CDP endpoint: http://127.0.0.1:${config.port}`);
        console.log('');
        console.log('To connect with Playwright:');
        console.log(`  npm run chrome:cdp:smoke`);
        return;
    }
    // Ensure profile directory exists
    if (!fs.existsSync(config.profileDir)) {
        console.log(`Creating profile directory: ${config.profileDir}`);
        fs.mkdirSync(config.profileDir, { recursive: true });
    }
    // Build Chrome arguments
    const args = [
        `--remote-debugging-port=${config.port}`,
        '--remote-debugging-address=127.0.0.1', // Security: localhost only
        `--user-data-dir=${config.profileDir}`,
        // Security: Restrict origins to localhost only (prevents remote access)
        '--remote-allow-origins=http://127.0.0.1,http://localhost,http://localhost:*,http://127.0.0.1:*',
        '--no-first-run',
        '--no-default-browser-check',
    ];
    console.log('Starting Chrome...');
    console.log(`Command: "${config.chromePath}" ${args.join(' ')}`);
    console.log('');
    // Spawn Chrome (detached so it survives this script)
    const chrome = (0, child_process_1.spawn)(config.chromePath, args, {
        detached: true,
        stdio: 'ignore',
    });
    chrome.unref();
    // Wait a moment for Chrome to start
    await new Promise((resolve) => setTimeout(resolve, 2000));
    // Verify port is now in use
    const nowInUse = await isPortInUse(config.port);
    if (nowInUse) {
        console.log('Chrome started successfully!');
        console.log(`CDP endpoint: http://127.0.0.1:${config.port}`);
        console.log('');
        console.log('To verify connection:');
        console.log('  npm run chrome:cdp:smoke');
        console.log('');
        console.log('Security notes:');
        console.log('  - Debug port is localhost-only (127.0.0.1)');
        console.log('  - Using dedicated profile (not your daily Chrome)');
        console.log('  - Keep Chrome running for session reuse');
    }
    else {
        console.error('Failed to start Chrome. Please check:');
        console.error('  1. Chrome path is correct');
        console.error('  2. No other process is blocking the port');
        console.error('  3. Profile directory is writable');
        process.exit(1);
    }
}
// Run
startChromeDebug().catch((err) => {
    console.error('Error:', err.message);
    process.exit(1);
});
