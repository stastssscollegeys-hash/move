"use strict";
/**
 * Observability Module - P5
 *
 * Event tracking, metrics collection, and monitoring
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createReportIssue = exports.postReportToIssue = exports.getLast7dPeriod = exports.getLast24hPeriod = exports.formatReportMarkdown = exports.generateReport = exports.getRecentEventsSummary = exports.clearEvents = exports.getMetricsSummary = exports.getEvents = exports.startTimer = exports.recordEvent = void 0;
var service_1 = require("./service");
Object.defineProperty(exports, "recordEvent", { enumerable: true, get: function () { return service_1.recordEvent; } });
Object.defineProperty(exports, "startTimer", { enumerable: true, get: function () { return service_1.startTimer; } });
Object.defineProperty(exports, "getEvents", { enumerable: true, get: function () { return service_1.getEvents; } });
Object.defineProperty(exports, "getMetricsSummary", { enumerable: true, get: function () { return service_1.getMetricsSummary; } });
Object.defineProperty(exports, "clearEvents", { enumerable: true, get: function () { return service_1.clearEvents; } });
Object.defineProperty(exports, "getRecentEventsSummary", { enumerable: true, get: function () { return service_1.getRecentEventsSummary; } });
var report_1 = require("./report");
Object.defineProperty(exports, "generateReport", { enumerable: true, get: function () { return report_1.generateReport; } });
Object.defineProperty(exports, "formatReportMarkdown", { enumerable: true, get: function () { return report_1.formatReportMarkdown; } });
Object.defineProperty(exports, "getLast24hPeriod", { enumerable: true, get: function () { return report_1.getLast24hPeriod; } });
Object.defineProperty(exports, "getLast7dPeriod", { enumerable: true, get: function () { return report_1.getLast7dPeriod; } });
var post_to_issue_1 = require("./post-to-issue");
Object.defineProperty(exports, "postReportToIssue", { enumerable: true, get: function () { return post_to_issue_1.postReportToIssue; } });
Object.defineProperty(exports, "createReportIssue", { enumerable: true, get: function () { return post_to_issue_1.createReportIssue; } });
