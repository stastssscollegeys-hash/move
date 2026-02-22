#!/usr/bin/env npx ts-node
"use strict";
/**
 * Memory Report CLI
 *
 * Generates reports from the TAISUN v2 memory system.
 *
 * Usage:
 *   npx ts-node scripts/memory-report.ts [command] [options]
 *
 * Commands:
 *   summary   - Show system overview (default)
 *   detailed  - Show detailed agent statistics
 *   trends    - Show daily activity trends
 *   errors    - Show error pattern analysis
 *   export    - Export data to file
 *   backup    - Create backup
 *   cleanup   - Remove old task records
 *
 * Options:
 *   --format=json|csv|yaml  - Export format (default: json)
 *   --output=<path>         - Output file path
 *   --help                  - Show help
 */
Object.defineProperty(exports, "__esModule", { value: true });
const MemoryService_1 = require("../src/memory/MemoryService");
const HELP_TEXT = `
TAISUN v2 Memory Report CLI
============================

Usage:
  npx ts-node scripts/memory-report.ts [command] [options]

Commands:
  summary   - Show system overview (default)
  detailed  - Show detailed agent statistics
  trends    - Show daily activity trends
  errors    - Show error pattern analysis
  export    - Export data to file
  backup    - Create backup of memory data
  cleanup   - Remove old task records (beyond retention period)

Options:
  --format=json|csv|yaml  - Export format (default: json)
  --output=<path>         - Output file path
  --path=<path>           - Memory base path (default: .claude/memory)
  --help                  - Show this help message

Examples:
  npx ts-node scripts/memory-report.ts summary
  npx ts-node scripts/memory-report.ts export --format=csv --output=report.csv
  npx ts-node scripts/memory-report.ts backup
`;
function parseArgs(args) {
    const options = {
        command: 'summary',
        format: 'json',
        output: '',
        basePath: '.claude/memory',
        help: false,
    };
    for (const arg of args) {
        if (arg === '--help' || arg === '-h') {
            options.help = true;
        }
        else if (arg.startsWith('--format=')) {
            options.format = arg.split('=')[1];
        }
        else if (arg.startsWith('--output=')) {
            options.output = arg.split('=')[1];
        }
        else if (arg.startsWith('--path=')) {
            options.basePath = arg.split('=')[1];
        }
        else if (!arg.startsWith('-')) {
            options.command = arg;
        }
    }
    return options;
}
function main() {
    const args = process.argv.slice(2);
    const options = parseArgs(args);
    if (options.help) {
        console.log(HELP_TEXT);
        process.exit(0);
    }
    const memoryService = new MemoryService_1.MemoryService(options.basePath);
    switch (options.command) {
        case 'summary':
            console.log(memoryService.generateReport('summary'));
            break;
        case 'detailed':
            console.log(memoryService.generateReport('detailed'));
            break;
        case 'trends':
            console.log(memoryService.generateReport('trends'));
            break;
        case 'errors':
            console.log(memoryService.generateReport('errors'));
            break;
        case 'export': {
            const outputPath = options.output || `memory-export-${Date.now()}.${options.format}`;
            memoryService.exportData(options.format, outputPath);
            console.log(`Data exported to: ${outputPath}`);
            break;
        }
        case 'backup': {
            const backupPath = memoryService.createBackup();
            console.log(`Backup created: ${backupPath}`);
            break;
        }
        case 'cleanup': {
            const cleanedCount = memoryService.cleanupOldTasks();
            console.log(`Cleaned up ${cleanedCount} old task records.`);
            break;
        }
        default:
            console.error(`Unknown command: ${options.command}`);
            console.log('Use --help for available commands.');
            process.exit(1);
    }
}
main();
