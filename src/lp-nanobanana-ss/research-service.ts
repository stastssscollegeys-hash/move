// ===== LP NanoBanana SS - Reference LP Design Research Service =====
// Design-only analysis: extracts colors, layout, backgrounds from reference LP.
// Does NOT extract or reference the LP's copywriting content.

import puppeteer from 'puppeteer';
import Anthropic from '@anthropic-ai/sdk';
import { DesignSettings, DEFAULT_DESIGN, LPType, getSectionDefs } from './types';

export class ResearchService {
  private claudeClient: Anthropic;

  constructor(claudeApiKey: string) {
    this.claudeClient = new Anthropic({ apiKey: claudeApiKey });
  }

  /**
   * Analyze a reference LP URL for design elements only.
   * Returns DesignSettings with colors, layout, and section styles extracted from the reference.
   */
  async analyzeReferenceLP(url: string, lpType: LPType): Promise<{ design: DesignSettings; screenshotBase64: string }> {
    console.log('[LP-Research] Taking screenshot of reference LP:', url);

    // Take screenshot with puppeteer
    const screenshotBase64 = await this.takeScreenshot(url);

    console.log('[LP-Research] Analyzing design elements with Claude Vision...');

    // Analyze design with Claude Vision - explicitly design-only
    const design = await this.analyzeDesign(screenshotBase64, lpType);

    return { design, screenshotBase64 };
  }

  /** Take full-page screenshot of URL */
  private async takeScreenshot(url: string): Promise<string> {
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    try {
      const page = await browser.newPage();
      await page.setViewport({ width: 1280, height: 800 });
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

      // Wait for lazy-loaded images
      await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
      await new Promise(r => setTimeout(r, 2000));
      await page.evaluate('window.scrollTo(0, 0)');
      await new Promise(r => setTimeout(r, 500));

      const screenshot = await page.screenshot({
        fullPage: true,
        encoding: 'base64',
        type: 'png',
      });

      return screenshot as string;
    } finally {
      await browser.close();
    }
  }

  /** Analyze screenshot for design elements only using Claude Vision */
  private async analyzeDesign(screenshotBase64: string, lpType: LPType): Promise<DesignSettings> {
    // Build dynamic section_styles template from LP type definitions
    const sectionDefs = getSectionDefs(lpType);
    const sectionStylesExample: Record<string, string> = {};
    for (const meta of sectionDefs) {
      const key = `section_${meta.id}_${meta.name.replace(/-/g, '_')}`;
      sectionStylesExample[key] = `セクション${meta.id}（${meta.nameJa}）のビジュアルスタイル英語記述`;
    }
    const sectionStylesJson = JSON.stringify(sectionStylesExample, null, 4);

    const response = await this.claudeClient.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 4096,
      messages: [{
        role: 'user',
        content: [
          {
            type: 'image',
            source: {
              type: 'base64',
              media_type: 'image/png',
              data: screenshotBase64,
            },
          },
          {
            type: 'text',
            text: `このランディングページのスクリーンショットから、**デザイン要素のみ**を分析してください。

【重要】コピーライティングの内容（文章・キャッチコピー・セールスコピー）は一切抽出しないでください。
【絶対禁止】以下の要素は画像生成プロンプトに絶対に反映しないでください:
- タイムスタンプ・日時表示（「2024年○月○日」「残り○日」等の具体的な日付）
- 具体的な数値データ（「満足度98%」「○○人が参加」等）
- 個人名・企業名・ブランド名・ロゴ
- 認定マーク・資格バッジ・受賞歴の具体的な名称
- 電話番号・メールアドレス・住所等の連絡先情報
- 著作権表示・コピーライト表記

分析対象はビジュアルデザインのみです:
- 配色（背景色、アクセントカラー、テキストカラー、CTAボタンの色など）をHEXコードで
- レイアウト構造（カラム数、余白、セクション間隔の印象）
- セクションごとのビジュアルスタイル（背景パターン、装飾、カード形状など）

このLPは${sectionDefs.length}セクション構成です。以下のJSON形式で出力してください:

\`\`\`json
{
  "colors": {
    "primary": "#HEX",
    "accent": "#HEX",
    "cta_button": "#HEX",
    "cta_text": "#HEX",
    "background": "#HEX",
    "section_bg_alt": "#HEX",
    "heading_color": "#HEX",
    "body_text": "#HEX",
    "subtext": "#HEX"
  },
  "layout": {
    "max_width": "value",
    "content_width": "value",
    "heading_font_size": "value",
    "subheading_font_size": "value",
    "body_font_size": "value",
    "cta_font_size": "value",
    "cta_button_padding": "value",
    "cta_border_radius": "value",
    "section_padding_vertical": "value",
    "section_padding_horizontal": "value",
    "hero_height": "value",
    "section_gap": "value"
  },
  "section_styles": ${sectionStylesJson}
}
\`\`\`

section_stylesの各値は、色・背景・レイアウト・装飾のビジュアル記述のみにしてください。
コピー文言は絶対に含めないでください。`,
          },
        ],
      }],
    });

    // Extract JSON from response
    const text = response.content[0].type === 'text' ? response.content[0].text : '';
    const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    const jsonStr = fenceMatch ? fenceMatch[1].trim() : text;
    const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);

    if (!jsonMatch) {
      console.warn('[LP-Research] Failed to parse design analysis, using defaults');
      return DEFAULT_DESIGN;
    }

    try {
      const parsed = JSON.parse(jsonMatch[0]) as DesignSettings;
      // Merge with defaults for any missing fields
      return {
        colors: { ...DEFAULT_DESIGN.colors, ...parsed.colors },
        layout: { ...DEFAULT_DESIGN.layout, ...parsed.layout },
        section_styles: { ...DEFAULT_DESIGN.section_styles, ...parsed.section_styles },
      };
    } catch {
      console.warn('[LP-Research] JSON parse error, using defaults');
      return DEFAULT_DESIGN;
    }
  }
}
