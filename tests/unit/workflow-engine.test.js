"use strict";
/**
 * Workflow Engine Tests (Phase 1)
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
const fs = __importStar(require("fs"));
const store_1 = require("../../src/proxy-mcp/workflow/store");
const registry_1 = require("../../src/proxy-mcp/workflow/registry");
const engine_1 = require("../../src/proxy-mcp/workflow/engine");
describe('Workflow Store', () => {
    const TEST_STATE_FILE = '.workflow_state.json';
    beforeEach(() => {
        // Cleanup
        if (fs.existsSync(TEST_STATE_FILE)) {
            fs.unlinkSync(TEST_STATE_FILE);
        }
    });
    afterEach(() => {
        // Cleanup
        if (fs.existsSync(TEST_STATE_FILE)) {
            fs.unlinkSync(TEST_STATE_FILE);
        }
    });
    it('should load null when no state file exists', () => {
        const state = (0, store_1.loadState)();
        expect(state).toBeNull();
    });
    it('should save and load state', () => {
        const testState = {
            workflowId: 'test_workflow',
            currentPhase: 'phase_0',
            completedPhases: [],
            startedAt: new Date().toISOString(),
            lastUpdatedAt: new Date().toISOString(),
            strict: false,
        };
        (0, store_1.saveState)(testState);
        const loaded = (0, store_1.loadState)();
        expect(loaded).not.toBeNull();
        expect(loaded?.workflowId).toBe('test_workflow');
        expect(loaded?.currentPhase).toBe('phase_0');
    });
    it('should clear state', () => {
        const testState = {
            workflowId: 'test_workflow',
            currentPhase: 'phase_0',
            completedPhases: [],
            startedAt: new Date().toISOString(),
            lastUpdatedAt: new Date().toISOString(),
            strict: false,
        };
        (0, store_1.saveState)(testState);
        expect((0, store_1.loadState)()).not.toBeNull();
        (0, store_1.clearState)();
        expect((0, store_1.loadState)()).toBeNull();
    });
});
describe('Workflow Registry', () => {
    it('should load workflow definitions', () => {
        const workflows = (0, registry_1.loadAllWorkflows)();
        expect(workflows.size).toBeGreaterThan(0);
    });
    it('should load video_generation_v1', () => {
        const workflow = (0, registry_1.getWorkflow)('video_generation_v1');
        expect(workflow.id).toBe('video_generation_v1');
        expect(workflow.phases).toBeDefined();
        expect(workflow.phases.length).toBeGreaterThan(0);
    });
    it('should throw error for non-existent workflow', () => {
        expect(() => (0, registry_1.getWorkflow)('non_existent_workflow')).toThrow();
    });
});
describe('Workflow Engine', () => {
    beforeEach(() => {
        (0, store_1.clearState)();
    });
    afterEach(() => {
        (0, store_1.clearState)();
    });
    it('should start workflow', () => {
        const state = (0, engine_1.startWorkflow)('video_generation_v1');
        expect(state.workflowId).toBe('video_generation_v1');
        expect(state.currentPhase).toBe('phase_0');
        expect(state.completedPhases).toEqual([]);
    });
    it('should get status', () => {
        (0, engine_1.startWorkflow)('video_generation_v1');
        const status = (0, engine_1.getStatus)();
        expect(status.active).toBe(true);
        expect(status.state).not.toBeNull();
        expect(status.currentPhase).not.toBeNull();
    });
    it('should not transition without required artifacts', () => {
        (0, engine_1.startWorkflow)('video_generation_v1');
        const result = (0, engine_1.transitionToNextPhase)();
        expect(result.success).toBe(false);
        expect(result.errors.length).toBeGreaterThan(0);
    });
});
describe('Workflow Phase 2 - Strict Mode', () => {
    beforeEach(() => {
        (0, store_1.clearState)();
    });
    afterEach(() => {
        (0, store_1.clearState)();
    });
    it('should start workflow in strict mode', () => {
        const state = (0, engine_1.startWorkflow)('video_generation_v1', true);
        expect(state.strict).toBe(true);
    });
    it('should allow skills in non-strict mode', () => {
        (0, engine_1.startWorkflow)('video_generation_v1', false);
        const result = (0, engine_1.canRunSkill)('unauthorized-skill');
        expect(result.ok).toBe(true);
    });
    it('should block unauthorized skills in strict mode', () => {
        // Start in strict mode and move to phase_1
        (0, engine_1.startWorkflow)('video_generation_v1', true);
        const state = (0, store_1.loadState)();
        if (state) {
            state.currentPhase = 'phase_1';
            (0, store_1.saveState)(state);
        }
        // Phase 1 allows: vsl, launch-video, copywriting-helper, taiyo-style-vsl
        const result = (0, engine_1.canRunSkill)('unauthorized-skill');
        expect(result.ok).toBe(false);
        expect(result.reason).toContain('🔒 strict mode');
    });
    it('should allow authorized skills in strict mode', () => {
        // Start in strict mode and move to phase_1
        (0, engine_1.startWorkflow)('video_generation_v1', true);
        const state = (0, store_1.loadState)();
        if (state) {
            state.currentPhase = 'phase_1';
            (0, store_1.saveState)(state);
        }
        // Phase 1 allows: vsl
        const result = (0, engine_1.canRunSkill)('vsl');
        expect(result.ok).toBe(true);
    });
});
