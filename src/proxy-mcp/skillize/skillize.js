"use strict";
/**
 * Skillize - M5
 *
 * Generate skills from URLs using templates
 *
 * Features:
 * - Template-driven: docs, ecommerce, internal-tool
 * - dry-run by default (confirmWrite=true to write)
 * - Minimal output: summary + refId
 * - Full generated skill stored in memory (long-term)
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
exports.listGeneratedSkills = exports.skillize = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const templates_1 = require("./templates");
const browser_1 = require("../browser");
const memory_1 = require("../tools/memory");
const SKILLS_DIR = path.join(process.cwd(), '.claude', 'skills');
/**
 * Generate a skill from URL
 *
 * @param url - URL to analyze and generate skill from
 * @param options - Skillize options
 * @returns SkillizeResult with summary + refId
 */
async function skillize(url, options = {}) {
    const { template: templateType, name: customName, confirmWrite = false, namespace = 'long-term' } = options;
    // Validate URL
    try {
        new URL(url);
    }
    catch {
        return {
            success: false,
            error: `Invalid URL: ${url}`,
        };
    }
    try {
        // Step 1: Read URL content using M4 web skill
        const readResult = await (0, browser_1.readUrl)(url, { namespace: 'short-term', maxLength: 30000 });
        if (!readResult.success) {
            return {
                success: false,
                error: `Failed to read URL: ${readResult.error}`,
            };
        }
        // Step 2: Analyze URL content
        const analysis = analyzeUrlContent(url, readResult.summary || '', readResult.data);
        // Step 3: Select template
        const template = templateType ? (0, templates_1.getTemplate)(templateType) : (0, templates_1.detectTemplate)(analysis);
        if (!template) {
            return {
                success: false,
                error: `Unknown template type: ${templateType}`,
            };
        }
        // Step 4: Generate skill using template
        const generated = template.generate(analysis);
        // Override name if custom name provided
        if (customName) {
            generated.name = sanitizeName(customName);
        }
        // Step 5: Store full generated skill in memory (long-term)
        const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
            skill: generated,
            analysis,
            url,
            generatedAt: new Date().toISOString(),
        }), namespace, {
            tags: ['skillize', 'generated-skill', template.type, generated.name],
            source: 'skillize',
        });
        if (!memResult.success) {
            return {
                success: false,
                error: `Failed to store skill: ${memResult.error}`,
            };
        }
        // Step 6: Write files if confirmWrite=true
        let writtenPath;
        if (confirmWrite) {
            try {
                writtenPath = await writeSkillFiles(generated);
            }
            catch (err) {
                return {
                    success: false,
                    error: `Failed to write skill files: ${err instanceof Error ? err.message : String(err)}`,
                    refId: memResult.referenceId,
                };
            }
        }
        // Step 7: Return minimal output (summary + refId)
        const preview = generated.skillMd.substring(0, 300);
        const summary = `Generated skill "${generated.name}" using ${template.type} template.\n\n${preview}${generated.skillMd.length > 300 ? '...' : ''}`;
        return {
            success: true,
            refId: memResult.referenceId,
            summary,
            template: template.type,
            data: {
                skillName: generated.name,
                preview: preview,
                filesCount: 1 + Object.keys(generated.files || {}).length,
                written: confirmWrite,
                path: writtenPath,
                message: confirmWrite
                    ? `Skill written to ${writtenPath}. Use memory_search("${memResult.referenceId}") for full content.`
                    : `Dry-run complete. Use confirmWrite=true to write. Use memory_search("${memResult.referenceId}") for full content.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `Skillize failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.skillize = skillize;
/**
 * Analyze URL content for template selection
 */
function analyzeUrlContent(url, summary, data) {
    const parsedUrl = new URL(url);
    const contentLower = summary.toLowerCase();
    // Detect content type
    let contentType = 'unknown';
    if (contentLower.includes('documentation') ||
        contentLower.includes('api reference') ||
        contentLower.includes('getting started') ||
        contentLower.includes('installation')) {
        contentType = 'documentation';
    }
    else if (contentLower.includes('api') ||
        contentLower.includes('endpoint') ||
        contentLower.includes('request') ||
        contentLower.includes('response')) {
        contentType = 'api';
    }
    else if (contentLower.includes('$') ||
        contentLower.includes('price') ||
        contentLower.includes('add to cart') ||
        contentLower.includes('buy')) {
        contentType = 'product';
    }
    else if (contentLower.includes('dashboard') ||
        contentLower.includes('admin') ||
        contentLower.includes('settings')) {
        contentType = 'tool';
    }
    else if (contentLower.includes('article') ||
        contentLower.includes('blog') ||
        contentLower.includes('post')) {
        contentType = 'article';
    }
    // Extract sections (headings)
    const headingMatches = summary.match(/^#+\s+.+$/gm) || [];
    const sections = headingMatches.map((h) => h.replace(/^#+\s+/, '').trim()).slice(0, 20);
    // Extract product info if applicable
    let productInfo;
    if (contentType === 'product') {
        const priceMatch = summary.match(/\$[\d,]+\.?\d*/);
        productInfo = {
            name: data?.title || parsedUrl.pathname.split('/').pop() || undefined,
            price: priceMatch ? priceMatch[0] : undefined,
        };
    }
    // Extract API endpoints if applicable
    let apiEndpoints;
    if (contentType === 'api') {
        const endpointMatches = summary.match(/(GET|POST|PUT|DELETE|PATCH)\s+\/[\w\-/{}]+/gi);
        apiEndpoints = endpointMatches?.slice(0, 10);
    }
    return {
        url,
        title: data?.title || parsedUrl.hostname,
        description: summary.substring(0, 200),
        contentType,
        hostname: parsedUrl.hostname,
        path: parsedUrl.pathname,
        sections,
        sampleContent: summary,
        apiEndpoints,
        productInfo,
    };
}
/**
 * Write skill files to disk
 */
async function writeSkillFiles(skill) {
    const skillDir = path.join(SKILLS_DIR, skill.name);
    // Create directory
    if (!fs.existsSync(skillDir)) {
        fs.mkdirSync(skillDir, { recursive: true });
    }
    // Write SKILL.md
    fs.writeFileSync(path.join(skillDir, 'SKILL.md'), skill.skillMd, 'utf-8');
    // Write additional files
    if (skill.files) {
        for (const [filename, content] of Object.entries(skill.files)) {
            fs.writeFileSync(path.join(skillDir, filename), content, 'utf-8');
        }
    }
    return skillDir;
}
/**
 * List generated skills
 */
function listGeneratedSkills() {
    if (!fs.existsSync(SKILLS_DIR)) {
        return [];
    }
    return fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
        .filter((entry) => entry.isDirectory())
        .map((entry) => entry.name);
}
exports.listGeneratedSkills = listGeneratedSkills;
/**
 * Sanitize string for use as skill name
 */
function sanitizeName(name) {
    return name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .substring(0, 50) || 'unnamed-skill';
}
