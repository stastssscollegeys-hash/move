"use strict";
/**
 * Memory Store - Base interface and factory
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.JsonlStore = exports.InMemoryStore = exports.createStore = void 0;
const inmemory_1 = require("./stores/inmemory");
const jsonl_1 = require("./stores/jsonl");
/**
 * Create a memory store based on configuration
 */
function createStore(config) {
    switch (config.storage.defaultBackend) {
        case 'jsonl':
            return new jsonl_1.JsonlStore(config.storage.directory);
        case 'inmemory':
        default:
            return new inmemory_1.InMemoryStore();
    }
}
exports.createStore = createStore;
/**
 * Re-export store implementations for direct use
 */
var inmemory_2 = require("./stores/inmemory");
Object.defineProperty(exports, "InMemoryStore", { enumerable: true, get: function () { return inmemory_2.InMemoryStore; } });
var jsonl_2 = require("./stores/jsonl");
Object.defineProperty(exports, "JsonlStore", { enumerable: true, get: function () { return jsonl_2.JsonlStore; } });
