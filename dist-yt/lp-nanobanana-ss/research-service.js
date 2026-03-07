"use strict";
// ===== LP NanoBanana SS - Reference LP Design Research Service =====
// Design-only analysis: extracts colors, layout, backgrounds from reference LP.
// Does NOT extract or reference the LP's copywriting content.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ResearchService = void 0;
const puppeteer_1 = __importDefault(require("puppeteer"));
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const types_1 = require("./types");
class ResearchService {
    constructor(claudeApiKey) {
        this.claudeClient = new sdk_1.default({ apiKey: claudeApiKey });
    }
    /**
     * Analyze a reference LP URL for design elements only.
     * Returns DesignSettings with colors, layout, and section styles extracted from the reference.
     */
    async analyzeReferenceLP(url) {
        console.log('[LP-Research] Taking screenshot of reference LP:', url);
        // Take screenshot with puppeteer
        const screenshotBase64 = await this.takeScreenshot(url);
        console.log('[LP-Research] Analyzing design elements with Claude Vision...');
        // Analyze design with Claude Vision - explicitly design-only
        const design = await this.analyzeDesign(screenshotBase64);
        return { design, screenshotBase64 };
    }
    /** Take full-page screenshot of URL */
    async takeScreenshot(url) {
        const browser = await puppeteer_1.default.launch({
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
            return screenshot;
        }
        finally {
            await browser.close();
        }
    }
    /** Analyze screenshot for design elements only using Claude Vision */
    async analyzeDesign(screenshotBase64) {
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
分析対象はビジュアルデザインのみです:
- 配色（背景色、アクセントカラー、テキストカラー、CTAボタンの色など）をHEXコードで
- レイアウト構造（カラム数、余白、セクション間隔の印象）
- セクションごとのビジュアルスタイル（背景パターン、装飾、カード形状など）

以下のJSON形式で出力してください:

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
  "section_styles": {
    "section_1_fv": "ビジュアルスタイルの英語記述（配色・背景・レイアウトのみ、コピー内容は含めない）",
    "section_2_problem": "...",
    "section_3_solution": "...",
    "section_4_benefit": "...",
    "section_5_testimonial": "...",
    "section_6_pricing": "...",
    "section_7_cta": "..."
  }
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
            return types_1.DEFAULT_DESIGN;
        }
        try {
            const parsed = JSON.parse(jsonMatch[0]);
            // Merge with defaults for any missing fields
            return {
                colors: { ...types_1.DEFAULT_DESIGN.colors, ...parsed.colors },
                layout: { ...types_1.DEFAULT_DESIGN.layout, ...parsed.layout },
                section_styles: { ...types_1.DEFAULT_DESIGN.section_styles, ...parsed.section_styles },
            };
        }
        catch {
            console.warn('[LP-Research] JSON parse error, using defaults');
            return types_1.DEFAULT_DESIGN;
        }
    }
}
exports.ResearchService = ResearchService;
