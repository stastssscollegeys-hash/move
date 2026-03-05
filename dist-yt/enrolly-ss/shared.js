"use strict";
// ============================================================
// Enrolly SS - Shared Module (re-exports from FunnelForge)
// Both projects share the same DB, types, and demo store
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.demoSupabase = exports.isDemoMode = exports.getSupabase = void 0;
var db_1 = require("../funnel-forge-ss/db");
Object.defineProperty(exports, "getSupabase", { enumerable: true, get: function () { return db_1.getSupabase; } });
Object.defineProperty(exports, "isDemoMode", { enumerable: true, get: function () { return db_1.isDemoMode; } });
var demo_store_1 = require("../funnel-forge-ss/demo-store");
Object.defineProperty(exports, "demoSupabase", { enumerable: true, get: function () { return demo_store_1.demoSupabase; } });
