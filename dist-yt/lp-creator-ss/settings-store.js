"use strict";
// ===== LP Creator SS - Settings Store =====
// Persists admin settings to a JSON file
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getEffectiveMaxTokens = exports.getEffectiveModel = exports.getEffectiveApiKey = exports.saveSettings = exports.loadSettings = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const SETTINGS_DIR = path_1.default.join(__dirname, '..', '..', 'data');
const SETTINGS_FILE = path_1.default.join(SETTINGS_DIR, 'lp-creator-settings.json');
const DEFAULTS = {
    anthropicApiKey: '',
    model: 'claude-sonnet-4-5-20250929',
    maxTokens: 4096,
};
/** Load settings from file, falling back to defaults */
function loadSettings() {
    try {
        if (fs_1.default.existsSync(SETTINGS_FILE)) {
            const raw = fs_1.default.readFileSync(SETTINGS_FILE, 'utf-8');
            const saved = JSON.parse(raw);
            return { ...DEFAULTS, ...saved };
        }
    }
    catch (err) {
        console.warn('[LP Creator] Failed to load settings, using defaults:', err);
    }
    return { ...DEFAULTS };
}
exports.loadSettings = loadSettings;
/** Save settings to file */
function saveSettings(settings) {
    const current = loadSettings();
    const merged = { ...current, ...settings };
    // Ensure data directory exists
    if (!fs_1.default.existsSync(SETTINGS_DIR)) {
        fs_1.default.mkdirSync(SETTINGS_DIR, { recursive: true });
    }
    fs_1.default.writeFileSync(SETTINGS_FILE, JSON.stringify(merged, null, 2), 'utf-8');
    return merged;
}
exports.saveSettings = saveSettings;
/** Get the effective API key (settings > env var) */
function getEffectiveApiKey() {
    const settings = loadSettings();
    return settings.anthropicApiKey || process.env.ANTHROPIC_API_KEY || undefined;
}
exports.getEffectiveApiKey = getEffectiveApiKey;
/** Get the effective model */
function getEffectiveModel() {
    const settings = loadSettings();
    return settings.model || process.env.CLAUDE_MODEL || DEFAULTS.model;
}
exports.getEffectiveModel = getEffectiveModel;
/** Get the effective max tokens */
function getEffectiveMaxTokens() {
    const settings = loadSettings();
    return settings.maxTokens || DEFAULTS.maxTokens;
}
exports.getEffectiveMaxTokens = getEffectiveMaxTokens;
