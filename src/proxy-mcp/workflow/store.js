"use strict";
/**
 * Workflow State Store
 * Handles .workflow_state.json persistence with UTF-8 safety
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
exports.hasState = exports.clearState = exports.saveState = exports.loadState = exports.resetStateDir = exports.setStateDir = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const STATE_FILE = '.workflow_state.json';
let stateDirectory = process.cwd();
/**
 * Set custom state directory (for testing)
 */
function setStateDir(dir) {
    stateDirectory = dir;
}
exports.setStateDir = setStateDir;
/**
 * Reset state directory to default (for testing cleanup)
 */
function resetStateDir() {
    stateDirectory = process.cwd();
}
exports.resetStateDir = resetStateDir;
/**
 * Get the state file path (project root or custom directory)
 */
function getStateFilePath() {
    return path.join(stateDirectory, STATE_FILE);
}
/**
 * Load workflow state from .workflow_state.json
 * Returns null if file doesn't exist
 */
function loadState() {
    const filePath = getStateFilePath();
    if (!fs.existsSync(filePath)) {
        return null;
    }
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const state = JSON.parse(content);
        return state;
    }
    catch (error) {
        const err = error;
        throw new Error(`Failed to load workflow state: ${err.message}`);
    }
}
exports.loadState = loadState;
/**
 * Save workflow state to .workflow_state.json (atomic write)
 */
function saveState(state) {
    const filePath = getStateFilePath();
    // Use unique temp file name to avoid race conditions in parallel tests
    const uniqueId = `${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const tmpPath = `${filePath}.${uniqueId}.tmp`;
    try {
        // Update timestamp
        state.lastUpdatedAt = new Date().toISOString();
        // Write to temp file first (atomic)
        const content = JSON.stringify(state, null, 2);
        fs.writeFileSync(tmpPath, content, 'utf-8');
        // Rename (atomic on POSIX, near-atomic on Windows)
        fs.renameSync(tmpPath, filePath);
    }
    catch (error) {
        // Cleanup temp file on error
        try {
            if (fs.existsSync(tmpPath)) {
                fs.unlinkSync(tmpPath);
            }
        }
        catch (cleanupError) {
            // Ignore cleanup errors (file may have been deleted by another test)
        }
        const err = error;
        throw new Error(`Failed to save workflow state: ${err.message}`);
    }
}
exports.saveState = saveState;
/**
 * Clear workflow state (delete .workflow_state.json)
 * Note: Temp files are not cleaned up here to avoid race conditions in parallel tests.
 * They will be cleaned up automatically by the OS or can be removed manually.
 */
function clearState() {
    const filePath = getStateFilePath();
    try {
        if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }
    }
    catch (error) {
        // Ignore ENOENT errors (file already deleted by another test)
        const err = error;
        if (err.code !== 'ENOENT') {
            throw error;
        }
    }
}
exports.clearState = clearState;
/**
 * Check if workflow state exists
 */
function hasState() {
    const filePath = getStateFilePath();
    return fs.existsSync(filePath);
}
exports.hasState = hasState;
