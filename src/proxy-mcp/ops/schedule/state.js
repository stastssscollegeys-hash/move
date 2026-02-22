"use strict";
/**
 * Schedule State Manager - P18
 *
 * Persists job state to prevent duplicate executions after restarts
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
exports.ScheduleStateManager = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const types_1 = require("./types");
const STATE_FILE = 'schedule-state.json';
/**
 * Create initial state for a job
 */
function createInitialJobState(jobName) {
    return {
        jobName,
        lastRunAt: null,
        lastStatus: null,
        consecutiveFailures: 0,
        runCount: 0,
    };
}
/**
 * Create initial schedule state
 */
function createInitialState() {
    const jobs = {};
    for (const jobName of types_1.JOB_NAMES) {
        jobs[jobName] = createInitialJobState(jobName);
    }
    return {
        version: 1,
        updatedAt: new Date().toISOString(),
        jobs,
    };
}
/**
 * Schedule State Manager
 */
class ScheduleStateManager {
    constructor(stateDir) {
        this.stateDir = stateDir;
        this.statePath = path.join(stateDir, STATE_FILE);
        this.state = this.load();
    }
    /**
     * Load state from disk
     */
    load() {
        try {
            if (!fs.existsSync(this.statePath)) {
                return createInitialState();
            }
            const content = fs.readFileSync(this.statePath, 'utf-8');
            const state = JSON.parse(content);
            // Ensure all jobs exist in state (for schema evolution)
            for (const jobName of types_1.JOB_NAMES) {
                if (!state.jobs[jobName]) {
                    state.jobs[jobName] = createInitialJobState(jobName);
                }
            }
            return state;
        }
        catch (error) {
            console.error('[schedule-state] Failed to load state, using initial:', error);
            return createInitialState();
        }
    }
    /**
     * Save state to disk
     */
    save() {
        try {
            // Ensure directory exists
            if (!fs.existsSync(this.stateDir)) {
                fs.mkdirSync(this.stateDir, { recursive: true });
            }
            this.state.updatedAt = new Date().toISOString();
            const content = JSON.stringify(this.state, null, 2);
            fs.writeFileSync(this.statePath, content, 'utf-8');
        }
        catch (error) {
            console.error('[schedule-state] Failed to save state:', error);
        }
    }
    /**
     * Get job state
     */
    getJobState(jobName) {
        return this.state.jobs[jobName] || createInitialJobState(jobName);
    }
    /**
     * Get all job states
     */
    getAllJobStates() {
        return { ...this.state.jobs };
    }
    /**
     * Record successful job run
     */
    recordSuccess(jobName) {
        const jobState = this.state.jobs[jobName] || createInitialJobState(jobName);
        jobState.lastRunAt = new Date().toISOString();
        jobState.lastStatus = 'ok';
        jobState.consecutiveFailures = 0;
        jobState.runCount++;
        delete jobState.lastError;
        this.state.jobs[jobName] = jobState;
        this.save();
    }
    /**
     * Record failed job run
     */
    recordFailure(jobName, error) {
        const jobState = this.state.jobs[jobName] || createInitialJobState(jobName);
        jobState.lastRunAt = new Date().toISOString();
        jobState.lastStatus = 'fail';
        jobState.consecutiveFailures++;
        jobState.runCount++;
        jobState.lastError = error;
        this.state.jobs[jobName] = jobState;
        this.save();
    }
    /**
     * Record skipped job run
     */
    recordSkipped(jobName) {
        const jobState = this.state.jobs[jobName] || createInitialJobState(jobName);
        jobState.lastStatus = 'skipped';
        // Don't update lastRunAt for skipped runs
        this.state.jobs[jobName] = jobState;
        this.save();
    }
    /**
     * Check if job was already run in the current period
     */
    wasRunInCurrentPeriod(jobName, cadence, now) {
        const jobState = this.state.jobs[jobName];
        if (!jobState?.lastRunAt || jobState.lastStatus !== 'ok') {
            return false;
        }
        const lastRun = new Date(jobState.lastRunAt);
        if (cadence === 'daily') {
            // Check if run today
            return (lastRun.getFullYear() === now.getFullYear() &&
                lastRun.getMonth() === now.getMonth() &&
                lastRun.getDate() === now.getDate());
        }
        else {
            // Check if run this week (same ISO week)
            return isSameISOWeek(lastRun, now);
        }
    }
    /**
     * Reset state (for testing)
     */
    reset() {
        this.state = createInitialState();
        this.save();
    }
    /**
     * Get state file path (for testing/debugging)
     */
    getStatePath() {
        return this.statePath;
    }
}
exports.ScheduleStateManager = ScheduleStateManager;
/**
 * Check if two dates are in the same ISO week
 */
function isSameISOWeek(date1, date2) {
    const getISOWeek = (date) => {
        const d = new Date(date);
        d.setHours(0, 0, 0, 0);
        d.setDate(d.getDate() + 4 - (d.getDay() || 7));
        const yearStart = new Date(d.getFullYear(), 0, 1);
        const week = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
        return { year: d.getFullYear(), week };
    };
    const w1 = getISOWeek(date1);
    const w2 = getISOWeek(date2);
    return w1.year === w2.year && w1.week === w2.week;
}
