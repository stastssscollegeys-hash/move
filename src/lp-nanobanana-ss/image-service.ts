// ===== LP NanoBanana SS - Image Generation Service =====
// Uses Gemini API (@google/genai) for image generation

import { GoogleGenAI, Modality } from '@google/genai';
import sharp from 'sharp';
import { SectionMeta } from './types';

const DEFAULT_MODEL = 'gemini-3-pro-image-preview';

export class ImageService {
  private ai: GoogleGenAI;
  private model: string;

  constructor(geminiApiKey: string, model?: string) {
    this.ai = new GoogleGenAI({ apiKey: geminiApiKey });
    this.model = model?.trim() || DEFAULT_MODEL;
  }

  /**
   * Generate a single section image using Gemini API.
   * Returns base64 PNG string resized to 1080px width.
   */
  async generateSectionImage(
    prompt: string,
    sectionMeta: SectionMeta,
  ): Promise<string> {
    console.log(`[LP-IMG] Generating section ${sectionMeta.id}: ${sectionMeta.nameJa} via ${this.model}`);

    const fullPrompt = `Generate a high-quality LP (landing page) section image.
Aspect ratio: ${sectionMeta.aspectRatio} (${sectionMeta.width}x${sectionMeta.height}px)
Style: ${sectionMeta.styleKeywords}

IMPORTANT: Generate the image only. Do not include any explanation text.

${prompt}`;

    // 120 second timeout per image
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('画像生成がタイムアウトしました（120秒）。もう一度お試しください。')), 120_000)
    );

    const response = await Promise.race([
      this.ai.models.generateContent({
        model: this.model,
        contents: fullPrompt,
        config: {
          responseModalities: [Modality.IMAGE, Modality.TEXT],
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
        const buffer = Buffer.from(part.inlineData.data!, 'base64');
        const resized = await this.resizeToWidth(buffer, 1080);
        return resized.toString('base64');
      }
    }

    throw new Error('Gemini APIから画像が返されませんでした。もう一度お試しください。');
  }

  /** Resize image buffer to target width, maintaining aspect ratio */
  private async resizeToWidth(buffer: Buffer, targetWidth: number): Promise<Buffer> {
    return sharp(buffer)
      .resize(targetWidth, null, { fit: 'inside', withoutEnlargement: false })
      .png()
      .toBuffer();
  }
}
