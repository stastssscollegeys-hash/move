"use strict";
/**
 * Supervisor Graph - M6
 *
 * State machine for supervised execution
 *
 * Graph flow:
 * ingest → route → plan → (approval?) → execute_safe → finalize
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createSupervisorGraph = exports.resumeSupervisor = exports.runSupervisor = void 0;
const policy_1 = require("./policy");
const github_1 = require("./github");
const router_1 = require("../router");
const registry_1 = require("../internal/registry");
const memory_1 = require("../tools/memory");
const observability_1 = require("../observability");
/**
 * Generate unique run ID
 */
function generateRunId() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `run-${timestamp}-${random}`;
}
/**
 * State storage key prefix
 */
const STATE_KEY_PREFIX = 'supervisor-state-';
/**
 * Save supervisor state to memory for resume
 */
async function saveState(state, namespace = 'short-term') {
    try {
        // Include state key as tag for searchability
        const stateKey = `${STATE_KEY_PREFIX}${state.runId}`;
        const result = await (0, memory_1.memoryAdd)(JSON.stringify(state), namespace, {
            tags: ['supervisor', 'state', state.runId, state.step, stateKey],
            source: 'supervisor',
            metadata: { stateKey },
        });
        (0, observability_1.recordEvent)('supervisor_step', state.runId, 'ok', {
            metadata: { step: state.step, saved: true },
        });
        return result.referenceId;
    }
    catch (error) {
        console.error('[supervisor] Failed to save state:', error);
        (0, observability_1.recordEvent)('supervisor_step', state.runId, 'fail', {
            errorType: 'state_save_failed',
            errorMessage: error instanceof Error ? error.message : String(error),
        });
        return undefined;
    }
}
/**
 * Load supervisor state from memory
 */
async function loadState(runId) {
    try {
        const stateKey = `${STATE_KEY_PREFIX}${runId}`;
        const result = await (0, memory_1.memorySearch)(stateKey, {
            tags: ['supervisor', 'state', runId],
            includeContent: true,
            limit: 1,
        });
        // Type assertion for the data structure
        const data = result.data;
        if (!result.success || !data?.found || !data.results?.length) {
            return null;
        }
        const entry = data.results[0];
        const content = entry.contentPreview || entry.summary;
        if (!content) {
            return null;
        }
        return JSON.parse(content);
    }
    catch (error) {
        console.error('[supervisor] Failed to load state:', error);
        return null;
    }
}
/**
 * Create initial state
 */
function createInitialState(input, options = {}) {
    return {
        runId: options.runId || generateRunId(),
        input,
        step: 'ingest',
        requiresApproval: false,
        refIds: [],
        timestamps: {
            started: new Date().toISOString(),
        },
    };
}
/**
 * Ingest step: Parse and validate input
 */
async function ingestStep(state) {
    // Check for dangerous patterns in input
    const dangerousPatterns = (0, policy_1.checkDangerousPatterns)(state.input);
    // Create RUNLOG issue if gh is available
    const runlogIssue = await (0, github_1.createRunlogIssue)(state);
    return {
        ...state,
        step: 'route',
        runlogIssue: runlogIssue || undefined,
        route: dangerousPatterns.length > 0
            ? {
                action: 'require_human',
                reason: `Dangerous patterns detected: ${dangerousPatterns.join(', ')}`,
                confidence: 1.0,
                dangerousPatterns,
            }
            : undefined,
    };
}
/**
 * Route step: Determine target MCP and action
 */
async function routeStep(state) {
    // If already marked as require_human from ingest, keep that
    if (state.route?.action === 'require_human') {
        return {
            ...state,
            step: 'plan',
            requiresApproval: true,
        };
    }
    // Use the router to find target MCP
    const mcps = (0, registry_1.getAllMcps)();
    const config = (0, registry_1.getRouterConfig)();
    const routeResult = (0, router_1.route)(state.input, mcps, config);
    const route = {
        action: routeResult.action,
        reason: routeResult.reason,
        targetMcp: routeResult.candidates?.[0]?.name,
        confidence: routeResult.confidence ?? 0,
        dangerousPatterns: routeResult.matchedRule?.includes('dangerous')
            ? [routeResult.matchedRule]
            : undefined,
    };
    const needsApproval = (0, policy_1.requiresApproval)(state.input, route);
    return {
        ...state,
        step: 'plan',
        route,
        requiresApproval: needsApproval,
    };
}
/**
 * Plan step: Create execution plan
 */
async function planStep(state) {
    const dangerousPatterns = (0, policy_1.checkDangerousPatterns)(state.input);
    const needsApproval = dangerousPatterns.length > 0 || state.requiresApproval;
    // Create simple execution plan
    const plan = {
        steps: [
            (0, policy_1.createPlanStep)('1', 'analyze', state.input.substring(0, 100)),
            (0, policy_1.createPlanStep)('2', state.route?.targetMcp || 'process', 'user input'),
        ],
        estimatedRisk: dangerousPatterns.length > 0 ? 'high' : 'low',
        requiresApproval: needsApproval,
        approvalReason: needsApproval
            ? `Detected patterns: ${dangerousPatterns.join(', ') || 'requires human review'}`
            : undefined,
    };
    // Log plan to RUNLOG
    if (state.runlogIssue) {
        await (0, github_1.addIssueComment)(state.runlogIssue, `## Plan Created\n\n**Risk:** ${plan.estimatedRisk}\n**Requires Approval:** ${plan.requiresApproval}\n\n${plan.steps.map((s) => `- ${s.action}`).join('\n')}`);
    }
    return {
        ...state,
        step: needsApproval ? 'approval' : 'execute_safe',
        plan,
        requiresApproval: needsApproval,
    };
}
/**
 * Approval step: Wait for human approval
 */
async function approvalStep(state) {
    if (!state.plan) {
        return {
            ...state,
            step: 'error',
            error: 'No plan available for approval',
        };
    }
    // Create approval issue
    const approvalIssue = await (0, github_1.createApprovalIssue)(state, state.plan);
    if (!approvalIssue) {
        // If we can't create an issue, we can't proceed
        return {
            ...state,
            step: 'error',
            error: 'Could not create approval issue. Manual approval required.',
            approval: {
                required: true,
                approved: false,
                reason: 'Approval issue creation failed',
            },
        };
    }
    // Log to RUNLOG
    if (state.runlogIssue) {
        await (0, github_1.addIssueComment)(state.runlogIssue, `## Approval Required\n\nWaiting for approval on issue #${approvalIssue}\n\nThis run is paused until approval is granted.`);
    }
    return {
        ...state,
        step: 'approval', // Stay in approval state - paused
        approval: {
            required: true,
            approved: false,
            issueId: approvalIssue,
            reason: state.plan.approvalReason,
        },
    };
}
/**
 * Execute safe step: Execute the plan safely
 */
async function executeSafeStep(state, namespace = 'short-term') {
    // Validate plan is safe to execute
    if (state.plan) {
        const validation = (0, policy_1.validatePlan)(state.plan, state.approval?.approved || false);
        if (!validation.valid) {
            return {
                ...state,
                step: 'error',
                error: validation.reason,
            };
        }
    }
    // Execute (placeholder - actual execution depends on the MCP)
    const summary = `Executed plan for: ${state.input.substring(0, 100)}`;
    // Store result in memory
    const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
        runId: state.runId,
        input: state.input,
        route: state.route,
        plan: state.plan,
        executedAt: new Date().toISOString(),
    }), namespace, {
        tags: ['supervisor', 'execution', state.runId],
        source: 'supervisor',
    });
    // Log to RUNLOG
    if (state.runlogIssue) {
        await (0, github_1.addIssueComment)(state.runlogIssue, `## Execution Complete\n\n**Summary:** ${summary}\n**RefId:** ${memResult.referenceId || 'N/A'}`);
    }
    return {
        ...state,
        step: 'finalize',
        result: {
            success: true,
            summary,
            refId: memResult.referenceId,
        },
        refIds: memResult.referenceId ? [...state.refIds, memResult.referenceId] : state.refIds,
    };
}
/**
 * Finalize step: Complete the run
 */
async function finalizeStep(state) {
    const completedAt = new Date().toISOString();
    // Close RUNLOG issue if exists
    if (state.runlogIssue) {
        await (0, github_1.closeIssue)(state.runlogIssue, `## Run Completed\n\n**Success:** ${state.result?.success || false}\n**Completed:** ${completedAt}\n**RefIds:** ${state.refIds.join(', ') || 'N/A'}`);
    }
    return {
        ...state,
        step: 'finalize',
        timestamps: {
            ...state.timestamps,
            completed: completedAt,
        },
    };
}
/**
 * Error step: Handle errors
 */
async function errorStep(state) {
    // Log error to RUNLOG
    if (state.runlogIssue) {
        await (0, github_1.addIssueComment)(state.runlogIssue, `## Error\n\n**Error:** ${state.error || 'Unknown error'}\n\nRun aborted.`);
    }
    return {
        ...state,
        step: 'error',
        timestamps: {
            ...state.timestamps,
            completed: new Date().toISOString(),
        },
    };
}
/**
 * Run the supervisor state machine
 */
async function runSupervisor(input, options = {}) {
    const namespace = options.namespace || 'short-term';
    let state = createInitialState(input, options);
    const maxSteps = options.maxSteps || 10;
    let stepCount = 0;
    // Record start event
    (0, observability_1.recordEvent)('supervisor_step', state.runId, 'ok', {
        metadata: { step: 'start', input: input.substring(0, 100) },
    });
    try {
        while (stepCount < maxSteps) {
            stepCount++;
            switch (state.step) {
                case 'ingest':
                    state = await ingestStep(state);
                    await saveState(state, namespace);
                    break;
                case 'route':
                    state = await routeStep(state);
                    await saveState(state, namespace);
                    break;
                case 'plan':
                    state = await planStep(state);
                    await saveState(state, namespace);
                    break;
                case 'approval':
                    // If approval required and not yet approved, pause here
                    if (state.requiresApproval && !state.approval?.approved) {
                        state = await approvalStep(state);
                        // Save state for resume
                        await saveState(state, namespace);
                        // Record pause event
                        (0, observability_1.recordEvent)('supervisor_pause', state.runId, 'ok', {
                            metadata: { approvalIssue: state.approval?.issueId },
                        });
                        // Return paused state
                        return {
                            success: false,
                            runId: state.runId,
                            step: state.step,
                            summary: 'Waiting for approval',
                            requiresApproval: true,
                            approvalIssue: state.approval?.issueId,
                            data: {
                                runlogIssue: state.runlogIssue,
                                timestamps: state.timestamps,
                                plan: state.plan,
                            },
                        };
                    }
                    // If approved, move to execute
                    state = { ...state, step: 'execute_safe' };
                    await saveState(state, namespace);
                    break;
                case 'execute_safe':
                    state = await executeSafeStep(state, namespace);
                    await saveState(state, namespace);
                    break;
                case 'finalize':
                    state = await finalizeStep(state);
                    // Record completion
                    (0, observability_1.recordEvent)('supervisor_step', state.runId, 'ok', {
                        metadata: { step: 'finalize', success: state.result?.success },
                    });
                    // Done
                    return {
                        success: state.result?.success || false,
                        runId: state.runId,
                        step: state.step,
                        summary: state.result?.summary,
                        refId: state.result?.refId,
                        requiresApproval: state.requiresApproval,
                        data: {
                            runlogIssue: state.runlogIssue,
                            timestamps: state.timestamps,
                        },
                    };
                case 'error':
                    state = await errorStep(state);
                    (0, observability_1.recordEvent)('supervisor_step', state.runId, 'fail', {
                        errorType: 'execution_error',
                        errorMessage: state.error,
                    });
                    return {
                        success: false,
                        runId: state.runId,
                        step: state.step,
                        requiresApproval: state.requiresApproval,
                        error: state.error,
                        data: {
                            runlogIssue: state.runlogIssue,
                            timestamps: state.timestamps,
                        },
                    };
                default:
                    (0, observability_1.recordEvent)('supervisor_step', state.runId, 'fail', {
                        errorType: 'unknown_step',
                        errorMessage: `Unknown step: ${state.step}`,
                    });
                    return {
                        success: false,
                        runId: state.runId,
                        step: 'error',
                        requiresApproval: false,
                        error: `Unknown step: ${state.step}`,
                    };
            }
        }
        // Max steps reached
        (0, observability_1.recordEvent)('supervisor_step', state.runId, 'fail', {
            errorType: 'max_steps',
            errorMessage: `Max steps (${maxSteps}) reached`,
        });
        return {
            success: false,
            runId: state.runId,
            step: 'error',
            requiresApproval: state.requiresApproval,
            error: `Max steps (${maxSteps}) reached`,
        };
    }
    catch (err) {
        (0, observability_1.recordEvent)('supervisor_step', state.runId, 'fail', {
            errorType: 'exception',
            errorMessage: err instanceof Error ? err.message : String(err),
        });
        return {
            success: false,
            runId: state.runId,
            step: 'error',
            requiresApproval: false,
            error: err instanceof Error ? err.message : String(err),
        };
    }
}
exports.runSupervisor = runSupervisor;
/**
 * Resume a paused supervisor run
 */
async function resumeSupervisor(runId, approvalIssueId, options = {}) {
    const endTimer = (0, observability_1.startTimer)('supervisor_resume', runId);
    // Load saved state
    const savedState = await loadState(runId);
    if (!savedState) {
        endTimer('fail', { errorType: 'state_not_found' });
        return {
            success: false,
            runId,
            step: 'error',
            requiresApproval: false,
            error: `No saved state found for runId: ${runId}. State may have expired (TTL).`,
        };
    }
    // Get approval issue ID from saved state if not provided
    const issueId = approvalIssueId || savedState.approval?.issueId;
    // If we're in approval state, check approval status
    if (savedState.step === 'approval' && issueId) {
        const approvalStatus = await (0, github_1.checkApproval)(issueId);
        if (!approvalStatus.approved) {
            endTimer('ok');
            return {
                success: false,
                runId,
                step: 'approval',
                summary: 'Still waiting for approval',
                requiresApproval: true,
                approvalIssue: issueId,
                data: {
                    runlogIssue: savedState.runlogIssue,
                    timestamps: savedState.timestamps,
                },
            };
        }
        // Approval granted - update state and continue
        (0, observability_1.recordEvent)('supervisor_resume', runId, 'ok', {
            metadata: { approvedBy: approvalStatus.approvedBy },
        });
        const approvedState = {
            ...savedState,
            step: 'execute_safe',
            approval: {
                required: true,
                approved: true,
                issueId,
                approvedBy: approvalStatus.approvedBy,
                approvedAt: new Date().toISOString(),
            },
        };
        // Save updated state
        await saveState(approvedState, options.namespace || 'short-term');
        // Continue execution from where we left off
        const namespace = options.namespace || 'short-term';
        let state = approvedState;
        const maxSteps = options.maxSteps || 10;
        let stepCount = 0;
        try {
            while (stepCount < maxSteps) {
                stepCount++;
                switch (state.step) {
                    case 'execute_safe':
                        state = await executeSafeStep(state, namespace);
                        await saveState(state, namespace);
                        break;
                    case 'finalize':
                        state = await finalizeStep(state);
                        endTimer('ok');
                        return {
                            success: state.result?.success || false,
                            runId: state.runId,
                            step: state.step,
                            summary: state.result?.summary,
                            refId: state.result?.refId,
                            requiresApproval: false,
                            data: {
                                runlogIssue: state.runlogIssue,
                                timestamps: state.timestamps,
                                resumedFrom: 'approval',
                            },
                        };
                    case 'error':
                        state = await errorStep(state);
                        endTimer('fail', { errorType: 'execution_error' });
                        return {
                            success: false,
                            runId: state.runId,
                            step: state.step,
                            requiresApproval: false,
                            error: state.error,
                            data: {
                                runlogIssue: state.runlogIssue,
                                timestamps: state.timestamps,
                            },
                        };
                    default:
                        endTimer('fail', { errorType: 'unexpected_step' });
                        return {
                            success: false,
                            runId: state.runId,
                            step: 'error',
                            requiresApproval: false,
                            error: `Unexpected step during resume: ${state.step}`,
                        };
                }
            }
            endTimer('fail', { errorType: 'max_steps' });
            return {
                success: false,
                runId: state.runId,
                step: 'error',
                requiresApproval: false,
                error: `Max steps (${maxSteps}) reached during resume`,
            };
        }
        catch (err) {
            endTimer('fail', { errorType: 'exception' });
            return {
                success: false,
                runId: state.runId,
                step: 'error',
                requiresApproval: false,
                error: err instanceof Error ? err.message : String(err),
            };
        }
    }
    // If not in approval state, just return the current state
    endTimer('ok');
    return {
        success: savedState.step === 'finalize',
        runId,
        step: savedState.step,
        summary: savedState.result?.summary,
        refId: savedState.result?.refId,
        requiresApproval: savedState.requiresApproval,
        approvalIssue: savedState.approval?.issueId,
        data: {
            runlogIssue: savedState.runlogIssue,
            timestamps: savedState.timestamps,
        },
    };
}
exports.resumeSupervisor = resumeSupervisor;
/**
 * Create supervisor graph (simplified - for compatibility)
 */
function createSupervisorGraph(options = {}) {
    return {
        invoke: async (input) => runSupervisor(input, options),
    };
}
exports.createSupervisorGraph = createSupervisorGraph;
