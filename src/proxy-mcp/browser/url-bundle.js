"use strict";
/**
 * URL Bundle Processing
 *
 * Normalizes and groups URLs collected from browser extensions or CDP.
 * Handles deduplication, UTM removal, trailing slash normalization, and domain grouping.
 *
 * Input: refId pointing to URL list in memory
 * Output: summary + outputRefId with normalized URLs
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getUrlBundleStats = exports.normalizeUrlBundle = exports.parseUrlList = exports.normalizeUrl = exports.DEFAULT_URL_BUNDLE_CONFIG = void 0;
const memory_1 = require("../tools/memory");
const observability_1 = require("../observability");
/** Default configuration */
exports.DEFAULT_URL_BUNDLE_CONFIG = {
    maxUrls: 200,
    removeUtm: true,
    normalizeTrailingSlash: true,
    groupByDomain: true,
    namespace: 'short-term',
};
/** UTM parameters to remove */
const UTM_PARAMS = [
    'utm_source',
    'utm_medium',
    'utm_campaign',
    'utm_term',
    'utm_content',
    'utm_id',
    'fbclid',
    'gclid',
    'ref',
    'source',
];
/**
 * Normalize a single URL
 */
function normalizeUrl(url, config) {
    try {
        const trimmed = url.trim();
        if (!trimmed)
            return null;
        // Parse URL
        const parsed = new URL(trimmed);
        // Remove UTM and tracking parameters
        if (config.removeUtm) {
            for (const param of UTM_PARAMS) {
                parsed.searchParams.delete(param);
            }
        }
        // Normalize trailing slash
        if (config.normalizeTrailingSlash) {
            // Remove trailing slash for paths (except root)
            if (parsed.pathname !== '/' && parsed.pathname.endsWith('/')) {
                parsed.pathname = parsed.pathname.slice(0, -1);
            }
        }
        // Build normalized URL
        const normalizedUrl = parsed.toString();
        return {
            url: normalizedUrl,
            domain: parsed.hostname,
            originalUrl: trimmed !== normalizedUrl ? trimmed : undefined,
        };
    }
    catch {
        // Invalid URL
        return null;
    }
}
exports.normalizeUrl = normalizeUrl;
/**
 * Parse URL list from various formats
 */
function parseUrlList(content) {
    const urls = [];
    // Try JSON parsing first
    try {
        const parsed = JSON.parse(content);
        // Handle array of strings
        if (Array.isArray(parsed)) {
            for (const item of parsed) {
                if (typeof item === 'string') {
                    urls.push(item);
                }
                else if (typeof item === 'object' && item !== null) {
                    // Handle { url: string } or { href: string } objects
                    if (item.url)
                        urls.push(item.url);
                    else if (item.href)
                        urls.push(item.href);
                }
            }
            return urls;
        }
        // Handle { urls: [...] } or { tabs: [...] } objects
        if (typeof parsed === 'object' && parsed !== null) {
            const urlArray = parsed.urls || parsed.tabs || parsed.links || [];
            for (const item of urlArray) {
                if (typeof item === 'string') {
                    urls.push(item);
                }
                else if (typeof item === 'object' && item !== null) {
                    if (item.url)
                        urls.push(item.url);
                    else if (item.href)
                        urls.push(item.href);
                }
            }
            return urls;
        }
    }
    catch {
        // Not JSON, try line-by-line parsing
    }
    // Parse as newline/comma separated text
    const lines = content.split(/[\n,]+/);
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed && (trimmed.startsWith('http://') || trimmed.startsWith('https://'))) {
            urls.push(trimmed);
        }
    }
    return urls;
}
exports.parseUrlList = parseUrlList;
/**
 * Normalize URL bundle from memory refId
 *
 * @param inputRefId - Reference ID to URL list in memory
 * @param config - Normalization configuration
 * @returns Normalized URL bundle result with outputRefId
 */
async function normalizeUrlBundle(inputRefId, config = {}) {
    const fullConfig = { ...exports.DEFAULT_URL_BUNDLE_CONFIG, ...config };
    try {
        // Fetch input from memory
        const memResult = await (0, memory_1.memoryGetContent)(inputRefId);
        const memData = memResult.data;
        if (!memResult.success || !memData?.content) {
            return {
                success: false,
                error: `Failed to find URL bundle with refId: ${inputRefId}`,
            };
        }
        // Get the content
        const content = memData.content;
        // Parse URL list
        const rawUrls = parseUrlList(content);
        const inputCount = rawUrls.length;
        if (inputCount === 0) {
            return {
                success: false,
                error: 'No valid URLs found in the input',
            };
        }
        // Normalize and deduplicate
        const normalizedMap = new Map();
        let invalidCount = 0;
        for (const rawUrl of rawUrls) {
            const normalized = normalizeUrl(rawUrl, fullConfig);
            if (normalized) {
                // Use normalized URL as key for deduplication
                if (!normalizedMap.has(normalized.url)) {
                    normalizedMap.set(normalized.url, normalized);
                }
            }
            else {
                invalidCount++;
            }
        }
        // Apply max URL limit
        let normalizedUrls = Array.from(normalizedMap.values());
        const preCapCount = normalizedUrls.length;
        if (normalizedUrls.length > fullConfig.maxUrls) {
            normalizedUrls = normalizedUrls.slice(0, fullConfig.maxUrls);
        }
        const duplicatesRemoved = inputCount - invalidCount - preCapCount;
        const cappedCount = preCapCount - normalizedUrls.length;
        // Group by domain
        const domainGroups = {};
        if (fullConfig.groupByDomain) {
            for (const normalized of normalizedUrls) {
                if (!domainGroups[normalized.domain]) {
                    domainGroups[normalized.domain] = {
                        domain: normalized.domain,
                        urls: [],
                        count: 0,
                    };
                }
                domainGroups[normalized.domain].urls.push(normalized);
                domainGroups[normalized.domain].count++;
            }
        }
        // Store normalized bundle in memory
        const outputData = {
            urls: normalizedUrls,
            domainGroups: fullConfig.groupByDomain ? Object.values(domainGroups) : undefined,
            metadata: {
                inputRefId,
                inputCount,
                outputCount: normalizedUrls.length,
                duplicatesRemoved,
                invalidUrls: invalidCount,
                cappedUrls: cappedCount,
                config: fullConfig,
                normalizedAt: new Date().toISOString(),
            },
        };
        const storeResult = await (0, memory_1.memoryAdd)(JSON.stringify(outputData), fullConfig.namespace, {
            tags: ['url-bundle', 'normalized', `count:${normalizedUrls.length}`],
            source: 'url-bundle.normalize',
        });
        if (!storeResult.success) {
            return {
                success: false,
                error: `Failed to store normalized URLs: ${storeResult.error}`,
            };
        }
        // Record observability event
        (0, observability_1.recordEvent)('url_bundle_normalize', 'url-bundle', 'ok', {
            metadata: {
                inputCount,
                outputCount: normalizedUrls.length,
                removedCount: duplicatesRemoved + invalidCount + cappedCount,
            },
        });
        // Build domain count summary
        const domainCounts = {};
        for (const group of Object.values(domainGroups)) {
            domainCounts[group.domain] = group.count;
        }
        // Generate summary
        const topDomains = Object.entries(domainCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([domain, count]) => `  - ${domain}: ${count}`)
            .join('\n');
        const summary = `Normalized ${normalizedUrls.length} URLs from ${inputCount} input URLs.
Removed: ${duplicatesRemoved} duplicates, ${invalidCount} invalid${cappedCount > 0 ? `, ${cappedCount} capped` : ''}
Top domains:
${topDomains}${Object.keys(domainCounts).length > 5 ? '\n  ...' : ''}`;
        return {
            success: true,
            outputRefId: storeResult.referenceId,
            summary,
            data: {
                inputCount,
                outputCount: normalizedUrls.length,
                removedCount: duplicatesRemoved + invalidCount + cappedCount,
                duplicatesRemoved,
                domainGroups: domainCounts,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `URL bundle normalization failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.normalizeUrlBundle = normalizeUrlBundle;
/**
 * Get URL bundle statistics without processing
 */
async function getUrlBundleStats(inputRefId, _namespace = 'short-term') {
    try {
        const memResult = await (0, memory_1.memoryGetContent)(inputRefId);
        const memData = memResult.data;
        if (!memResult.success || !memData?.content) {
            return {
                success: false,
                error: `Failed to find URL bundle with refId: ${inputRefId}`,
            };
        }
        const content = memData.content;
        const rawUrls = parseUrlList(content);
        // Count by domain
        const domainCounts = {};
        for (const url of rawUrls) {
            try {
                const domain = new URL(url.trim()).hostname;
                domainCounts[domain] = (domainCounts[domain] || 0) + 1;
            }
            catch {
                // Skip invalid URLs
            }
        }
        const topDomains = Object.entries(domainCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([domain, count]) => ({ domain, count }));
        return {
            success: true,
            stats: {
                totalUrls: rawUrls.length,
                uniqueDomains: Object.keys(domainCounts).length,
                topDomains,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `Failed to get stats: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.getUrlBundleStats = getUrlBundleStats;
