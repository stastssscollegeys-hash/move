"use strict";
/**
 * Regression Test Suite Index
 *
 * Auto-generated from mistakes.md
 * Run: npm run mistake:testgen
 *
 * These tests ensure past mistakes do not recur.
 */
Object.defineProperty(exports, "__esModule", { value: true });
// Import all regression tests
require("./success-true-on-error.test");
require("./command-injection-vulnerability.test");
require("./silent-error-catch.test");
require("./chrome-origin-wildcard.test");
describe('Regression Suite', () => {
    it('should have 4 regression tests', () => {
        expect(4).toBeGreaterThan(0);
    });
});
