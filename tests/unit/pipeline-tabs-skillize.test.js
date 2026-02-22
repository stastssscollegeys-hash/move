"use strict";
/**
 * Pipeline: web_skillize_from_tabs Unit Tests - P7.3
 *
 * Tests for the one-command pipeline:
 * list_tabs_urls(CDP) -> normalize URL bundle -> batch skillize
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
const pipeline_tabs_skillize_1 = require("../../src/proxy-mcp/browser/pipeline-tabs-skillize");
const cdpModule = __importStar(require("../../src/proxy-mcp/browser/cdp"));
const urlBundleModule = __importStar(require("../../src/proxy-mcp/browser/url-bundle"));
const skillizeModule = __importStar(require("../../src/proxy-mcp/browser/url-bundle-skillize"));
const memoryTools = __importStar(require("../../src/proxy-mcp/tools/memory"));
// Mock dependencies
jest.mock('../../src/proxy-mcp/browser/cdp');
jest.mock('../../src/proxy-mcp/browser/url-bundle');
jest.mock('../../src/proxy-mcp/browser/url-bundle-skillize');
jest.mock('../../src/proxy-mcp/tools/memory');
jest.mock('../../src/proxy-mcp/observability', () => ({
    recordEvent: jest.fn(),
}));
const mockListTabsViaCDP = cdpModule.listTabsViaCDP;
const mockNormalizeUrlBundle = urlBundleModule.normalizeUrlBundle;
const mockBatchSkillizeUrlBundle = skillizeModule.batchSkillizeUrlBundle;
const mockMemoryAdd = memoryTools.memoryAdd;
describe('Pipeline: web_skillize_from_tabs', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });
    describe('DEFAULT_PIPELINE_CONFIG', () => {
        it('should have sensible defaults', () => {
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.inputRefId).toBeNull();
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.maxUrls).toBe(200);
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.perDomainLimit).toBe(50);
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.stripTracking).toBe(true);
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.maxFetch).toBe(20);
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.confirmWrite).toBe(false);
            expect(pipeline_tabs_skillize_1.DEFAULT_PIPELINE_CONFIG.namespace).toBe('long-term');
        });
    });
    describe('runPipelineTabsSkillize', () => {
        const mockTabs = {
            tabs: [
                { url: 'https://docs.example.com/page1', title: 'Page 1', index: 0 },
                { url: 'https://docs.example.com/page2', title: 'Page 2', index: 1 },
                { url: 'https://other.com/api', title: 'API', index: 2 },
            ],
            totalTabs: 3,
            tabsPreview: [
                { url: 'https://docs.example.com/page1', title: 'Page 1', index: 0 },
                { url: 'https://docs.example.com/page2', title: 'Page 2', index: 1 },
                { url: 'https://other.com/api', title: 'API', index: 2 },
            ],
        };
        it('should run full pipeline: tabs -> normalize -> skillize', async () => {
            // Setup mocks
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'tabs-ref-123',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref-456',
                summary: 'Normalized 3 URLs',
                data: {
                    inputCount: 3,
                    outputCount: 3,
                    duplicatesRemoved: 0,
                    removedCount: 0,
                    domainGroups: { 'docs.example.com': 2, 'other.com': 1 },
                },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref-789',
                summary: 'Batch Skillize (dry-run)',
                data: {
                    inputCount: 3,
                    processedCount: 3,
                    successCount: 3,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)();
            expect(result.success).toBe(true);
            expect(result.refId).toBeDefined();
            expect(result.summary).toContain('Pipeline: web_skillize_from_tabs');
            expect(result.summary).toContain('DRY-RUN');
            expect(mockListTabsViaCDP).toHaveBeenCalledTimes(1);
            expect(mockNormalizeUrlBundle).toHaveBeenCalledTimes(1);
            expect(mockBatchSkillizeUrlBundle).toHaveBeenCalledTimes(1);
        });
        it('should skip tabs collection when inputRefId is provided', async () => {
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref-456',
                summary: 'Normalized URLs',
                data: {
                    inputCount: 5,
                    outputCount: 5,
                    duplicatesRemoved: 0,
                    removedCount: 0,
                    domainGroups: {},
                },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref-789',
                summary: 'Skillize complete',
                data: {
                    inputCount: 5,
                    processedCount: 5,
                    successCount: 5,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'run-ref-123',
            });
            const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)({
                inputRefId: 'existing-bundle-ref',
            });
            expect(result.success).toBe(true);
            expect(result.summary).toContain('skipped');
            expect(mockListTabsViaCDP).not.toHaveBeenCalled();
            expect(mockNormalizeUrlBundle).toHaveBeenCalledWith('existing-bundle-ref', expect.any(Object));
        });
        it('should return require_human when CDP connection fails', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: false,
                error: 'CDP connection failed: ECONNREFUSED',
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'run-ref-error',
            });
            const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)();
            expect(result.success).toBe(false);
            expect(result.requireHuman).toBe(true);
            expect(result.humanInstruction).toContain('Chrome CDP connection failed');
            expect(result.humanInstruction).toContain('npm run chrome:debug:start');
        });
        it('should pass confirmWrite to batch skillize', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-123',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref',
                data: { inputCount: 3, outputCount: 3, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref',
                data: {
                    inputCount: 3,
                    processedCount: 3,
                    successCount: 3,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: false,
                },
            });
            await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)({ confirmWrite: true });
            expect(mockBatchSkillizeUrlBundle).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ confirmWrite: true }));
        });
        it('should filter tabs by includeDomains', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'tabs-ref',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref',
                data: { inputCount: 2, outputCount: 2, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref',
                data: {
                    inputCount: 2,
                    processedCount: 2,
                    successCount: 2,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)({
                includeDomains: ['docs.example.com'],
            });
            // Verify that memoryAdd was called with filtered tabs
            expect(mockMemoryAdd).toHaveBeenCalledWith(expect.stringContaining('docs.example.com'), expect.any(String), expect.any(Object));
        });
        it('should filter tabs by excludeDomains', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'tabs-ref',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref',
                data: { inputCount: 1, outputCount: 1, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref',
                data: {
                    inputCount: 1,
                    processedCount: 1,
                    successCount: 1,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)({
                excludeDomains: ['docs.example.com'],
            });
            // Verify memoryAdd was called without docs.example.com URLs
            const memoryCall = mockMemoryAdd.mock.calls[0][0];
            expect(memoryCall).not.toContain('docs.example.com');
        });
        it('should return minimal output (summary + refId)', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'run-ref-minimal',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref',
                data: { inputCount: 3, outputCount: 3, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref',
                data: {
                    inputCount: 3,
                    processedCount: 3,
                    successCount: 3,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)();
            // Verify minimal output - no URL lists
            expect(result.refId).toBeDefined();
            expect(result.summary).toBeDefined();
            expect(typeof result.summary).toBe('string');
            // Summary should not contain raw URLs
            expect(result.summary).not.toContain('https://docs.example.com/page1');
        });
        it('should store pipeline run record with all intermediate refIds', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd
                .mockResolvedValueOnce({ success: true, referenceId: 'tabs-ref-111' })
                .mockResolvedValueOnce({ success: true, referenceId: 'run-ref-final' });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref-222',
                data: { inputCount: 3, outputCount: 3, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref-333',
                data: {
                    inputCount: 3,
                    processedCount: 3,
                    successCount: 3,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)();
            // Verify run record contains all intermediate refIds
            const runRecordCall = mockMemoryAdd.mock.calls[1];
            const runRecord = JSON.parse(runRecordCall[0]);
            expect(runRecord.stages.tabs?.refId).toBe('tabs-ref-111');
            expect(runRecord.stages.normalize?.outputRefId).toBe('normalized-ref-222');
            expect(runRecord.stages.skillize?.outputRefId).toBe('skillize-ref-333');
            expect(runRecord.status).toBe('completed');
        });
        it('should handle normalize failure gracefully', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-123',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: false,
                error: 'Invalid URL format',
            });
            const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)();
            expect(result.success).toBe(false);
            expect(result.error).toContain('Normalize failed');
        });
        it('should handle skillize failure gracefully', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-123',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref',
                data: { inputCount: 3, outputCount: 3, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: false,
                error: 'Skillize processing error',
            });
            const result = await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)();
            expect(result.success).toBe(false);
            expect(result.error).toContain('Skillize failed');
        });
        it('should respect maxFetch limit for skillize', async () => {
            mockListTabsViaCDP.mockResolvedValue({
                success: true,
                data: mockTabs,
            });
            mockMemoryAdd.mockResolvedValue({
                success: true,
                referenceId: 'ref-123',
            });
            mockNormalizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'normalized-ref',
                data: { inputCount: 3, outputCount: 3, duplicatesRemoved: 0, removedCount: 0 },
            });
            mockBatchSkillizeUrlBundle.mockResolvedValue({
                success: true,
                outputRefId: 'skillize-ref',
                data: {
                    inputCount: 3,
                    processedCount: 5,
                    successCount: 5,
                    failureCount: 0,
                    skippedCount: 0,
                    results: [],
                    dryRun: true,
                },
            });
            await (0, pipeline_tabs_skillize_1.runPipelineTabsSkillize)({ maxFetch: 5 });
            expect(mockBatchSkillizeUrlBundle).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ maxUrls: 5 }));
        });
    });
});
