"use strict";
/**
 * Workflow Phase 3 - Rollback Tests
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
const TEMP_BASE = path.join(os.tmpdir(), 'taisun-test-rollback-' + process.pid);
const WORKFLOW_DIR = path.join(TEMP_BASE, 'config', 'workflows');
const TEST_WORKFLOW_PATH = path.join(WORKFLOW_DIR, 'test_rollback_v1.json');
const TEST_FILES_DIR = path.join(TEMP_BASE, 'test-rollback-temp');
// テストがスキップされるべきかどうかをチェック
let canRunTests = true;
let skipReason = '';
(0, globals_1.describe)('Workflow Phase 3 - Rollback', () => {
    // 一時ディレクトリのセットアップ（全テスト開始前）
    (0, globals_1.beforeAll)(() => {
        try {
            // ベースディレクトリ作成
            fs.mkdirSync(TEMP_BASE, { recursive: true });
            fs.mkdirSync(WORKFLOW_DIR, { recursive: true });
            fs.mkdirSync(TEST_FILES_DIR, { recursive: true });
            // 書き込みテスト
            const testFile = path.join(TEMP_BASE, '.write-test');
            fs.writeFileSync(testFile, 'test', 'utf-8');
            fs.unlinkSync(testFile);
            // ワークフローディレクトリをテスト用に設定
            (0, registry_1.setWorkflowsDir)(WORKFLOW_DIR);
            // 状態ファイルディレクトリをテスト用に設定
            (0, store_1.setStateDir)(TEMP_BASE);
        }
        catch (error) {
            canRunTests = false;
            skipReason = `Cannot create temp directories: ${error.message}`;
            console.warn(`Skipping tests: ${skipReason}`);
        }
    });
    // 一時ディレクトリのクリーンアップ（全テスト終了後）
    (0, globals_1.afterAll)(() => {
        // ワークフローディレクトリをリセット
        (0, registry_1.resetWorkflowsDir)();
        // 状態ファイルディレクトリをリセット
        (0, store_1.resetStateDir)();
        try {
            if (fs.existsSync(TEMP_BASE)) {
                fs.rmSync(TEMP_BASE, { recursive: true, force: true });
            }
        }
        catch (error) {
            // クリーンアップエラーは無視
            console.warn(`Cleanup warning: ${error.message}`);
        }
    });
    (0, globals_1.beforeEach)(() => {
        // 権限問題でテストをスキップ
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
        // 権限問題でテストをスキップ
        if (!canRunTests) {
            return;
        }
        try {
            if (fs.existsSync(TEST_FILES_DIR)) {
                fs.rmSync(TEST_FILES_DIR, { recursive: true, force: true });
            }
            // テスト用ディレクトリを再作成（次のテスト用）
            fs.mkdirSync(TEST_FILES_DIR, { recursive: true });
            if (fs.existsSync(TEST_WORKFLOW_PATH)) {
                fs.unlinkSync(TEST_WORKFLOW_PATH);
            }
        }
        catch (error) {
            // クリーンアップエラーは無視
            console.warn(`Cleanup warning: ${error.message}`);
        }
        // ワークフロー状態のクリーンアップ
        (0, store_1.clearState)();
        (0, registry_1.clearCache)();
    });
    (0, globals_1.describe)('basic rollback functionality', () => {
        (0, globals_1.beforeEach)(() => {
            if (!canRunTests) {
                return;
            }
            (0, registry_1.clearCache)();
            const workflow = {
                id: 'test_rollback_v1',
                name: 'Rollback Test Workflow',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Planning',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'Design',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'design.txt')],
                        nextPhase: 'phase_2',
                    },
                    {
                        id: 'phase_2',
                        name: 'Implementation',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'code.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_3',
                        name: 'Testing',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'tests.txt')],
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
        });
        (0, globals_1.it)('should rollback from phase_2 to phase_1 and delete artifacts', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            // Advance to phase_2
            (0, engine_1.transitionToNextPhase)(); // phase_0 → phase_1
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design content');
            (0, engine_1.transitionToNextPhase)(); // phase_1 → phase_2
            // Create phase_2 artifact
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'code.txt'), 'code content');
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_2');
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'code.txt'))).toBe(true);
            // Rollback to phase_1
            const result = (0, engine_1.rollbackToPhase)('phase_1', 'Need to revise design');
            (0, globals_1.expect)(result.fromPhase).toBe('phase_2');
            (0, globals_1.expect)(result.toPhase).toBe('phase_1');
            (0, globals_1.expect)(result.reason).toBe('Need to revise design');
            (0, globals_1.expect)(result.deletedArtifacts).toContain(path.join(TEST_FILES_DIR, 'code.txt'));
            (0, globals_1.expect)(result.rollbackId).toMatch(/^rollback_\d+$/);
            // Verify current phase
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_1');
            (0, globals_1.expect)(status.state?.completedPhases).toContain('phase_0');
            (0, globals_1.expect)(status.state?.completedPhases).not.toContain('phase_1');
            (0, globals_1.expect)(status.state?.completedPhases).not.toContain('phase_2');
            // Verify artifact deletion
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'code.txt'))).toBe(false);
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'design.txt'))).toBe(true);
            // Verify rollback history
            (0, globals_1.expect)(status.state?.rollbackHistory).toHaveLength(1);
            (0, globals_1.expect)(status.state?.rollbackHistory[0].fromPhase).toBe('phase_2');
            (0, globals_1.expect)(status.state?.rollbackHistory[0].toPhase).toBe('phase_1');
        });
        (0, globals_1.it)('should rollback multiple phases and delete all intermediate artifacts', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            // Advance to phase_3
            (0, engine_1.transitionToNextPhase)(); // phase_0 → phase_1
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design');
            (0, engine_1.transitionToNextPhase)(); // phase_1 → phase_2
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'code.txt'), 'code');
            (0, engine_1.transitionToNextPhase)(); // phase_2 → phase_3
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'tests.txt'), 'tests');
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_3');
            // Rollback to phase_1
            const result = (0, engine_1.rollbackToPhase)('phase_1');
            (0, globals_1.expect)(result.deletedArtifacts).toHaveLength(2);
            (0, globals_1.expect)(result.deletedArtifacts).toContain(path.join(TEST_FILES_DIR, 'code.txt'));
            (0, globals_1.expect)(result.deletedArtifacts).toContain(path.join(TEST_FILES_DIR, 'tests.txt'));
            // Verify current phase
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_1');
            // Verify artifact deletions
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'design.txt'))).toBe(true);
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'code.txt'))).toBe(false);
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'tests.txt'))).toBe(false);
        });
        (0, globals_1.it)('should record multiple rollbacks in history', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            // Advance to phase_2
            (0, engine_1.transitionToNextPhase)();
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design');
            (0, engine_1.transitionToNextPhase)();
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'code.txt'), 'code');
            // First rollback
            (0, engine_1.rollbackToPhase)('phase_1', 'First revision');
            // Re-advance
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design v2');
            (0, engine_1.transitionToNextPhase)();
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'code.txt'), 'code v2');
            // Second rollback
            (0, engine_1.rollbackToPhase)('phase_1', 'Second revision');
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.rollbackHistory).toHaveLength(2);
            (0, globals_1.expect)(status.state?.rollbackHistory[0].reason).toBe('First revision');
            (0, globals_1.expect)(status.state?.rollbackHistory[1].reason).toBe('Second revision');
        });
    });
    (0, globals_1.describe)('rollback restrictions', () => {
        (0, globals_1.beforeEach)(() => {
            if (!canRunTests) {
                return;
            }
            (0, registry_1.clearCache)();
            const workflow = {
                id: 'test_rollback_v1',
                name: 'Rollback Restrictions Test',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Planning',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'Design',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'design.txt')],
                        nextPhase: 'phase_2',
                    },
                    {
                        id: 'phase_2',
                        name: 'Implementation',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'code.txt')],
                        allowRollbackTo: ['phase_1'], // Only allow rollback to phase_1
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_3',
                        name: 'Testing',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
        });
        (0, globals_1.it)('should allow rollback when specified in allowRollbackTo', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            (0, engine_1.transitionToNextPhase)();
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design');
            (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(() => (0, engine_1.rollbackToPhase)('phase_1')).not.toThrow();
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_1');
        });
        (0, globals_1.it)('should reject rollback when not in allowRollbackTo', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            (0, engine_1.transitionToNextPhase)();
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design');
            (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(() => (0, engine_1.rollbackToPhase)('phase_0')).toThrow('Rollback to phase_0 is not allowed from phase_2');
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_2');
        });
    });
    (0, globals_1.describe)('error handling', () => {
        (0, globals_1.beforeEach)(() => {
            if (!canRunTests) {
                return;
            }
            (0, registry_1.clearCache)();
            const workflow = {
                id: 'test_rollback_v1',
                name: 'Error Handling Test',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Start',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'End',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
        });
        (0, globals_1.it)('should throw error when no active workflow', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, globals_1.expect)(() => (0, engine_1.rollbackToPhase)('phase_0')).toThrow('No active workflow');
        });
        (0, globals_1.it)('should throw error when target phase does not exist', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            (0, globals_1.expect)(() => (0, engine_1.rollbackToPhase)('phase_nonexistent')).toThrow('Phase phase_nonexistent not found in workflow');
        });
    });
    (0, globals_1.describe)('backward compatibility', () => {
        (0, globals_1.it)('should work with workflows without rollback features', () => {
            if (!canRunTests) {
                console.log(`Skipped: ${skipReason}`);
                return;
            }
            (0, registry_1.clearCache)();
            const workflow = {
                id: 'test_rollback_v1',
                name: 'Old Style Workflow',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Start',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'End',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            (0, engine_1.startWorkflow)('test_rollback_v1', false);
            (0, engine_1.transitionToNextPhase)();
            // Rollback should work even without allowRollbackTo
            (0, globals_1.expect)(() => (0, engine_1.rollbackToPhase)('phase_0')).not.toThrow();
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_0');
        });
    });
});
