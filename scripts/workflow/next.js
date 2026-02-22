#!/usr/bin/env tsx
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const engine_1 = require("../../src/proxy-mcp/workflow/engine");
try {
    const result = (0, engine_1.transitionToNextPhase)();
    if (result.success) {
        console.log(result.message);
        console.log('\n次のステップ: npm run workflow:status');
    }
    else {
        console.error(`❌ ${result.message}\n`);
        result.errors.forEach(e => console.error(`  - ${e}`));
        process.exit(1);
    }
}
catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
}
