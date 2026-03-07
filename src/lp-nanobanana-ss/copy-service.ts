// ===== LP NanoBanana SS - Copy Generation Service =====

import Anthropic from '@anthropic-ai/sdk';
import { LPSections } from './types';
import { buildCopyFullPrompt } from './prompts';
import type { LPType } from './types';

export class CopyService {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  /**
   * Generate LP copy via Claude API (non-streaming for reliability).
   * Returns parsed 7-section copy.
   */
  async generate(
    productName: string,
    target: string,
    strength: string,
    lpType: LPType,
    onChunk: (text: string) => void,
    price?: string,
    description?: string,
  ): Promise<LPSections> {
    const fullPrompt = buildCopyFullPrompt(productName, target, strength, lpType, price, description);

    console.log('[LP-Copy] Sending request to Claude API...');
    const startTime = Date.now();

    // Use same pattern as handleParseInput (no timeout, no system param)
    const client = new Anthropic({ apiKey: this.apiKey });
    const response = await client.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 4096,
      messages: [{ role: 'user', content: fullPrompt }],
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[LP-Copy] Response received in ${elapsed}s`);

    const text = response.content[0].type === 'text' ? response.content[0].text : '';

    // Send the complete text as a single chunk for preview
    if (text) onChunk(text);

    return this.parseResponse(text);
  }

  /** Extract JSON from AI response */
  private parseResponse(raw: string): LPSections {
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

    return parsed as LPSections;
  }
}
