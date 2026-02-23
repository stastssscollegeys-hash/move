#!/usr/bin/env npx ts-node
"use strict";
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
/**
 * LLM Auto-Switching System v1.0 - Cost Report CLI
 * Usage: npx ts-node scripts/cost-report.ts [--period=day|week|month] [--json]
 */
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
function parseArgs() {
    const args = process.argv.slice(2);
    let period = 'day';
    let json = false;
    for (const arg of args) {
        if (arg.startsWith('--period='))
            period = arg.split('=')[1];
        if (arg === '--json')
            json = true;
    }
    return { period, json };
}
function loadRecords(logPath) {
    if (!fs.existsSync(logPath))
        return [];
    return fs.readFileSync(logPath, 'utf-8').trim().split('\n').filter(Boolean).flatMap((line) => {
        try {
            return [JSON.parse(line)];
        }
        catch {
            return [];
        }
    });
}
function filterByPeriod(records, period) {
    const now = new Date();
    let cutoff;
    switch (period) {
        case 'week': {
            const d = new Date(now);
            d.setDate(d.getDate() - 7);
            cutoff = d;
            break;
        }
        case 'month':
            cutoff = new Date(now.getFullYear(), now.getMonth(), 1);
            break;
        default: cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    }
    return records.filter((r) => new Date(r.timestamp) >= cutoff);
}
function main() {
    const { period, json } = parseArgs();
    const projLog = path.join(process.cwd(), 'logs', 'cost-tracking.jsonl');
    const globalLog = path.join(process.env.HOME ?? '~', '.claude', 'global-cost-tracking.jsonl');
    const all = [...loadRecords(projLog), ...loadRecords(globalLog)];
    if (all.length === 0) {
        console.log('No cost records found.');
        return;
    }
    const filtered = filterByPeriod(all, period);
    const totalCost = filtered.reduce((s, r) => s + r.cost, 0);
    const byModel = {};
    const byProvider = {};
    for (const r of filtered) {
        if (!byModel[r.model])
            byModel[r.model] = { cost: 0, reqs: 0 };
        byModel[r.model].cost += r.cost;
        byModel[r.model].reqs += 1;
        if (!byProvider[r.provider])
            byProvider[r.provider] = { cost: 0, reqs: 0 };
        byProvider[r.provider].cost += r.cost;
        byProvider[r.provider].reqs += 1;
    }
    const report = { period, totalCost: Math.round(totalCost * 10000) / 10000, requests: filtered.length, byModel, byProvider };
    if (json) {
        console.log(JSON.stringify(report, null, 2));
        return;
    }
    console.log('\n============================================');
    console.log('  LLM Cost Report - Period:', period);
    console.log('============================================');
    console.log('  Total Cost:     $' + report.totalCost);
    console.log('  Total Requests: ' + report.requests);
    console.log('\n  --- By Model ---');
    for (const [m, d] of Object.entries(byModel).sort((a, b) => b[1].cost - a[1].cost)) {
        console.log('  ' + m.padEnd(22) + '$' + d.cost.toFixed(4).padStart(8) + '  (' + d.reqs + ' reqs)');
    }
    console.log('\n  --- By Provider ---');
    for (const [p, d] of Object.entries(byProvider).sort((a, b) => b[1].cost - a[1].cost)) {
        console.log('  ' + p.padEnd(22) + '$' + d.cost.toFixed(4).padStart(8) + '  (' + d.reqs + ' reqs)');
    }
    console.log('============================================');
}
main();
