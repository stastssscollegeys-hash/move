"use strict";
/**
 * Overlay Configuration System
 *
 * Loads and merges MCP configurations from multiple sources:
 * 1. Base: config/proxy-mcp/internal-mcps.json
 * 2. Overlay: TAISUN_INTERNAL_MCPS_OVERLAY_PATH env var
 * 3. Local: config/proxy-mcp/internal-mcps.local.json (fallback)
 *
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
exports.getOverlayPath = exports.getRolloutConfig = exports.loadMergedConfig = exports.mergeConfigs = exports.loadLocalConfig = exports.loadOverlayConfig = exports.loadBaseConfig = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const CONFIG_DIR = path.join(process.cwd(), 'config', 'proxy-mcp');
const BASE_CONFIG_PATH = path.join(CONFIG_DIR, 'internal-mcps.json');
const LOCAL_CONFIG_PATH = path.join(CONFIG_DIR, 'internal-mcps.local.json');
/**
 * Load base configuration
 */
function loadBaseConfig() {
    try {
        if (fs.existsSync(BASE_CONFIG_PATH)) {
            const content = fs.readFileSync(BASE_CONFIG_PATH, 'utf-8');
            return JSON.parse(content);
        }
    }
    catch (error) {
        console.error('[overlay] Failed to load base config:', error);
    }
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
exports.loadBaseConfig = loadBaseConfig;
/**
 * Load overlay configuration from environment-specified path
 */
function loadOverlayConfig() {
    const overlayPath = process.env.TAISUN_INTERNAL_MCPS_OVERLAY_PATH;
    if (!overlayPath) {
        return null;
    }
    try {
        if (fs.existsSync(overlayPath)) {
            const content = fs.readFileSync(overlayPath, 'utf-8');
            return JSON.parse(content);
        }
    }
    catch (error) {
        console.error('[overlay] Failed to load overlay config:', error);
    }
    return null;
}
exports.loadOverlayConfig = loadOverlayConfig;
/**
 * Load local configuration (fallback)
 */
function loadLocalConfig() {
    try {
        if (fs.existsSync(LOCAL_CONFIG_PATH)) {
            const content = fs.readFileSync(LOCAL_CONFIG_PATH, 'utf-8');
            return JSON.parse(content);
        }
    }
    catch (error) {
        console.error('[overlay] Failed to load local config:', error);
    }
    return null;
}
exports.loadLocalConfig = loadLocalConfig;
/**
 * Merge configurations with priority: overlay > local > base
 */
function mergeConfigs(base, local, overlay) {
    const result = base.mcps.map((mcp) => ({ ...mcp }));
    // Apply local overrides
    if (local?.mcps) {
        for (const override of local.mcps) {
            const existing = result.find((m) => m.name === override.name);
            if (existing) {
                if (override.enabled !== undefined)
                    existing.enabled = override.enabled;
                if (override.versionPin)
                    existing.versionPin = override.versionPin;
                if (override.requiredEnv)
                    existing.requiredEnv = override.requiredEnv;
                if (override.allowlist)
                    existing.allowlist = override.allowlist;
            }
        }
    }
    // Apply overlay overrides (highest priority)
    if (overlay?.mcps) {
        for (const override of overlay.mcps) {
            const existing = result.find((m) => m.name === override.name);
            if (existing) {
                if (override.enabled !== undefined)
                    existing.enabled = override.enabled;
                if (override.versionPin)
                    existing.versionPin = override.versionPin;
                if (override.requiredEnv)
                    existing.requiredEnv = override.requiredEnv;
                if (override.allowlist)
                    existing.allowlist = override.allowlist;
                // Store rollout config in metadata
                if (override.rollout) {
                    existing.rollout = override.rollout;
                }
            }
        }
    }
    return result;
}
exports.mergeConfigs = mergeConfigs;
/**
 * Load and merge all configurations
 */
function loadMergedConfig() {
    const base = loadBaseConfig();
    const local = loadLocalConfig();
    const overlay = loadOverlayConfig();
    return mergeConfigs(base, local, overlay);
}
exports.loadMergedConfig = loadMergedConfig;
/**
 * Get rollout config for a specific MCP
 */
function getRolloutConfig(mcpName) {
    const overlay = loadOverlayConfig();
    if (!overlay?.mcps)
        return null;
    const mcpOverride = overlay.mcps.find((m) => m.name === mcpName);
    return mcpOverride?.rollout || null;
}
exports.getRolloutConfig = getRolloutConfig;
/**
 * Get overlay path (for CLI tools)
 */
function getOverlayPath() {
    return process.env.TAISUN_INTERNAL_MCPS_OVERLAY_PATH || null;
}
exports.getOverlayPath = getOverlayPath;
