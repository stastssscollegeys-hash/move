#!/usr/bin/env node
/**
 * upstream-merge.js
 *
 * 太陽さんエージェント（上流）のアップデートを開発1に安全に取り込むスクリプト。
 *
 * Phase 1: 新規ファイルを自動コピー（開発1に存在しないもの）
 * Phase 2: 変更ファイルのレポート生成（upstream-merge-report.md）
 * Phase 3: 保護ファイルの変更有無を報告
 *
 * Usage:
 *   npm run upstream:merge          # Phase 1 自動実行 + Phase 2-3 レポート
 *   npm run upstream:merge:dry      # 全体のレポートのみ（ファイル変更なし）
 */

const fs = require('fs');
const path = require('path');

// --- Configuration ---

const PROJECT_ROOT = path.resolve(__dirname, '..');
const UPSTREAM_ROOT = path.resolve(PROJECT_ROOT, '..', '太陽さんエージェント');

const SCAN_DIRS = [
  '.claude/hooks',
  '.claude/skills',
  '.claude/agents',
  '.claude/commands',
  '.claude/rules',
  '.claude/references',
  '.claude/memory',
  '.claude/mcp-servers',
  'scripts',
  'src',
  'cli',
];

const PROTECTED_PATTERNS = [
  'CLAUDE.md',
  'settings.json',
  'settings.local.json',
  'settings.development.json',
  'package.json',
  '.mcp.json',
];

const DRY_RUN = process.argv.includes('--dry-run');

// --- Utilities ---

function getAllFiles(dir, base) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relPath = path.join(base, entry.name);
    if (entry.isDirectory()) {
      results.push(...getAllFiles(fullPath, relPath));
    } else {
      results.push(relPath);
    }
  }
  return results;
}

function isProtected(relPath) {
  const basename = path.basename(relPath);
  return PROTECTED_PATTERNS.some(p => basename === p || basename.startsWith(p.replace('.json', '')));
}

function isProtectedExact(relPath) {
  const basename = path.basename(relPath);
  return PROTECTED_PATTERNS.includes(basename);
}

function countLines(content) {
  if (!content) return 0;
  return content.split('\n').length;
}

function diffSummary(upstreamContent, localContent) {
  const upLines = upstreamContent.split('\n');
  const localLines = localContent.split('\n');

  const upSet = new Set(upLines);
  const localSet = new Set(localLines);

  let added = 0;
  let removed = 0;

  for (const line of upLines) {
    if (!localSet.has(line)) added++;
  }
  for (const line of localLines) {
    if (!upSet.has(line)) removed++;
  }

  return { added, removed };
}

function findNewSections(upstreamContent, localContent) {
  const sectionRegex = /^#{1,3}\s+(.+)$/gm;
  const upSections = new Set();
  const localSections = new Set();

  let match;
  while ((match = sectionRegex.exec(upstreamContent)) !== null) {
    upSections.add(match[1].trim());
  }
  sectionRegex.lastIndex = 0;
  while ((match = sectionRegex.exec(localContent)) !== null) {
    localSections.add(match[1].trim());
  }

  const newSections = [];
  for (const s of upSections) {
    if (!localSections.has(s)) newSections.push(s);
  }
  return newSections;
}

function copyFileSync(src, dest) {
  const destDir = path.dirname(dest);
  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }
  fs.copyFileSync(src, dest);
}

// --- Main ---

function main() {
  console.log('=== Upstream Merge ===');
  console.log(`Source: ${UPSTREAM_ROOT}`);
  console.log(`Target: ${PROJECT_ROOT}`);
  if (DRY_RUN) {
    console.log('[DRY RUN] ファイル変更は行いません\n');
  } else {
    console.log('');
  }

  // Check upstream exists
  if (!fs.existsSync(UPSTREAM_ROOT)) {
    console.error(`ERROR: 上流フォルダが見つかりません: ${UPSTREAM_ROOT}`);
    console.error('先に git pull で太陽さんエージェントを更新してください。');
    process.exit(1);
  }

  const added = [];
  const changed = [];
  const protectedChanged = [];
  const protectedUnchanged = [];

  // Scan all directories
  for (const scanDir of SCAN_DIRS) {
    const upstreamDir = path.join(UPSTREAM_ROOT, scanDir);
    if (!fs.existsSync(upstreamDir)) continue;

    const files = getAllFiles(upstreamDir, scanDir);
    for (const relPath of files) {
      const upstreamFile = path.join(UPSTREAM_ROOT, relPath);
      const localFile = path.join(PROJECT_ROOT, relPath);

      if (!fs.existsSync(localFile)) {
        // New file
        added.push(relPath);
      } else {
        // Both exist - compare
        const upContent = fs.readFileSync(upstreamFile, 'utf-8');
        const localContent = fs.readFileSync(localFile, 'utf-8');

        if (upContent !== localContent) {
          const diff = diffSummary(upContent, localContent);
          const newSections = findNewSections(upContent, localContent);

          if (isProtectedExact(relPath)) {
            protectedChanged.push({
              path: relPath,
              diff,
              newSections,
              upstreamLines: countLines(upContent),
              localLines: countLines(localContent),
            });
          } else {
            changed.push({
              path: relPath,
              diff,
              newSections,
              upstreamLines: countLines(upContent),
              localLines: countLines(localContent),
            });
          }
        } else if (isProtectedExact(relPath)) {
          protectedUnchanged.push(relPath);
        }
      }
    }
  }

  // --- Phase 1: New files ---
  console.log('--- Phase 1: 新規ファイル ---');
  if (added.length === 0) {
    console.log('  新規ファイルなし');
  } else {
    for (const relPath of added) {
      if (DRY_RUN) {
        console.log(`  [NEW] ${relPath}    (dry-run, skipped)`);
      } else {
        const src = path.join(UPSTREAM_ROOT, relPath);
        const dest = path.join(PROJECT_ROOT, relPath);
        copyFileSync(src, dest);
        console.log(`  [ADDED] ${relPath}    copied`);
      }
    }
  }
  console.log(`  ${DRY_RUN ? 'New' : 'Added'}: ${added.length} files\n`);

  // --- Phase 2: Changed files ---
  console.log('--- Phase 2: 変更のあるファイル ---');
  if (changed.length === 0) {
    console.log('  変更ファイルなし');
  } else {
    for (const file of changed) {
      const plusMinus = `(+${file.diff.added} lines, -${file.diff.removed} lines)`;
      console.log(`  [CHANGED] ${file.path}  ${plusMinus}`);
    }
  }
  console.log(`  Changed: ${changed.length} files`);
  if (changed.length > 0) {
    console.log('  → 詳細は upstream-merge-report.md を確認\n');
  } else {
    console.log('');
  }

  // --- Phase 3: Protected files ---
  console.log('--- Phase 3: 保護ファイル ---');
  if (protectedChanged.length === 0 && protectedUnchanged.length === 0) {
    console.log('  保護ファイルの変更なし');
  } else {
    for (const file of protectedChanged) {
      console.log(`  [PROTECTED] ${file.path}      changed (review manually)`);
    }
    for (const relPath of protectedUnchanged) {
      console.log(`  [PROTECTED] ${relPath}      unchanged`);
    }
  }
  console.log(`  Protected changed: ${protectedChanged.length} files\n`);

  // --- Generate report ---
  if (changed.length > 0 || protectedChanged.length > 0) {
    const report = generateReport(added, changed, protectedChanged);
    const reportPath = path.join(PROJECT_ROOT, 'upstream-merge-report.md');
    fs.writeFileSync(reportPath, report, 'utf-8');
    console.log(`レポート出力: ${reportPath}`);
  } else if (added.length === 0) {
    console.log('変更なし。上流と同期済みです。');
  }
}

function generateReport(added, changed, protectedChanged) {
  const now = new Date();
  const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

  let md = `# Upstream Merge Report - ${dateStr}\n\n`;
  md += `Source: \`../太陽さんエージェント/\`\n\n`;

  // Summary
  md += `## サマリー\n\n`;
  md += `| 種別 | 件数 |\n`;
  md += `|------|------|\n`;
  md += `| 新規ファイル（自動コピー済み） | ${added.length} |\n`;
  md += `| 変更ファイル（要確認） | ${changed.length} |\n`;
  md += `| 保護ファイル（要確認） | ${protectedChanged.length} |\n\n`;

  // New files
  if (added.length > 0) {
    md += `## 新規ファイル（Phase 1 で自動コピー済み）\n\n`;
    for (const relPath of added) {
      md += `- \`${relPath}\`\n`;
    }
    md += '\n';
  }

  // Changed files detail
  if (changed.length > 0) {
    md += `## 変更ファイル詳細\n\n`;
    for (const file of changed) {
      md += `### ${file.path}\n`;
      md += `- 上流: ${file.upstreamLines} 行 / ローカル: ${file.localLines} 行\n`;
      md += `- 差分: +${file.diff.added} lines, -${file.diff.removed} lines\n`;
      if (file.newSections.length > 0) {
        md += `- 上流で追加されたセクション: ${file.newSections.map(s => `「${s}」`).join(', ')}\n`;
      }
      md += `- 推奨: Claudeが差分を確認してから判断\n`;
      md += '\n';
    }
  }

  // Protected files detail
  if (protectedChanged.length > 0) {
    md += `## 保護ファイル詳細\n\n`;
    md += `> 保護ファイルは自動変更しません。手動で確認・マージしてください。\n\n`;
    for (const file of protectedChanged) {
      md += `### ${file.path}\n`;
      md += `- 上流: ${file.upstreamLines} 行 / ローカル: ${file.localLines} 行\n`;
      md += `- 差分: +${file.diff.added} lines, -${file.diff.removed} lines\n`;
      if (file.newSections.length > 0) {
        md += `- 上流で追加されたセクション: ${file.newSections.map(s => `「${s}」`).join(', ')}\n`;
      }
      md += `- 推奨: 差分を確認してから手動マージ\n`;
      md += '\n';
    }
  }

  md += `---\n`;
  md += `*このレポートは \`npm run upstream:merge\` で自動生成されました。*\n`;
  md += `*Claudeがこのレポートを読んで、変更ファイルを1つずつ清水さんに確認します。*\n`;

  return md;
}

main();
