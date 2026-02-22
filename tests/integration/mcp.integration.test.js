"use strict";
/**
 * MCP Integration Tests
 *
 * Tests for Model Context Protocol server integrations.
 */
Object.defineProperty(exports, "__esModule", { value: true });
const mock_mcp_server_1 = require("../mocks/mock-mcp-server");
describe('MCP Integration Tests', () => {
    let postgresClient;
    let notionClient;
    let githubClient;
    let slackClient;
    let dockerClient;
    beforeAll(() => {
        postgresClient = (0, mock_mcp_server_1.getMockPostgresClient)();
        notionClient = (0, mock_mcp_server_1.getMockNotionClient)();
        githubClient = (0, mock_mcp_server_1.getMockGitHubClient)();
        slackClient = (0, mock_mcp_server_1.getMockSlackClient)();
        dockerClient = (0, mock_mcp_server_1.getMockDockerClient)();
    });
    describe('PostgreSQL MCP', () => {
        it('should list tables', async () => {
            const response = await postgresClient.call('list_tables');
            expect(response.result).toBeDefined();
            expect(response.result.tables).toContain('users');
            expect(response.result.tables).toContain('orders');
            expect(response.result.tables).toContain('products');
        });
        it('should describe table structure', async () => {
            const response = await postgresClient.call('describe_table', { table: 'users' });
            expect(response.result).toBeDefined();
            const columns = response.result.columns;
            expect(columns.some((c) => c.name === 'id')).toBe(true);
            expect(columns.some((c) => c.name === 'name')).toBe(true);
            expect(columns.some((c) => c.name === 'email')).toBe(true);
        });
        it('should return error for non-existent table', async () => {
            const response = await postgresClient.call('describe_table', { table: 'non_existent' });
            expect(response.error).toBeDefined();
            expect(response.error?.code).toBe(404);
        });
        it('should execute SELECT query on users', async () => {
            const response = await postgresClient.call('query', {
                sql: 'SELECT * FROM users',
            });
            expect(response.result).toBeDefined();
            const rows = response.result.rows;
            expect(rows.length).toBeGreaterThan(0);
            expect(rows[0]).toHaveProperty('id');
            expect(rows[0]).toHaveProperty('name');
            expect(rows[0]).toHaveProperty('email');
        });
        it('should execute SELECT query on orders', async () => {
            const response = await postgresClient.call('query', {
                sql: 'SELECT * FROM orders',
            });
            expect(response.result).toBeDefined();
            const rows = response.result.rows;
            expect(rows.length).toBeGreaterThan(0);
            expect(rows[0]).toHaveProperty('user_id');
            expect(rows[0]).toHaveProperty('total');
            expect(rows[0]).toHaveProperty('status');
        });
        it('should execute COUNT query', async () => {
            const response = await postgresClient.call('query', {
                sql: 'SELECT COUNT(*) FROM users',
            });
            expect(response.result).toBeDefined();
            const rows = response.result.rows;
            expect(rows.length).toBeGreaterThan(0);
            expect(rows[0]).toHaveProperty('count');
        });
        it('should return empty rows for non-matching query', async () => {
            const response = await postgresClient.call('query', {
                sql: 'SELECT * FROM unknown_table',
            });
            expect(response.result).toBeDefined();
            const rows = response.result.rows;
            expect(rows.length).toBe(0);
        });
        it('should handle unknown methods', async () => {
            const response = await postgresClient.call('unknown_method');
            expect(response.error).toBeDefined();
            expect(response.error?.code).toBe(400);
        });
    });
    describe('Notion MCP', () => {
        it('should search pages', async () => {
            const response = await notionClient.call('search', { query: 'roadmap' });
            expect(response.result).toBeDefined();
            const pages = response.result.pages;
            expect(pages.some((p) => p.title.toLowerCase().includes('roadmap'))).toBe(true);
        });
        it('should search with case insensitive query', async () => {
            const response = await notionClient.call('search', { query: 'MEETING' });
            expect(response.result).toBeDefined();
            const pages = response.result.pages;
            expect(pages.some((p) => p.title.toLowerCase().includes('meeting'))).toBe(true);
        });
        it('should return empty results for non-matching search', async () => {
            const response = await notionClient.call('search', { query: 'xyz123nonexistent' });
            expect(response.result).toBeDefined();
            const pages = response.result.pages;
            expect(pages.length).toBe(0);
        });
        it('should get page by ID', async () => {
            const response = await notionClient.call('get_page', { page_id: 'page-1' });
            expect(response.result).toBeDefined();
            expect(response.result.title).toBe('Project Roadmap');
        });
        it('should return error for non-existent page', async () => {
            const response = await notionClient.call('get_page', { page_id: 'non-existent' });
            expect(response.error).toBeDefined();
            expect(response.error?.code).toBe(404);
        });
        it('should list databases', async () => {
            const response = await notionClient.call('list_databases');
            expect(response.result).toBeDefined();
            const databases = response.result.databases;
            expect(databases.length).toBeGreaterThan(0);
            expect(databases.some((d) => d.title === 'Tasks')).toBe(true);
        });
        it('should create new page', async () => {
            const response = await notionClient.call('create_page', {
                title: 'Test Page',
                content: 'Test content',
            });
            expect(response.result).toBeDefined();
            const page = response.result;
            expect(page.id).toBeDefined();
            expect(page.title).toBe('Test Page');
        });
        it('should handle unknown methods', async () => {
            const response = await notionClient.call('unknown_method');
            expect(response.error).toBeDefined();
            expect(response.error?.code).toBe(400);
        });
    });
    describe('MCP Error Handling', () => {
        it('should handle postgres connection errors gracefully', async () => {
            const response = await postgresClient.call('query', { sql: undefined });
            // Should return empty results, not crash
            expect(response.result || response.error).toBeDefined();
        });
        it('should handle notion API errors gracefully', async () => {
            const response = await notionClient.call('get_page', { page_id: undefined });
            // Should return error, not crash
            expect(response.error).toBeDefined();
        });
    });
    describe('MCP Integration Scenarios', () => {
        it('should query postgres and create notion page with results', async () => {
            // Step 1: Query PostgreSQL
            const queryResponse = await postgresClient.call('query', {
                sql: 'SELECT * FROM users',
            });
            expect(queryResponse.result).toBeDefined();
            const users = queryResponse.result.rows;
            // Step 2: Create Notion page with results
            const createResponse = await notionClient.call('create_page', {
                title: 'User Report',
                content: `Found ${users.length} users in the database`,
            });
            expect(createResponse.result).toBeDefined();
        });
        it('should search notion and query related postgres data', async () => {
            // Step 1: Search Notion for project info
            const searchResponse = await notionClient.call('search', { query: 'project' });
            expect(searchResponse.result).toBeDefined();
            // Step 2: Query related PostgreSQL data
            const queryResponse = await postgresClient.call('query', {
                sql: 'SELECT * FROM orders WHERE status = "completed"',
            });
            expect(queryResponse.result).toBeDefined();
        });
    });
    describe('GitHub MCP', () => {
        it('should list open issues', async () => {
            const response = await githubClient.call('list_issues', { state: 'open' });
            expect(response.result).toBeDefined();
            const issues = response.result.issues;
            expect(issues.length).toBeGreaterThan(0);
            expect(issues.every((i) => i.state === 'open')).toBe(true);
        });
        it('should list all issues', async () => {
            const response = await githubClient.call('list_issues', { state: 'all' });
            expect(response.result).toBeDefined();
            const issues = response.result.issues;
            expect(issues.length).toBeGreaterThan(0);
        });
        it('should get specific issue', async () => {
            const response = await githubClient.call('get_issue', { number: 1 });
            expect(response.result).toBeDefined();
            expect(response.result.number).toBe(1);
        });
        it('should return error for non-existent issue', async () => {
            const response = await githubClient.call('get_issue', { number: 999 });
            expect(response.error).toBeDefined();
            expect(response.error?.code).toBe(404);
        });
        it('should list pull requests', async () => {
            const response = await githubClient.call('list_pulls');
            expect(response.result).toBeDefined();
            const pulls = response.result.pulls;
            expect(pulls.length).toBeGreaterThan(0);
        });
        it('should create new issue', async () => {
            const response = await githubClient.call('create_issue', {
                title: 'Test Issue',
                labels: ['test'],
            });
            expect(response.result).toBeDefined();
            const issue = response.result;
            expect(issue.title).toBe('Test Issue');
            expect(issue.number).toBeGreaterThan(0);
        });
    });
    describe('Slack MCP', () => {
        it('should list channels', async () => {
            const response = await slackClient.call('list_channels');
            expect(response.result).toBeDefined();
            const channels = response.result.channels;
            expect(channels.length).toBeGreaterThan(0);
            expect(channels.some((c) => c.name === 'general')).toBe(true);
        });
        it('should get channel history', async () => {
            const response = await slackClient.call('get_channel_history', { channel: 'C001' });
            expect(response.result).toBeDefined();
            const messages = response.result.messages;
            expect(messages.length).toBeGreaterThan(0);
        });
        it('should post message', async () => {
            const response = await slackClient.call('post_message', {
                channel: 'C001',
                text: 'Hello from test!',
            });
            expect(response.result).toBeDefined();
            expect(response.result.ok).toBe(true);
        });
    });
    describe('Docker MCP', () => {
        it('should list running containers', async () => {
            const response = await dockerClient.call('list_containers');
            expect(response.result).toBeDefined();
            const containers = response.result.containers;
            expect(containers.length).toBeGreaterThan(0);
            expect(containers.every((c) => c.state === 'running')).toBe(true);
        });
        it('should list all containers including stopped', async () => {
            const response = await dockerClient.call('list_containers', { all: true });
            expect(response.result).toBeDefined();
            const containers = response.result.containers;
            expect(containers.length).toBeGreaterThan(0);
        });
        it('should get specific container', async () => {
            const response = await dockerClient.call('get_container', { id: 'web-app' });
            expect(response.result).toBeDefined();
            expect(response.result.name).toBe('web-app');
        });
        it('should return error for non-existent container', async () => {
            const response = await dockerClient.call('get_container', { id: 'non-existent' });
            expect(response.error).toBeDefined();
            expect(response.error?.code).toBe(404);
        });
        it('should list images', async () => {
            const response = await dockerClient.call('list_images');
            expect(response.result).toBeDefined();
            const images = response.result.images;
            expect(images.length).toBeGreaterThan(0);
        });
        it('should get container logs', async () => {
            const response = await dockerClient.call('container_logs', { id: 'web-app' });
            expect(response.result).toBeDefined();
            expect(response.result.logs).toContain('Mock container logs');
        });
    });
    describe('Cross-MCP Workflows', () => {
        it('should create GitHub issue and notify Slack', async () => {
            // Step 1: Create GitHub issue
            const issueResponse = await githubClient.call('create_issue', {
                title: 'New Feature Request',
                labels: ['enhancement'],
            });
            expect(issueResponse.result).toBeDefined();
            const issue = issueResponse.result;
            // Step 2: Notify Slack
            const slackResponse = await slackClient.call('post_message', {
                channel: 'C002',
                text: `New issue created: #${issue.number} - ${issue.title}`,
            });
            expect(slackResponse.result).toBeDefined();
        });
        it('should check Docker containers and report to Notion', async () => {
            // Step 1: Get Docker container status
            const dockerResponse = await dockerClient.call('list_containers');
            expect(dockerResponse.result).toBeDefined();
            const containers = dockerResponse.result.containers;
            // Step 2: Create Notion page with status
            const notionResponse = await notionClient.call('create_page', {
                title: 'Infrastructure Status',
                content: `Running containers: ${containers.length}`,
            });
            expect(notionResponse.result).toBeDefined();
        });
    });
});
