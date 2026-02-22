#!/usr/bin/env node
"use strict";
/* istanbul ignore file */
/**
 * Rollout CLI for Internal MCP Management
 *
 * Usage:
 *   internal-mcp:rollout --overlay <path> --mcp <name> --mode <off|canary|full> [--percent <0-100>]
 *
 * Examples:
 *   # Enable canary at 5%
 *   npm run internal-mcp:rollout -- --overlay /etc/taisun/internal-mcps.prod.json --mcp github --mode canary --percent 5
 *
 *   # Enable full rollout
 *   npm run internal-mcp:rollout -- --overlay /etc/taisun/internal-mcps.prod.json --mcp github --mode full
 *
 *   # Disable MCP
 *   npm run internal-mcp:rollout -- --overlay /etc/taisun/internal-mcps.prod.json --mcp github --mode off
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
function parseArgs() {
    const args = process.argv.slice(2);
    const result = {};
    for (let i = 0; i < args.length; i++) {
        switch (args[i]) {
            case '--overlay':
                result.overlay = args[++i];
                break;
            case '--mcp':
                result.mcp = args[++i];
                break;
            case '--mode': {
                const mode = args[++i];
                if (mode === 'off' || mode === 'canary' || mode === 'full') {
                    result.mode = mode;
                }
                else {
                    console.error(`Invalid mode: ${mode}. Must be off, canary, or full.`);
                    return null;
                }
                break;
            }
            case '--percent':
                result.percent = parseInt(args[++i], 10);
                if (isNaN(result.percent) || result.percent < 0 || result.percent > 100) {
                    console.error('Percent must be 0-100');
                    return null;
                }
                break;
            case '--help':
            case '-h':
                printUsage();
                process.exit(0);
        }
    }
    if (!result.overlay || !result.mcp || !result.mode) {
        console.error('Missing required arguments: --overlay, --mcp, --mode');
        printUsage();
        return null;
    }
    return result;
}
function printUsage() {
    console.log(`
Usage: internal-mcp:rollout --overlay <path> --mcp <name> --mode <off|canary|full> [--percent <0-100>]

Options:
  --overlay <path>  Path to overlay config file
  --mcp <name>      Name of the internal MCP
  --mode <mode>     Rollout mode: off, canary, or full
  --percent <n>     Canary percentage (0-100), only used with mode=canary

Examples:
  # Enable canary at 5%
  npm run internal-mcp:rollout -- --overlay /etc/taisun/internal-mcps.prod.json --mcp github --mode canary --percent 5

  # Enable full rollout
  npm run internal-mcp:rollout -- --overlay /etc/taisun/internal-mcps.prod.json --mcp github --mode full

  # Disable MCP
  npm run internal-mcp:rollout -- --overlay /etc/taisun/internal-mcps.prod.json --mcp github --mode off
`);
}
function loadOverlay(path) {
    try {
        if (fs.existsSync(path)) {
            const content = fs.readFileSync(path, 'utf-8');
            return JSON.parse(content);
        }
    }
    catch (error) {
        console.error(`Failed to load overlay: ${error}`);
    }
    return { mcps: [] };
}
function saveOverlay(path, config) {
    const content = JSON.stringify(config, null, 2);
    fs.writeFileSync(path, content, 'utf-8');
}
function createBackup(path) {
    const backupPath = `${path}.bak`;
    if (fs.existsSync(path)) {
        fs.copyFileSync(path, backupPath);
        console.log(`Created backup: ${backupPath}`);
    }
    return backupPath;
}
function main() {
    const args = parseArgs();
    if (!args) {
        process.exit(1);
    }
    // Create backup before making changes
    createBackup(args.overlay);
    // Load existing overlay
    const config = loadOverlay(args.overlay);
    // Find or create MCP entry
    let mcpEntry = config.mcps.find((m) => m.name === args.mcp);
    if (!mcpEntry) {
        mcpEntry = { name: args.mcp, enabled: true };
        config.mcps.push(mcpEntry);
    }
    // Update rollout config
    const newRollout = {
        mode: args.mode,
    };
    if (args.mode === 'canary') {
        newRollout.canaryPercent = args.percent ?? 5;
    }
    if (args.mode === 'off') {
        mcpEntry.enabled = false;
    }
    else {
        mcpEntry.enabled = true;
    }
    mcpEntry.rollout = newRollout;
    // Save updated config
    saveOverlay(args.overlay, config);
    console.log(`
✓ Updated rollout configuration

MCP: ${args.mcp}
Mode: ${args.mode}${args.mode === 'canary' ? ` (${newRollout.canaryPercent}%)` : ''}
Enabled: ${mcpEntry.enabled}

File: ${args.overlay}
Backup: ${args.overlay}.bak

Next steps:
1. Restart Proxy to apply changes
2. Monitor metrics for issues
3. Rollback if needed: cp ${args.overlay}.bak ${args.overlay} && restart
`);
}
main();
