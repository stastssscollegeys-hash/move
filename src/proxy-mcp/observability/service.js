"use strict";
/**
 * Observability Service - P5
 *
 * Event tracking, metrics collection, and monitoring
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
exports.getRecentEventsSummary = exports.clearEvents = exports.getMetricsSummary = exports.getEvents = exports.startTimer = exports.recordEvent = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const EVENTS_DIR = path.join(process.cwd(), '.taisun', 'observability');
const EVENTS_FILE = path.join(EVENTS_DIR, 'events.jsonl');
const MAX_EVENTS_IN_MEMORY = 1000;
// In-memory event buffer
let eventBuffer = [];
let initialized = false;
/**
 * Initialize observability (create directories if needed)
 */
function ensureInitialized() {
    if (initialized)
        return;
    try {
        if (!fs.existsSync(EVENTS_DIR)) {
            fs.mkdirSync(EVENTS_DIR, { recursive: true });
        }
        initialized = true;
    }
    catch (error) {
        console.error('[observability] Failed to initialize:', error);
    }
}
/**
 * Record an event
 */
function recordEvent(type, runId, status, options = {}) {
    ensureInitialized();
    const event = {
        timestamp: new Date().toISOString(),
        type,
        runId,
        status,
        ...options,
    };
    // Add to buffer
    eventBuffer.push(event);
    // Trim buffer if too large
    if (eventBuffer.length > MAX_EVENTS_IN_MEMORY) {
        eventBuffer = eventBuffer.slice(-MAX_EVENTS_IN_MEMORY);
    }
    // Persist to file
    try {
        fs.appendFileSync(EVENTS_FILE, JSON.stringify(event) + '\n');
    }
    catch (error) {
        console.error('[observability] Failed to persist event:', error);
    }
    return event;
}
exports.recordEvent = recordEvent;
/**
 * Create event recorder with timing
 */
function startTimer(type, runId, options = {}) {
    const startTime = Date.now();
    return (status = 'ok', errorInfo) => {
        const durationMs = Date.now() - startTime;
        return recordEvent(type, runId, status, {
            ...options,
            durationMs,
            ...errorInfo,
        });
    };
}
exports.startTimer = startTimer;
/**
 * Get events matching filter
 */
function getEvents(filter = {}) {
    let events = [...eventBuffer];
    if (filter.type) {
        events = events.filter((e) => e.type === filter.type);
    }
    if (filter.runId) {
        events = events.filter((e) => e.runId === filter.runId);
    }
    if (filter.status) {
        events = events.filter((e) => e.status === filter.status);
    }
    if (filter.since) {
        events = events.filter((e) => e.timestamp >= filter.since);
    }
    if (filter.limit) {
        events = events.slice(-filter.limit);
    }
    return events;
}
exports.getEvents = getEvents;
/**
 * Get metrics summary
 */
function getMetricsSummary(since) {
    const events = since
        ? eventBuffer.filter((e) => e.timestamp >= since)
        : eventBuffer;
    const successCount = events.filter((e) => e.status === 'ok').length;
    const failureCount = events.filter((e) => e.status === 'fail').length;
    const totalEvents = events.length;
    // Calculate average duration
    const durationsMs = events
        .filter((e) => e.durationMs !== undefined)
        .map((e) => e.durationMs);
    const avgDurationMs = durationsMs.length > 0
        ? durationsMs.reduce((a, b) => a + b, 0) / durationsMs.length
        : 0;
    // Count failures by type
    const failuresByType = {};
    events
        .filter((e) => e.status === 'fail' && e.errorType)
        .forEach((e) => {
        failuresByType[e.errorType] = (failuresByType[e.errorType] || 0) + 1;
    });
    // Count events by type
    const eventsByType = {};
    events.forEach((e) => {
        eventsByType[e.type] = (eventsByType[e.type] || 0) + 1;
    });
    return {
        totalEvents,
        successCount,
        failureCount,
        successRate: totalEvents > 0 ? successCount / totalEvents : 0,
        avgDurationMs: Math.round(avgDurationMs * 100) / 100,
        failuresByType,
        eventsByType,
        lastUpdated: new Date().toISOString(),
    };
}
exports.getMetricsSummary = getMetricsSummary;
/**
 * Clear event buffer (for testing)
 */
function clearEvents() {
    eventBuffer = [];
}
exports.clearEvents = clearEvents;
/**
 * Get recent events summary (for system_health)
 */
function getRecentEventsSummary(_limit = 100) {
    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
    const summary = getMetricsSummary(last24h);
    // Get top errors
    const topErrors = Object.entries(summary.failuresByType)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([type, count]) => ({ type, count }));
    return {
        total: eventBuffer.length,
        last24h: summary,
        topErrors,
    };
}
exports.getRecentEventsSummary = getRecentEventsSummary;
