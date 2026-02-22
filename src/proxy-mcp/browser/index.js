"use strict";
/**
 * Browser Module - Chrome/Puppeteer integration for M4
 *
 * Exports:
 * - Web skills (read_url, extract_links, capture_dom_map)
 * - CAPTCHA detection utilities
 * - Types
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
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.webSkillizeFromTabs = exports.batchSkillizePreview = exports.batchSkillizeUrlBundle = exports.getUrlBundleStats = exports.normalizeUrlBundle = exports.listTabsUrls = exports.captureDomMap = exports.extractLinks = exports.readUrl = exports.checkBlockedPatterns = exports.guardCaptcha = exports.detectCaptcha = void 0;
__exportStar(require("./types"), exports);
var captcha_1 = require("./captcha");
Object.defineProperty(exports, "detectCaptcha", { enumerable: true, get: function () { return captcha_1.detectCaptcha; } });
Object.defineProperty(exports, "guardCaptcha", { enumerable: true, get: function () { return captcha_1.guardCaptcha; } });
Object.defineProperty(exports, "checkBlockedPatterns", { enumerable: true, get: function () { return captcha_1.checkBlockedPatterns; } });
var skills_1 = require("./skills");
Object.defineProperty(exports, "readUrl", { enumerable: true, get: function () { return skills_1.readUrl; } });
Object.defineProperty(exports, "extractLinks", { enumerable: true, get: function () { return skills_1.extractLinks; } });
Object.defineProperty(exports, "captureDomMap", { enumerable: true, get: function () { return skills_1.captureDomMap; } });
Object.defineProperty(exports, "listTabsUrls", { enumerable: true, get: function () { return skills_1.listTabsUrls; } });
Object.defineProperty(exports, "normalizeUrlBundle", { enumerable: true, get: function () { return skills_1.normalizeUrlBundle; } });
Object.defineProperty(exports, "getUrlBundleStats", { enumerable: true, get: function () { return skills_1.getUrlBundleStats; } });
Object.defineProperty(exports, "batchSkillizeUrlBundle", { enumerable: true, get: function () { return skills_1.batchSkillizeUrlBundle; } });
Object.defineProperty(exports, "batchSkillizePreview", { enumerable: true, get: function () { return skills_1.batchSkillizePreview; } });
Object.defineProperty(exports, "webSkillizeFromTabs", { enumerable: true, get: function () { return skills_1.webSkillizeFromTabs; } });
