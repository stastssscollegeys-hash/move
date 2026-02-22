"use strict";
/**
 * GitHub Integration - M6
 *
 * Issue logging and approval management
 * P20 Update: i18n support for Japanese default
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.closeIssue = exports.addIssueComment = exports.checkApproval = exports.createApprovalIssue = exports.createRunlogIssue = exports.getDefaultRepo = exports.isGhAvailable = void 0;
const child_process_1 = require("child_process");
const i18n_1 = require("../../i18n");
/**
 * Check if gh CLI is available
 */
function isGhAvailable() {
    try {
        (0, child_process_1.execSync)('gh --version', { stdio: 'pipe' });
        return true;
    }
    catch {
        return false;
    }
}
exports.isGhAvailable = isGhAvailable;
/**
 * Get default repository from git remote
 */
function getDefaultRepo() {
    try {
        const remote = (0, child_process_1.execSync)('git remote get-url origin', { encoding: 'utf8', stdio: 'pipe' }).trim();
        // Parse GitHub URL
        const match = remote.match(/github\.com[/:]([\w-]+\/[\w-]+)/);
        if (match) {
            return match[1].replace(/\.git$/, '');
        }
        return null;
    }
    catch {
        return null;
    }
}
exports.getDefaultRepo = getDefaultRepo;
/**
 * Create a RUNLOG issue for tracking the supervisor run
 */
async function createRunlogIssue(state, repo) {
    // Skip GitHub issue creation in test environment
    if (process.env.NODE_ENV === 'test') {
        console.debug('[Supervisor] Skipping GitHub issue creation in test environment');
        return null;
    }
    if (!isGhAvailable()) {
        console.warn('[Supervisor] gh CLI not available, skipping RUNLOG issue');
        return null;
    }
    const targetRepo = repo || getDefaultRepo();
    if (!targetRepo) {
        console.warn('[Supervisor] Could not determine repository, skipping RUNLOG issue');
        return null;
    }
    const body = (0, i18n_1.t)('supervisor.runlog.body', {
        runId: state.runId,
        inputPreview: state.input.substring(0, 200) + (state.input.length > 200 ? '...' : ''),
        startedAt: state.timestamps.started,
        step: state.step,
    });
    try {
        // Use spawnSync with array arguments to prevent command injection
        const result = (0, child_process_1.spawnSync)('gh', [
            'issue', 'create',
            '--repo', targetRepo,
            '--title', `[SUPERVISOR] ${state.runId}`,
            '--body', body,
        ], { encoding: 'utf8', stdio: 'pipe' });
        if (result.error || result.status !== 0) {
            console.error('[Supervisor] gh issue create failed:', result.stderr || result.error);
            return null;
        }
        // Extract issue number from URL
        const match = result.stdout.trim().match(/\/issues\/(\d+)/);
        return match ? parseInt(match[1], 10) : null;
    }
    catch (err) {
        console.error('[Supervisor] Failed to create RUNLOG issue:', err);
        return null;
    }
}
exports.createRunlogIssue = createRunlogIssue;
/**
 * Create an approval request issue
 */
async function createApprovalIssue(state, plan, repo) {
    // Skip GitHub issue creation in test environment
    if (process.env.NODE_ENV === 'test') {
        console.debug('[Supervisor] Skipping GitHub issue creation in test environment');
        return null;
    }
    if (!isGhAvailable()) {
        console.warn('[Supervisor] gh CLI not available, cannot create approval issue');
        return null;
    }
    const targetRepo = repo || getDefaultRepo();
    if (!targetRepo) {
        console.warn('[Supervisor] Could not determine repository');
        return null;
    }
    const stepsText = (0, i18n_1.formatSteps)(plan.steps);
    const title = (0, i18n_1.t)('supervisor.approval.title', { runId: state.runId });
    const body = (0, i18n_1.t)('supervisor.approval.body', {
        runId: state.runId,
        inputPreview: state.input.substring(0, 500) + (state.input.length > 500 ? '...' : ''),
        riskLevel: plan.estimatedRisk,
        reason: plan.approvalReason || 'Dangerous operation detected',
        stepsText,
    });
    try {
        // Use spawnSync with array arguments to prevent command injection
        const result = (0, child_process_1.spawnSync)('gh', [
            'issue', 'create',
            '--repo', targetRepo,
            '--title', title,
            '--body', body,
            '--label', 'approval-required',
        ], { encoding: 'utf8', stdio: 'pipe' });
        if (result.error || result.status !== 0) {
            console.error('[Supervisor] gh issue create failed:', result.stderr || result.error);
            return null;
        }
        const match = result.stdout.trim().match(/\/issues\/(\d+)/);
        return match ? parseInt(match[1], 10) : null;
    }
    catch (err) {
        console.error('[Supervisor] Failed to create approval issue:', err);
        return null;
    }
}
exports.createApprovalIssue = createApprovalIssue;
/**
 * Check if an issue has been approved
 */
async function checkApproval(issueId, repo) {
    if (!isGhAvailable()) {
        return { approved: false };
    }
    const targetRepo = repo || getDefaultRepo();
    if (!targetRepo) {
        return { approved: false };
    }
    try {
        // Check for approved label - use spawnSync with array arguments
        const labelsResult = (0, child_process_1.spawnSync)('gh', [
            'issue', 'view', String(issueId),
            '--repo', targetRepo,
            '--json', 'labels',
            '-q', '.labels[].name',
        ], { encoding: 'utf8', stdio: 'pipe' });
        const labels = labelsResult.stdout?.trim() || '';
        if (labels.includes('approved')) {
            return { approved: true };
        }
        // Check for APPROVE/REJECT comments - use spawnSync with array arguments
        const commentsResult = (0, child_process_1.spawnSync)('gh', [
            'issue', 'view', String(issueId),
            '--repo', targetRepo,
            '--json', 'comments',
            '-q', '.comments[] | "\\(.author.login): \\(.body)"',
        ], { encoding: 'utf8', stdio: 'pipe' });
        const comments = commentsResult.stdout?.trim() || '';
        for (const line of comments.split('\n')) {
            const match = line.match(/^(\w+): (.+)/);
            if (match) {
                const [, author, body] = match;
                if (body.trim().toUpperCase() === 'APPROVE') {
                    return { approved: true, approvedBy: author };
                }
                if (body.trim().toUpperCase() === 'REJECT') {
                    return { approved: false, rejectedBy: author };
                }
            }
        }
        return { approved: false };
    }
    catch (err) {
        console.error('[Supervisor] Failed to check approval:', err);
        return { approved: false };
    }
}
exports.checkApproval = checkApproval;
/**
 * Add a comment to an issue
 */
async function addIssueComment(issueId, comment, repo) {
    if (!isGhAvailable()) {
        return false;
    }
    const targetRepo = repo || getDefaultRepo();
    if (!targetRepo) {
        return false;
    }
    try {
        // Use spawnSync with array arguments to prevent command injection
        const result = (0, child_process_1.spawnSync)('gh', [
            'issue', 'comment', String(issueId),
            '--repo', targetRepo,
            '--body', comment,
        ], { encoding: 'utf8', stdio: 'pipe' });
        if (result.error || result.status !== 0) {
            console.error('[Supervisor] gh issue comment failed:', result.stderr || result.error);
            return false;
        }
        return true;
    }
    catch (err) {
        console.error('[Supervisor] Failed to add comment:', err);
        return false;
    }
}
exports.addIssueComment = addIssueComment;
/**
 * Close an issue
 */
async function closeIssue(issueId, comment, repo) {
    if (!isGhAvailable()) {
        return false;
    }
    const targetRepo = repo || getDefaultRepo();
    if (!targetRepo) {
        return false;
    }
    try {
        if (comment) {
            await addIssueComment(issueId, comment, targetRepo);
        }
        // Use spawnSync with array arguments to prevent command injection
        const result = (0, child_process_1.spawnSync)('gh', [
            'issue', 'close', String(issueId),
            '--repo', targetRepo,
        ], { encoding: 'utf8', stdio: 'pipe' });
        if (result.error || result.status !== 0) {
            console.error('[Supervisor] gh issue close failed:', result.stderr || result.error);
            return false;
        }
        return true;
    }
    catch (err) {
        console.error('[Supervisor] Failed to close issue:', err);
        return false;
    }
}
exports.closeIssue = closeIssue;
