// ============================================================
// Shared Database Client (auto-detect Supabase or Demo Store)
// ============================================================

import { demoSupabase } from './demo-store';

let supabase: any = null;

export function isDemoMode() {
  return !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY;
}

export function getSupabase() {
  if (supabase) return supabase;

  if (!isDemoMode()) {
    const { createClient } = require('@supabase/supabase-js');
    supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);
    console.log('[UTAGE] Connected to Supabase');
  } else {
    supabase = demoSupabase;
    console.log('[UTAGE] Running in DEMO mode (in-memory store)');
  }
  return supabase;
}
