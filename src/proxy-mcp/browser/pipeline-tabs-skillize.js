"use strict";
/**
 * Pipeline: web_skillize_from_tabs - P7.3
 *
 * One-command pipeline: list_tabs_urls(CDP) -> normalize URL bundle -> batch skillize
 *
 * Features:
 * - Minimal output: summary + refId only (no URL lists in response)
 * - Dry-run default: confirmWrite=false
 * - CDP connection check with human-friendly error
 * - inputRefId option: skip tabs collection, use existing URL bundle
 * - All intermediate data stored in memory with refIds
 *
 * Output: pipeline-run record containing all intermediate refIds
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.runPipelineTabsSkillize = exports.DEFAULT_PIPELINE_CONFIG = void 0;
const memory_1 = require("../tools/memory");
const observability_1 = require("../observability");
const cdp_1 = require("./cdp");
const url_bundle_1 = require("./url-bundle");
const url_bundle_skillize_1 = require("./url-bundle-skillize");
/** Default configuration */
exports.DEFAULT_PIPELINE_CONFIG = {
    inputRefId: null,
    includeDomains: null,
    excludeDomains: null,
    excludeUrlPatterns: null,
    maxUrls: 200,
    perDomainLimit: 50,
    stripTracking: true,
    maxFetch: 20,
    concurrency: 3,
    rateLimitMs: 1000,
    confirmWrite: false,
    namespace: 'long-term',
};
/**
 * Run the full pipeline: tabs -> normalize -> skillize
 *
 * @param config Pipeline configuration
 * @returns Pipeline result with summary + refId
 */
async function runPipelineTabsSkillize(config = {}) {
    const startTime = Date.now();
    const pipelineId = `pipeline-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const fullConfig = { ...exports.DEFAULT_PIPELINE_CONFIG, ...config };
    // Initialize run record
    const runRecord = {
        pipelineId,
        startedAt: new Date().toISOString(),
        status: 'running',
        config: fullConfig,
        stages: {},
    };
    try {
        let tabsRefId;
        let totalTabs = 0;
        // Stage 1: Get tabs (or use inputRefId)
        if (fullConfig.inputRefId) {
            // Skip tabs collection, use provided refId
            tabsRefId = fullConfig.inputRefId;
            runRecord.stages.tabs = {
                refId: tabsRefId,
                totalTabs: 0,
                skipped: true,
            };
        }
        else {
            // Collect tabs via CDP
            const tabsResult = await (0, cdp_1.listTabsViaCDP)();
            if (!tabsResult.success) {
                // CDP connection failed - return human-friendly error
                runRecord.status = 'failed';
                runRecord.error = tabsResult.error;
                await storeRunRecord(runRecord, fullConfig.namespace);
                return {
                    success: false,
                    error: tabsResult.error,
                    requireHuman: true,
                    humanInstruction: `Chrome CDP connection failed. Please ensure Chrome is running with debugging enabled:

1. Start Chrome with CDP:
   npm run chrome:debug:start

   Or manually:
   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222

2. Open the tabs you want to skillize

3. Run this pipeline again`,
                };
            }
            const tabsData = tabsResult.data;
            totalTabs = tabsData.totalTabs;
            // Filter tabs by domain if configured
            let filteredTabs = tabsData.tabs;
            if (fullConfig.includeDomains && fullConfig.includeDomains.length > 0) {
                filteredTabs = filteredTabs.filter((tab) => {
                    try {
                        const hostname = new URL(tab.url).hostname;
                        return fullConfig.includeDomains.some((d) => hostname.includes(d));
                    }
                    catch {
                        return false;
                    }
                });
            }
            if (fullConfig.excludeDomains && fullConfig.excludeDomains.length > 0) {
                filteredTabs = filteredTabs.filter((tab) => {
                    try {
                        const hostname = new URL(tab.url).hostname;
                        return !fullConfig.excludeDomains.some((d) => hostname.includes(d));
                    }
                    catch {
                        return true;
                    }
                });
            }
            if (fullConfig.excludeUrlPatterns && fullConfig.excludeUrlPatterns.length > 0) {
                const patterns = fullConfig.excludeUrlPatterns.map((p) => new RegExp(p, 'i'));
                filteredTabs = filteredTabs.filter((tab) => {
                    return !patterns.some((p) => p.test(tab.url));
                });
            }
            // Store tabs in memory
            const tabsMemResult = await (0, memory_1.memoryAdd)(JSON.stringify({
                tabs: filteredTabs,
                totalTabs: filteredTabs.length,
                originalTotalTabs: totalTabs,
                collectedAt: new Date().toISOString(),
            }), fullConfig.namespace, {
                tags: ['pipeline', 'tabs', 'cdp'],
                source: 'pipeline.web_skillize_from_tabs',
            });
            if (!tabsMemResult.success) {
                throw new Error(`Failed to store tabs: ${tabsMemResult.error}`);
            }
            tabsRefId = tabsMemResult.referenceId;
            runRecord.stages.tabs = {
                refId: tabsRefId,
                totalTabs: filteredTabs.length,
            };
        }
        // Stage 2: Normalize URL bundle
        const normalizeConfig = {
            maxUrls: fullConfig.maxUrls,
            removeUtm: fullConfig.stripTracking,
            normalizeTrailingSlash: true,
            groupByDomain: true,
            namespace: fullConfig.namespace,
        };
        const normalizeResult = await (0, url_bundle_1.normalizeUrlBundle)(tabsRefId, normalizeConfig);
        if (!normalizeResult.success) {
            throw new Error(`Normalize failed: ${normalizeResult.error}`);
        }
        runRecord.stages.normalize = {
            inputRefId: tabsRefId,
            outputRefId: normalizeResult.outputRefId,
            inputCount: normalizeResult.data?.inputCount || 0,
            outputCount: normalizeResult.data?.outputCount || 0,
            duplicatesRemoved: normalizeResult.data?.duplicatesRemoved || 0,
        };
        // Stage 3: Batch skillize
        const skillizeConfig = {
            maxUrls: fullConfig.maxFetch,
            rateLimitMs: fullConfig.rateLimitMs,
            confirmWrite: fullConfig.confirmWrite,
            namespace: fullConfig.namespace,
            stopOnError: false,
        };
        const skillizeResult = await (0, url_bundle_skillize_1.batchSkillizeUrlBundle)(normalizeResult.outputRefId, skillizeConfig);
        if (!skillizeResult.success) {
            throw new Error(`Skillize failed: ${skillizeResult.error}`);
        }
        runRecord.stages.skillize = {
            inputRefId: normalizeResult.outputRefId,
            outputRefId: skillizeResult.outputRefId,
            processedCount: skillizeResult.data?.processedCount || 0,
            successCount: skillizeResult.data?.successCount || 0,
            failureCount: skillizeResult.data?.failureCount || 0,
            dryRun: skillizeResult.data?.dryRun ?? true,
        };
        // Complete run record
        runRecord.status = 'completed';
        runRecord.completedAt = new Date().toISOString();
        const runRefId = await storeRunRecord(runRecord, fullConfig.namespace);
        // Record observability event
        const durationMs = Date.now() - startTime;
        (0, observability_1.recordEvent)('pipeline_tabs_skillize', 'pipeline', 'ok', {
            metadata: {
                pipelineId,
                durationMs,
                tabsCount: runRecord.stages.tabs?.totalTabs || 0,
                normalizedCount: runRecord.stages.normalize?.outputCount || 0,
                skillizedCount: runRecord.stages.skillize?.successCount || 0,
                dryRun: fullConfig.confirmWrite === false,
            },
        });
        // Generate summary
        const summary = generatePipelineSummary(runRecord, durationMs);
        return {
            success: true,
            refId: runRefId,
            summary,
        };
    }
    catch (err) {
        runRecord.status = 'failed';
        runRecord.error = err instanceof Error ? err.message : String(err);
        await storeRunRecord(runRecord, fullConfig.namespace);
        const durationMs = Date.now() - startTime;
        (0, observability_1.recordEvent)('pipeline_tabs_skillize', 'pipeline', 'fail', {
            metadata: {
                pipelineId,
                durationMs,
                error: runRecord.error,
            },
        });
        return {
            success: false,
            error: `Pipeline failed: ${runRecord.error}`,
        };
    }
}
exports.runPipelineTabsSkillize = runPipelineTabsSkillize;
/**
 * Store pipeline run record in memory
 */
async function storeRunRecord(record, namespace) {
    const memResult = await (0, memory_1.memoryAdd)(JSON.stringify(record), namespace, {
        tags: ['pipeline', 'run-record', record.status],
        source: 'pipeline.web_skillize_from_tabs',
    });
    if (!memResult.success) {
        throw new Error(`Failed to store run record: ${memResult.error}`);
    }
    return memResult.referenceId;
}
/**
 * Generate pipeline summary
 */
function generatePipelineSummary(record, durationMs) {
    const tabs = record.stages.tabs;
    const normalize = record.stages.normalize;
    const skillize = record.stages.skillize;
    const dryRunNote = skillize?.dryRun
        ? ' (DRY-RUN - use confirmWrite=true to write)'
        : ' (WRITTEN)';
    const lines = [
        `Pipeline: web_skillize_from_tabs${dryRunNote}`,
        `Duration: ${Math.round(durationMs / 1000)}s`,
        '',
        'Stages:',
    ];
    if (tabs) {
        if (tabs.skipped) {
            lines.push(`  1. Tabs: skipped (using inputRefId)`);
        }
        else {
            lines.push(`  1. Tabs: ${tabs.totalTabs} collected`);
        }
    }
    if (normalize) {
        lines.push(`  2. Normalize: ${normalize.inputCount} -> ${normalize.outputCount} URLs (${normalize.duplicatesRemoved} duplicates removed)`);
    }
    if (skillize) {
        lines.push(`  3. Skillize: ${skillize.successCount}/${skillize.processedCount} success`);
        if (skillize.failureCount > 0) {
            lines.push(`     (${skillize.failureCount} failures)`);
        }
    }
    lines.push('');
    lines.push(`Use memory_search with refId to inspect intermediate results.`);
    return lines.join('\n');
}
