"use strict";
/**
 * CDP Session Manager
 *
 * Manages Playwright CDP connection to existing Chrome instance.
 * Connection is cached for reuse across operations.
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
exports.clearConnectionCache = exports.disconnectCDP = exports.getCachedConnection = exports.connectCDP = exports.isCDPPortOpen = void 0;
const playwright_core_1 = require("playwright-core");
const net = __importStar(require("net"));
const types_1 = require("./types");
/** Cached connection */
let cachedConnection = null;
/**
 * Check if CDP port is available
 */
async function isCDPPortOpen(port = 9222) {
    return new Promise((resolve) => {
        const client = new net.Socket();
        const timeout = setTimeout(() => {
            client.destroy();
            resolve(false);
        }, 1000);
        client.connect(port, '127.0.0.1', () => {
            clearTimeout(timeout);
            client.destroy();
            resolve(true);
        });
        client.on('error', () => {
            clearTimeout(timeout);
            resolve(false);
        });
    });
}
exports.isCDPPortOpen = isCDPPortOpen;
/**
 * Connect to existing Chrome via CDP
 */
async function connectCDP(config = {}) {
    const fullConfig = { ...types_1.DEFAULT_CDP_CONFIG, ...config };
    // Return cached connection if still valid
    if (cachedConnection?.isConnected) {
        try {
            // Verify connection is still alive
            await cachedConnection.browser.contexts();
            return cachedConnection;
        }
        catch (error) {
            // Connection is stale, clear cache and log for diagnostics
            console.debug('[CDP] Cached connection stale, reconnecting:', error instanceof Error ? error.message : String(error));
            cachedConnection = null;
        }
    }
    // Extract port from endpoint URL
    const portMatch = fullConfig.endpointUrl.match(/:(\d+)/);
    const port = portMatch ? parseInt(portMatch[1], 10) : 9222;
    // Check if Chrome is running
    const isOpen = await isCDPPortOpen(port);
    if (!isOpen) {
        throw new Error(`Chrome is not running on port ${port}. ` +
            'Start Chrome with: npm run chrome:debug:start');
    }
    // Connect via CDP
    let browser;
    let attempts = 0;
    while (attempts < fullConfig.maxRetries) {
        try {
            browser = await playwright_core_1.chromium.connectOverCDP(fullConfig.endpointUrl, {
                timeout: fullConfig.timeout,
            });
            break;
        }
        catch (err) {
            attempts++;
            if (attempts >= fullConfig.maxRetries) {
                throw new Error(`Failed to connect to Chrome after ${fullConfig.maxRetries} attempts: ${err}`);
            }
            // Wait before retry
            await new Promise((resolve) => setTimeout(resolve, 1000));
        }
    }
    // Get existing context (preserves login state) or create new one
    const contexts = browser.contexts();
    const context = contexts.length > 0 ? contexts[0] : await browser.newContext();
    cachedConnection = {
        browser: browser,
        context,
        isConnected: true,
    };
    // Handle disconnect
    browser.on('disconnected', () => {
        if (cachedConnection) {
            cachedConnection.isConnected = false;
        }
    });
    return cachedConnection;
}
exports.connectCDP = connectCDP;
/**
 * Get cached connection if available
 */
function getCachedConnection() {
    if (cachedConnection?.isConnected) {
        return cachedConnection;
    }
    return null;
}
exports.getCachedConnection = getCachedConnection;
/**
 * Disconnect from Chrome (does NOT close Chrome, just releases connection)
 */
async function disconnectCDP() {
    if (cachedConnection) {
        try {
            // Just disconnect, don't close browser
            await cachedConnection.browser.close();
        }
        catch (error) {
            // Log at debug level for diagnostics, but don't fail
            console.debug('[CDP] Error during disconnect (non-fatal):', error instanceof Error ? error.message : String(error));
        }
        cachedConnection = null;
    }
}
exports.disconnectCDP = disconnectCDP;
/**
 * Clear cached connection (for testing)
 */
function clearConnectionCache() {
    cachedConnection = null;
}
exports.clearConnectionCache = clearConnectionCache;
