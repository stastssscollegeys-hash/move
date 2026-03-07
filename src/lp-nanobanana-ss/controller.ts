// ===== LP NanoBanana SS - Controller (SSE) =====

import { Request, Response } from 'express';
import Anthropic from '@anthropic-ai/sdk';
import { LPGenerateRequest, RetrySectionRequest, ParseInputRequest, SSEEvent, DEFAULT_DESIGN, SECTION_DEFS } from './types';
import { CopyService } from './copy-service';
import { ResearchService } from './research-service';
import { ImageService } from './image-service';
import { buildAllImagePrompts } from './prompts';

const MAX_PRODUCT_NAME = 100;
const MAX_TARGET = 200;
const MAX_STRENGTH = 500;

/** Send SSE event */
function sendSSE(res: Response, event: SSEEvent): void {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

/** Classify error for user-friendly message */
function classifyError(err: unknown): string {
  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes('401') || msg.includes('authentication') || msg.includes('invalid'))
      return 'APIキーが無効です。正しいキーを設定してください。';
    if (msg.includes('429') || msg.includes('rate limit'))
      return 'APIレート制限に達しました。しばらくしてから再度お試しください。';
    if (msg.includes('JSON'))
      return 'AIの出力解析に失敗しました。もう一度お試しください。';
    if (msg.includes('タイムアウト'))
      return msg;
    return `エラー: ${msg}`;
  }
  return 'サーバー内部エラーが発生しました';
}

/** POST /api/generate — Full LP generation with SSE streaming */
export async function handleGenerate(req: Request, res: Response): Promise<void> {
  const body = req.body as LPGenerateRequest;

  // --- Validation ---
  if (!body.productName?.trim()) {
    res.status(400).json({ success: false, error: '商品名を入力してください' });
    return;
  }
  if (!body.target?.trim()) {
    res.status(400).json({ success: false, error: 'ターゲットを入力してください' });
    return;
  }
  if (!body.strength?.trim()) {
    res.status(400).json({ success: false, error: '強み・特徴を入力してください' });
    return;
  }
  if (body.productName.length > MAX_PRODUCT_NAME) {
    res.status(400).json({ success: false, error: `商品名は${MAX_PRODUCT_NAME}文字以内で入力してください` });
    return;
  }
  if (body.target.length > MAX_TARGET) {
    res.status(400).json({ success: false, error: `ターゲットは${MAX_TARGET}文字以内で入力してください` });
    return;
  }
  if (body.strength.length > MAX_STRENGTH) {
    res.status(400).json({ success: false, error: `強み・特徴は${MAX_STRENGTH}文字以内で入力してください` });
    return;
  }
  if (!body.claudeApiKey?.trim()) {
    res.status(400).json({ success: false, error: 'Claude APIキーを設定してください' });
    return;
  }
  if (!body.geminiApiKey?.trim()) {
    res.status(400).json({ success: false, error: 'Gemini APIキーを設定してください' });
    return;
  }

  // --- SSE Setup ---
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  let closed = false;
  req.on('close', () => { closed = true; });

  try {
    // Send immediate SSE event so frontend knows processing started
    sendSSE(res, { type: 'copy_chunk', data: '', timestamp: Date.now() });

    // ===== Phase 1: Copy Generation =====
    console.log('[LP-NB] Phase 1: Starting copy generation...');
    const copyService = new CopyService(body.claudeApiKey.trim());

    const sections = await copyService.generate(
      body.productName.trim(),
      body.target.trim(),
      body.strength.trim(),
      body.lpType || 'education',
      (chunk) => {
        if (!closed) sendSSE(res, { type: 'copy_chunk', data: chunk, timestamp: Date.now() });
      },
      body.price?.trim(),
      body.description?.trim(),
    );
    console.log('[LP-NB] Phase 1: Copy generation complete');

    if (closed) return;
    sendSSE(res, { type: 'copy_complete', data: sections, timestamp: Date.now() });

    // ===== Phase 2: Design Research =====
    let design = DEFAULT_DESIGN;

    if (body.referenceUrl?.trim()) {
      // URL provided — analyze reference LP
      try {
        sendSSE(res, { type: 'research_start', data: { url: body.referenceUrl.trim() }, timestamp: Date.now() });

        const researchService = new ResearchService(body.claudeApiKey.trim());
        const result = await researchService.analyzeReferenceLP(body.referenceUrl.trim());
        design = result.design;

        if (!closed) {
          sendSSE(res, { type: 'research_complete', data: { design }, timestamp: Date.now() });
        }
      } catch (err) {
        console.error('[LP-Research] Research failed, using defaults:', err);
        if (!closed) {
          sendSSE(res, {
            type: 'research_complete',
            data: { design: DEFAULT_DESIGN, warning: '参考LP分析に失敗しました。デフォルトデザインを使用します。' },
            timestamp: Date.now(),
          });
        }
      }
    } else {
      // No URL — generate field-appropriate design from product info
      try {
        sendSSE(res, { type: 'research_start', data: { mode: 'auto-design' }, timestamp: Date.now() });

        const designClient = new Anthropic({ apiKey: body.claudeApiKey.trim() });
        const designResponse = await designClient.messages.create({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 1500,
          messages: [{
            role: 'user',
            content: `以下の商品情報に最適なLP（ランディングページ）のデザイン設定をJSON形式で提案してください。

商品名: ${body.productName.trim()}
ターゲット: ${body.target.trim()}
強み・特徴: ${body.strength.trim()}
${body.price ? `価格: ${body.price.trim()}` : ''}
${body.description ? `詳細: ${body.description.trim()}` : ''}
LPタイプ: ${body.lpType || 'education'}

この分野・ターゲットに最もマッチする配色とスタイルを提案してください。
例えば:
- ビジネス系 → 信頼感のある紺・青系
- 美容・健康系 → 柔らかいピンク・グリーン系
- テクノロジー系 → モダンな黒・紫系
- 教育系 → 知的な青・白系
- 副業・投資系 → ゴールド・ダークブルー系

以下のJSON形式で返してください（マークダウンのコードブロックで囲んでOK）:

\`\`\`json
{
  "colors": {
    "primary": "#HEX",
    "accent": "#HEX",
    "cta_button": "#HEX",
    "cta_text": "#FFFFFF",
    "background": "#HEX",
    "section_bg_alt": "#HEX",
    "heading_color": "#HEX",
    "body_text": "#HEX",
    "subtext": "#HEX"
  },
  "section_styles": {
    "section_1_fv": "この商品に合ったFVスタイルの説明",
    "section_2_problem": "問題提起セクションのスタイル",
    "section_3_solution": "解決策セクションのスタイル",
    "section_4_benefit": "ベネフィットセクションのスタイル",
    "section_5_testimonial": "お客様の声セクションのスタイル",
    "section_6_pricing": "特典・料金セクションのスタイル",
    "section_7_cta": "CTAセクションのスタイル"
  }
}
\`\`\`

JSONのみ返してください。`,
          }],
        });

        const designText = designResponse.content[0].type === 'text' ? designResponse.content[0].text : '';
        const fenceMatch = designText.match(/```(?:json)?\s*([\s\S]*?)```/);
        const jsonStr = fenceMatch ? fenceMatch[1].trim() : designText;
        const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);

        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          // Merge with defaults (keep layout from DEFAULT_DESIGN, override colors and styles)
          design = {
            colors: { ...DEFAULT_DESIGN.colors, ...parsed.colors },
            layout: DEFAULT_DESIGN.layout,
            section_styles: { ...DEFAULT_DESIGN.section_styles, ...parsed.section_styles },
          };
          console.log('[LP-Research] Auto-design generated for field:', body.productName.trim());
        }

        if (!closed) {
          sendSSE(res, { type: 'research_complete', data: { design, mode: 'auto-design' }, timestamp: Date.now() });
        }
      } catch (err) {
        console.error('[LP-Research] Auto-design failed, using defaults:', err);
        if (!closed) {
          sendSSE(res, {
            type: 'research_complete',
            data: { design: DEFAULT_DESIGN, mode: 'default' },
            timestamp: Date.now(),
          });
        }
      }
    }

    if (closed) return;

    // ===== Phase 3: Image Generation (Gemini API) =====
    console.log('[LP-NB] Phase 3: Starting image generation...');
    const imageService = new ImageService(body.geminiApiKey.trim());
    const imagePrompts = buildAllImagePrompts(sections, design);
    const results: { id: number; base64?: string; error?: string }[] = [];

    for (const { sectionMeta, prompt } of imagePrompts) {
      if (closed) return;

      sendSSE(res, {
        type: 'image_start',
        data: { id: sectionMeta.id, name: sectionMeta.nameJa },
        timestamp: Date.now(),
      });

      try {
        const base64 = await imageService.generateSectionImage(prompt, sectionMeta);
        results.push({ id: sectionMeta.id, base64 });

        if (!closed) {
          sendSSE(res, {
            type: 'image_complete',
            data: {
              id: sectionMeta.id,
              name: sectionMeta.nameJa,
              base64,
              progress: `${results.filter(r => r.base64).length}/${SECTION_DEFS.length}`,
            },
            timestamp: Date.now(),
          });
        }
      } catch (err) {
        console.error(`[LP-IMG] Section ${sectionMeta.id} failed:`, err);
        results.push({ id: sectionMeta.id, error: classifyError(err) });

        if (!closed) {
          sendSSE(res, {
            type: 'image_error',
            data: {
              id: sectionMeta.id,
              name: sectionMeta.nameJa,
              error: classifyError(err),
              prompt,
            },
            timestamp: Date.now(),
          });
        }
      }
    }

    if (!closed) {
      sendSSE(res, {
        type: 'all_complete',
        data: {
          total: SECTION_DEFS.length,
          success: results.filter(r => r.base64).length,
          failed: results.filter(r => r.error).length,
        },
        timestamp: Date.now(),
      });
    }
  } catch (err) {
    console.error('[LP-NanoBanana] Generation error:', err);
    if (!closed) {
      sendSSE(res, { type: 'error', data: classifyError(err), timestamp: Date.now() });
    }
  } finally {
    if (!closed) res.end();
  }
}

/** POST /api/retry-section — Retry a single failed section */
export async function handleRetrySection(req: Request, res: Response): Promise<void> {
  const body = req.body as RetrySectionRequest;

  if (!body.prompt?.trim()) {
    res.status(400).json({ success: false, error: 'プロンプトが必要です' });
    return;
  }
  if (!body.sectionId || body.sectionId < 1 || body.sectionId > 7) {
    res.status(400).json({ success: false, error: 'セクションID (1-7) が必要です' });
    return;
  }
  if (!body.geminiApiKey?.trim()) {
    res.status(400).json({ success: false, error: 'Gemini APIキーが必要です' });
    return;
  }

  const sectionMeta = SECTION_DEFS.find(s => s.id === body.sectionId);
  if (!sectionMeta) {
    res.status(400).json({ success: false, error: '無効なセクションIDです' });
    return;
  }

  try {
    const imageService = new ImageService(body.geminiApiKey.trim());
    const base64 = await imageService.generateSectionImage(body.prompt.trim(), sectionMeta);

    res.json({
      success: true,
      data: { id: body.sectionId, name: sectionMeta.nameJa, base64 },
    });
  } catch (err) {
    console.error(`[LP-IMG] Retry section ${body.sectionId} failed:`, err);
    res.status(500).json({ success: false, error: classifyError(err) });
  }
}

/** POST /api/parse-input — Parse bulk input text into structured product info */
export async function handleParseInput(req: Request, res: Response): Promise<void> {
  const body = req.body as { rawText: string; claudeApiKey: string };

  if (!body.rawText?.trim()) {
    res.status(400).json({ success: false, error: 'テキストを入力してください' });
    return;
  }
  if (!body.claudeApiKey?.trim()) {
    res.status(400).json({ success: false, error: 'Claude APIキーを設定してください' });
    return;
  }

  try {
    const client = new Anthropic({ apiKey: body.claudeApiKey.trim() });

    const response = await client.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 1024,
      messages: [{
        role: 'user',
        content: `以下のテキストから商品情報を抽出してJSON形式で返してください。
テキストが曖昧な場合は、推測して最も適切な値を入れてください。

\`\`\`json
{
  "productName": "商品名・サービス名",
  "target": "ターゲット（想定顧客・ペルソナ）",
  "strength": "強み・特徴・差別化ポイント",
  "price": "価格（記載があれば）",
  "description": "詳細説明（追加情報）"
}
\`\`\`

price と description は情報がなければ空文字にしてください。
JSONのみ返してください（マークダウンのコードブロックで囲んでOK）。

---

入力テキスト:
${body.rawText.trim()}`,
      }],
    });

    const text = response.content[0].type === 'text' ? response.content[0].text : '';
    const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    const jsonStr = fenceMatch ? fenceMatch[1].trim() : text;
    const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);

    if (!jsonMatch) {
      res.status(500).json({ success: false, error: '解析結果の取得に失敗しました' });
      return;
    }

    const parsed = JSON.parse(jsonMatch[0]);
    res.json({ success: true, data: parsed });
  } catch (err) {
    console.error('[LP-Parse] Parse input failed:', err);
    res.status(500).json({ success: false, error: classifyError(err) });
  }
}

/** POST /api/test-keys — Test API keys before generation */
export async function handleTestKeys(req: Request, res: Response): Promise<void> {
  const { claudeApiKey, geminiApiKey } = req.body as { claudeApiKey?: string; geminiApiKey?: string };

  const results: { claude?: { ok: boolean; error?: string; ms?: number }; gemini?: { ok: boolean; error?: string; ms?: number } } = {};

  // Test Claude API key
  if (claudeApiKey?.trim()) {
    const start = Date.now();
    try {
      const client = new Anthropic({ apiKey: claudeApiKey.trim(), timeout: 15_000 });
      await client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 10,
        messages: [{ role: 'user', content: 'test' }],
      });
      results.claude = { ok: true, ms: Date.now() - start };
    } catch (err: any) {
      results.claude = { ok: false, error: classifyError(err), ms: Date.now() - start };
    }
  }

  // Test Gemini API key
  if (geminiApiKey?.trim()) {
    const start = Date.now();
    try {
      const { GoogleGenAI } = require('@google/genai');
      const ai = new GoogleGenAI({ apiKey: geminiApiKey.trim() });
      await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: 'test',
      });
      results.gemini = { ok: true, ms: Date.now() - start };
    } catch (err: any) {
      results.gemini = { ok: false, error: classifyError(err), ms: Date.now() - start };
    }
  }

  res.json({ success: true, data: results });
}

/** GET /api/health */
export function handleHealth(_req: Request, res: Response): void {
  res.json({ status: 'OK', service: 'lp-nanobanana-ss' });
}
