"use strict";
/**
 * Template renderer using Handlebars
 *
 * Renders template files with provided context data
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
exports.TemplateRenderer = void 0;
const fs = __importStar(require("fs"));
/**
 * Simple Handlebars-like template renderer
 * Supports basic variable interpolation and conditionals
 */
class TemplateRenderer {
    /**
     * Render a template file with context data
     *
     * @param templatePath - Path to template file
     * @param context - Context data for template
     * @returns Rendered content
     */
    render(templatePath, context) {
        const templateContent = fs.readFileSync(templatePath, 'utf8');
        return this.renderString(templateContent, context);
    }
    /**
     * Render a template string with context data
     *
     * @param template - Template string
     * @param context - Context data
     * @returns Rendered content
     */
    renderString(template, context) {
        let result = template;
        // Handle {{#each array}}...{{/each}} FIRST (before other replacements)
        result = result.replace(/\{\{#each\s+([^}]+)\}\}([\s\S]*?)\{\{\/each\}\}/g, (match, arrayName, content) => {
            const array = this.resolveValue(arrayName.trim(), context);
            if (!array || !Array.isArray(array)) {
                // Try to interpret as object
                if (typeof array === 'object') {
                    const entries = Object.entries(array);
                    // Return empty string for empty objects
                    if (entries.length === 0) {
                        return '';
                    }
                    return entries
                        .map(([key, value], index, arr) => {
                        const itemContext = {
                            ...context,
                            '@key': key,
                            '@value': value,
                            '@index': index,
                            '@first': index === 0,
                            '@last': index === arr.length - 1,
                            this: value
                        };
                        return this.renderString(content, itemContext);
                    })
                        .join('');
                }
                return '';
            }
            // Return empty string for empty arrays
            if (array.length === 0) {
                return '';
            }
            return array
                .map((item, index) => {
                const itemContext = {
                    ...context,
                    '@index': index,
                    '@first': index === 0,
                    '@last': index === array.length - 1,
                    this: item
                };
                return this.renderString(content, itemContext);
            })
                .join('');
        });
        // Handle {{#if condition}}...{{/if}} AFTER each
        result = result.replace(/\{\{#if\s+([^}]+)\}\}([\s\S]*?)\{\{\/if\}\}/g, (match, condition, content) => {
            const value = this.resolveValue(condition.trim(), context);
            return value ? this.renderString(content, context) : '';
        });
        // Handle {{#unless condition}}...{{/unless}}
        result = result.replace(/\{\{#unless\s+([^}]+)\}\}([\s\S]*?)\{\{\/unless\}\}/g, (match, condition, content) => {
            const value = this.resolveValue(condition.trim(), context);
            return !value ? this.renderString(content, context) : '';
        });
        // Replace simple variables {{variable}} LAST
        result = result.replace(/\{\{([^{}#/]+)\}\}/g, (match, key) => {
            const trimmedKey = key.trim();
            return this.resolveValue(trimmedKey, context) || '';
        });
        return result;
    }
    /**
     * Resolve nested property path (e.g., "user.name")
     */
    resolveValue(path, context) {
        const parts = path.split('.');
        let value = context;
        for (const part of parts) {
            if (value && typeof value === 'object' && part in value) {
                value = value[part];
            }
            else {
                return undefined;
            }
        }
        return value;
    }
}
exports.TemplateRenderer = TemplateRenderer;
