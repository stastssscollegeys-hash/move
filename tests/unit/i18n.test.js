"use strict";
/**
 * i18n Test Suite
 *
 * Tests for internationalization support (P20)
 */
Object.defineProperty(exports, "__esModule", { value: true });
const i18n_1 = require("../../src/i18n");
describe('i18n', () => {
    // Store original locale and restore after tests
    let originalLocale;
    beforeAll(() => {
        originalLocale = (0, i18n_1.getLocale)();
    });
    afterAll(() => {
        (0, i18n_1.setLocale)(originalLocale);
    });
    beforeEach(() => {
        // Reset to Japanese (default)
        (0, i18n_1.setLocale)('ja');
        // Clear environment variable
        delete process.env.TAISUN_LOCALE;
    });
    describe('getLocale', () => {
        it('should return "ja" by default', () => {
            expect((0, i18n_1.getLocale)()).toBe('ja');
        });
        it('should return "en" when TAISUN_LOCALE is "en"', () => {
            process.env.TAISUN_LOCALE = 'en';
            expect((0, i18n_1.getLocale)()).toBe('en');
        });
        it('should return "en" when TAISUN_LOCALE is "en-US"', () => {
            process.env.TAISUN_LOCALE = 'en-US';
            expect((0, i18n_1.getLocale)()).toBe('en');
        });
        it('should return "ja" when TAISUN_LOCALE is "ja"', () => {
            process.env.TAISUN_LOCALE = 'ja';
            expect((0, i18n_1.getLocale)()).toBe('ja');
        });
        it('should return "ja" when TAISUN_LOCALE is "ja-JP"', () => {
            process.env.TAISUN_LOCALE = 'ja-JP';
            expect((0, i18n_1.getLocale)()).toBe('ja');
        });
        it('should fallback to "ja" when TAISUN_LOCALE is unknown value', () => {
            process.env.TAISUN_LOCALE = 'fr';
            expect((0, i18n_1.getLocale)()).toBe('ja');
        });
        it('should fallback to "ja" when TAISUN_LOCALE is empty string', () => {
            process.env.TAISUN_LOCALE = '';
            expect((0, i18n_1.getLocale)()).toBe('ja');
        });
    });
    describe('setLocale', () => {
        it('should change locale to "en"', () => {
            (0, i18n_1.setLocale)('en');
            // Note: getLocale() checks env first, so we need to test with t()
            const result = (0, i18n_1.t)('supervisor.runlog.title', { runId: 'test-123' });
            expect(result).toBe('[SUPERVISOR] test-123');
        });
        it('should change locale to "ja"', () => {
            (0, i18n_1.setLocale)('ja');
            const result = (0, i18n_1.t)('supervisor.runlog.title', { runId: 'test-123' });
            expect(result).toBe('[SUPERVISOR] test-123');
        });
    });
    describe('t (translate)', () => {
        describe('Japanese locale', () => {
            beforeEach(() => {
                (0, i18n_1.setLocale)('ja');
            });
            it('should translate supervisor.runlog.title', () => {
                const result = (0, i18n_1.t)('supervisor.runlog.title', { runId: 'run-abc' });
                expect(result).toBe('[SUPERVISOR] run-abc');
            });
            it('should translate supervisor.approval.title in Japanese', () => {
                const result = (0, i18n_1.t)('supervisor.approval.title', { runId: 'run-xyz' });
                expect(result).toBe('[承認要求] run-xyz');
            });
            it('should translate agent.progress.status.in_progress', () => {
                const result = (0, i18n_1.t)('agent.progress.status.in_progress');
                expect(result).toBe('進行中');
            });
            it('should translate agent.progress.status.completed', () => {
                const result = (0, i18n_1.t)('agent.progress.status.completed');
                expect(result).toBe('完了');
            });
            it('should replace multiple placeholders', () => {
                const result = (0, i18n_1.t)('agent.progress.body', {
                    statusEmoji: '🔄',
                    status: '進行中',
                    progressBar: '[████░░░░░░░░░░░░░░░░] 20%',
                    completed: 2,
                    total: 10,
                    currentTaskLine: '**現在のタスク**: テスト',
                    timestamp: '2024-01-01T00:00:00Z',
                });
                expect(result).toContain('🔄');
                expect(result).toContain('進行中');
                expect(result).toContain('2/10');
            });
        });
        describe('English locale', () => {
            beforeEach(() => {
                process.env.TAISUN_LOCALE = 'en';
            });
            it('should translate supervisor.runlog.title', () => {
                const result = (0, i18n_1.t)('supervisor.runlog.title', { runId: 'run-abc' });
                expect(result).toBe('[SUPERVISOR] run-abc');
            });
            it('should translate supervisor.approval.title in English', () => {
                const result = (0, i18n_1.t)('supervisor.approval.title', { runId: 'run-xyz' });
                expect(result).toBe('[APPROVAL] run-xyz');
            });
            it('should translate agent.progress.status.in_progress', () => {
                const result = (0, i18n_1.t)('agent.progress.status.in_progress');
                expect(result).toBe('IN PROGRESS');
            });
            it('should translate agent.progress.status.completed', () => {
                const result = (0, i18n_1.t)('agent.progress.status.completed');
                expect(result).toBe('COMPLETED');
            });
        });
        it('should return key if translation not found', () => {
            const result = (0, i18n_1.t)('nonexistent.key');
            expect(result).toBe('nonexistent.key');
        });
    });
    describe('getStatusEmoji', () => {
        it('should return 🔄 for in_progress', () => {
            expect((0, i18n_1.getStatusEmoji)('in_progress')).toBe('🔄');
        });
        it('should return ✅ for completed', () => {
            expect((0, i18n_1.getStatusEmoji)('completed')).toBe('✅');
        });
        it('should return ❌ for failed', () => {
            expect((0, i18n_1.getStatusEmoji)('failed')).toBe('❌');
        });
    });
    describe('formatSteps', () => {
        it('should format steps with action and risk', () => {
            const steps = [
                { action: 'Read file', risk: 'low' },
                { action: 'Write file', risk: 'medium' },
            ];
            const result = (0, i18n_1.formatSteps)(steps);
            expect(result).toBe('1. **Read file** (low risk)\n2. **Write file** (medium risk)');
        });
        it('should include target when present', () => {
            const steps = [
                { action: 'Delete file', risk: 'high', target: '/path/to/file.txt' },
            ];
            const result = (0, i18n_1.formatSteps)(steps);
            expect(result).toBe('1. **Delete file** (high risk) - /path/to/file.txt');
        });
        it('should handle empty array', () => {
            const result = (0, i18n_1.formatSteps)([]);
            expect(result).toBe('');
        });
    });
    describe('createProgressBar', () => {
        it('should create 0% progress bar', () => {
            const result = (0, i18n_1.createProgressBar)(0, 10);
            expect(result).toBe('[░░░░░░░░░░░░░░░░░░░░] 0%');
        });
        it('should create 50% progress bar', () => {
            const result = (0, i18n_1.createProgressBar)(5, 10);
            expect(result).toBe('[██████████░░░░░░░░░░] 50%');
        });
        it('should create 100% progress bar', () => {
            const result = (0, i18n_1.createProgressBar)(10, 10);
            expect(result).toBe('[████████████████████] 100%');
        });
        it('should handle 0 total gracefully', () => {
            const result = (0, i18n_1.createProgressBar)(0, 0);
            expect(result).toBe('[░░░░░░░░░░░░░░░░░░░░] 0%');
        });
    });
    describe('templates', () => {
        const requiredKeys = [
            'supervisor.runlog.title',
            'supervisor.runlog.body',
            'supervisor.approval.title',
            'supervisor.approval.body',
            'agent.progress.title',
            'observability.thread.title',
            'observability.report.body',
            'env.missing.github_token',
        ];
        it('should have all Japanese templates', () => {
            for (const key of requiredKeys) {
                expect(i18n_1.jaTemplates[key]).toBeDefined();
            }
        });
        it('should have all English templates', () => {
            for (const key of requiredKeys) {
                expect(i18n_1.enTemplates[key]).toBeDefined();
            }
        });
        it('should have matching keys in both locales', () => {
            const jaKeys = Object.keys(i18n_1.jaTemplates).sort();
            const enKeys = Object.keys(i18n_1.enTemplates).sort();
            expect(jaKeys).toEqual(enKeys);
        });
    });
});
