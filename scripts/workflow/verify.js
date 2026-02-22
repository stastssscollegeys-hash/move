#!/usr/bin/env tsx
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const engine_1 = require("../../src/proxy-mcp/workflow/engine");
try {
    const result = (0, engine_1.verifyCompletion)();
    if (result.passed) {
        console.log('✅ ワークフロー完了！');
        console.log('すべてのフェーズと検証が完了しました。');
        process.exit(0);
    }
    else {
        console.error('❌ ワークフローは未完了です\n');
        result.errors.forEach(e => console.error(`  - ${e}`));
        if (result.warnings.length > 0) {
            console.warn('\n⚠️  警告:');
            result.warnings.forEach(w => console.warn(`  - ${w}`));
        }
        process.exit(1);
    }
}
catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
}
