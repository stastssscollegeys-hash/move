"use strict";
/**
 * Schedule Runner Types - P18
 *
 * Type definitions for scheduled ops jobs
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.JOB_NAMES = exports.DAY_OF_WEEK_MAP = void 0;
exports.DAY_OF_WEEK_MAP = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
};
exports.JOB_NAMES = [
    'daily_observability_report',
    'weekly_observability_report',
    'weekly_improvement_digest',
];
