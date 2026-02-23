"use strict";
/**
 * Step 3: Framework Selection
 *
 * Allows user to select a framework
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
exports.groupFrameworksByType = exports.getFrameworkById = exports.loadFrameworks = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/**
 * Load available frameworks
 */
function loadFrameworks() {
    const configPath = path.join(__dirname, '../../config/frameworks.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    return config.frameworks;
}
exports.loadFrameworks = loadFrameworks;
/**
 * Get framework by ID
 */
function getFrameworkById(id) {
    const frameworks = loadFrameworks();
    return frameworks.find(f => f.id === id);
}
exports.getFrameworkById = getFrameworkById;
/**
 * Group frameworks by type
 */
function groupFrameworksByType() {
    const frameworks = loadFrameworks();
    const grouped = new Map();
    for (const framework of frameworks) {
        if (!grouped.has(framework.type)) {
            grouped.set(framework.type, []);
        }
        grouped.get(framework.type).push(framework);
    }
    return grouped;
}
exports.groupFrameworksByType = groupFrameworksByType;
