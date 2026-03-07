"use strict";
// ===== LP NanoBanana SS - Image Generation Service =====
// Uses Gemini API (@google/genai) for image generation
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ImageService = void 0;
const genai_1 = require("@google/genai");
const sharp_1 = __importDefault(require("sharp"));
/** Gemini model for image generation (NanoBanana 2 / Gemini 3.1 Flash Image) */
const GEMINI_MODEL = 'gemini-3.1-flash-image-preview';
class ImageService {
    constructor(geminiApiKey) {
        this.ai = new genai_1.GoogleGenAI({ apiKey: geminiApiKey });
    }
    /**
     * Generate a single section image using Gemini API.
     * Returns base64 PNG string resized to 1080px width.
     */
    async generateSectionImage(prompt, sectionMeta) {
        console.log(`[LP-IMG] Generating section ${sectionMeta.id}: ${sectionMeta.nameJa} via Gemini API`);
        const fullPrompt = `Generate a high-quality LP (landing page) section image.
Aspect ratio: ${sectionMeta.aspectRatio} (${sectionMeta.width}x${sectionMeta.height}px)
Style: ${sectionMeta.styleKeywords}

IMPORTANT: Generate the image only. Do not include any explanation text.

${prompt}`;
        // 120 second timeout per image
        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('画像生成がタイムアウトしました（120秒）。もう一度お試しください。')), 120000));
        const response = await Promise.race([
            this.ai.models.generateContent({
                model: GEMINI_MODEL,
                contents: fullPrompt,
                config: {
                    responseModalities: [genai_1.Modality.IMAGE, genai_1.Modality.TEXT],
                },
            }),
            timeoutPromise,
        ]);
        // Extract image from response
        const parts = response.candidates?.[0]?.content?.parts;
        if (!parts) {
            throw new Error('Gemini APIから応答がありませんでした');
        }
        for (const part of parts) {
            if (part.inlineData?.mimeType?.startsWith('image/')) {
                const buffer = Buffer.from(part.inlineData.data, 'base64');
                const resized = await this.resizeToWidth(buffer, 1080);
                return resized.toString('base64');
            }
        }
        throw new Error('Gemini APIから画像が返されませんでした。もう一度お試しください。');
    }
    /** Resize image buffer to target width, maintaining aspect ratio */
    async resizeToWidth(buffer, targetWidth) {
        return (0, sharp_1.default)(buffer)
            .resize(targetWidth, null, { fit: 'inside', withoutEnlargement: false })
            .png()
            .toBuffer();
    }
}
exports.ImageService = ImageService;
