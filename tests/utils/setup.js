"use strict";
/**
 * Integration Test Setup
 *
 * This file is executed before each integration test file.
 */
// Increase timeout for integration tests
jest.setTimeout(30000);
// Global test setup
beforeAll(async () => {
    // Setup test environment
    process.env.NODE_ENV = 'test';
    console.log('🧪 Integration test environment initialized');
});
// Global test teardown
afterAll(async () => {
    // Cleanup test environment
    console.log('🧹 Integration test cleanup completed');
});
// Global error handler for unhandled promises
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
