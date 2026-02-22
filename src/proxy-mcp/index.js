"use strict";
/**
 * Proxy MCP - Single entry point for Claude Code
 *
 * Exposes minimal public interface to reduce context pressure.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.memoryClearAll = exports.memoryClearShortTerm = exports.memoryStats = exports.memorySearch = exports.memoryAdd = exports.skillRun = exports.skillSearch = exports.systemHealth = exports.TOOLS = exports.server = void 0;
var server_1 = require("./server");
Object.defineProperty(exports, "server", { enumerable: true, get: function () { return server_1.server; } });
Object.defineProperty(exports, "TOOLS", { enumerable: true, get: function () { return server_1.TOOLS; } });
var system_1 = require("./tools/system");
Object.defineProperty(exports, "systemHealth", { enumerable: true, get: function () { return system_1.systemHealth; } });
var skill_1 = require("./tools/skill");
Object.defineProperty(exports, "skillSearch", { enumerable: true, get: function () { return skill_1.skillSearch; } });
Object.defineProperty(exports, "skillRun", { enumerable: true, get: function () { return skill_1.skillRun; } });
var memory_1 = require("./tools/memory");
Object.defineProperty(exports, "memoryAdd", { enumerable: true, get: function () { return memory_1.memoryAdd; } });
Object.defineProperty(exports, "memorySearch", { enumerable: true, get: function () { return memory_1.memorySearch; } });
Object.defineProperty(exports, "memoryStats", { enumerable: true, get: function () { return memory_1.memoryStats; } });
Object.defineProperty(exports, "memoryClearShortTerm", { enumerable: true, get: function () { return memory_1.memoryClearShortTerm; } });
Object.defineProperty(exports, "memoryClearAll", { enumerable: true, get: function () { return memory_1.memoryClearAll; } });
