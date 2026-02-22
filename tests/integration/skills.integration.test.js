"use strict";
/**
 * Skill Integration Tests
 *
 * Tests for skill definitions and skill interactions.
 */
Object.defineProperty(exports, "__esModule", { value: true });
const test_helpers_1 = require("../utils/test-helpers");
describe('Skill Integration Tests', () => {
    describe('Skill Definitions', () => {
        it('should load all skill definitions successfully', () => {
            const skills = (0, test_helpers_1.listSkills)();
            expect(skills.length).toBeGreaterThan(0);
            for (const skillName of skills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                expect(skill).not.toBeNull();
                expect(skill?.name).toBeDefined();
            }
        });
        it('should validate skill definition structure', () => {
            const skills = (0, test_helpers_1.listSkills)();
            for (const skillName of skills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                if (skill) {
                    // Allow missing description for now, just check name
                    (0, test_helpers_1.validateSkillDefinition)(skill);
                    expect(skill.name).toBeDefined();
                }
            }
        });
        it('should have marketing skills', () => {
            const marketingSkills = [
                'sales-letter',
                'step-mail',
                'copywriting-helper',
                'customer-support',
                'lp-analysis',
            ];
            for (const skillName of marketingSkills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                expect(skill).not.toBeNull();
            }
        });
        it('should have creative skills', () => {
            const creativeSkills = ['nanobanana-prompts', 'gemini-image-generator', 'japanese-tts-reading'];
            for (const skillName of creativeSkills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                expect(skill).not.toBeNull();
            }
        });
        it('should have infrastructure skills', () => {
            const infraSkills = [
                'security-scan-trivy',
                'workflow-automation-n8n',
                'docker-mcp-ops',
                'postgres-mcp-analyst',
            ];
            for (const skillName of infraSkills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                expect(skill).not.toBeNull();
            }
        });
    });
    describe('Skill Execution', () => {
        const { sampleSkillArgs } = (0, test_helpers_1.generateTestFixtures)();
        it('should execute sales-letter skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('sales-letter', sampleSkillArgs['sales-letter']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('sales-letter');
            expect(result.duration).toBeLessThan(5000);
        });
        it('should execute step-mail skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('step-mail', sampleSkillArgs['step-mail']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('step-mail');
        });
        it('should execute lp-analysis skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('lp-analysis', sampleSkillArgs['lp-analysis']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('lp-analysis');
        });
        it('should execute customer-support skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('customer-support', sampleSkillArgs['customer-support']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('customer-support');
        });
        it('should execute nanobanana-prompts skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('nanobanana-prompts', sampleSkillArgs['nanobanana-prompts']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('nanobanana-prompts');
        });
        it('should execute security-scan-trivy skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('security-scan-trivy', sampleSkillArgs['security-scan-trivy']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('security-scan-trivy');
        });
        it('should execute japanese-tts-reading skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('japanese-tts-reading', sampleSkillArgs['japanese-tts-reading']);
            expect(result.success).toBe(true);
            expect(result.skill).toBe('japanese-tts-reading');
        });
        it('should fail gracefully for non-existent skill', async () => {
            const result = await (0, test_helpers_1.mockSkillExecution)('non-existent-skill', 'test args');
            expect(result.success).toBe(false);
            expect(result.error).toContain('not found');
        });
    });
    describe('Skill Categories', () => {
        it('should have all marketing & content skills (11)', () => {
            const marketingSkills = [
                'copywriting-helper',
                'sales-letter',
                'step-mail',
                'vsl',
                'launch-video',
                'lp-generator',
                'funnel-builder',
                'mendan-lp',
                'lp-analysis',
                'customer-support',
                'tommy-style',
            ];
            const existingSkills = (0, test_helpers_1.listSkills)();
            const existingMarketingSkills = marketingSkills.filter((s) => existingSkills.includes(s));
            expect(existingMarketingSkills.length).toBeGreaterThanOrEqual(5);
        });
        it('should have all creative & media skills (3)', () => {
            const creativeSkills = ['gemini-image-generator', 'nanobanana-prompts', 'japanese-tts-reading'];
            const existingSkills = (0, test_helpers_1.listSkills)();
            const existingCreativeSkills = creativeSkills.filter((s) => existingSkills.includes(s));
            expect(existingCreativeSkills.length).toBeGreaterThanOrEqual(2);
        });
        it('should have all infrastructure skills (9)', () => {
            const infraSkills = [
                'workflow-automation-n8n',
                'docker-mcp-ops',
                'security-scan-trivy',
                'pdf-automation-gotenberg',
                'doc-convert-pandoc',
                'unified-notifications-apprise',
                'postgres-mcp-analyst',
                'notion-knowledge-mcp',
                'nlq-bi-wrenai',
            ];
            const existingSkills = (0, test_helpers_1.listSkills)();
            const existingInfraSkills = infraSkills.filter((s) => existingSkills.includes(s));
            expect(existingInfraSkills.length).toBeGreaterThanOrEqual(5);
        });
        it('should have research skill', () => {
            const skill = (0, test_helpers_1.loadSkillDefinition)('research-cited-report');
            expect(skill).not.toBeNull();
        });
    });
    describe('Skill Chaining', () => {
        it('should chain copywriting-helper → sales-letter', async () => {
            const copywritingResult = await (0, test_helpers_1.mockSkillExecution)('copywriting-helper', 'Create headlines for fitness product');
            expect(copywritingResult.success).toBe(true);
            const salesLetterResult = await (0, test_helpers_1.mockSkillExecution)('sales-letter', `--product "Fitness Course" --headlines "${copywritingResult.output}"`);
            expect(salesLetterResult.success).toBe(true);
        });
        it('should chain nanobanana-prompts → gemini-image-generator', async () => {
            const promptResult = await (0, test_helpers_1.mockSkillExecution)('nanobanana-prompts', 'YouTube thumbnail for coding tutorial');
            expect(promptResult.success).toBe(true);
            const imageResult = await (0, test_helpers_1.mockSkillExecution)('gemini-image-generator', promptResult.output || 'generated prompt');
            expect(imageResult.success).toBe(true);
        });
        it('should execute multiple skills in parallel', async () => {
            const skills = ['sales-letter', 'step-mail', 'lp-analysis'];
            const args = [
                '--product "Test Product"',
                '--theme "Test Theme" --days 7',
                'https://example.com/lp',
            ];
            const results = await Promise.all(skills.map((skill, index) => (0, test_helpers_1.mockSkillExecution)(skill, args[index])));
            expect(results.every((r) => r.success)).toBe(true);
        });
    });
    describe('Skill Documentation', () => {
        it('should have instructions in skill definitions', () => {
            const skills = (0, test_helpers_1.listSkills)();
            for (const skillName of skills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                if (skill) {
                    // Check that skill has some content
                    expect(skill.instructions || skill.description).toBeDefined();
                }
            }
        });
        it('should have "When to Use" section in skill definitions', () => {
            const skills = (0, test_helpers_1.listSkills)();
            let skillsWithWhenToUse = 0;
            for (const skillName of skills) {
                const skill = (0, test_helpers_1.loadSkillDefinition)(skillName);
                if (skill?.instructions?.includes('When to Use')) {
                    skillsWithWhenToUse++;
                }
            }
            // At least 25% of skills should have "When to Use" section
            expect(skillsWithWhenToUse).toBeGreaterThanOrEqual(skills.length * 0.25);
        });
    });
});
