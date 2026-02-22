"use strict";
/**
 * CDP Browser Types
 *
 * Type definitions for Chrome DevTools Protocol integration.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_CDP_CONFIG = exports.detectCaptchaOrLogin = exports.CAPTCHA_PATTERNS = void 0;
/** Patterns that indicate CAPTCHA or login requirements */
exports.CAPTCHA_PATTERNS = [
    /captcha/i,
    /verify.*human/i,
    /are.*you.*robot/i,
    /security.*check/i,
    /prove.*not.*bot/i,
    /recaptcha/i,
    /hcaptcha/i,
    /cloudflare.*challenge/i,
    /access.*denied/i,
    /please.*sign.*in/i,
    /login.*required/i,
    /authentication.*required/i,
];
/** Check if content indicates CAPTCHA or login requirement */
function detectCaptchaOrLogin(title, content, url) {
    const combined = `${title} ${content} ${url}`.toLowerCase();
    for (const pattern of exports.CAPTCHA_PATTERNS) {
        if (pattern.test(combined)) {
            return {
                detected: true,
                reason: `Detected pattern: ${pattern.source}`,
            };
        }
    }
    return { detected: false };
}
exports.detectCaptchaOrLogin = detectCaptchaOrLogin;
exports.DEFAULT_CDP_CONFIG = {
    endpointUrl: 'http://127.0.0.1:9222',
    timeout: 10000,
    maxRetries: 3,
};
