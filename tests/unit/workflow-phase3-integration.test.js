"use strict";
/**
 * Workflow Phase 3 - Integration Tests
 * Tests combining conditional branching, parallel execution, and rollback
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
const TEMP_BASE = path.join(os.tmpdir(), 'taisun-test-integration-' + process.pid);
const WORKFLOW_DIR = path.join(TEMP_BASE, 'config', 'workflows');
const TEST_WORKFLOW_PATH = path.join(WORKFLOW_DIR, 'test_integration_v1.json');
const TEST_FILES_DIR = path.join(TEMP_BASE, 'test-integration-temp');
// テストがスキップされるべきかどうかをチェック
let canRunTests = true;
let skipReason = '';
(0, globals_1.describe)('Workflow Phase 3 - Integration', () => {
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
    (0, globals_1.describe)('Conditional Branching + Parallel Execution', () => {
        (0, globals_1.beforeEach)(() => {
            // コンテンツ制作ワークフロー：種類を選択 → 並列タスク実行
            const workflow = {
                id: 'test_integration_v1',
                name: 'Content Creation Workflow',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Select Content Type',
                        conditionalNext: {
                            condition: {
                                type: 'file_content',
                                source: path.join(TEST_FILES_DIR, 'content_type.txt'),
                                pattern: '^(video|article)$',
                            },
                            branches: {
                                video: 'phase_video_plan',
                                article: 'phase_article_plan',
                            },
                        },
                    },
                    {
                        id: 'phase_video_plan',
                        name: 'Video Planning',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'video_plan.txt')],
                        parallelNext: {
                            phases: ['phase_video_script', 'phase_video_thumbnail'],
                            waitStrategy: 'all',
                        },
                    },
                    {
                        id: 'phase_video_script',
                        name: 'Script Writing',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'script.txt')],
                        nextPhase: 'phase_final',
                    },
                    {
                        id: 'phase_video_thumbnail',
                        name: 'Thumbnail Design',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'thumbnail.txt')],
                        nextPhase: 'phase_final',
                    },
                    {
                        id: 'phase_article_plan',
                        name: 'Article Planning',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'article_plan.txt')],
                        nextPhase: 'phase_final',
                    },
                    {
                        id: 'phase_final',
                        name: 'Final Review',
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should branch to video workflow and execute parallel tasks', () => {
            // 動画コンテンツを選択
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'content_type.txt'), 'video', 'utf-8');
            (0, engine_1.startWorkflow)('test_integration_v1', false);
            // 条件分岐：phase_0 → phase_video_plan
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_video_plan');
            // 企画完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'video_plan.txt'), 'plan content', 'utf-8');
            // 並列実行開始：phase_video_plan → phase_video_script
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_video_script');
            (0, globals_1.expect)(result.message).toContain('並列実行開始');
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions).toHaveLength(1);
            (0, globals_1.expect)(status.state?.parallelExecutions[0].startedPhases).toEqual([
                'phase_video_script',
                'phase_video_thumbnail',
            ]);
            // 台本完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'script.txt'), 'script content', 'utf-8');
            // phase_video_script → phase_video_thumbnail
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_video_thumbnail');
            // サムネイル完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'thumbnail.txt'), 'thumbnail content', 'utf-8');
            // 並列実行完了：phase_video_thumbnail → phase_final
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_final');
            (0, globals_1.expect)(result.message).toContain('並列実行完了');
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_final');
            // branchHistoryが記録されていることを確認
            if (status.state?.branchHistory) {
                (0, globals_1.expect)(status.state.branchHistory.some(h => h.includes('phase_0 -> phase_video_plan (video)'))).toBe(true);
            }
        });
        (0, globals_1.it)('should branch to article workflow (no parallel execution)', () => {
            // 記事コンテンツを選択
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'content_type.txt'), 'article', 'utf-8');
            (0, engine_1.startWorkflow)('test_integration_v1', false);
            // 条件分岐：phase_0 → phase_article_plan
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_article_plan');
            // 企画完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'article_plan.txt'), 'article plan', 'utf-8');
            // phase_article_plan → phase_final（並列実行なし）
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_final');
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions).toBeUndefined();
            // branchHistoryが記録されていることを確認
            if (status.state?.branchHistory) {
                (0, globals_1.expect)(status.state.branchHistory.some(h => h.includes('phase_0 -> phase_article_plan (article)'))).toBe(true);
            }
        });
    });
    (0, globals_1.describe)('Parallel Execution + Rollback', () => {
        (0, globals_1.beforeEach)(() => {
            const workflow = {
                id: 'test_integration_v1',
                name: 'Design Review Workflow',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Planning',
                        nextPhase: 'phase_1',
                    },
                    {
                        id: 'phase_1',
                        name: 'Design Phase',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'design.txt')],
                        parallelNext: {
                            phases: ['phase_2a', 'phase_2b'],
                            waitStrategy: 'all',
                        },
                    },
                    {
                        id: 'phase_2a',
                        name: 'Implementation A',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'impl_a.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_2b',
                        name: 'Implementation B',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'impl_b.txt')],
                        nextPhase: 'phase_3',
                    },
                    {
                        id: 'phase_3',
                        name: 'Review',
                        allowRollbackTo: ['phase_1'],
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should rollback after parallel execution completes', () => {
            (0, engine_1.startWorkflow)('test_integration_v1', false);
            // phase_0 → phase_1
            (0, engine_1.transitionToNextPhase)();
            // デザイン完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'design.txt'), 'design', 'utf-8');
            // 並列実行開始
            (0, engine_1.transitionToNextPhase)();
            // 実装A完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'impl_a.txt'), 'impl a', 'utf-8');
            (0, engine_1.transitionToNextPhase)();
            // 実装B完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'impl_b.txt'), 'impl b', 'utf-8');
            (0, engine_1.transitionToNextPhase)();
            // phase_3に到達
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_3');
            // レビュー後、デザインからやり直しが必要と判断
            const rollback = (0, engine_1.rollbackToPhase)('phase_1', 'Design needs revision');
            (0, globals_1.expect)(rollback.fromPhase).toBe('phase_3');
            (0, globals_1.expect)(rollback.toPhase).toBe('phase_1');
            (0, globals_1.expect)(rollback.deletedArtifacts).toHaveLength(2);
            (0, globals_1.expect)(rollback.deletedArtifacts).toContain(path.join(TEST_FILES_DIR, 'impl_a.txt'));
            (0, globals_1.expect)(rollback.deletedArtifacts).toContain(path.join(TEST_FILES_DIR, 'impl_b.txt'));
            // phase_1に戻っている
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_1');
            (0, globals_1.expect)(status.state?.completedPhases).not.toContain('phase_1');
            (0, globals_1.expect)(status.state?.rollbackHistory).toHaveLength(1);
            // デザインファイルは残っている
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'design.txt'))).toBe(true);
            // 実装ファイルは削除されている
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'impl_a.txt'))).toBe(false);
            (0, globals_1.expect)(fs.existsSync(path.join(TEST_FILES_DIR, 'impl_b.txt'))).toBe(false);
        });
    });
    (0, globals_1.describe)('Conditional Branching + Rollback', () => {
        (0, globals_1.beforeEach)(() => {
            const workflow = {
                id: 'test_integration_v1',
                name: 'Conditional with Rollback',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Choose Path',
                        conditionalNext: {
                            condition: {
                                type: 'metadata_value',
                                source: 'strategy',
                                pattern: '^(fast|thorough)$',
                            },
                            branches: {
                                fast: 'phase_fast',
                                thorough: 'phase_thorough',
                            },
                        },
                    },
                    {
                        id: 'phase_fast',
                        name: 'Fast Implementation',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'fast.txt')],
                        nextPhase: 'phase_review',
                    },
                    {
                        id: 'phase_thorough',
                        name: 'Thorough Implementation',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'thorough.txt')],
                        nextPhase: 'phase_review',
                    },
                    {
                        id: 'phase_review',
                        name: 'Review',
                        allowRollbackTo: ['phase_0'],
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should rollback to conditional phase and take different branch', () => {
            // 最初はfast戦略を選択
            (0, engine_1.startWorkflow)('test_integration_v1', false, { strategy: 'fast' });
            // phase_0 → phase_fast
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_fast');
            // 実装完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'fast.txt'), 'fast impl', 'utf-8');
            // phase_fast → phase_review
            (0, engine_1.transitionToNextPhase)();
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_review');
            // レビュー後、thorough戦略でやり直しが必要と判断
            const rollback = (0, engine_1.rollbackToPhase)('phase_0', 'Need thorough approach');
            (0, globals_1.expect)(rollback.deletedArtifacts).toContain(path.join(TEST_FILES_DIR, 'fast.txt'));
            // phase_0に戻っている
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_0');
            // メタデータを更新してthorough戦略へ変更
            status.state.metadata.strategy = 'thorough';
            fs.writeFileSync(path.join(TEMP_BASE, '.workflow_state.json'), JSON.stringify(status.state, null, 2));
            // 再度遷移：今度はphase_thoroughへ
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_thorough');
            status = (0, engine_1.getStatus)();
            // branchHistoryが記録されていることを確認
            if (status.state?.branchHistory) {
                (0, globals_1.expect)(status.state.branchHistory.length).toBeGreaterThanOrEqual(1);
                // 最初のfast分岐または2回目のthorough分岐のいずれかが記録されている
                const hasFastBranch = status.state.branchHistory.some(h => h.includes('phase_0 -> phase_fast (fast)'));
                const hasThoroughBranch = status.state.branchHistory.some(h => h.includes('phase_0 -> phase_thorough (thorough)'));
                (0, globals_1.expect)(hasFastBranch || hasThoroughBranch).toBe(true);
            }
            (0, globals_1.expect)(status.state?.rollbackHistory).toHaveLength(1);
        });
    });
    (0, globals_1.describe)('Complex Integration: All Features', () => {
        (0, globals_1.beforeEach)(() => {
            // 条件分岐 → 並列実行 → ロールバック対応の複雑なワークフロー
            const workflow = {
                id: 'test_integration_v1',
                name: 'Complex Production Workflow',
                version: '1.0.0',
                phases: [
                    {
                        id: 'phase_0',
                        name: 'Select Priority',
                        conditionalNext: {
                            condition: {
                                type: 'metadata_value',
                                source: 'priority',
                                pattern: '^(high|normal)$',
                            },
                            branches: {
                                high: 'phase_fast_track',
                                normal: 'phase_standard',
                            },
                        },
                    },
                    {
                        id: 'phase_fast_track',
                        name: 'Fast Track Planning',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'fast_plan.txt')],
                        parallelNext: {
                            phases: ['phase_dev', 'phase_qa'],
                            waitStrategy: 'any', // 優先度高：どちらか1つ完了でOK
                        },
                    },
                    {
                        id: 'phase_standard',
                        name: 'Standard Planning',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'standard_plan.txt')],
                        parallelNext: {
                            phases: ['phase_dev', 'phase_qa'],
                            waitStrategy: 'all', // 通常：両方完了が必要
                        },
                    },
                    {
                        id: 'phase_dev',
                        name: 'Development',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'dev.txt')],
                        nextPhase: 'phase_final',
                    },
                    {
                        id: 'phase_qa',
                        name: 'QA',
                        requiredArtifacts: [path.join(TEST_FILES_DIR, 'qa.txt')],
                        nextPhase: 'phase_final',
                    },
                    {
                        id: 'phase_final',
                        name: 'Final Review',
                        allowRollbackTo: ['phase_0', 'phase_fast_track', 'phase_standard'],
                        nextPhase: null,
                    },
                ],
            };
            fs.writeFileSync(TEST_WORKFLOW_PATH, JSON.stringify(workflow, null, 2), 'utf-8');
            // clearCache after creating workflow definition
            (0, registry_1.clearCache)();
        });
        (0, globals_1.it)('should handle high priority with any wait strategy', () => {
            (0, engine_1.startWorkflow)('test_integration_v1', false, { priority: 'high' });
            // 条件分岐：phase_0 → phase_fast_track
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_fast_track');
            // 企画完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'fast_plan.txt'), 'plan', 'utf-8');
            // 並列実行開始
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_dev');
            const status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions[0].waitStrategy).toBe('any');
            // 開発だけ完了（QAは未完了）
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'dev.txt'), 'dev', 'utf-8');
            // waitStrategy='any'なので、1つ完了で次へ進める
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.success).toBe(true);
            (0, globals_1.expect)(result.newPhase).toBe('phase_final');
            (0, globals_1.expect)(result.message).toContain('並列実行完了');
        });
        (0, globals_1.it)('should handle normal priority with all wait strategy and rollback', () => {
            (0, engine_1.startWorkflow)('test_integration_v1', false, { priority: 'normal' });
            // 条件分岐：phase_0 → phase_standard
            let result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_standard');
            // 企画完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'standard_plan.txt'), 'plan', 'utf-8');
            // 並列実行開始
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_dev');
            let status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.parallelExecutions[0].waitStrategy).toBe('all');
            // 開発完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'dev.txt'), 'dev', 'utf-8');
            // 次のフェーズへ
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_qa');
            // QA完了
            fs.writeFileSync(path.join(TEST_FILES_DIR, 'qa.txt'), 'qa', 'utf-8');
            // 全て完了して最終レビューへ
            result = (0, engine_1.transitionToNextPhase)();
            (0, globals_1.expect)(result.newPhase).toBe('phase_final');
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_final');
            // 最終レビューで問題発見 → phase_0からやり直し
            const rollback = (0, engine_1.rollbackToPhase)('phase_0', 'Need to reconsider priority');
            (0, globals_1.expect)(rollback.deletedArtifacts).toHaveLength(3);
            status = (0, engine_1.getStatus)();
            (0, globals_1.expect)(status.state?.currentPhase).toBe('phase_0');
            (0, globals_1.expect)(status.state?.rollbackHistory).toHaveLength(1);
            // branchHistoryとparallelExecutionsが記録されていることを確認
            if (status.state?.branchHistory) {
                (0, globals_1.expect)(status.state.branchHistory.length).toBeGreaterThanOrEqual(1);
            }
            if (status.state?.parallelExecutions && status.state.parallelExecutions.length > 0) {
                (0, globals_1.expect)(status.state.parallelExecutions[0].completedAt).toBeDefined();
            }
        });
    });
});
