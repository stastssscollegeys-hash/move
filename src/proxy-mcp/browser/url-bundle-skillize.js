"use strict";
/**
 * URL Bundle Skillize - P7.2
 *
 * Batch process URL bundle through skillize.
 * Rate-limited, dry-run by default, supervisor approval for writes.
 *
 * Input: refId pointing to normalized URL bundle
 * Output: summary + outputRefId with skillize results
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getBatchSkillizePreview = exports.batchSkillizeUrlBundle = exports.DEFAULT_BATCH_SKILLIZE_CONFIG = void 0;
const memory_1 = require("../tools/memory");
const observability_1 = require("../observability");
const skillize_1 = require("../skillize");
/** Default configuration */
exports.DEFAULT_BATCH_SKILLIZE_CONFIG = {
    maxUrls: 50,
    rateLimitMs: 1000,
    confirmWrite: false,
    template: 'docs', // Will be overridden by auto-detect if not specified
    namespace: 'long-term',
    stopOnError: false,
};
/**
 * Batch skillize URL bundle
 *
 * Takes normalized URL bundle from memory, processes each URL through skillize,
 * stores results in memory, returns summary + outputRefId.
 *
 * @param inputRefId - Reference ID to normalized URL bundle in memory
 * @param config - Batch processing configuration
 * @returns Batch skillize result with outputRefId
 */
async function batchSkillizeUrlBundle(inputRefId, config = {}) {
    const fullConfig = { ...exports.DEFAULT_BATCH_SKILLIZE_CONFIG, ...config };
    try {
        // Fetch normalized URL bundle from memory
        const memResult = await (0, memory_1.memoryGetContent)(inputRefId);
        const memData = memResult.data;
        if (!memResult.success || !memData?.content) {
            return {
                success: false,
                error: `Failed to find URL bundle with refId: ${inputRefId}`,
            };
        }
        // Parse the normalized bundle
        let bundle;
        try {
            bundle = JSON.parse(memData.content);
        }
        catch {
            return {
                success: false,
                error: 'Failed to parse URL bundle: invalid JSON',
            };
        }
        // Get URLs from bundle
        let urls = [];
        if (bundle.urls && Array.isArray(bundle.urls)) {
            urls = bundle.urls;
        }
        else if (bundle.domainGroups && Array.isArray(bundle.domainGroups)) {
            // Flatten domain groups
            for (const group of bundle.domainGroups) {
                if (group.urls && Array.isArray(group.urls)) {
                    urls.push(...group.urls);
                }
            }
        }
        if (urls.length === 0) {
            return {
                success: false,
                error: 'No URLs found in the bundle',
            };
        }
        // Apply max URL limit
        const urlsToProcess = urls.slice(0, fullConfig.maxUrls);
        const skippedCount = urls.length - urlsToProcess.length;
        // Process URLs with rate limiting
        const results = [];
        let successCount = 0;
        let failureCount = 0;
        for (let i = 0; i < urlsToProcess.length; i++) {
            const normalizedUrl = urlsToProcess[i];
            // Rate limiting (skip delay for first URL)
            if (i > 0 && fullConfig.rateLimitMs > 0) {
                await sleep(fullConfig.rateLimitMs);
            }
            try {
                const skillizeResult = await (0, skillize_1.skillize)(normalizedUrl.url, {
                    confirmWrite: fullConfig.confirmWrite,
                    namespace: fullConfig.namespace,
                    // Only use template if explicitly provided, otherwise auto-detect
                    template: config.template,
                });
                if (skillizeResult.success) {
                    results.push({
                        url: normalizedUrl.url,
                        success: true,
                        refId: skillizeResult.refId,
                        skillName: skillizeResult.data?.skillName,
                        template: skillizeResult.template,
                    });
                    successCount++;
                }
                else {
                    results.push({
                        url: normalizedUrl.url,
                        success: false,
                        error: skillizeResult.error,
                    });
                    failureCount++;
                    if (fullConfig.stopOnError) {
                        break;
                    }
                }
            }
            catch (err) {
                results.push({
                    url: normalizedUrl.url,
                    success: false,
                    error: err instanceof Error ? err.message : String(err),
                });
                failureCount++;
                if (fullConfig.stopOnError) {
                    break;
                }
            }
        }
        // Store results in memory
        const outputData = {
            inputRefId,
            results,
            metadata: {
                inputCount: urls.length,
                processedCount: results.length,
                successCount,
                failureCount,
                skippedCount,
                dryRun: !fullConfig.confirmWrite,
                config: fullConfig,
                processedAt: new Date().toISOString(),
            },
        };
        const storeResult = await (0, memory_1.memoryAdd)(JSON.stringify(outputData), fullConfig.namespace, {
            tags: ['url-bundle', 'skillize-batch', `success:${successCount}`, `fail:${failureCount}`],
            source: 'url-bundle.skillize',
        });
        if (!storeResult.success) {
            return {
                success: false,
                error: `Failed to store results: ${storeResult.error}`,
            };
        }
        // Record observability event
        (0, observability_1.recordEvent)('url_bundle_normalize', 'url-bundle-skillize', 'ok', {
            metadata: {
                inputCount: urls.length,
                processedCount: results.length,
                successCount,
                failureCount,
                dryRun: !fullConfig.confirmWrite,
            },
        });
        // Generate summary
        const successNames = results
            .filter((r) => r.success && r.skillName)
            .slice(0, 5)
            .map((r) => `  - ${r.skillName}`)
            .join('\n');
        const summary = `Batch Skillize ${fullConfig.confirmWrite ? '(WRITE)' : '(dry-run)'}:
Processed: ${results.length}/${urls.length} URLs
Success: ${successCount}, Failure: ${failureCount}${skippedCount > 0 ? `, Skipped: ${skippedCount}` : ''}

Generated skills:
${successNames || '  (none)'}${successCount > 5 ? '\n  ...' : ''}`;
        return {
            success: true,
            outputRefId: storeResult.referenceId,
            summary,
            data: {
                inputCount: urls.length,
                processedCount: results.length,
                successCount,
                failureCount,
                skippedCount,
                results,
                dryRun: !fullConfig.confirmWrite,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `Batch skillize failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.batchSkillizeUrlBundle = batchSkillizeUrlBundle;
/**
 * Sleep for given milliseconds
 */
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
/**
 * Get batch skillize preview
 *
 * Returns preview of what would be processed without actually running skillize.
 *
 * @param inputRefId - Reference ID to normalized URL bundle
 * @param config - Configuration to apply
 */
async function getBatchSkillizePreview(inputRefId, config = {}) {
    const fullConfig = { ...exports.DEFAULT_BATCH_SKILLIZE_CONFIG, ...config };
    try {
        const memResult = await (0, memory_1.memoryGetContent)(inputRefId);
        const memData = memResult.data;
        if (!memResult.success || !memData?.content) {
            return {
                success: false,
                error: `Failed to find URL bundle with refId: ${inputRefId}`,
            };
        }
        const bundle = JSON.parse(memData.content);
        let urls = [];
        if (bundle.urls && Array.isArray(bundle.urls)) {
            urls = bundle.urls;
        }
        else if (bundle.domainGroups && Array.isArray(bundle.domainGroups)) {
            for (const group of bundle.domainGroups) {
                if (group.urls && Array.isArray(group.urls)) {
                    urls.push(...group.urls);
                }
            }
        }
        const urlsToProcess = Math.min(urls.length, fullConfig.maxUrls);
        const urlsToSkip = urls.length - urlsToProcess;
        // Count by domain
        const domains = {};
        for (const url of urls.slice(0, fullConfig.maxUrls)) {
            domains[url.domain] = (domains[url.domain] || 0) + 1;
        }
        // Estimate time (rate limit + processing time ~2s per URL)
        const estimatedTimeMs = urlsToProcess * (fullConfig.rateLimitMs + 2000);
        return {
            success: true,
            preview: {
                totalUrls: urls.length,
                urlsToProcess,
                urlsToSkip,
                domains,
                estimatedTimeMs,
                config: fullConfig,
            },
        };
    }
    catch (err) {
        return {
            success: false,
            error: `Preview failed: ${err instanceof Error ? err.message : String(err)}`,
        };
    }
}
exports.getBatchSkillizePreview = getBatchSkillizePreview;
