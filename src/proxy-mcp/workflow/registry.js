"use strict";
/**
 * Workflow Registry
 * Loads and validates workflow definitions from config/workflows/
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
exports.clearCache = exports.getWorkflow = exports.loadWorkflow = exports.loadAllWorkflows = exports.resetWorkflowsDir = exports.setWorkflowsDir = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
let WORKFLOWS_DIR = path.join(process.cwd(), 'config', 'workflows');
/**
 * Set custom workflows directory (for testing)
 */
function setWorkflowsDir(dir) {
    WORKFLOWS_DIR = dir;
}
exports.setWorkflowsDir = setWorkflowsDir;
/**
 * Reset workflows directory to default (for testing cleanup)
 */
function resetWorkflowsDir() {
    WORKFLOWS_DIR = path.join(process.cwd(), 'config', 'workflows');
}
exports.resetWorkflowsDir = resetWorkflowsDir;
/**
 * Load all workflow definitions
 */
function loadAllWorkflows() {
    const workflows = new Map();
    if (!fs.existsSync(WORKFLOWS_DIR)) {
        throw new Error(`Workflows directory not found: ${WORKFLOWS_DIR}\n` +
            'ワークフロー定義ディレクトリが見つかりません。');
    }
    const files = fs.readdirSync(WORKFLOWS_DIR);
    for (const file of files) {
        // Skip schema file and non-JSON files
        if (file.startsWith('_') || !file.endsWith('.json')) {
            continue;
        }
        const filePath = path.join(WORKFLOWS_DIR, file);
        try {
            // Check if file still exists (might have been deleted by another test)
            if (!fs.existsSync(filePath)) {
                continue;
            }
            const content = fs.readFileSync(filePath, 'utf-8');
            // Skip empty files (might be in the process of being written)
            if (!content || content.trim() === '') {
                continue;
            }
            const definition = JSON.parse(content);
            // Basic validation
            validateWorkflowDefinition(definition, file);
            workflows.set(definition.id, definition);
        }
        catch (error) {
            const err = error;
            // Skip files that were deleted or are being modified (ENOENT, empty JSON, etc.)
            if (err.code === 'ENOENT' || err.message.includes('Unexpected end of JSON input')) {
                continue;
            }
            throw new Error(`Failed to load workflow definition ${file}: ${err.message}\n` +
                `ワークフロー定義の読み込みに失敗: ${file}`);
        }
    }
    return workflows;
}
exports.loadAllWorkflows = loadAllWorkflows;
/**
 * Load a specific workflow by ID
 */
function loadWorkflow(workflowId) {
    const workflows = loadAllWorkflows();
    const workflow = workflows.get(workflowId);
    if (!workflow) {
        const available = Array.from(workflows.keys()).join(', ');
        throw new Error(`Workflow '${workflowId}' not found.\n` +
            `ワークフロー '${workflowId}' が見つかりません。\n` +
            `利用可能なワークフロー: ${available}`);
    }
    return workflow;
}
exports.loadWorkflow = loadWorkflow;
/**
 * Validate workflow definition structure
 */
function validateWorkflowDefinition(def, filename) {
    const errors = [];
    if (!def.id) {
        errors.push('Missing required field: id');
    }
    if (!def.name) {
        errors.push('Missing required field: name');
    }
    if (!def.version) {
        errors.push('Missing required field: version');
    }
    if (!Array.isArray(def.phases) || def.phases.length === 0) {
        errors.push('Missing or empty phases array');
    }
    // Validate phases
    if (def.phases) {
        const phaseIds = new Set();
        for (const phase of def.phases) {
            if (!phase.id) {
                errors.push(`Phase missing id: ${JSON.stringify(phase)}`);
            }
            if (!phase.name) {
                errors.push(`Phase ${phase.id} missing name`);
            }
            // Check for duplicate phase IDs
            if (phaseIds.has(phase.id)) {
                errors.push(`Duplicate phase ID: ${phase.id}`);
            }
            phaseIds.add(phase.id);
        }
        // Validate nextPhase references
        for (const phase of def.phases) {
            if (phase.nextPhase && !phaseIds.has(phase.nextPhase)) {
                errors.push(`Phase ${phase.id} references non-existent nextPhase: ${phase.nextPhase}`);
            }
        }
    }
    if (errors.length > 0) {
        throw new Error(`Invalid workflow definition in ${filename}:\n` +
            errors.map((e) => `  - ${e}`).join('\n') +
            '\n\nワークフロー定義が不正です。');
    }
}
/**
 * Get workflow by ID (cached)
 */
let cachedWorkflows = null;
function getWorkflow(workflowId) {
    if (!cachedWorkflows) {
        cachedWorkflows = loadAllWorkflows();
    }
    const workflow = cachedWorkflows.get(workflowId);
    if (!workflow) {
        const available = Array.from(cachedWorkflows.keys()).join(', ');
        throw new Error(`Workflow '${workflowId}' not found. Available: ${available}`);
    }
    return workflow;
}
exports.getWorkflow = getWorkflow;
/**
 * Clear cache (for testing)
 */
function clearCache() {
    cachedWorkflows = null;
}
exports.clearCache = clearCache;
