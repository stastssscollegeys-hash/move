#!/usr/bin/env npx ts-node
"use strict";
/**
 * Session Briefing CLI
 *
 * 新しいセッション開始時に現在の状態を表示
 *
 * Usage:
 *   npx ts-node scripts/session-briefing.ts
 *   npm run briefing
 */
Object.defineProperty(exports, "__esModule", { value: true });
const directive_sync_1 = require("../src/proxy-mcp/memory/directive-sync");
async function main() {
    try {
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        // Show briefing
        const briefing = await (0, directive_sync_1.getSessionBriefing)();
        console.log(briefing);
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        // Sync to memory (optional)
        if (process.argv.includes('--sync')) {
            console.log('\n🔄 Syncing directives to memory...');
            const result = await (0, directive_sync_1.syncDirectivesToMemory)();
            console.log(`✅ Synced ${result.synced} entries`);
            if (result.errors.length > 0) {
                console.log(`⚠️  Errors: ${result.errors.join(', ')}`);
            }
        }
    }
    catch (err) {
        console.error('❌ Error:', err instanceof Error ? err.message : err);
        process.exit(1);
    }
}
main();
