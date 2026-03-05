"use strict";
// ============================================================
// Shared Database Client (auto-detect Supabase or Demo Store)
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSupabase = exports.isDemoMode = void 0;
const demo_store_1 = require("./demo-store");
let supabase = null;
function isDemoMode() {
    return !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY;
}
exports.isDemoMode = isDemoMode;
function getSupabase() {
    if (supabase)
        return supabase;
    if (!isDemoMode()) {
        const { createClient } = require('@supabase/supabase-js');
        supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
        console.log('[UTAGE] Connected to Supabase');
    }
    else {
        supabase = demo_store_1.demoSupabase;
        console.log('[UTAGE] Running in DEMO mode (in-memory store)');
    }
    return supabase;
}
exports.getSupabase = getSupabase;
