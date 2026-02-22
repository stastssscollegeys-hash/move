#!/usr/bin/env node
"use strict";
/* istanbul ignore file */
/**
 * Observability Report CLI
 *
 * Usage:
 *   npx ts-node src/proxy-mcp/observability/report-cli.ts --period 24h
 *   npx ts-node src/proxy-mcp/observability/report-cli.ts --period 7d --post
 *   npm run obs:report:daily
 *   npm run obs:post:weekly
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
const report_1 = require("./report");
const post_to_issue_1 = require("./post-to-issue");
function parseArgs() {
    const args = process.argv.slice(2);
    const result = {
        period: '24h',
        post: false,
        help: false,
    };
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        switch (arg) {
            case '--period':
            case '-p': {
                const period = args[++i];
                if (period === '24h' || period === '7d') {
                    result.period = period;
                }
                else {
                    console.error(`Invalid period: ${period}. Use 24h or 7d.`);
                    process.exit(1);
                }
                break;
            }
            case '--post':
                result.post = true;
                break;
            case '--output':
            case '-o':
                result.output = args[++i];
                break;
            case '--help':
            case '-h':
                result.help = true;
                break;
        }
    }
    return result;
}
function showHelp() {
    console.log(`
Observability Report Generator

Usage:
  report-cli [options]

Options:
  --period, -p <24h|7d>   Report period (default: 24h)
  --post                   Post report to GitHub Issue
  --output, -o <file>      Save report to file
  --help, -h               Show this help message

Examples:
  report-cli --period 24h                    Generate daily report
  report-cli --period 7d --post              Generate weekly report and post to GitHub
  report-cli --period 24h --output report.md Save report to file
`);
}
async function main() {
    const args = parseArgs();
    if (args.help) {
        showHelp();
        process.exit(0);
    }
    // Get report period
    const period = args.period === '7d' ? (0, report_1.getLast7dPeriod)() : (0, report_1.getLast24hPeriod)();
    console.log(`[report-cli] Generating ${args.period} report...`);
    console.log(`[report-cli] Period: ${period.start.toISOString()} ~ ${period.end.toISOString()}`);
    // Generate report
    const reportData = (0, report_1.generateReport)(period);
    const markdown = (0, report_1.formatReportMarkdown)(reportData);
    // Summary output
    console.log(`[report-cli] Report generated:`);
    console.log(`  - Total events: ${reportData.totalEvents}`);
    console.log(`  - Success rate: ${(reportData.successRate * 100).toFixed(1)}%`);
    console.log(`  - Failure count: ${reportData.failureCount}`);
    console.log(`  - MCPs tracked: ${reportData.mcpMetrics.length}`);
    console.log(`  - Recommendations: ${reportData.recommendations.length}`);
    // Save to file if requested
    if (args.output) {
        const outputPath = path.isAbsolute(args.output) ? args.output : path.join(process.cwd(), args.output);
        fs.writeFileSync(outputPath, markdown, 'utf-8');
        console.log(`[report-cli] Report saved to: ${outputPath}`);
    }
    // Post to GitHub if requested
    if (args.post) {
        console.log(`[report-cli] Posting report to GitHub Issue...`);
        try {
            const result = await (0, post_to_issue_1.postReportToIssue)(reportData, markdown);
            if (result.success) {
                console.log(`[report-cli] Report posted successfully: ${result.issueUrl}`);
            }
            else {
                console.error(`[report-cli] Failed to post report: ${result.error}`);
                process.exit(1);
            }
        }
        catch (error) {
            console.error(`[report-cli] Error posting report:`, error);
            process.exit(1);
        }
    }
    else {
        // Print markdown to stdout
        console.log('\n--- Report ---\n');
        console.log(markdown);
    }
}
main().catch((error) => {
    console.error('[report-cli] Fatal error:', error);
    process.exit(1);
});
