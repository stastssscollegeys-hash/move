"use strict";
/**
 * Web Skills - Browser automation skills for M4/P7
 *
 * Skills:
 * - web.read_url: Read URL and summarize (full content to refId)
 * - web.extract_links: Extract page links (large lists to refId)
 * - web.capture_dom_map: Capture DOM structure (map to refId)
 * - web.list_tabs_urls: List all open tab URLs via CDP
 * - url.normalize_bundle: Normalize URL bundle (refId → refId)
 *
 * Backends:
 * - default: Uses chrome MCP (puppeteer)
 * - cdp: Uses Playwright CDP to connect to existing Chrome (P7)
 *
 * All output follows minimal output principle: summary + refId
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.webSkillizeFromTabs = exports.batchSkillizePreview = exports.batchSkillizeUrlBundle = exports.getUrlBundleStats = exports.normalizeUrlBundle = exports.listTabsUrls = exports.captureDomMap = exports.extractLinks = exports.readUrl = void 0;
const captcha_1 = require("./captcha");
const mcp_client_1 = require("../internal/mcp-client");
const memory_1 = require("../tools/memory");
const cdp_1 = require("./cdp");
const url_bundle_1 = require("./url-bundle");
const url_bundle_skillize_1 = require("./url-bundle-skillize");
const pipeline_tabs_skillize_1 = require("./pipeline-tabs-skillize");
/**
 * web.read_url - Read URL and summarize
 *
 * Opens URL, extracts text content, checks for CAPTCHA,
 * stores full content in memory, returns summary + refId
 *
 * @param url - URL to read
 * @param options.backend - 'default' (puppeteer) or 'cdp' (Playwright CDP)
 * @param options.namespace - Memory namespace for storage
 * @param options.maxLength - Max content length
 */
async function readUrl(url, options) {
    // Check for blocked patterns (login, auth, etc.)
    const blocked = (0, captcha_1.checkBlockedPatterns)(url);
    if (blocked)
        return blocked;
    const backend = options?.backend || 'default';
    const namespace = options?.namespace || 'short-term';
    const maxLength = options?.maxLength || 50000;
    // Use CDP backend if specified
    if (backend === 'cdp') {
        return readUrlViaCDPWithMemory(url, namespace, maxLength);
    }
    try {
        // Try to use chrome MCP (default backend)
        const client = (0, mcp_client_1.getClient)('chrome');
        if (!client || !client.isAvailable()) {
            return {
                success: false,
                error: 'Chrome MCP not available. Ensure it is enabled and mcp-server-puppeteer is installed.',
                data: {
                    help: [
                        '1. Check config/proxy-mcp/internal-mcps.json - chrome.enabled should be true',
                        '2. Install puppeteer MCP: npx -y @anthropic/mcp-server-puppeteer',
                        '3. Ensure Chrome/Chromium is available on the system',
                    ],
                },
            };
        }
        // Start client if needed
        await client.start();
        // Navigate to URL and get content
        let pageContent;
        let pageTitle;
        try {
            // Navigate
            await client.callTool('puppeteer_navigate', { url });
            // Get page content
            const evalResult = (await client.callTool('puppeteer_evaluate', {
                script: `
          JSON.stringify({
            title: document.title,
            text: document.body.innerText.substring(0, ${maxLength}),
            html: document.documentElement.outerHTML.substring(0, ${maxLength})
          })
        `,
            }));
            const parsed = JSON.parse(evalResult.result || '{}');
            pageTitle = parsed.title || 'Untitled';
            pageContent = parsed.text || '';
        }
        catch (err) {
            // Fallback: try simple fetch if MCP call fails
            return {
                success: false,
                error: `Failed to load page: ${err instanceof Error ? err.message : String(err)}`,
                data: {
                    url,
                    suggestion: 'Try accessing the URL directly or check if the site is accessible.',
                },
            };
        }
        // Check for CAPTCHA
        const captchaCheck = (0, captcha_1.guardCaptcha)(pageContent, url);
        if (captchaCheck)
            return captchaCheck;
        // Store full content in memory
        const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
            url,
            title: pageTitle,
            content: pageContent,
            fetchedAt: new Date().toISOString(),
        }), namespace, {
            tags: ['web', 'page-content', new URL(url).hostname],
            source: 'web.read_url',
        });
        if (!memResult.success) {
            return {
                success: false,
                error: `Failed to store content: ${memResult.error}`,
            };
        }
        // Generate summary
        const summary = generateSummary(pageTitle, pageContent, url);
        return {
            success: true,
            action: 'allow',
            refId: memResult.referenceId,
            summary,
            data: {
                url,
                title: pageTitle,
                contentLength: pageContent.length,
                message: `Page loaded. Use memory_search("${memResult.referenceId}") for full content.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `web.read_url failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.readUrl = readUrl;
/**
 * web.extract_links - Extract page links
 *
 * Extracts all links from page, stores full list in memory,
 * returns summary with link count + refId
 *
 * @param url - URL to extract links from
 * @param options.backend - 'default' (puppeteer) or 'cdp' (Playwright CDP)
 * @param options.namespace - Memory namespace for storage
 * @param options.filter - 'internal', 'external', or 'all'
 */
async function extractLinks(url, options) {
    const blocked = (0, captcha_1.checkBlockedPatterns)(url);
    if (blocked)
        return blocked;
    const backend = options?.backend || 'default';
    const namespace = options?.namespace || 'short-term';
    const filter = options?.filter || 'all';
    // Use CDP backend if specified
    if (backend === 'cdp') {
        return extractLinksViaCDPWithMemory(url, namespace, filter);
    }
    try {
        const client = (0, mcp_client_1.getClient)('chrome');
        if (!client || !client.isAvailable()) {
            return {
                success: false,
                error: 'Chrome MCP not available.',
                data: {
                    help: ['Enable chrome in config/proxy-mcp/internal-mcps.json'],
                },
            };
        }
        await client.start();
        // Navigate and extract links
        let links;
        try {
            await client.callTool('puppeteer_navigate', { url });
            const evalResult = (await client.callTool('puppeteer_evaluate', {
                script: `
          JSON.stringify(
            Array.from(document.querySelectorAll('a[href]')).map(a => ({
              href: a.href,
              text: a.innerText.trim().substring(0, 200),
              title: a.title || undefined
            })).filter(l => l.href && l.href.startsWith('http'))
          )
        `,
            }));
            links = JSON.parse(evalResult.result || '[]');
        }
        catch (err) {
            return {
                success: false,
                error: `Failed to extract links: ${err instanceof Error ? err.message : String(err)}`,
            };
        }
        // Check for CAPTCHA in link texts
        const allText = links.map((l) => l.text).join(' ');
        const captchaCheck = (0, captcha_1.guardCaptcha)(allText, url);
        if (captchaCheck)
            return captchaCheck;
        // Filter links
        const baseHost = new URL(url).hostname;
        let filteredLinks = links;
        if (filter === 'internal') {
            filteredLinks = links.filter((l) => {
                try {
                    return new URL(l.href).hostname === baseHost;
                }
                catch {
                    return false;
                }
            });
        }
        else if (filter === 'external') {
            filteredLinks = links.filter((l) => {
                try {
                    return new URL(l.href).hostname !== baseHost;
                }
                catch {
                    return false;
                }
            });
        }
        // Store full link list in memory
        const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
            url,
            filter,
            links: filteredLinks,
            extractedAt: new Date().toISOString(),
        }), namespace, {
            tags: ['web', 'links', baseHost],
            source: 'web.extract_links',
        });
        if (!memResult.success) {
            return {
                success: false,
                error: `Failed to store links: ${memResult.error}`,
            };
        }
        // Summary with top 5 links
        const topLinks = filteredLinks.slice(0, 5).map((l) => `- ${l.text || l.href}`);
        const summary = `Extracted ${filteredLinks.length} ${filter} links from ${baseHost}.\nTop links:\n${topLinks.join('\n')}${filteredLinks.length > 5 ? '\n...' : ''}`;
        return {
            success: true,
            action: 'allow',
            refId: memResult.referenceId,
            summary,
            data: {
                url,
                linkCount: filteredLinks.length,
                filter,
                message: `Use memory_search("${memResult.referenceId}") for full link list.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `web.extract_links failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.extractLinks = extractLinks;
/**
 * web.capture_dom_map - Capture DOM structure
 *
 * Analyzes page DOM structure, identifies major components,
 * stores full map in memory, returns summary + refId
 *
 * @param url - URL to capture DOM from
 * @param options.backend - 'default' (puppeteer) or 'cdp' (Playwright CDP)
 * @param options.namespace - Memory namespace for storage
 */
async function captureDomMap(url, options) {
    const blocked = (0, captcha_1.checkBlockedPatterns)(url);
    if (blocked)
        return blocked;
    const backend = options?.backend || 'default';
    const namespace = options?.namespace || 'short-term';
    // Use CDP backend if specified
    if (backend === 'cdp') {
        return captureDomMapViaCDPWithMemory(url, namespace);
    }
    try {
        const client = (0, mcp_client_1.getClient)('chrome');
        if (!client || !client.isAvailable()) {
            return {
                success: false,
                error: 'Chrome MCP not available.',
            };
        }
        await client.start();
        // Navigate and analyze DOM
        let domMap;
        try {
            await client.callTool('puppeteer_navigate', { url });
            const evalResult = (await client.callTool('puppeteer_evaluate', {
                script: `
          (function() {
            const components = [];
            const selectors = [
              { selector: 'header', type: 'header' },
              { selector: 'nav', type: 'nav' },
              { selector: 'main', type: 'main' },
              { selector: 'article', type: 'article' },
              { selector: 'section', type: 'section' },
              { selector: 'form', type: 'form' },
              { selector: 'ul, ol', type: 'list' },
              { selector: '[class*="card"], [class*="Card"]', type: 'card' },
              { selector: 'footer', type: 'footer' },
            ];

            for (const { selector, type } of selectors) {
              const elements = document.querySelectorAll(selector);
              elements.forEach((el, i) => {
                components.push({
                  type,
                  selector: selector + (elements.length > 1 ? ':nth-of-type(' + (i+1) + ')' : ''),
                  text: el.innerText.substring(0, 100),
                  children: el.children.length
                });
              });
            }

            return JSON.stringify({
              url: window.location.href,
              title: document.title,
              components: components.slice(0, 50)
            });
          })()
        `,
            }));
            domMap = JSON.parse(evalResult.result || '{}');
        }
        catch (err) {
            return {
                success: false,
                error: `Failed to capture DOM: ${err instanceof Error ? err.message : String(err)}`,
            };
        }
        // Check for CAPTCHA in component texts
        const allText = domMap.components.map((c) => c.text || '').join(' ');
        const captchaCheck = (0, captcha_1.guardCaptcha)(allText, url);
        if (captchaCheck)
            return captchaCheck;
        // Store DOM map in memory
        const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
            ...domMap,
            capturedAt: new Date().toISOString(),
        }), namespace, {
            tags: ['web', 'dom-map', new URL(url).hostname],
            source: 'web.capture_dom_map',
        });
        if (!memResult.success) {
            return {
                success: false,
                error: `Failed to store DOM map: ${memResult.error}`,
            };
        }
        // Summary
        const typeCounts = domMap.components.reduce((acc, c) => {
            acc[c.type] = (acc[c.type] || 0) + 1;
            return acc;
        }, {});
        const summary = `DOM map for ${domMap.title || url}:\n${Object.entries(typeCounts)
            .map(([type, count]) => `- ${type}: ${count}`)
            .join('\n')}`;
        return {
            success: true,
            action: 'allow',
            refId: memResult.referenceId,
            summary,
            data: {
                url,
                title: domMap.title,
                componentsCount: domMap.components.length,
                typeCounts,
                message: `Use memory_search("${memResult.referenceId}") for full DOM map.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `web.capture_dom_map failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.captureDomMap = captureDomMap;
/**
 * Generate summary from page content
 */
function generateSummary(title, content, url) {
    const hostname = new URL(url).hostname;
    const preview = content.slice(0, 300).replace(/\s+/g, ' ').trim();
    return `${title} (${hostname})\n\n${preview}${content.length > 300 ? '...' : ''}`;
}
// ============================================
// CDP Backend Helper Functions
// ============================================
/**
 * Read URL via CDP with memory storage
 */
async function readUrlViaCDPWithMemory(url, namespace, maxLength) {
    const result = await (0, cdp_1.readUrlViaCDP)(url);
    if (!result.success) {
        if (result.requireHuman) {
            return {
                success: false,
                action: 'require_human',
                error: result.error,
                data: {
                    reason: result.humanReason,
                    instruction: 'Please resolve CAPTCHA/login in Chrome, then retry.',
                },
            };
        }
        return {
            success: false,
            error: result.error,
        };
    }
    const pageData = result.data;
    const content = pageData.content.substring(0, maxLength);
    // Store full content in memory
    const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
        url: pageData.url,
        title: pageData.title,
        content,
        fetchedAt: new Date().toISOString(),
        backend: 'cdp',
    }), namespace, {
        tags: ['web', 'page-content', new URL(url).hostname, 'cdp'],
        source: 'web.read_url',
    });
    if (!memResult.success) {
        return {
            success: false,
            error: `Failed to store content: ${memResult.error}`,
        };
    }
    const summary = generateSummary(pageData.title, content, pageData.url);
    return {
        success: true,
        action: 'allow',
        refId: memResult.referenceId,
        summary,
        data: {
            url: pageData.url,
            title: pageData.title,
            contentLength: content.length,
            backend: 'cdp',
            message: `Page loaded via CDP. Use memory_search("${memResult.referenceId}") for full content.`,
        },
    };
}
/**
 * Extract links via CDP with memory storage
 */
async function extractLinksViaCDPWithMemory(url, namespace, filter) {
    const result = await (0, cdp_1.extractLinksViaCDP)(url);
    if (!result.success) {
        if (result.requireHuman) {
            return {
                success: false,
                action: 'require_human',
                error: result.error,
                data: {
                    reason: result.humanReason,
                    instruction: 'Please resolve CAPTCHA/login in Chrome, then retry.',
                },
            };
        }
        return {
            success: false,
            error: result.error,
        };
    }
    const linkData = result.data;
    // Filter links
    const baseHost = new URL(url).hostname;
    let filteredLinks = linkData.links;
    if (filter === 'internal') {
        filteredLinks = linkData.links.filter((l) => {
            try {
                return new URL(l.href).hostname === baseHost;
            }
            catch {
                return false;
            }
        });
    }
    else if (filter === 'external') {
        filteredLinks = linkData.links.filter((l) => {
            try {
                return new URL(l.href).hostname !== baseHost;
            }
            catch {
                return false;
            }
        });
    }
    // Store full link list in memory
    const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
        url: linkData.url,
        filter,
        links: filteredLinks,
        extractedAt: new Date().toISOString(),
        backend: 'cdp',
    }), namespace, {
        tags: ['web', 'links', baseHost, 'cdp'],
        source: 'web.extract_links',
    });
    if (!memResult.success) {
        return {
            success: false,
            error: `Failed to store links: ${memResult.error}`,
        };
    }
    // Summary with top 5 links
    const topLinks = filteredLinks.slice(0, 5).map((l) => `- ${l.text || l.href}`);
    const summary = `Extracted ${filteredLinks.length} ${filter} links from ${baseHost} (CDP).\nTop links:\n${topLinks.join('\n')}${filteredLinks.length > 5 ? '\n...' : ''}`;
    return {
        success: true,
        action: 'allow',
        refId: memResult.referenceId,
        summary,
        data: {
            url: linkData.url,
            linkCount: filteredLinks.length,
            filter,
            backend: 'cdp',
            message: `Use memory_search("${memResult.referenceId}") for full link list.`,
        },
    };
}
/**
 * Capture DOM map via CDP with memory storage
 */
async function captureDomMapViaCDPWithMemory(url, namespace) {
    const result = await (0, cdp_1.captureDOMMapViaCDP)(url);
    if (!result.success) {
        if (result.requireHuman) {
            return {
                success: false,
                action: 'require_human',
                error: result.error,
                data: {
                    reason: result.humanReason,
                    instruction: 'Please resolve CAPTCHA/login in Chrome, then retry.',
                },
            };
        }
        return {
            success: false,
            error: result.error,
        };
    }
    const domData = result.data;
    // Store DOM map in memory
    const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
        url: domData.url,
        title: domData.title,
        elements: domData.elements,
        totalElements: domData.totalElements,
        capturedAt: new Date().toISOString(),
        backend: 'cdp',
    }), namespace, {
        tags: ['web', 'dom-map', new URL(url).hostname, 'cdp'],
        source: 'web.capture_dom_map',
    });
    if (!memResult.success) {
        return {
            success: false,
            error: `Failed to store DOM map: ${memResult.error}`,
        };
    }
    // Build summary from elements
    const tagCounts = {};
    const countTags = (elements) => {
        for (const el of elements) {
            tagCounts[el.tag] = (tagCounts[el.tag] || 0) + 1;
            if (el.children && Array.isArray(el.children)) {
                countTags(el.children);
            }
        }
    };
    countTags(domData.elements);
    const summary = `DOM map for ${domData.title || url} (CDP):\n${Object.entries(tagCounts)
        .slice(0, 10)
        .map(([tag, count]) => `- ${tag}: ${count}`)
        .join('\n')}${Object.keys(tagCounts).length > 10 ? '\n...' : ''}`;
    return {
        success: true,
        action: 'allow',
        refId: memResult.referenceId,
        summary,
        data: {
            url: domData.url,
            title: domData.title,
            totalElements: domData.totalElements,
            backend: 'cdp',
            message: `Use memory_search("${memResult.referenceId}") for full DOM map.`,
        },
    };
}
/**
 * web.list_tabs_urls - List all open tab URLs via CDP
 *
 * Lists all open tabs in the connected Chrome browser.
 * Stores full list in memory, returns summary + refId.
 * CDP-only skill (requires Chrome running with --remote-debugging-port).
 *
 * @param options.namespace - Memory namespace for storage
 */
async function listTabsUrls(options) {
    const namespace = options?.namespace || 'short-term';
    try {
        const result = await (0, cdp_1.listTabsViaCDP)();
        if (!result.success) {
            return {
                success: false,
                error: result.error,
                data: {
                    help: [
                        'Ensure Chrome is running with CDP enabled:',
                        'npm run chrome:debug:start',
                        'or: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222',
                    ],
                },
            };
        }
        const tabsData = result.data;
        // Store full tab list in memory
        const memResult = await (0, memory_1.memoryAdd)(JSON.stringify({
            tabs: tabsData.tabs,
            totalTabs: tabsData.totalTabs,
            listedAt: new Date().toISOString(),
            backend: 'cdp',
        }), namespace, {
            tags: ['web', 'tabs', 'cdp'],
            source: 'web.list_tabs_urls',
        });
        if (!memResult.success) {
            return {
                success: false,
                error: `Failed to store tabs: ${memResult.error}`,
            };
        }
        // Summary with top tabs
        const topTabs = tabsData.tabsPreview
            .slice(0, 5)
            .map((t) => `- [${t.index}] ${t.title || t.url}`);
        const summary = `Found ${tabsData.totalTabs} open tabs:\n${topTabs.join('\n')}${tabsData.totalTabs > 5 ? '\n...' : ''}`;
        return {
            success: true,
            action: 'allow',
            refId: memResult.referenceId,
            summary,
            data: {
                totalTabs: tabsData.totalTabs,
                tabs: tabsData.tabsPreview,
                backend: 'cdp',
                message: `Use memory_search("${memResult.referenceId}") for full tab list.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `web.list_tabs_urls failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.listTabsUrls = listTabsUrls;
/**
 * url.normalize_bundle - Normalize URL bundle
 *
 * Takes an input refId pointing to URL list in memory,
 * normalizes (dedup, UTM removal, trailing slash), groups by domain,
 * stores result in memory, returns summary + outputRefId.
 *
 * Input formats supported:
 * - JSON array of URLs: ["url1", "url2"]
 * - JSON array of objects: [{ url: "url1" }, { href: "url2" }]
 * - JSON object with urls/tabs/links array
 * - Newline-separated URLs
 * - Comma-separated URLs
 *
 * @param inputRefId - Memory refId pointing to URL list
 * @param options.maxUrls - Maximum URLs to process (default: 200)
 * @param options.removeUtm - Remove UTM parameters (default: true)
 * @param options.normalizeTrailingSlash - Normalize trailing slashes (default: true)
 * @param options.groupByDomain - Group results by domain (default: true)
 * @param options.namespace - Memory namespace for output (default: 'short-term')
 */
async function normalizeUrlBundle(inputRefId, options) {
    try {
        const result = await (0, url_bundle_1.normalizeUrlBundle)(inputRefId, options);
        if (!result.success) {
            return {
                success: false,
                error: result.error,
            };
        }
        return {
            success: true,
            action: 'allow',
            refId: result.outputRefId,
            summary: result.summary,
            data: {
                inputRefId,
                outputRefId: result.outputRefId,
                inputCount: result.data?.inputCount,
                outputCount: result.data?.outputCount,
                duplicatesRemoved: result.data?.duplicatesRemoved,
                removedCount: result.data?.removedCount,
                domainGroups: result.data?.domainGroups,
                message: `Use memory_search("${result.outputRefId}") for normalized URL list.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `url.normalize_bundle failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.normalizeUrlBundle = normalizeUrlBundle;
/**
 * url.get_bundle_stats - Get URL bundle statistics
 *
 * Returns statistics about a URL bundle without processing.
 * Useful for preview before normalization.
 *
 * @param inputRefId - Memory refId pointing to URL list
 * @param options.namespace - Memory namespace (default: 'short-term')
 */
async function getUrlBundleStats(inputRefId, options) {
    try {
        const result = await (0, url_bundle_1.getUrlBundleStats)(inputRefId, options?.namespace);
        if (!result.success) {
            return {
                success: false,
                error: result.error,
            };
        }
        const stats = result.stats;
        const topDomainsStr = stats.topDomains
            .slice(0, 5)
            .map((d) => `  - ${d.domain}: ${d.count}`)
            .join('\n');
        const summary = `URL Bundle Stats:\n- Total URLs: ${stats.totalUrls}\n- Unique domains: ${stats.uniqueDomains}\nTop domains:\n${topDomainsStr}`;
        return {
            success: true,
            action: 'allow',
            summary,
            data: {
                inputRefId,
                totalUrls: stats.totalUrls,
                uniqueDomains: stats.uniqueDomains,
                topDomains: stats.topDomains,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `url.get_bundle_stats failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.getUrlBundleStats = getUrlBundleStats;
/**
 * url.batch_skillize - Batch skillize URL bundle
 *
 * Takes a normalized URL bundle (refId), runs skillize on each URL,
 * stores results in memory, returns summary + outputRefId.
 *
 * IMPORTANT: dry-run by default (confirmWrite=false).
 * Use confirmWrite=true only after preview/approval.
 *
 * @param inputRefId - Memory refId pointing to normalized URL bundle
 * @param options.maxUrls - Maximum URLs to process (default: 50)
 * @param options.rateLimitMs - Delay between URLs in ms (default: 1000)
 * @param options.confirmWrite - Write to disk (default: false = dry-run)
 * @param options.template - Force template type (auto-detect if not specified)
 * @param options.namespace - Memory namespace (default: 'long-term')
 * @param options.stopOnError - Stop on first error (default: false)
 */
async function batchSkillizeUrlBundle(inputRefId, options) {
    try {
        const result = await (0, url_bundle_skillize_1.batchSkillizeUrlBundle)(inputRefId, options);
        if (!result.success) {
            return {
                success: false,
                error: result.error,
            };
        }
        return {
            success: true,
            action: 'allow',
            refId: result.outputRefId,
            summary: result.summary,
            data: {
                inputRefId,
                outputRefId: result.outputRefId,
                inputCount: result.data?.inputCount,
                processedCount: result.data?.processedCount,
                successCount: result.data?.successCount,
                failureCount: result.data?.failureCount,
                skippedCount: result.data?.skippedCount,
                dryRun: result.data?.dryRun,
                message: result.data?.dryRun
                    ? `Dry-run complete. Use confirmWrite=true to write. Use memory_search("${result.outputRefId}") for results.`
                    : `Skills written. Use memory_search("${result.outputRefId}") for results.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `url.batch_skillize failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.batchSkillizeUrlBundle = batchSkillizeUrlBundle;
/**
 * url.batch_skillize_preview - Preview batch skillize
 *
 * Returns preview of what would be processed without running skillize.
 * Use this before batchSkillizeUrlBundle to verify config.
 *
 * @param inputRefId - Memory refId pointing to normalized URL bundle
 * @param options - Configuration to preview
 */
async function batchSkillizePreview(inputRefId, options) {
    try {
        const result = await (0, url_bundle_skillize_1.getBatchSkillizePreview)(inputRefId, options);
        if (!result.success) {
            return {
                success: false,
                error: result.error,
            };
        }
        const preview = result.preview;
        const domains = Object.entries(preview.domains)
            .slice(0, 5)
            .map(([domain, count]) => `  - ${domain}: ${count}`)
            .join('\n');
        const estimatedMinutes = Math.ceil(preview.estimatedTimeMs / 60000);
        const summary = `Batch Skillize Preview:
- URLs to process: ${preview.urlsToProcess}/${preview.totalUrls}
- URLs to skip: ${preview.urlsToSkip}
- Estimated time: ~${estimatedMinutes} minutes
- Dry-run: ${!preview.config.confirmWrite}

Domains:
${domains}${Object.keys(preview.domains).length > 5 ? '\n  ...' : ''}`;
        return {
            success: true,
            action: 'allow',
            summary,
            data: {
                inputRefId,
                ...preview,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `url.batch_skillize_preview failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.batchSkillizePreview = batchSkillizePreview;
/**
 * pipeline.web_skillize_from_tabs - One-command pipeline
 *
 * Runs the full pipeline: list_tabs_urls(CDP) -> normalize URL bundle -> batch skillize
 *
 * Features:
 * - Minimal output: summary + refId only (no URL lists in response)
 * - Dry-run by default: confirmWrite=false
 * - CDP connection check with human-friendly error
 * - inputRefId option: skip tabs collection, use existing URL bundle
 *
 * @param options.inputRefId - Skip tabs collection, use existing URL bundle
 * @param options.includeDomains - Include only these domains
 * @param options.excludeDomains - Exclude these domains
 * @param options.excludeUrlPatterns - Exclude URLs matching these patterns
 * @param options.maxUrls - Maximum URLs to process (default: 200)
 * @param options.perDomainLimit - Per-domain limit (default: 50)
 * @param options.stripTracking - Remove tracking parameters (default: true)
 * @param options.maxFetch - Maximum URLs to skillize (default: 20)
 * @param options.rateLimitMs - Rate limit between URLs (default: 1000)
 * @param options.confirmWrite - Write to disk (default: false = dry-run)
 * @param options.namespace - Memory namespace (default: 'long-term')
 */
async function webSkillizeFromTabs(options) {
    try {
        const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)(options);
        if (!result.success) {
            if (result.requireHuman) {
                return {
                    success: false,
                    action: 'require_human',
                    error: result.error,
                    data: {
                        instruction: result.humanInstruction,
                    },
                };
            }
            return {
                success: false,
                error: result.error,
            };
        }
        return {
            success: true,
            action: 'allow',
            refId: result.refId,
            summary: result.summary,
            data: {
                refId: result.refId,
                message: `Pipeline complete. Use memory_search("${result.refId}") for run record with all intermediate refIds.`,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `pipeline.web_skillize_from_tabs failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.webSkillizeFromTabs = webSkillizeFromTabs;
