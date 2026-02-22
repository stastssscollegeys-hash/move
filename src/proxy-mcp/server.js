"use strict";
/**
 * Proxy MCP Server
 *
 * Single entry point for Claude Code. Bundles multiple internal MCPs
 * behind a minimal public interface to reduce context pressure.
 *
 * Public Tools (exposed to Claude):
 * - system.health: Check if proxy is alive
 * - skill.search: Find skills from .claude/skills
 * - skill.run: Execute a skill
 * - memory.add: Store large content, return reference ID
 * - memory.search: Retrieve content by ID or keyword
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.memoryStats = exports.memorySearch = exports.memoryAdd = exports.skillRun = exports.skillSearch = exports.systemHealth = exports.TOOLS = exports.server = void 0;
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const system_1 = require("./tools/system");
Object.defineProperty(exports, "systemHealth", { enumerable: true, get: function () { return system_1.systemHealth; } });
const skill_1 = require("./tools/skill");
Object.defineProperty(exports, "skillSearch", { enumerable: true, get: function () { return skill_1.skillSearch; } });
Object.defineProperty(exports, "skillRun", { enumerable: true, get: function () { return skill_1.skillRun; } });
const memory_1 = require("./tools/memory");
Object.defineProperty(exports, "memoryAdd", { enumerable: true, get: function () { return memory_1.memoryAdd; } });
Object.defineProperty(exports, "memorySearch", { enumerable: true, get: function () { return memory_1.memorySearch; } });
Object.defineProperty(exports, "memoryStats", { enumerable: true, get: function () { return memory_1.memoryStats; } });
const server = new index_js_1.Server({
    name: 'taisun-proxy-mcp',
    version: '0.1.0',
}, {
    capabilities: {
        tools: {},
    },
});
exports.server = server;
// Tool definitions (minimal surface area)
const TOOLS = [
    {
        name: 'system_health',
        description: 'Check if Proxy MCP is alive and get status',
        inputSchema: {
            type: 'object',
            properties: {},
            required: [],
        },
    },
    {
        name: 'skill_search',
        description: 'Search for skills in .claude/skills directory. Returns up to 10 matches.',
        inputSchema: {
            type: 'object',
            properties: {
                query: {
                    type: 'string',
                    description: 'Search query (optional, empty returns all)',
                },
            },
            required: [],
        },
    },
    {
        name: 'skill_run',
        description: 'Load and preview a skill by name. Full execution requires M2+ integration.',
        inputSchema: {
            type: 'object',
            properties: {
                name: {
                    type: 'string',
                    description: 'Skill name (directory name in .claude/skills)',
                },
                params: {
                    type: 'object',
                    description: 'Optional parameters for the skill',
                },
            },
            required: ['name'],
        },
    },
    {
        name: 'memory_add',
        description: 'Store large content and return a reference ID. Use this to avoid cluttering conversation. Either content or content_path must be provided (not both).',
        inputSchema: {
            type: 'object',
            properties: {
                content: {
                    type: 'string',
                    description: 'Content to store directly',
                },
                content_path: {
                    type: 'string',
                    description: 'Path to file to read and store (for large logs). Project-relative paths only.',
                },
                type: {
                    type: 'string',
                    enum: ['short-term', 'long-term'],
                    description: 'Memory type (default: short-term)',
                },
                metadata: {
                    type: 'object',
                    description: 'Optional metadata',
                },
            },
            required: [],
        },
    },
    {
        name: 'memory_search',
        description: 'Search memory by reference ID or keyword',
        inputSchema: {
            type: 'object',
            properties: {
                query: {
                    type: 'string',
                    description: 'Reference ID or search keyword',
                },
            },
            required: ['query'],
        },
    },
];
exports.TOOLS = TOOLS;
// List tools handler
server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
    return { tools: TOOLS };
});
// Call tool handler
server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    let result;
    switch (name) {
        case 'system_health':
            result = (0, system_1.systemHealth)();
            break;
        case 'skill_search':
            result = (0, skill_1.skillSearch)(args?.query || '');
            break;
        case 'skill_run':
            result = (0, skill_1.skillRun)(args?.name, args?.params);
            break;
        case 'memory_add':
            result = await (0, memory_1.memoryAdd)(args?.content, args?.type || 'short-term', {
                ...args?.metadata,
                contentPath: args?.content_path,
            });
            break;
        case 'memory_search':
            result = await (0, memory_1.memorySearch)(args?.query);
            break;
        default:
            result = {
                success: false,
                error: `Unknown tool: ${name}`,
            };
    }
    return {
        content: [
            {
                type: 'text',
                text: JSON.stringify(result, null, 2),
            },
        ],
        isError: !result.success,
    };
});
// Run server if executed directly
async function main() {
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
    console.error('Proxy MCP server running on stdio');
}
// Check if running as main module
const isMain = process.argv[1]?.endsWith('server.ts') || process.argv[1]?.endsWith('server.js');
if (isMain) {
    main().catch(console.error);
}
