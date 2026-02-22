"use strict";
/**
 * CAPTCHA Detection - Guardrails for browser automation
 *
 * Detects CAPTCHA/anti-bot patterns and returns require_human action
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.checkBlockedPatterns = exports.guardCaptcha = exports.detectCaptcha = void 0;
/**
 * CAPTCHA detection patterns (case-insensitive)
 */
const CAPTCHA_PATTERNS = [
    'captcha',
    'recaptcha',
    'hcaptcha',
    'cloudflare',
    'verify you are human',
    "verify you're human",
    "i'm not a robot",
    'please verify',
    'security check',
    'bot detection',
    'challenge-platform',
    'cf-turnstile',
    'cf-challenge',
    'challenge-running',
];
/**
 * Check if content contains CAPTCHA patterns
 */
function detectCaptcha(content) {
    const lowerContent = content.toLowerCase();
    for (const pattern of CAPTCHA_PATTERNS) {
        if (lowerContent.includes(pattern)) {
            return { detected: true, pattern };
        }
    }
    return { detected: false };
}
exports.detectCaptcha = detectCaptcha;
/**
 * Check page content and return require_human if CAPTCHA detected
 */
function guardCaptcha(content, url) {
    const check = detectCaptcha(content);
    if (check.detected) {
        return {
            success: false,
            action: 'require_human',
            reason: `CAPTCHA detected: "${check.pattern}"`,
            error: `CAPTCHA detected on ${url}. Manual intervention required.`,
            data: {
                url,
                detectedPattern: check.pattern,
                instructions: [
                    '1. Open the URL in a browser manually',
                    '2. Complete the CAPTCHA/verification',
                    '3. If you have access, provide the page content directly',
                    '4. Alternatively, try a different approach or URL',
                ],
            },
        };
    }
    return null;
}
exports.guardCaptcha = guardCaptcha;
/**
 * Check if URL is potentially blocked or requires authentication
 */
function checkBlockedPatterns(url) {
    const blocked = [
        'accounts.google.com',
        'login.',
        '/signin',
        '/login',
        'auth.',
        '/oauth',
    ];
    const lowerUrl = url.toLowerCase();
    for (const pattern of blocked) {
        if (lowerUrl.includes(pattern)) {
            return {
                success: false,
                action: 'require_human',
                reason: `Authentication required: URL contains "${pattern}"`,
                error: `This URL appears to require authentication. Manual login required.`,
                data: {
                    url,
                    detectedPattern: pattern,
                },
            };
        }
    }
    return null;
}
exports.checkBlockedPatterns = checkBlockedPatterns;
