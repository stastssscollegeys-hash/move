"use strict";
/**
 * Tests for utf8-guard.ts
 *
 * UTF-8 validation and mojibake detection
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
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const os = __importStar(require("os"));
const utf8_guard_1 = require("../../scripts/text/utf8-guard");
describe('utf8-guard', () => {
    let tempDir;
    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'utf8-guard-test-'));
    });
    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
    });
    describe('isTextFile', () => {
        it('should identify TypeScript files', () => {
            expect((0, utf8_guard_1.isTextFile)('app.ts')).toBe(true);
            expect((0, utf8_guard_1.isTextFile)('component.tsx')).toBe(true);
        });
        it('should identify markdown files', () => {
            expect((0, utf8_guard_1.isTextFile)('README.md')).toBe(true);
            expect((0, utf8_guard_1.isTextFile)('docs/guide.md')).toBe(true);
        });
        it('should identify JSON files', () => {
            expect((0, utf8_guard_1.isTextFile)('package.json')).toBe(true);
            expect((0, utf8_guard_1.isTextFile)('config.json')).toBe(true);
        });
        it('should identify YAML files', () => {
            expect((0, utf8_guard_1.isTextFile)('config.yml')).toBe(true);
            expect((0, utf8_guard_1.isTextFile)('docker-compose.yaml')).toBe(true);
        });
        it('should reject binary files', () => {
            expect((0, utf8_guard_1.isTextFile)('image.png')).toBe(false);
            expect((0, utf8_guard_1.isTextFile)('video.mp4')).toBe(false);
            expect((0, utf8_guard_1.isTextFile)('archive.zip')).toBe(false);
        });
    });
    describe('validateUtf8', () => {
        it('should accept valid UTF-8', () => {
            const buffer = Buffer.from('Hello 世界 🌍', 'utf-8');
            expect((0, utf8_guard_1.validateUtf8)(buffer)).toEqual({ valid: true });
        });
        it('should accept Japanese text', () => {
            const buffer = Buffer.from('日本語テスト', 'utf-8');
            expect((0, utf8_guard_1.validateUtf8)(buffer)).toEqual({ valid: true });
        });
        it('should accept emoji', () => {
            const buffer = Buffer.from('🎉🎊🎁', 'utf-8');
            expect((0, utf8_guard_1.validateUtf8)(buffer)).toEqual({ valid: true });
        });
        it('should reject invalid UTF-8 sequences', () => {
            // Invalid continuation byte
            const invalidBuffer = Buffer.from([0xC0, 0x80]);
            const result = (0, utf8_guard_1.validateUtf8)(invalidBuffer);
            expect(result.valid).toBe(false);
            expect(result.error).toBeDefined();
        });
        it('should reject truncated UTF-8 sequences', () => {
            // Start of 3-byte sequence without continuation
            const truncatedBuffer = Buffer.from([0xE0, 0xA0]);
            const result = (0, utf8_guard_1.validateUtf8)(truncatedBuffer);
            expect(result.valid).toBe(false);
        });
    });
    describe('findReplacementChars', () => {
        it('should find U+FFFD positions', () => {
            const content = 'Hello\uFFFDWorld\uFFFD';
            const positions = (0, utf8_guard_1.findReplacementChars)(content);
            expect(positions).toEqual([5, 11]);
        });
        it('should return empty array for clean content', () => {
            const content = 'Hello 日本語 World';
            expect((0, utf8_guard_1.findReplacementChars)(content)).toEqual([]);
        });
        it('should detect multiple adjacent U+FFFD', () => {
            const content = '\uFFFD\uFFFD\uFFFD';
            expect((0, utf8_guard_1.findReplacementChars)(content)).toEqual([0, 1, 2]);
        });
    });
    describe('hasBom', () => {
        it('should detect UTF-8 BOM', () => {
            const bufferWithBom = Buffer.from([0xEF, 0xBB, 0xBF, 0x48, 0x65, 0x6C, 0x6C, 0x6F]);
            expect((0, utf8_guard_1.hasBom)(bufferWithBom)).toBe(true);
        });
        it('should return false for content without BOM', () => {
            const bufferWithoutBom = Buffer.from('Hello', 'utf-8');
            expect((0, utf8_guard_1.hasBom)(bufferWithoutBom)).toBe(false);
        });
        it('should handle empty buffer', () => {
            expect((0, utf8_guard_1.hasBom)(Buffer.from([]))).toBe(false);
        });
    });
    describe('removeBom', () => {
        it('should remove UTF-8 BOM', () => {
            const bufferWithBom = Buffer.from([0xEF, 0xBB, 0xBF, 0x48, 0x69]);
            const result = (0, utf8_guard_1.removeBom)(bufferWithBom);
            expect(result.toString('utf-8')).toBe('Hi');
        });
        it('should not modify content without BOM', () => {
            const bufferWithoutBom = Buffer.from('Hello', 'utf-8');
            const result = (0, utf8_guard_1.removeBom)(bufferWithoutBom);
            expect(result.toString('utf-8')).toBe('Hello');
        });
    });
    describe('getLineNumber', () => {
        it('should return correct line number', () => {
            const content = 'line1\nline2\nline3';
            expect((0, utf8_guard_1.getLineNumber)(content, 0)).toBe(1);
            expect((0, utf8_guard_1.getLineNumber)(content, 6)).toBe(2);
            expect((0, utf8_guard_1.getLineNumber)(content, 12)).toBe(3);
        });
        it('should handle single line', () => {
            const content = 'single line';
            expect((0, utf8_guard_1.getLineNumber)(content, 5)).toBe(1);
        });
    });
    describe('validateFile', () => {
        it('should pass valid UTF-8 file', () => {
            const filePath = path.join(tempDir, 'valid.txt');
            fs.writeFileSync(filePath, 'Hello 日本語 🌍', 'utf-8');
            const result = (0, utf8_guard_1.validateFile)(filePath);
            expect(result.valid).toBe(true);
            expect(result.errors).toHaveLength(0);
        });
        it('should fail file with U+FFFD', () => {
            const filePath = path.join(tempDir, 'mojibake.txt');
            fs.writeFileSync(filePath, 'Hello \uFFFD World', 'utf-8');
            const result = (0, utf8_guard_1.validateFile)(filePath);
            expect(result.valid).toBe(false);
            expect(result.errors[0]).toContain('U+FFFD');
        });
        it('should warn about BOM', () => {
            const filePath = path.join(tempDir, 'bom.txt');
            const contentWithBom = Buffer.concat([
                Buffer.from([0xEF, 0xBB, 0xBF]),
                Buffer.from('Hello', 'utf-8'),
            ]);
            fs.writeFileSync(filePath, contentWithBom);
            const result = (0, utf8_guard_1.validateFile)(filePath);
            expect(result.valid).toBe(true);
            expect(result.warnings).toContain('UTF-8 BOM detected (use --fix-bom to remove)');
        });
        it('should fix BOM when requested', () => {
            const filePath = path.join(tempDir, 'bom-fix.txt');
            const contentWithBom = Buffer.concat([
                Buffer.from([0xEF, 0xBB, 0xBF]),
                Buffer.from('Hello', 'utf-8'),
            ]);
            fs.writeFileSync(filePath, contentWithBom);
            const result = (0, utf8_guard_1.validateFile)(filePath, { fixBom: true });
            expect(result.warnings).toContain('UTF-8 BOM removed');
            const fixedContent = fs.readFileSync(filePath);
            expect((0, utf8_guard_1.hasBom)(fixedContent)).toBe(false);
        });
        it('should handle non-existent file', () => {
            const result = (0, utf8_guard_1.validateFile)('/non/existent/file.txt');
            expect(result.valid).toBe(false);
            expect(result.errors[0]).toContain('File not found');
        });
    });
    describe('runGuard', () => {
        it('should validate multiple files', () => {
            const file1 = path.join(tempDir, 'file1.txt');
            const file2 = path.join(tempDir, 'file2.txt');
            fs.writeFileSync(file1, 'Valid content', 'utf-8');
            fs.writeFileSync(file2, 'Also valid 日本語', 'utf-8');
            const summary = (0, utf8_guard_1.runGuard)([file1, file2]);
            expect(summary.total).toBe(2);
            expect(summary.passed).toBe(2);
            expect(summary.failed).toBe(0);
        });
        it('should count failures correctly', () => {
            const validFile = path.join(tempDir, 'valid.txt');
            const invalidFile = path.join(tempDir, 'invalid.txt');
            fs.writeFileSync(validFile, 'Valid', 'utf-8');
            fs.writeFileSync(invalidFile, 'Invalid \uFFFD', 'utf-8');
            const summary = (0, utf8_guard_1.runGuard)([validFile, invalidFile]);
            expect(summary.passed).toBe(1);
            expect(summary.failed).toBe(1);
        });
    });
});
