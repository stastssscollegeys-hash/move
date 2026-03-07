// ===== LP NanoBanana SS - Copy Generation Service =====

import Anthropic from '@anthropic-ai/sdk';
import { buildCopyFullPrompt } from './prompts';
import { LPType, getSectionDefs } from './types';

export class CopyService {
  private apiKey: string;
  private model: string;

  constructor(apiKey: string, model?: string) {
    this.apiKey = apiKey;
    this.model = model || 'claude-haiku-4-5-20251001';
  }

  /**
   * Generate LP copy via Claude API (non-streaming for reliability).
   * Returns parsed sections as Record<string, string> with dynamic keys.
   */
  async generate(
    productName: string,
    target: string,
    strength: string,
    lpType: LPType,
    onChunk: (text: string) => void,
    price?: string,
    description?: string,
    ctaText?: string,
  ): Promise<Record<string, string>> {
    const fullPrompt = buildCopyFullPrompt(productName, target, strength, lpType, price, description, ctaText);

    console.log(`[LP-Copy] Sending request to Claude API (model: ${this.model})...`);
    const startTime = Date.now();

    // Use same pattern as handleParseInput (no timeout, no system param)
    const client = new Anthropic({ apiKey: this.apiKey });
    const response = await client.messages.create({
      model: this.model,
      max_tokens: 4096,
      messages: [{ role: 'user', content: fullPrompt }],
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[LP-Copy] Response received in ${elapsed}s`);

    const text = response.content[0].type === 'text' ? response.content[0].text : '';

    // Send the complete text as a single chunk for preview
    if (text) onChunk(text);

    return this.parseResponse(text, lpType);
  }

  /** Extract JSON from AI response and validate sections */
  private parseResponse(raw: string, lpType: LPType): Record<string, string> {
    // Remove markdown code fences
    const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
    const jsonStr = fenceMatch ? fenceMatch[1].trim() : raw;

    const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('AIの出力からJSONを抽出できませんでした');
    }

    const parsed = JSON.parse(jsonMatch[0]);

    // Validate sections exist based on LP type
    const sectionDefs = getSectionDefs(lpType);
    for (const meta of sectionDefs) {
      const key = `section${meta.id}_${meta.name.replace(/-/g, '_')}`;
      if (!parsed[key] || typeof parsed[key] !== 'string') {
        console.warn(`[LP-Copy] Section ${key} (${meta.nameJa}) not found in response, using placeholder`);
        parsed[key] = meta.nameJa;
      }
    }

    return parsed as Record<string, string>;
  }
}
