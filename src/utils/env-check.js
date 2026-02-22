"use strict";
/**
 * Environment Check Utility
 *
 * Checks for common configuration issues and provides helpful advice.
 * P20: Auto-advice feature for beginners
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
exports.runDoctor = exports.formatEnvCheckResults = exports.runEnvChecks = exports.checkUnicodeReminder = exports.checkBun = exports.checkOpenCode = exports.checkTextSafety = exports.checkGitConfig = exports.checkEnvFile = exports.checkConfigFiles = exports.checkNodeVersion = exports.checkGhCli = exports.checkGitHubToken = void 0;
const child_process_1 = require("child_process");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const i18n_1 = require("../i18n");
const MIN_NODE_VERSION = '18.0.0';
/**
 * Compare semver versions
 */
function compareVersions(a, b) {
    const aParts = a.split('.').map(Number);
    const bParts = b.split('.').map(Number);
    for (let i = 0; i < 3; i++) {
        const aVal = aParts[i] || 0;
        const bVal = bParts[i] || 0;
        if (aVal > bVal)
            return 1;
        if (aVal < bVal)
            return -1;
    }
    return 0;
}
/**
 * Check if GITHUB_TOKEN is set
 */
function checkGitHubToken() {
    const token = process.env.GITHUB_TOKEN;
    if (!token) {
        return {
            name: 'GITHUB_TOKEN',
            status: 'error',
            message: 'GITHUB_TOKEN is not set',
            advice: (0, i18n_1.t)('env.missing.github_token'),
        };
    }
    // Basic validation
    if (!token.startsWith('ghp_') && !token.startsWith('github_pat_')) {
        return {
            name: 'GITHUB_TOKEN',
            status: 'warning',
            message: 'GITHUB_TOKEN format may be incorrect',
            advice: 'Expected format: ghp_xxxx or github_pat_xxxx',
        };
    }
    return {
        name: 'GITHUB_TOKEN',
        status: 'ok',
        message: 'GITHUB_TOKEN is configured',
    };
}
exports.checkGitHubToken = checkGitHubToken;
/**
 * Check if gh CLI is available
 */
function checkGhCli() {
    try {
        (0, child_process_1.execSync)('gh --version', { stdio: 'pipe' });
    }
    catch {
        return {
            name: 'GitHub CLI',
            status: 'warning',
            message: 'GitHub CLI (gh) is not installed',
            advice: (0, i18n_1.t)('env.missing.gh_cli'),
        };
    }
    // Check if logged in
    try {
        const result = (0, child_process_1.execSync)('gh auth status 2>&1', { encoding: 'utf8', stdio: 'pipe' });
        if (result.includes('Logged in')) {
            return {
                name: 'GitHub CLI',
                status: 'ok',
                message: 'GitHub CLI is installed and logged in',
            };
        }
    }
    catch {
        // gh auth status returns non-zero when not logged in
    }
    return {
        name: 'GitHub CLI',
        status: 'warning',
        message: 'GitHub CLI is installed but not logged in',
        advice: (0, i18n_1.t)('env.missing.gh_login'),
    };
}
exports.checkGhCli = checkGhCli;
/**
 * Check Node.js version
 */
function checkNodeVersion() {
    const currentVersion = process.version.replace(/^v/, '');
    if (compareVersions(currentVersion, MIN_NODE_VERSION) < 0) {
        return {
            name: 'Node.js',
            status: 'error',
            message: `Node.js version ${currentVersion} is too old`,
            advice: (0, i18n_1.t)('env.missing.node_version', {
                current: currentVersion,
                required: MIN_NODE_VERSION,
            }),
        };
    }
    return {
        name: 'Node.js',
        status: 'ok',
        message: `Node.js ${currentVersion} is installed`,
    };
}
exports.checkNodeVersion = checkNodeVersion;
/**
 * Check if required config files exist
 */
function checkConfigFiles() {
    const configDir = path.join(process.cwd(), 'config', 'proxy-mcp');
    const requiredFiles = ['internal-mcps.json'];
    const missingFiles = [];
    for (const file of requiredFiles) {
        const filePath = path.join(configDir, file);
        if (!fs.existsSync(filePath)) {
            missingFiles.push(file);
        }
    }
    if (missingFiles.length > 0) {
        return {
            name: 'Config Files',
            status: 'warning',
            message: `Missing config files: ${missingFiles.join(', ')}`,
            advice: `Run 'npm run setup' or create the missing files manually.`,
        };
    }
    return {
        name: 'Config Files',
        status: 'ok',
        message: 'All required config files exist',
    };
}
exports.checkConfigFiles = checkConfigFiles;
/**
 * Check if .env file exists
 */
function checkEnvFile() {
    const envPath = path.join(process.cwd(), '.env');
    const envExamplePath = path.join(process.cwd(), '.env.example');
    if (!fs.existsSync(envPath)) {
        const advice = fs.existsSync(envExamplePath)
            ? 'Copy .env.example to .env and fill in the values:\n  cp .env.example .env'
            : 'Create a .env file with required environment variables.';
        return {
            name: '.env File',
            status: 'warning',
            message: '.env file not found',
            advice,
        };
    }
    return {
        name: '.env File',
        status: 'ok',
        message: '.env file exists',
    };
}
exports.checkEnvFile = checkEnvFile;
/**
 * Check Git configuration
 */
function checkGitConfig() {
    try {
        // Check if in a git repository
        (0, child_process_1.execSync)('git rev-parse --is-inside-work-tree', { stdio: 'pipe' });
    }
    catch {
        return {
            name: 'Git',
            status: 'error',
            message: 'Not in a Git repository',
            advice: (0, i18n_1.t)('env.missing.git_repo'),
        };
    }
    // Check for user configuration
    try {
        (0, child_process_1.execSync)('git config user.email', { stdio: 'pipe' });
        (0, child_process_1.execSync)('git config user.name', { stdio: 'pipe' });
    }
    catch {
        return {
            name: 'Git',
            status: 'warning',
            message: 'Git user not configured',
            advice: 'Configure Git user:\n  git config --global user.name "Your Name"\n  git config --global user.email "your@email.com"',
        };
    }
    return {
        name: 'Git',
        status: 'ok',
        message: 'Git is configured',
    };
}
exports.checkGitConfig = checkGitConfig;
/**
 * Check text safety tools availability
 */
function checkTextSafety() {
    const safeReplacePath = path.join(process.cwd(), 'scripts', 'text', 'safe-replace.ts');
    const utf8GuardPath = path.join(process.cwd(), 'scripts', 'text', 'utf8-guard.ts');
    const hasSafeReplace = fs.existsSync(safeReplacePath);
    const hasUtf8Guard = fs.existsSync(utf8GuardPath);
    if (!hasSafeReplace || !hasUtf8Guard) {
        const missing = [];
        if (!hasSafeReplace)
            missing.push('safe-replace.ts');
        if (!hasUtf8Guard)
            missing.push('utf8-guard.ts');
        return {
            name: 'Text Safety Tools',
            status: 'warning',
            message: `Missing text safety tools: ${missing.join(', ')}`,
            advice: (0, i18n_1.t)('env.missing.text_safety'),
        };
    }
    return {
        name: 'Text Safety Tools',
        status: 'ok',
        message: 'Text safety tools available (safe-replace, utf8-guard)',
    };
}
exports.checkTextSafety = checkTextSafety;
/**
 * Check OpenCode/OMO availability (optional feature)
 */
function checkOpenCode() {
    try {
        (0, child_process_1.execSync)('opencode --version', { stdio: 'pipe' });
        return {
            name: 'OpenCode (Optional)',
            status: 'ok',
            message: 'OpenCode CLI is available',
            advice: 'You can use /opencode-setup, /opencode-fix, /opencode-ralph-loop commands.',
        };
    }
    catch {
        return {
            name: 'OpenCode (Optional)',
            status: 'warning',
            message: 'OpenCode CLI is not installed',
            advice: 'OpenCode/OMO is an optional feature for advanced bug fixing and TDD iteration.\n' +
                'If needed, see: docs/opencode/README-ja.md\n' +
                'Note: This is NOT required for normal TAISUN usage.',
        };
    }
}
exports.checkOpenCode = checkOpenCode;
/**
 * Check bun/bunx availability (optional, for OMO installation)
 */
function checkBun() {
    try {
        (0, child_process_1.execSync)('bunx --version', { stdio: 'pipe' });
        return {
            name: 'Bun/Bunx (Optional)',
            status: 'ok',
            message: 'Bun/Bunx is available',
        };
    }
    catch {
        return {
            name: 'Bun/Bunx (Optional)',
            status: 'warning',
            message: 'Bun/Bunx is not installed',
            advice: 'Bun/Bunx may be needed if you want to install Oh My OpenCode (OMO).\n' +
                'Alternative: You can use npx instead of bunx.\n' +
                'Note: This is NOT required for normal TAISUN usage.',
        };
    }
}
exports.checkBun = checkBun;
/**
 * Check for Unicode/encoding issues (reminder)
 */
function checkUnicodeReminder() {
    return {
        name: 'Unicode Safety',
        status: 'ok',
        message: 'Remember to run `npm run check:unicode` after editing files',
        advice: 'To prevent encoding issues:\n' +
            '  - Run: npm run check:unicode\n' +
            '  - Use: npm run text:utf8-guard\n' +
            '  - See: docs/operations/text-safety-ja.md',
    };
}
exports.checkUnicodeReminder = checkUnicodeReminder;
/**
 * Run all environment checks
 */
function runEnvChecks() {
    const results = [
        checkNodeVersion(),
        checkGitConfig(),
        checkEnvFile(),
        checkGitHubToken(),
        checkGhCli(),
        checkConfigFiles(),
        checkTextSafety(),
        checkOpenCode(),
        checkBun(),
        checkUnicodeReminder(),
    ];
    const critical = results.filter((r) => r.status === 'error').length;
    const warnings = results.filter((r) => r.status === 'warning').length;
    return {
        ok: critical === 0,
        results,
        critical,
        warnings,
    };
}
exports.runEnvChecks = runEnvChecks;
/**
 * Format environment check results for console output
 */
function formatEnvCheckResults(summary) {
    const lines = [];
    lines.push('=== Environment Check ===\n');
    for (const result of summary.results) {
        const icon = result.status === 'ok' ? '✅' : result.status === 'warning' ? '⚠️' : '❌';
        lines.push(`${icon} ${result.name}: ${result.message}`);
        if (result.advice) {
            lines.push('');
            lines.push(result.advice);
            lines.push('');
        }
    }
    lines.push('\n--- Summary ---');
    if (summary.ok) {
        lines.push('✅ All critical checks passed');
    }
    else {
        lines.push(`❌ ${summary.critical} critical issue(s) found`);
    }
    if (summary.warnings > 0) {
        lines.push(`⚠️ ${summary.warnings} warning(s)`);
    }
    return lines.join('\n');
}
exports.formatEnvCheckResults = formatEnvCheckResults;
/**
 * CLI entry point for environment check
 */
function runDoctor() {
    const summary = runEnvChecks();
    console.log(formatEnvCheckResults(summary));
    process.exit(summary.ok ? 0 : 1);
}
exports.runDoctor = runDoctor;
// Export for direct execution
if (require.main === module) {
    runDoctor();
}
