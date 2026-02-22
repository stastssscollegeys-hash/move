"use strict";
/**
 * Normalize - Utility functions for normalizing MCP descriptions
 *
 * Used to create compact, searchable representations of MCPs
 * for semantic routing without exposing full tool definitions to Claude.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.formatMinimalMcpList = exports.formatMinimalMcp = exports.createMcpIndex = exports.createIndexEntry = exports.extractKeywords = exports.normalizeText = void 0;
/**
 * Normalize text for indexing
 */
function normalizeText(text) {
    return text
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}
exports.normalizeText = normalizeText;
/**
 * Extract keywords from text
 */
function extractKeywords(text, maxKeywords = 10) {
    const normalized = normalizeText(text);
    const words = normalized.split(' ').filter((w) => w.length > 2);
    // Simple stop words
    const stopWords = new Set([
        'the',
        'and',
        'for',
        'are',
        'but',
        'not',
        'you',
        'all',
        'can',
        'had',
        'her',
        'was',
        'one',
        'our',
        'out',
        'with',
        'this',
        'that',
        'from',
        'they',
        'have',
        'been',
    ]);
    const keywords = words.filter((w) => !stopWords.has(w));
    // Count frequency
    const freq = {};
    for (const word of keywords) {
        freq[word] = (freq[word] || 0) + 1;
    }
    // Sort by frequency and return top N
    return Object.entries(freq)
        .sort((a, b) => b[1] - a[1])
        .slice(0, maxKeywords)
        .map(([word]) => word);
}
exports.extractKeywords = extractKeywords;
/**
 * Create index entry for an MCP
 */
function createIndexEntry(mcp) {
    const keywords = extractKeywords(mcp.shortDescription);
    return {
        name: mcp.name,
        keywords,
        tags: mcp.tags.map((t) => t.toLowerCase()),
        shortDescription: mcp.shortDescription.slice(0, 100),
    };
}
exports.createIndexEntry = createIndexEntry;
/**
 * Create index for all MCPs
 */
function createMcpIndex(mcps) {
    return mcps.map(createIndexEntry);
}
exports.createMcpIndex = createMcpIndex;
/**
 * Format MCP for minimal context exposure
 */
function formatMinimalMcp(mcp) {
    return `${mcp.name}: ${mcp.shortDescription} [${mcp.tags.join(', ')}]`;
}
exports.formatMinimalMcp = formatMinimalMcp;
/**
 * Format multiple MCPs for minimal context exposure
 */
function formatMinimalMcpList(mcps) {
    return mcps.map(formatMinimalMcp).join('\n');
}
exports.formatMinimalMcpList = formatMinimalMcpList;
