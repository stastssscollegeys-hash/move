"use strict";
// ===== LP NanoBanana SS - Copy Generation Service =====
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.CopyService = void 0;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const prompts_1 = require("./prompts");
class CopyService {
    constructor(apiKey) {
        this.client = new sdk_1.default({
            apiKey,
            timeout: 90000, // 90 seconds timeout
        });
    }
    /**
     * Generate LP copy via Claude API (non-streaming for reliability).
     * Returns parsed 7-section copy.
     */
    async generate(productName, target, strength, lpType, onChunk, price, description) {
        const systemPrompt = (0, prompts_1.buildCopySystemPrompt)();
        const userPrompt = (0, prompts_1.buildCopyUserPrompt)(productName, target, strength, lpType, price, description);
        console.log('[LP-Copy] Sending request to Claude API (non-streaming)...');
        const startTime = Date.now();
        const response = await this.client.messages.create({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 2048,
            system: systemPrompt,
            messages: [{ role: 'user', content: userPrompt }],
        });
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log(`[LP-Copy] Response received in ${elapsed}s`);
        const text = response.content[0].type === 'text' ? response.content[0].text : '';
        // Send the complete text as a single chunk for preview
        if (text)
            onChunk(text);
        return this.parseResponse(text);
    }
    /** Extract JSON from AI response */
    parseResponse(raw) {
        // Remove markdown code fences
        const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
        const jsonStr = fenceMatch ? fenceMatch[1].trim() : raw;
        const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            throw new Error('AIの出力からJSONを抽出できませんでした');
        }
        const parsed = JSON.parse(jsonMatch[0]);
        // Validate all 7 sections exist
        const required = [
            'section1_fv', 'section2_problem', 'section3_solution',
            'section4_benefit', 'section5_testimonial', 'section6_pricing', 'section7_cta',
        ];
        for (const key of required) {
            if (!parsed[key] || typeof parsed[key] !== 'string') {
                throw new Error(`セクション ${key} が見つかりません`);
            }
        }
        return parsed;
    }
}
exports.CopyService = CopyService;
