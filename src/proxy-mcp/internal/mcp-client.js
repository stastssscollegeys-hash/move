"use strict";
/**
 * Internal MCP Client - Communicates with internal MCP servers via stdio
 *
 * M4: Minimal implementation for chrome/puppeteer integration
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.stopAllClients = exports.getClient = exports.McpClient = void 0;
const child_process_1 = require("child_process");
const registry_1 = require("./registry");
const safe_json_1 = require("../../utils/safe-json");
/**
 * MCP Client for stdio transport
 */
class McpClient {
    constructor(definition, options = {}) {
        this.process = null;
        this.requestId = 0;
        this.pendingRequests = new Map();
        this.buffer = '';
        this.definition = definition;
        this.options = {
            timeout: options.timeout || 30000, // 30s default
        };
    }
    /**
     * Get client for named MCP
     */
    static forMcp(name, options) {
        const definition = (0, registry_1.getMcpByName)(name);
        if (!definition) {
            return null;
        }
        return new McpClient(definition, options);
    }
    /**
     * Check if MCP is available (enabled)
     */
    isAvailable() {
        return this.definition.enabled;
    }
    /**
     * Start the MCP server process
     */
    async start() {
        if (this.process) {
            return; // Already started
        }
        if (!this.definition.enabled) {
            throw new Error(`MCP ${this.definition.name} is not enabled`);
        }
        if (!this.definition.command) {
            throw new Error(`MCP ${this.definition.name} has no command configured`);
        }
        return new Promise((resolve, reject) => {
            try {
                const proc = (0, child_process_1.spawn)(this.definition.command, this.definition.args || [], {
                    stdio: ['pipe', 'pipe', 'pipe'],
                    env: { ...process.env },
                });
                this.process = proc;
                proc.stdout?.on('data', (data) => {
                    this.handleData(data.toString());
                });
                proc.stderr?.on('data', (data) => {
                    console.error(`[${this.definition.name}] stderr:`, data.toString());
                });
                proc.on('error', (err) => {
                    this.cleanup();
                    reject(new Error(`Failed to start MCP ${this.definition.name}: ${err.message}`));
                });
                proc.on('close', (code) => {
                    this.cleanup();
                    if (code !== 0) {
                        console.error(`[${this.definition.name}] exited with code ${code}`);
                    }
                });
                // Wait briefly for process to start
                setTimeout(resolve, 500);
            }
            catch (err) {
                reject(err);
            }
        });
    }
    /**
     * Stop the MCP server process
     */
    stop() {
        this.cleanup();
    }
    /**
     * Call a tool on the MCP server
     */
    async callTool(name, args) {
        if (!this.process) {
            throw new Error(`MCP ${this.definition.name} not started. Call start() first.`);
        }
        const id = ++this.requestId;
        const request = {
            jsonrpc: '2.0',
            id,
            method: 'tools/call',
            params: {
                name,
                arguments: args || {},
            },
        };
        return this.sendRequest(request);
    }
    /**
     * List available tools
     */
    async listTools() {
        if (!this.process) {
            throw new Error(`MCP ${this.definition.name} not started. Call start() first.`);
        }
        const id = ++this.requestId;
        const request = {
            jsonrpc: '2.0',
            id,
            method: 'tools/list',
        };
        return this.sendRequest(request);
    }
    /**
     * Send JSON-RPC request and wait for response
     */
    sendRequest(request) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                this.pendingRequests.delete(request.id);
                reject(new Error(`Request ${request.id} timed out after ${this.options.timeout}ms`));
            }, this.options.timeout);
            this.pendingRequests.set(request.id, { resolve, reject, timeout });
            const message = JSON.stringify(request) + '\n';
            this.process?.stdin?.write(message);
        });
    }
    /**
     * Handle incoming data from the MCP server
     */
    handleData(data) {
        this.buffer += data;
        // Process complete lines
        let newlineIndex;
        while ((newlineIndex = this.buffer.indexOf('\n')) !== -1) {
            const line = this.buffer.slice(0, newlineIndex).trim();
            this.buffer = this.buffer.slice(newlineIndex + 1);
            if (line) {
                // Security: Use safe JSON parser to prevent prototype pollution
                const response = (0, safe_json_1.safeJSONParse)(line);
                if (response && response.jsonrpc === '2.0' && typeof response.id === 'number') {
                    this.handleResponse(response);
                }
                else if (line.startsWith('{')) {
                    // Likely JSON but failed validation
                    console.debug(`[${this.definition.name}] Invalid JSON-RPC response:`, line.substring(0, 100));
                }
                else {
                    // Not JSON, might be a notification or log
                    console.debug(`[${this.definition.name}] Non-JSON output:`, line);
                }
            }
        }
    }
    /**
     * Handle JSON-RPC response
     */
    handleResponse(response) {
        const pending = this.pendingRequests.get(response.id);
        if (!pending) {
            console.warn(`Received response for unknown request ${response.id}`);
            return;
        }
        clearTimeout(pending.timeout);
        this.pendingRequests.delete(response.id);
        if (response.error) {
            pending.reject(new Error(response.error.message));
        }
        else {
            pending.resolve(response.result);
        }
    }
    /**
     * Cleanup resources
     */
    cleanup() {
        // Clear pending requests
        for (const [, { reject, timeout }] of this.pendingRequests) {
            clearTimeout(timeout);
            reject(new Error('MCP client shutdown'));
        }
        this.pendingRequests.clear();
        // Kill process
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
    }
}
exports.McpClient = McpClient;
/**
 * Singleton clients for each MCP
 */
const clients = new Map();
/**
 * Get or create client for named MCP
 */
function getClient(name) {
    if (clients.has(name)) {
        return clients.get(name);
    }
    const client = McpClient.forMcp(name);
    if (client) {
        clients.set(name, client);
    }
    return client;
}
exports.getClient = getClient;
/**
 * Stop all clients
 */
function stopAllClients() {
    for (const client of clients.values()) {
        client.stop();
    }
    clients.clear();
}
exports.stopAllClients = stopAllClients;
