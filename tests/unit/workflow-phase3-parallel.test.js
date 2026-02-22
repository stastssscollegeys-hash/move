"use strict";
/**
 * Workflow Phase 3 - Parallel Execution Tests
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
const globals_1 = require("@jest/globals");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const os = __importStar(require("os"));
const engine_1 = require("../../src/proxy-mcp/workflow/engine");
const store_1 = require("../../src/proxy-mcp/workflow/store");
const registry_1 = require("../../src/proxy-mcp/workflow/registry");
// テスト用のディレクトリ（OSの一時ディレクトリを使用して権限問題を回避）
const TEMP_BASE = path.join(os.tmpdir(), 'taisun-test-parallel-' + process.pid);
const WORKFLOW_DIR = path.join(TEMP_BASE, 'config', 'workflows');
const TEST_WORKFLOW_PATH = path.join(WORKFLOW_DIR, 'test_parallel_v1.json');
const TEST_FILES_DIR = path.join(TEMP_BASE, 'test-parallel-temp');
// テストがスキップされるべきかどうかをチェック
let canRunTests = true;
let skipReason = '';
(0, globals_1.describe)('Workflow Phase 3 - Parallel Execution', () => {
    // 一時ディレクトリのセットアップ（全テスト開始前）
    (0, globals_1.beforeAll)(() => {
        try {
            fs.mkdirSync(TEMP_BASE, { recursive: true });
            fs.mkdirSync(WORKFLOW_DIR, { recursive: true });
            fs.mkdirSync(TEST_FILES_DIR, { recursive: true });
            const testFile = path.join(TEMP_BASE, '.write-test');
            fs.writeFileSync(testFile, 'test', 'utf-8');
            fs.unlinkSync(testFile);
            (0, registry_1.setWorkflowsDir)(WORKFLOW_DIR);
            (0, store_1.setStateDir)(TEMP_BASE);
        }
        catch (error) {
            canRunTests = false;
            skipReason = `Cannot create temp directories: ${error.message}`;
            console.warn(`Skipping tests: ${skipReason}`);
        }
    });
    (0, globals_1.afterAll)(() => {
        (0, registry_1.resetWorkflowsDir)();
        (0, store_1.resetStateDir)();
        try {
            if (fs.existsSync(TEMP_BASE)) {
                fs.rmSync(TEMP_BASE, { recursive: true, force: true });
            }
        }
        catch (error) {
            console.warn(`Cleanup warning: ${error.message}`);
        }
    });
    (0, globals_1.beforeEach)(() => {
        if (!canRunTests) {
            return;
        }
        (0, registry_1.clearCache)();
        try {
            if (!fs.existsSync(TEST_FILES_DIR)) {
                fs.mkdirSync(TEST_FILES_DIR, { recursive: true });
            }
            if (!fs.existsSync(WORKFLOW_DIR)) {
                fs.mkdirSync(WORKFLOW_DIR, { recursive: true });
            }
        }
        catch (error) {
            console.warn(`Setup warning: ${error.message}`);
        }
    });
    (0, globals_1.afterEach)(() => {
        if (!canRunTests) {
            return;
        }
        try {
            if (fs.existsSync(TEST_FILES_DIR)) {
                fs.rmSync(TEST_FILES_DIR, { recursive: true, force: true });
            }
            fs.mkdirSync(TEST_FILES_DIR, { recursive: true });
            if (fs.existsSync(TEST_WORKFLOW_PATH)) {
                fs.unlinkSync(TEST_WORKFLOW_PATH);
            }
        }
        catch (error) {
            console.warn(`Cleanup warning: ${error.message}`);
        }
        (0, store_1.clearState)();
        (0, registry_1.clearCache)();
    });
    (0, globals_1.describe)('waitStrategy: all', () => {
        (0, globals_1.beforeEach)(() => {
            const workflow = {
                id: 'test_parallel_v1',
                name: 'Parallel Execution Test (All)',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Preparation',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'Start Parallel',
                        parallelNext: {
                            phases: ['phase_2a', 'phase_2b', 'phase_2c'],
                            waitStrategy: 'all',
                        },
                    },
                    {
                        id: 'phase_2a',
                        name: 'Design',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'design.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_2b',
                        name: 'Copy',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'copy.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_2c',
                        name: 'SEO',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'seo.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_3',
                        name: 'Integration',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should start parallel execution and transition to first parallel phase', () => {
            (0, engine_1.startWorkflow)('test_parallel_v1', false);
            // phase_0 → phase_1
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_1');
            // phase_1 → phase_2a (並列実行開始)
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_2a');
            (0, globals_1.expect)(result.message).toContain('並列実行開始');
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_2a');
            (0, globals_1.expect)(status.state?.parallelExecutions).toHaveLength(1);
            (0, globals_1.expect)(status.state?.parallelExecutions[0].startedPhases).toEqual([
                'phase_2a',
                'phase_2b',
                'phase_2c',
            ]);
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toEqual([]);
            (0, globals_1.expect)(status.state?.parallelExecutions[0].waitStrategy).toBe('all');
        });
        (0, globals_1.it)('should transition through all parallel phases with waitStrategy=all', () => {
            (0, engine_1.startWorkflow)('test_parallel_v1', false);
            // phase_0 → phase_1 → phase_2a
            (0, engine_1.transitionToNextPhase)();
            (0, engine_1.transitionToNextPhase)();
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_2a');
            // phase_2a 完了 → phase_2b
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'done');
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_2b');
            (0, globals_1.expect)(result.message).toContain('次の並列フェーズ');
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toContain('phase_2a');
            // phase_2b 完了 → phase_2c
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'copy.txt'), 'done');
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_2c');
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toContain('phase_2b');
            // phase_2c 完了 → phase_3 (並列実行完了)
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'seo.txt'), 'done');
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_3');
            (0, globals_1.expect)(result.message).toContain('並列実行完了');
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_3');
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toHaveLength(3);
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedAt).toBeDefined();
        });
    });
    (0, globals_1.describe)('waitStrategy: any', () => {
        (0, globals_1.beforeEach)(() => {
            const workflow = {
                id: 'test_parallel_v1',
                name: 'Parallel Execution Test (Any)',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Preparation',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'Start Parallel',
                        parallelNext: {
                            phases: ['phase_2a', 'phase_2b'],
                            waitStrategy: 'any',
                        },
                    },
                    {
                        id: 'phase_2a',
                        name: 'Fast Path',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'fast.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_2b',
                        name: 'Slow Path',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'slow.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_3',
                        name: 'Integration',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should complete parallel execution when any phase completes', () => {
            (0, engine_1.startWorkflow)('test_parallel_v1', false);
            // phase_0 → phase_1 → phase_2a
            (0, engine_1.transitionToNextPhase)();
            (0, engine_1.transitionToNextPhase)();
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_2a');
            (0, globals_1.expect)(status.state?.parallelExecutions[0].waitStrategy).toBe('any');
            // phase_2a 完了 → すぐに phase_3 に進む（waitStrategy='any'なので1つでも完了したらOK）
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'fast.txt'), 'done');
            const result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_3');
            (0, globals_1.expect)(result.message).toContain('並列実行完了');
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_3');
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toContain('phase_2a');
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedAt).toBeDefined();
        });
    });
    (0, globals_1.describe)('parallel execution state management', () => {
        (0, globals_1.beforeEach)(() => {
            const workflow = {
                id: 'test_parallel_v1',
                name: 'Parallel State Test',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Start',
                        parallelNext: {
                            phases: ['phase_1a', 'phase_1b'],
                            waitStrategy: 'all',
                        },
                    },
                    {
                        id: 'phase_1a',
                        name: 'Task A',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'a.txt')],
                        nextPhase: 'phase_2',
                    },
                    {
                        id: 'phase_1b',
                        name: 'Task B',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'b.txt')],
                        nextPhase: 'phase_2',
                    },
                    {
                        id: 'phase_2',
                        name: 'End',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should track parallel execution state correctly', () => {
            (0, engine_1.startWorkflow)('test_parallel_v1', false);
            // 並列実行開始
            let result = (0, engine_1.transitionToNextPhase)();
            let status = (0, engine_1.getStatus)();
            const parallelExecution = status.state?.parallelExecutions[0];
            (0, globals_1.expect)(parallelExecution?.parallelGroupId).toMatch(/^parallel_\d+$/);
            (0, globals_1.expect)(parallelExecution?.startedPhases).toEqual(['phase_1a', 'phase_1b']);
            (0, globals_1.expect)(parallelExecution?.completedPhases).toEqual([]);
            (0, globals_1.expect)(parallelExecution?.startedAt).toBeDefined();
            (0, globals_1.expect)(parallelExecution?.completedAt).toBeUndefined();
            // 最初のフェーズ完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'a.txt'), 'done');
            result = (0, engine_1.transitionToNextPhase)();
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toContain('phase_1a');
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedAt).toBeUndefined();
            // 2番目のフェーズ完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'b.txt'), 'done');
            result = (0, engine_1.transitionToNextPhase)();
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedPhases).toHaveLength(2);
            (0, globals_1.expect)(status.state?.parallelExecutions[0].completedAt).toBeDefined();
        });
    });
    (0, globals_1.describe)('backward compatibility', () => {
        (0, globals_1.it)('should work with Phase 1-2 workflows (no parallelNext)', () => {
            (0, registry_1.clearCache)();
            const workflow = {
                id: 'test_parallel_v1',
                name: 'Old Style',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Phase 0',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'Phase 1',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            (0, engine_1.startWorkflow)('test_parallel_v1', false);
            const result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_1');
            (0, globals_1.expect)(result.message).not.toContain('並列');
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions).toBeUndefined();
        });
    });
    (0, globals_1.describe)('error handling', () => {
        (0, globals_1.it)('should handle missing artifacts in parallel phases', () => {
            (0, registry_1.clearCache)();
            const workflow = {
                id: 'test_parallel_v1',
                name: 'Error Test',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Start',
                        parallelNext: {
                            phases: ['phase_1'],
                            waitStrategy: 'all',
                        },
                    },
                    {
                        id: 'phase_1',
                        name: 'Task',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'missing.txt')],
                        nextPhase: 'phase_2',
                    },
                    {
                        id: 'phase_2',
                        name: 'End',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            (0, engine_1.startWorkflow)('test_parallel_v1', false);
            (0, engine_1.transitionToNextPhase)(); // Start parallel
            // Try to complete without artifact
            const result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(false);
            (0, globals_1.expect)(result.errors[0]).toContain('必須成果物が見つかりません');
        });
    });
});
