"use strict";
/**
 * Directive Sync - Memory Enhancement
 *
 * Syncs directives.md, mistakes.md, memory.md to MCP memory
 * for semantic search and session continuity.
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
exports.checkRelatedMistakes = exports.getSessionBriefing = exports.searchDirectives = exports.syncDirectivesToMemory = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const service_1 = require("./service");
const CLAUDE_DIR = path.join(process.cwd(), '.claude');
const SYNC_FILES = [
    {
        name: 'directives',
        path: path.join(CLAUDE_DIR, 'directives.md'),
        namespace: 'long-term',
        tags: ['directive', 'instruction', 'contract'],
        importance: 0.9,
    },
    {
        name: 'mistakes',
        path: path.join(CLAUDE_DIR, 'mistakes.md'),
        namespace: 'long-term',
        tags: ['mistake', 'anti-regression', 'prevention'],
        importance: 1.0,
    },
    {
        name: 'memory',
        path: path.join(CLAUDE_DIR, 'memory.md'),
        namespace: 'long-term',
        tags: ['rule', 'architecture', 'security', 'quality'],
        importance: 0.95,
    },
    {
        name: 'running_summary',
        path: path.join(CLAUDE_DIR, 'running_summary.md'),
        namespace: 'short-term',
        tags: ['progress', 'status', 'current'],
        importance: 0.8,
    },
    {
        name: 'task_contract',
        path: path.join(CLAUDE_DIR, 'task_contract.md'),
        namespace: 'short-term',
        tags: ['task', 'contract', 'dod', 'current'],
        importance: 0.85,
    },
];
/**
 * Parse markdown file into sections
 */
function parseMarkdownSections(content) {
    const sections = new Map();
    const lines = content.split('\n');
    let currentSection = 'header';
    let currentContent = [];
    for (const line of lines) {
        const headerMatch = line.match(/^##\s+(.+)/);
        if (headerMatch) {
            // Save previous section
            if (currentContent.length > 0) {
                sections.set(currentSection, currentContent.join('\n').trim());
            }
            currentSection = headerMatch[1];
            currentContent = [];
        }
        else {
            currentContent.push(line);
        }
    }
    // Save last section
    if (currentContent.length > 0) {
        sections.set(currentSection, currentContent.join('\n').trim());
    }
    return sections;
}
/**
 * Sync directive files to memory
 */
async function syncDirectivesToMemory() {
    const memory = (0, service_1.getMemoryService)();
    let synced = 0;
    const errors = [];
    for (const file of SYNC_FILES) {
        try {
            if (!fs.existsSync(file.path)) {
                continue;
            }
            const content = fs.readFileSync(file.path, 'utf-8');
            const sections = parseMarkdownSections(content);
            // Add each section as a separate memory entry
            for (const [sectionName, sectionContent] of sections) {
                if (sectionContent.length < 10)
                    continue; // Skip empty sections
                await memory.add(sectionContent, {
                    namespace: file.namespace,
                    tags: [...file.tags, file.name, sectionName.toLowerCase()],
                    source: `${file.name}.md#${sectionName}`,
                    importance: file.importance,
                    metadata: {
                        file: file.name,
                        section: sectionName,
                        syncedAt: Date.now(),
                    },
                });
                synced++;
            }
        }
        catch (err) {
            const errorMsg = err instanceof Error ? err.message : String(err);
            errors.push(`${file.name}: ${errorMsg}`);
        }
    }
    return { synced, errors };
}
exports.syncDirectivesToMemory = syncDirectivesToMemory;
/**
 * Search across all directive memory
 */
async function searchDirectives(query, options = {}) {
    const memory = (0, service_1.getMemoryService)();
    const results = await memory.search(query, {
        limit: options.limit || 10,
        tags: options.tags,
        includeContent: true,
    });
    return results.map((r) => ({
        source: r.source || 'unknown',
        summary: r.summary,
        score: r.score || 0,
        tags: r.tags,
    }));
}
exports.searchDirectives = searchDirectives;
/**
 * Get session briefing (for session start)
 */
async function getSessionBriefing() {
    const lines = [];
    lines.push('# セッション開始ブリーフィング\n');
    // 1. Running Summary
    const summaryPath = path.join(CLAUDE_DIR, 'running_summary.md');
    if (fs.existsSync(summaryPath)) {
        const summary = fs.readFileSync(summaryPath, 'utf-8');
        const statusMatch = summary.match(/## 現在のステータス[\s\S]*?(?=##|$)/);
        if (statusMatch) {
            lines.push('## 現在の状態');
            lines.push(statusMatch[0].replace('## 現在のステータス', '').trim());
            lines.push('');
        }
    }
    // 2. Current Task Contract
    const contractPath = path.join(CLAUDE_DIR, 'task_contract.md');
    if (fs.existsSync(contractPath)) {
        const contract = fs.readFileSync(contractPath, 'utf-8');
        const goalMatch = contract.match(/## Goal[\s\S]*?(?=##|$)/);
        const dodMatch = contract.match(/## Acceptance Criteria[\s\S]*?(?=##|$)/);
        if (goalMatch) {
            lines.push('## 現在のタスク');
            lines.push(goalMatch[0].replace('## Goal', '**Goal**:').trim());
        }
        if (dodMatch) {
            lines.push('');
            lines.push('**未完了のDoD**:');
            const unchecked = dodMatch[0].match(/- \[ \].+/g);
            if (unchecked) {
                lines.push(unchecked.join('\n'));
            }
            else {
                lines.push('（すべて完了）');
            }
        }
        lines.push('');
    }
    // 3. Recent Mistakes (top 3)
    const mistakesPath = path.join(CLAUDE_DIR, 'mistakes.md');
    if (fs.existsSync(mistakesPath)) {
        const mistakes = fs.readFileSync(mistakesPath, 'utf-8');
        const mistakeMatches = mistakes.match(/## \d{4}-\d{2}-\d{2} Mistake:.+/g);
        if (mistakeMatches && mistakeMatches.length > 0) {
            lines.push('## 再発防止リマインダー');
            lines.push('以下のミスを繰り返さないこと:');
            mistakeMatches.slice(0, 3).forEach((m) => {
                const name = m.replace(/## \d{4}-\d{2}-\d{2} Mistake:\s*/, '');
                lines.push(`- ⚠️ ${name}`);
            });
            lines.push('');
        }
    }
    // 4. Key Rules from memory.md
    const memoryPath = path.join(CLAUDE_DIR, 'memory.md');
    if (fs.existsSync(memoryPath)) {
        lines.push('## 重要ルール');
        lines.push('- Proxy-Only: 外部MCP通信はtaisun-proxy経由');
        lines.push('- 最小差分: 勝手にリファクタしない');
        lines.push('- No-Guessing: 既存コードを読んでから修正');
        lines.push('- 日本語優先: Issue/RUNLOGは日本語');
        lines.push('');
    }
    return lines.join('\n');
}
exports.getSessionBriefing = getSessionBriefing;
/**
 * Check for related mistakes before starting task
 */
async function checkRelatedMistakes(taskDescription) {
    const memory = (0, service_1.getMemoryService)();
    const results = await memory.search(taskDescription, {
        tags: ['mistake'],
        limit: 5,
    });
    return results
        .filter((r) => (r.score || 0) > 0.3)
        .map((r) => r.summary);
}
exports.checkRelatedMistakes = checkRelatedMistakes;
