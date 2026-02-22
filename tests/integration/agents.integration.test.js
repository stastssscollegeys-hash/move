"use strict";
/**
 * Agent Integration Tests
 *
 * Tests for multi-agent coordination and agent interactions.
 */
Object.defineProperty(exports, "__esModule", { value: true });
const test_helpers_1 = require("../utils/test-helpers");
describe('Agent Integration Tests', () => {
    describe('Agent Definitions', () => {
        it('should load all agent definitions successfully', () => {
            const agents = (0, test_helpers_1.listAgents)();
            expect(agents.length).toBeGreaterThan(0);
            for (const agentName of agents) {
                const agent = (0, test_helpers_1.loadAgentDefinition)(agentName);
                expect(agent).not.toBeNull();
                expect(agent?.name).toBeDefined();
            }
        });
        it('should validate agent definition structure', () => {
            const agents = (0, test_helpers_1.listAgents)();
            for (const agentName of agents) {
                const agent = (0, test_helpers_1.loadAgentDefinition)(agentName);
                if (agent) {
                    const errors = (0, test_helpers_1.validateAgentDefinition)(agent);
                    expect(errors).toEqual([]);
                }
            }
        });
        it('should have required coordinator agents', () => {
            const requiredCoordinators = [
                'ait42-coordinator',
                'ait42-coordinator-fast',
                'omega-aware-coordinator',
                'self-healing-coordinator',
            ];
            for (const coordinator of requiredCoordinators) {
                const agent = (0, test_helpers_1.loadAgentDefinition)(coordinator);
                expect(agent).not.toBeNull();
            }
        });
        it('should have required development agents', () => {
            const requiredAgents = [
                'system-architect',
                'backend-developer',
                'frontend-developer',
                'api-developer',
                'database-developer',
            ];
            for (const agentName of requiredAgents) {
                const agent = (0, test_helpers_1.loadAgentDefinition)(agentName);
                expect(agent).not.toBeNull();
            }
        });
        it('should have required quality assurance agents', () => {
            const requiredAgents = [
                'code-reviewer',
                'test-generator',
                'security-tester',
                'qa-validator',
            ];
            for (const agentName of requiredAgents) {
                const agent = (0, test_helpers_1.loadAgentDefinition)(agentName);
                expect(agent).not.toBeNull();
            }
        });
    });
    describe('Agent Execution', () => {
        const { samplePrompts } = (0, test_helpers_1.generateTestFixtures)();
        it('should execute system-architect agent', async () => {
            const result = await (0, test_helpers_1.mockAgentExecution)('system-architect', samplePrompts['system-architect']);
            expect(result.success).toBe(true);
            expect(result.agent).toBe('system-architect');
            expect(result.duration).toBeLessThan(5000);
        });
        it('should execute backend-developer agent', async () => {
            const result = await (0, test_helpers_1.mockAgentExecution)('backend-developer', samplePrompts['backend-developer']);
            expect(result.success).toBe(true);
            expect(result.agent).toBe('backend-developer');
        });
        it('should execute test-generator agent', async () => {
            const result = await (0, test_helpers_1.mockAgentExecution)('test-generator', samplePrompts['test-generator']);
            expect(result.success).toBe(true);
            expect(result.agent).toBe('test-generator');
        });
        it('should execute code-reviewer agent', async () => {
            const result = await (0, test_helpers_1.mockAgentExecution)('code-reviewer', samplePrompts['code-reviewer']);
            expect(result.success).toBe(true);
            expect(result.agent).toBe('code-reviewer');
        });
        it('should fail gracefully for non-existent agent', async () => {
            const result = await (0, test_helpers_1.mockAgentExecution)('non-existent-agent', 'test prompt');
            expect(result.success).toBe(false);
            expect(result.error).toContain('not found');
        });
    });
    describe('Multi-Agent Coordination', () => {
        const { samplePrompts } = (0, test_helpers_1.generateTestFixtures)();
        it('should execute ait42-coordinator', async () => {
            const result = await (0, test_helpers_1.mockAgentExecution)('ait42-coordinator', samplePrompts['ait42-coordinator']);
            expect(result.success).toBe(true);
            expect(result.agent).toBe('ait42-coordinator');
        });
        it('should execute agents in sequence', async () => {
            const agents = ['system-architect', 'backend-developer', 'test-generator'];
            const results = [];
            for (const agent of agents) {
                const result = await (0, test_helpers_1.mockAgentExecution)(agent, `Task for ${agent}`);
                results.push(result);
            }
            expect(results.every((r) => r.success)).toBe(true);
            expect(results.map((r) => r.agent)).toEqual(agents);
        });
        it('should execute agents in parallel', async () => {
            const agents = ['frontend-developer', 'backend-developer', 'database-developer'];
            const results = await Promise.all(agents.map((agent) => (0, test_helpers_1.mockAgentExecution)(agent, `Parallel task for ${agent}`)));
            expect(results.every((r) => r.success)).toBe(true);
            expect(results.map((r) => r.agent)).toEqual(agents);
        });
    });
    describe('Agent Categories', () => {
        it('should have architecture agents', () => {
            const architectureAgents = [
                'system-architect',
                'api-designer',
                'database-designer',
                'security-architect',
                'cloud-architect',
                'ui-ux-designer',
            ];
            for (const agent of architectureAgents) {
                expect((0, test_helpers_1.loadAgentDefinition)(agent)).not.toBeNull();
            }
        });
        it('should have operations agents', () => {
            const opsAgents = [
                'devops-engineer',
                'cicd-manager',
                'monitoring-specialist',
                'incident-responder',
            ];
            for (const agent of opsAgents) {
                expect((0, test_helpers_1.loadAgentDefinition)(agent)).not.toBeNull();
            }
        });
        it('should have specialized agents', () => {
            const specializedAgents = ['bug-fixer', 'refactor-specialist', 'feature-builder'];
            for (const agent of specializedAgents) {
                expect((0, test_helpers_1.loadAgentDefinition)(agent)).not.toBeNull();
            }
        });
    });
    describe('Multi-Agent Modes', () => {
        it('should have competition mode agent', () => {
            const agent = (0, test_helpers_1.loadAgentDefinition)('multi-agent-competition');
            expect(agent).not.toBeNull();
        });
        it('should have debate mode agent', () => {
            const agent = (0, test_helpers_1.loadAgentDefinition)('multi-agent-debate');
            expect(agent).not.toBeNull();
        });
        it('should have ensemble mode agent', () => {
            const agent = (0, test_helpers_1.loadAgentDefinition)('multi-agent-ensemble');
            expect(agent).not.toBeNull();
        });
        it('should have reflection agent for quality gating', () => {
            const agent = (0, test_helpers_1.loadAgentDefinition)('reflection-agent');
            expect(agent).not.toBeNull();
        });
    });
});
