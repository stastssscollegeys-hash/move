"use strict";
/**
 * Performance System Module
 *
 * Exports for the TAISUN v2 performance optimization system.
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
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.benchmarkRunner = exports.BenchmarkRunner = exports.performanceService = exports.PerformanceService = void 0;
var PerformanceService_1 = require("./PerformanceService");
Object.defineProperty(exports, "PerformanceService", { enumerable: true, get: function () { return PerformanceService_1.PerformanceService; } });
Object.defineProperty(exports, "performanceService", { enumerable: true, get: function () { return PerformanceService_1.performanceService; } });
var BenchmarkRunner_1 = require("./BenchmarkRunner");
Object.defineProperty(exports, "BenchmarkRunner", { enumerable: true, get: function () { return BenchmarkRunner_1.BenchmarkRunner; } });
Object.defineProperty(exports, "benchmarkRunner", { enumerable: true, get: function () { return BenchmarkRunner_1.benchmarkRunner; } });
__exportStar(require("./types"), exports);
