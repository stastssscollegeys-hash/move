"use strict";
/**
 * Workflow Phase 3 - Type Definitions Tests
 */
Object.defineProperty(exports, "__esModule", { value: true });
const globals_1 = require("@jest/globals");
(0, globals_1.describe)('Workflow Phase 3 - Type Definitions', () => {
    (0, globals_1.describe)('Conditional Branching Types', () => {
        (0, globals_1.it)('should accept valid ConditionType values', () => {
            const validTypes = [
                'file_content',
                'file_exists',
                'command_output',
                'metadata_value',
            ];
            validTypes.forEach((type) => {
                const condition = {
                    type,
                    source: 'test.txt',
                };
                (0, globals_1.expect)(condition.type).toBe(type);
            });
        });
        (0, globals_1.it)('should create valid Condition objects', () => {
            const condition = {
                type: 'file_content',
                source: 'content_type.txt',
                pattern: '^(video|article)$',
                expectedValue: 'video',
            };
            (0, globals_1.expect)(condition.type).toBe('file_content');
            (0, globals_1.expect)(condition.source).toBe('content_type.txt');
            (0, globals_1.expect)(condition.pattern).toBe('^(video|article)$');
            (0, globals_1.expect)(condition.expectedValue).toBe('video');
        });
        (0, globals_1.it)('should create valid ConditionalNext objects', () => {
            const conditionalNext = {
                condition: {
                    type: 'file_content',
                    source: 'type.txt',
                },
                branches: {
                    video: 'phase_video',
                    article: 'phase_article',
                },
                defaultNext: 'phase_default',
            };
            (0, globals_1.expect)(conditionalNext.branches.video).toBe('phase_video');
            (0, globals_1.expect)(conditionalNext.branches.article).toBe('phase_article');
            (0, globals_1.expect)(conditionalNext.defaultNext).toBe('phase_default');
        });
    });
    (0, globals_1.describe)('Parallel Execution Types', () => {
        (0, globals_1.it)('should create valid ParallelNext objects', () => {
            const parallelNext = {
                phases: ['phase_a', 'phase_b', 'phase_c'],
                waitStrategy: 'all',
                timeoutMs: 30000,
            };
            (0, globals_1.expect)(parallelNext.phases).toHaveLength(3);
            (0, globals_1.expect)(parallelNext.waitStrategy).toBe('all');
            (0, globals_1.expect)(parallelNext.timeoutMs).toBe(30000);
        });
        (0, globals_1.it)('should accept both wait strategies', () => {
            const waitAll = {
                phases: ['a', 'b'],
                waitStrategy: 'all',
            };
            const waitAny = {
                phases: ['a', 'b'],
                waitStrategy: 'any',
            };
            (0, globals_1.expect)(waitAll.waitStrategy).toBe('all');
            (0, globals_1.expect)(waitAny.waitStrategy).toBe('any');
        });
        (0, globals_1.it)('should create valid ParallelExecutionState objects', () => {
            const parallelState = {
                parallelGroupId: 'parallel_123',
                startedPhases: ['phase_a', 'phase_b'],
                completedPhases: ['phase_a'],
                waitStrategy: 'all',
                startedAt: new Date().toISOString(),
                completedAt: new Date().toISOString(),
            };
            (0, globals_1.expect)(parallelState.startedPhases).toHaveLength(2);
            (0, globals_1.expect)(parallelState.completedPhases).toHaveLength(1);
            (0, globals_1.expect)(parallelState.completedAt).toBeDefined();
        });
    });
    (0, globals_1.describe)('Rollback Types', () => {
        (0, globals_1.it)('should create valid RollbackHistory objects', () => {
            const rollback = {
                rollbackId: 'rollback_456',
                fromPhase: 'phase_3',
                toPhase: 'phase_1',
                reason: 'Design review required changes',
                deletedArtifacts: ['output.md', 'design.png'],
                timestamp: new Date().toISOString(),
                performedBy: 'user@example.com',
            };
            (0, globals_1.expect)(rollback.fromPhase).toBe('phase_3');
            (0, globals_1.expect)(rollback.toPhase).toBe('phase_1');
            (0, globals_1.expect)(rollback.deletedArtifacts).toHaveLength(2);
        });
        (0, globals_1.it)('should create valid PhaseSnapshot objects', () => {
            const snapshot = {
                phaseId: 'phase_2',
                artifacts: {
                    'file1.md': 'content1',
                    'file2.md': 'content2',
                },
                metadata: {
                    author: 'test',
                    version: '1.0',
                },
                timestamp: new Date().toISOString(),
            };
            (0, globals_1.expect)(snapshot.phaseId).toBe('phase_2');
            (0, globals_1.expect)(Object.keys(snapshot.artifacts)).toHaveLength(2);
            (0, globals_1.expect)(snapshot.metadata.author).toBe('test');
        });
    });
    (0, globals_1.describe)('Extended WorkflowPhase', () => {
        (0, globals_1.it)('should support Phase 1-2 basic nextPhase', () => {
            const phase = {
                id: 'phase_1',
                name: 'Phase 1',
                nextPhase: 'phase_2',
            };
            (0, globals_1.expect)(phase.nextPhase).toBe('phase_2');
        });
        (0, globals_1.it)('should support Phase 3 conditional branching', () => {
            const phase = {
                id: 'phase_0',
                name: 'Planning',
                conditionalNext: {
                    condition: {
                        type: 'file_content',
                        source: 'type.txt',
                    },
                    branches: {
                        video: 'video_phase',
                        article: 'article_phase',
                    },
                },
            };
            (0, globals_1.expect)(phase.conditionalNext).toBeDefined();
            (0, globals_1.expect)(phase.conditionalNext?.branches.video).toBe('video_phase');
        });
        (0, globals_1.it)('should support Phase 3 parallel execution', () => {
            const phase = {
                id: 'phase_prep',
                name: 'Preparation',
                parallelNext: {
                    phases: ['design', 'copy', 'seo'],
                    waitStrategy: 'all',
                },
            };
            (0, globals_1.expect)(phase.parallelNext).toBeDefined();
            (0, globals_1.expect)(phase.parallelNext?.phases).toHaveLength(3);
        });
        (0, globals_1.it)('should support Phase 3 rollback configuration', () => {
            const phase = {
                id: 'phase_3',
                name: 'Integration',
                allowRollbackTo: ['phase_1', 'phase_2'],
                snapshotEnabled: true,
            };
            (0, globals_1.expect)(phase.allowRollbackTo).toContain('phase_1');
            (0, globals_1.expect)(phase.snapshotEnabled).toBe(true);
        });
        (0, globals_1.it)('should maintain backward compatibility', () => {
            // Phase 1-2 style workflow should still work
            const oldStylePhase = {
                id: 'phase_1',
                name: 'Old Style Phase',
                nextPhase: 'phase_2',
                allowedSkills: ['skill1'],
                requiredArtifacts: ['artifact.md'],
            };
            (0, globals_1.expect)(oldStylePhase.id).toBe('phase_1');
            (0, globals_1.expect)(oldStylePhase.conditionalNext).toBeUndefined();
            (0, globals_1.expect)(oldStylePhase.parallelNext).toBeUndefined();
        });
    });
    (0, globals_1.describe)('Extended WorkflowState', () => {
        (0, globals_1.it)('should support Phase 3 parallel executions', () => {
            const state = {
                workflowId: 'test_workflow',
                currentPhase: 'phase_1',
                completedPhases: [],
                startedAt: new Date().toISOString(),
                lastUpdatedAt: new Date().toISOString(),
                strict: false,
                parallelExecutions: [
                    {
                        parallelGroupId: 'group_1',
                        startedPhases: ['a', 'b'],
                        completedPhases: [],
                        waitStrategy: 'all',
                        startedAt: new Date().toISOString(),
                    },
                ],
            };
            (0, globals_1.expect)(state.parallelExecutions).toHaveLength(1);
            (0, globals_1.expect)(state.parallelExecutions[0].startedPhases).toContain('a');
        });
        (0, globals_1.it)('should support Phase 3 rollback history', () => {
            const state = {
                workflowId: 'test_workflow',
                currentPhase: 'phase_1',
                completedPhases: [],
                startedAt: new Date().toISOString(),
                lastUpdatedAt: new Date().toISOString(),
                strict: false,
                rollbackHistory: [
                    {
                        rollbackId: 'rb_1',
                        fromPhase: 'phase_3',
                        toPhase: 'phase_1',
                        deletedArtifacts: ['file.md'],
                        timestamp: new Date().toISOString(),
                    },
                ],
            };
            (0, globals_1.expect)(state.rollbackHistory).toHaveLength(1);
            (0, globals_1.expect)(state.rollbackHistory[0].fromPhase).toBe('phase_3');
        });
        (0, globals_1.it)('should support Phase 3 snapshots', () => {
            const state = {
                workflowId: 'test_workflow',
                currentPhase: 'phase_2',
                completedPhases: ['phase_1'],
                startedAt: new Date().toISOString(),
                lastUpdatedAt: new Date().toISOString(),
                strict: false,
                snapshots: [
                    {
                        phaseId: 'phase_1',
                        artifacts: { 'file.md': 'content' },
                        metadata: {},
                        timestamp: new Date().toISOString(),
                    },
                ],
            };
            (0, globals_1.expect)(state.snapshots).toHaveLength(1);
            (0, globals_1.expect)(state.snapshots[0].phaseId).toBe('phase_1');
        });
        (0, globals_1.it)('should support Phase 3 branch history', () => {
            const state = {
                workflowId: 'test_workflow',
                currentPhase: 'video_phase',
                completedPhases: ['phase_0'],
                startedAt: new Date().toISOString(),
                lastUpdatedAt: new Date().toISOString(),
                strict: false,
                branchHistory: ['phase_0 -> video_phase (video)'],
            };
            (0, globals_1.expect)(state.branchHistory).toHaveLength(1);
            (0, globals_1.expect)(state.branchHistory[0]).toContain('video');
        });
        (0, globals_1.it)('should maintain backward compatibility', () => {
            // Phase 1-2 style state should still work
            const oldStyleState = {
                workflowId: 'old_workflow',
                currentPhase: 'phase_1',
                completedPhases: [],
                startedAt: new Date().toISOString(),
                lastUpdatedAt: new Date().toISOString(),
                strict: false,
            };
            (0, globals_1.expect)(oldStyleState.workflowId).toBe('old_workflow');
            (0, globals_1.expect)(oldStyleState.parallelExecutions).toBeUndefined();
            (0, globals_1.expect)(oldStyleState.rollbackHistory).toBeUndefined();
            (0, globals_1.expect)(oldStyleState.snapshots).toBeUndefined();
        });
    });
});
