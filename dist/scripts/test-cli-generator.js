"use strict";
/**
 * Debug script for CLI generator
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
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const generator_1 = require("../cli/generator");
const framework_1 = require("../cli/wizard/steps/framework");
async function main() {
    const outputDir = '/tmp/test-cli-debug';
    // Clean up
    if (fs.existsSync(outputDir)) {
        fs.rmSync(outputDir, { recursive: true, force: true });
    }
    fs.mkdirSync(outputDir, { recursive: true });
    const generator = new generator_1.FileGenerator();
    const express = (0, framework_1.getFrameworkById)('express');
    if (!express) {
        console.error('Express framework not found');
        process.exit(1);
    }
    const results = await generator.generateAll({
        projectName: 'test-debug',
        description: 'Debug test',
        author: 'test@example.com',
        framework: express,
        features: [],
        apiKeys: {},
        outputDir
    });
    const pkgPath = path.join(outputDir, 'package.json');
    if (fs.existsSync(pkgPath)) {
        const content = fs.readFileSync(pkgPath, 'utf8');
        console.log('=== GENERATED package.json ===');
        console.log(content);
        console.log('=== END ===');
        // Try to parse JSON
        try {
            JSON.parse(content);
            console.log('\n✅ Valid JSON');
        }
        catch (error) {
            console.log('\n❌ Invalid JSON:', error.message);
        }
    }
    else {
        console.error('package.json not found');
    }
}
main().catch(console.error);
