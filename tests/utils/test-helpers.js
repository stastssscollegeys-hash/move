"use strict";
/**
 * Test Helpers for TAISUN v2 Integration Tests
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
exports.waitWithTimeout = exports.generateTestFixtures = exports.validateSkillDefinition = exports.validateAgentDefinition = exports.mockSkillExecution = exports.mockAgentExecution = exports.listSkills = exports.listAgents = exports.loadSkillDefinition = exports.loadAgentDefinition = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const yaml = __importStar(require("yaml"));
// Agent and Skill definitions paths
const AGENTS_PATH = path.join(__dirname, '../../.claude/agents');
const SKILLS_PATH = path.join(__dirname, '../../.claude/skills');
/**
 * Load agent definition from Markdown file with YAML frontmatter
 * Agent files are stored as .md files directly in .claude/agents/
 */
function loadAgentDefinition(agentName) {
    // Try multiple file naming patterns
    const patterns = [
        `ait42-${agentName}.md`,
        `00-ait42-${agentName}.md`,
        `ait42-01-${agentName}.md`,
        `${agentName}.md`,
    ];
    for (const pattern of patterns) {
        const filePath = path.join(AGENTS_PATH, pattern);
        if (fs.existsSync(filePath)) {
            const content = fs.readFileSync(filePath, 'utf-8');
            return parseAgentMarkdown(content, agentName);
        }
    }
    // Fallback: search all files for matching agent name
    const files = fs.readdirSync(AGENTS_PATH).filter((f) => f.endsWith('.md'));
    for (const file of files) {
        const filePath = path.join(AGENTS_PATH, file);
        const content = fs.readFileSync(filePath, 'utf-8');
        const parsed = parseAgentMarkdown(content, agentName);
        if (parsed && parsed.name === agentName) {
            return parsed;
        }
    }
    return null;
}
exports.loadAgentDefinition = loadAgentDefinition;
/**
 * Parse agent markdown file with YAML frontmatter
 */
function parseAgentMarkdown(content, fallbackName) {
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (frontmatterMatch) {
        try {
            const frontmatter = yaml.parse(frontmatterMatch[1]);
            return {
                name: frontmatter.name || fallbackName,
                description: frontmatter.description || '',
                model: frontmatter.model,
                tools: typeof frontmatter.tools === 'string'
                    ? frontmatter.tools.split(',').map((t) => t.trim())
                    : frontmatter.tools,
            };
        }
        catch {
            return null;
        }
    }
    return null;
}
/**
 * Load skill definition from SKILL.md
 */
function loadSkillDefinition(skillName) {
    const skillPath = path.join(SKILLS_PATH, skillName, 'SKILL.md');
    if (!fs.existsSync(skillPath)) {
        return null;
    }
    const content = fs.readFileSync(skillPath, 'utf-8');
    // Parse YAML frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (frontmatterMatch) {
        const frontmatter = yaml.parse(frontmatterMatch[1]);
        return {
            name: frontmatter.name || skillName,
            description: frontmatter.description || '',
            instructions: content.replace(/^---\n[\s\S]*?\n---\n/, ''),
        };
    }
    return {
        name: skillName,
        description: '',
        instructions: content,
    };
}
exports.loadSkillDefinition = loadSkillDefinition;
/**
 * List all available agents
 * Agent files are stored as .md files directly in .claude/agents/
 */
function listAgents() {
    const agents = [];
    if (!fs.existsSync(AGENTS_PATH)) {
        return agents;
    }
    const files = fs.readdirSync(AGENTS_PATH).filter((f) => f.endsWith('.md'));
    for (const file of files) {
        const filePath = path.join(AGENTS_PATH, file);
        const content = fs.readFileSync(filePath, 'utf-8');
        const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
        if (frontmatterMatch) {
            try {
                const frontmatter = yaml.parse(frontmatterMatch[1]);
                if (frontmatter.name) {
                    agents.push(frontmatter.name);
                }
            }
            catch {
                // Skip files with invalid frontmatter
            }
        }
    }
    return agents;
}
exports.listAgents = listAgents;
/**
 * List all available skills
 */
function listSkills() {
    const skills = [];
    const skillDirs = fs.readdirSync(SKILLS_PATH);
    for (const dir of skillDirs) {
        const skillPath = path.join(SKILLS_PATH, dir);
        if (fs.statSync(skillPath).isDirectory()) {
            const skillMdPath = path.join(skillPath, 'SKILL.md');
            if (fs.existsSync(skillMdPath)) {
                skills.push(dir);
            }
        }
    }
    return skills;
}
exports.listSkills = listSkills;
/**
 * Mock agent execution for testing
 */
async function mockAgentExecution(agentName, prompt, options = {}) {
    const startTime = Date.now();
    // Note: timeout option available for future use
    void options.timeout;
    try {
        const agent = loadAgentDefinition(agentName);
        if (!agent) {
            return {
                success: false,
                agent: agentName,
                duration: Date.now() - startTime,
                error: `Agent '${agentName}' not found`,
            };
        }
        // Simulate agent processing
        await new Promise((resolve) => setTimeout(resolve, 100));
        return {
            success: true,
            agent: agentName,
            duration: Date.now() - startTime,
            output: `Mock response from ${agentName}: processed "${prompt.substring(0, 50)}..."`,
        };
    }
    catch (error) {
        return {
            success: false,
            agent: agentName,
            duration: Date.now() - startTime,
            error: error instanceof Error ? error.message : String(error),
        };
    }
}
exports.mockAgentExecution = mockAgentExecution;
/**
 * Mock skill execution for testing
 */
async function mockSkillExecution(skillName, args, options = {}) {
    const startTime = Date.now();
    // Note: timeout option available for future use
    void options.timeout;
    try {
        const skill = loadSkillDefinition(skillName);
        if (!skill) {
            return {
                success: false,
                skill: skillName,
                duration: Date.now() - startTime,
                error: `Skill '${skillName}' not found`,
            };
        }
        // Simulate skill processing
        await new Promise((resolve) => setTimeout(resolve, 100));
        return {
            success: true,
            skill: skillName,
            duration: Date.now() - startTime,
            output: `Mock response from ${skillName}: processed "${args.substring(0, 50)}..."`,
        };
    }
    catch (error) {
        return {
            success: false,
            skill: skillName,
            duration: Date.now() - startTime,
            error: error instanceof Error ? error.message : String(error),
        };
    }
}
exports.mockSkillExecution = mockSkillExecution;
/**
 * Validate agent definition structure
 */
function validateAgentDefinition(agent) {
    const errors = [];
    if (!agent.name) {
        errors.push('Missing required field: name');
    }
    if (!agent.description) {
        errors.push('Missing required field: description');
    }
    // Accept both short names (haiku, sonnet, opus) and full model IDs (claude-3-5-haiku-20241022)
    const validModels = ['haiku', 'sonnet', 'opus'];
    const validModelPrefixes = ['claude-3-5-haiku', 'claude-3-5-sonnet', 'claude-opus', 'claude-3-opus'];
    if (agent.model) {
        const isShortName = validModels.includes(agent.model);
        const isFullName = validModelPrefixes.some((prefix) => agent.model?.startsWith(prefix));
        if (!isShortName && !isFullName) {
            errors.push(`Invalid model: ${agent.model}. Must be haiku, sonnet, or opus`);
        }
    }
    return errors;
}
exports.validateAgentDefinition = validateAgentDefinition;
/**
 * Validate skill definition structure
 */
function validateSkillDefinition(skill) {
    const errors = [];
    if (!skill.name) {
        errors.push('Missing required field: name');
    }
    if (!skill.description) {
        errors.push('Missing required field: description');
    }
    return errors;
}
exports.validateSkillDefinition = validateSkillDefinition;
/**
 * Generate test fixtures
 */
function generateTestFixtures() {
    return {
        samplePrompts: {
            'system-architect': 'Design a microservices architecture for an e-commerce platform',
            'backend-developer': 'Implement a REST API for user authentication',
            'frontend-developer': 'Create a React component for a login form',
            'test-generator': 'Generate unit tests for the user service',
            'code-reviewer': 'Review this pull request for security issues',
            'bug-fixer': 'Fix the NullPointerException in the payment module',
            'ait42-coordinator': 'Implement a complete user management feature',
        },
        sampleSkillArgs: {
            'sales-letter': '--product "Online Course" --target "Entrepreneurs"',
            'step-mail': '--theme "Fitness Program" --days 7',
            'lp-analysis': 'https://example.com/landing-page',
            'customer-support': 'Customer inquiry about order status',
            'nanobanana-prompts': 'YouTube thumbnail for AI tutorial',
            'security-scan-trivy': '',
            'japanese-tts-reading': '"こんにちは、世界"',
        },
    };
}
exports.generateTestFixtures = generateTestFixtures;
/**
 * Wait for async operations with timeout
 */
async function waitWithTimeout(promise, timeout, timeoutMessage = 'Operation timed out') {
    let timeoutHandle;
    const timeoutPromise = new Promise((_, reject) => {
        timeoutHandle = setTimeout(() => reject(new Error(timeoutMessage)), timeout);
    });
    return Promise.race([promise, timeoutPromise]).finally(() => {
        clearTimeout(timeoutHandle);
    });
}
exports.waitWithTimeout = waitWithTimeout;
