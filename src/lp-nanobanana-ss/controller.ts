// ===== LP NanoBanana SS - Controller (Polling) =====

import { Request, Response } from 'express';
import Anthropic from '@anthropic-ai/sdk';
import crypto from 'crypto';
import { LPGenerateRequest, RetrySectionRequest, JobState, SectionStatus, DEFAULT_DESIGN, LPType, getSectionDefs } from './types';
import { CopyService } from './copy-service';
import { ResearchService } from './research-service';
import { ImageService } from './image-service';
import { buildAllImagePrompts } from './prompts';

const MAX_PRODUCT_NAME = 100;
const MAX_TARGET = 200;
const MAX_STRENGTH = 500;

/** In-memory job store */
const jobStore = new Map<string, JobState>();

/** Auto-cleanup completed/errored jobs older than 30 minutes */
setInterval(() => {
  const now = Date.now();
  for (const [id, job] of jobStore) {
    // Only clean up finished jobs — never delete active ones
    if ((job.phase === 'done' || job.phase === 'error') && now - job.startedAt > 30 * 60 * 1000) {
      jobStore.delete(id);
    }
  }
}, 5 * 60 * 1000);

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

/** POST /api/generate — Start LP generation, return jobId immediately */
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

  // --- Create job with dynamic sections ---
  const lpType: LPType = body.lpType || 'education';
  const sectionDefs = getSectionDefs(lpType);
  const jobId = crypto.randomUUID();
  const initSections: Record<number, SectionStatus> = {};
  for (const meta of sectionDefs) {
    initSections[meta.id] = { status: 'waiting' };
  }

  const job: JobState = {
    jobId,
    lpType,
    phase: 'copy',
    statusText: 'コピー生成開始...',
    copyText: '',
    sections: initSections,
    imagesCompleted: 0,
    imagesTotal: sectionDefs.length,
    startedAt: Date.now(),
  };
  jobStore.set(jobId, job);

  // Return jobId and section info immediately
  res.json({
    success: true,
    jobId,
    lpType,
    sectionDefs: sectionDefs.map(m => ({ id: m.id, name: m.name, nameJa: m.nameJa })),
  });

  // --- Run generation in background ---
  runGeneration(job, body).catch(err => {
    console.error('[LP-NB] Background generation fatal error:', err);
    job.phase = 'error';
    job.error = classifyError(err);
    job.statusText = job.error;
  });
}

/** POST /api/cancel/:jobId — Cancel a running job */
export function handleCancelJob(req: Request, res: Response): void {
  const { jobId } = req.params;
  const job = jobStore.get(jobId);

  if (!job) {
    res.status(404).json({ success: false, error: 'ジョブが見つかりません' });
    return;
  }

  if (job.phase === 'done' || job.phase === 'error') {
    res.json({ success: true, message: 'ジョブは既に終了しています' });
    return;
  }

  // Mark job as cancelled (error phase with special message)
  job.phase = 'error';
  job.error = 'ユーザーにより停止されました';
  job.statusText = '生成を停止しました';
  console.log(`[LP-NB] Job ${jobId} cancelled by user`);

  res.json({ success: true, message: '生成を停止しました' });
}

/** Background generation pipeline */
async function runGeneration(job: JobState, body: LPGenerateRequest): Promise<void> {
  const lpType = job.lpType;
  const sectionDefs = getSectionDefs(lpType);
  const totalSections = sectionDefs.length;

  try {
    // ===== Phase 1: Copy Generation =====
    console.log('[LP-NB] Phase 1: Starting copy generation...');
    job.statusText = 'Claude APIにリクエスト送信中...';

    const copyService = new CopyService(body.claudeApiKey.trim(), body.claudeModel?.trim());
    const phase1Start = Date.now();

    const copySections = await copyService.generate(
      body.productName.trim(),
      body.target.trim(),
      body.strength.trim(),
      lpType,
      (chunk) => {
        const elapsed = ((Date.now() - phase1Start) / 1000).toFixed(1);
        job.statusText = `応答受信 (${elapsed}秒)、JSON解析中...`;
        job.copyText = chunk;
      },
      body.price?.trim(),
      body.description?.trim(),
      body.ctaText?.trim(),
    );

    const phase1Elapsed = ((Date.now() - phase1Start) / 1000).toFixed(1);
    console.log(`[LP-NB] Phase 1: Copy generation complete in ${phase1Elapsed}s`);
    job.statusText = `コピー生成完了 (${phase1Elapsed}秒)`;

    // ===== Phase 2: Design Research =====
    job.phase = 'design';
    let design = DEFAULT_DESIGN;

    if (body.referenceUrl?.trim()) {
      try {
        job.statusText = '参考LP分析中...';
        const researchService = new ResearchService(body.claudeApiKey.trim());
        const result = await researchService.analyzeReferenceLP(body.referenceUrl.trim(), lpType);
        design = result.design;
        job.statusText = '参考LP分析完了';
      } catch (err) {
        console.error('[LP-Research] Research failed, using defaults:', err);
        job.statusText = '参考LP分析失敗、デフォルトデザイン使用';
      }
    } else {
      try {
        job.statusText = '自動デザイン分析中...';
        const designClient = new Anthropic({ apiKey: body.claudeApiKey.trim() });

        // Build dynamic section style request
        const sectionStyleFields = sectionDefs
          .map(m => `    "section_${m.id}_${m.name.replace(/-/g, '_')}": "${m.nameJa}セクションのスタイル"`)
          .join(',\n');

        const designResponse = await designClient.messages.create({
          model: body.claudeModel?.trim() || 'claude-haiku-4-5-20251001',
          max_tokens: 2000,
          messages: [{
            role: 'user',
            content: `以下の商品情報に最適なLP（ランディングページ）のデザイン設定をJSON形式で提案してください。

商品名: ${body.productName.trim()}
ターゲット: ${body.target.trim()}
強み・特徴: ${body.strength.trim()}
${body.price ? `価格: ${body.price.trim()}` : ''}
${body.description ? `詳細: ${body.description.trim()}` : ''}
LPタイプ: ${lpType}

この分野・ターゲットに最もマッチする配色とスタイルを提案してください。
※タイムスタンプ・日付・具体的な数値・個人名・企業名・認定マーク等の具体的コンテンツは含めないでください。純粋なビジュアルスタイルのみ提案してください。
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
${sectionStyleFields}
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
          design = {
            colors: { ...DEFAULT_DESIGN.colors, ...parsed.colors },
            layout: DEFAULT_DESIGN.layout,
            section_styles: { ...DEFAULT_DESIGN.section_styles, ...parsed.section_styles },
          };
          console.log('[LP-Research] Auto-design generated for:', body.productName.trim());
        }
        job.statusText = 'デザイン分析完了';
      } catch (err) {
        console.error('[LP-Research] Auto-design failed, using defaults:', err);
        job.statusText = 'デザイン分析失敗、デフォルト使用';
      }
    }

    // ===== Phase 3: Image Generation =====
    job.phase = 'image';
    console.log(`[LP-NB] Phase 3: Starting image generation (${totalSections} sections)...`);
    const imageService = new ImageService(body.geminiApiKey.trim(), body.geminiModel);

    // copySections is Record<string, string> keyed by section key
    const imagePrompts = buildAllImagePrompts(copySections as any, design, lpType, body.ctaText?.trim());

    for (const { sectionMeta, prompt } of imagePrompts) {
      // Check if job was cancelled (phase may be changed externally by cancel handler)
      if ((job.phase as string) === 'error') {
        console.log(`[LP-NB] Job ${job.jobId} cancelled, stopping image generation`);
        return;
      }

      job.sections[sectionMeta.id] = { status: 'generating' };
      job.statusText = `${sectionMeta.id}/${totalSections}: ${sectionMeta.nameJa} 生成中...`;

      try {
        const base64 = await imageService.generateSectionImage(prompt, sectionMeta);

        // Check again after async operation
        if ((job.phase as string) === 'error') {
          console.log(`[LP-NB] Job ${job.jobId} cancelled during image generation`);
          return;
        }

        job.sections[sectionMeta.id] = { status: 'complete', base64, prompt };
        job.imagesCompleted++;
        console.log(`[LP-IMG] Section ${sectionMeta.id} complete (${job.imagesCompleted}/${totalSections})`);
      } catch (err) {
        if ((job.phase as string) === 'error') return; // cancelled
        console.error(`[LP-IMG] Section ${sectionMeta.id} failed:`, err);
        job.sections[sectionMeta.id] = {
          status: 'error',
          error: classifyError(err),
          prompt,
        };
      }
    }

    // ===== Done =====
    job.phase = 'done';
    const totalCompleted = Object.values(job.sections).filter(s => s.status === 'complete').length;
    const totalFailed = Object.values(job.sections).filter(s => s.status === 'error').length;
    job.statusText = `完了! ${totalCompleted}/${totalSections}セクション成功${totalFailed > 0 ? ` (${totalFailed}件失敗)` : ''}`;
    console.log(`[LP-NB] All done: ${totalCompleted} success, ${totalFailed} failed`);

  } catch (err) {
    console.error('[LP-NanoBanana] Generation error:', err);
    job.phase = 'error';
    job.error = classifyError(err);
    job.statusText = job.error;
  }
}

/** GET /api/status/:jobId — Poll job status */
export function handleGetStatus(req: Request, res: Response): void {
  const { jobId } = req.params;
  const job = jobStore.get(jobId);

  if (!job) {
    res.status(404).json({ success: false, error: 'ジョブが見つかりません' });
    return;
  }

  // Return job state (without base64 for sections that haven't changed)
  const receivedSections = req.query.received
    ? (req.query.received as string).split(',').map(Number)
    : [];

  const sectionsResponse: Record<number, SectionStatus> = {};
  for (const [idStr, sec] of Object.entries(job.sections)) {
    const id = parseInt(idStr);
    if (sec.status === 'complete' && receivedSections.includes(id)) {
      // Client already has this image — send status only, skip base64 but keep prompt
      sectionsResponse[id] = { status: 'complete', prompt: sec.prompt };
    } else {
      sectionsResponse[id] = { ...sec };
    }
  }

  res.json({
    success: true,
    data: {
      jobId: job.jobId,
      lpType: job.lpType,
      phase: job.phase,
      statusText: job.statusText,
      copyText: job.copyText,
      sections: sectionsResponse,
      imagesCompleted: job.imagesCompleted,
      imagesTotal: job.imagesTotal,
      error: job.error,
      elapsed: Math.floor((Date.now() - job.startedAt) / 1000),
    },
  });
}

/** POST /api/retry-section — Retry a single failed section */
export async function handleRetrySection(req: Request, res: Response): Promise<void> {
  const body = req.body as RetrySectionRequest;

  if (!body.prompt?.trim()) {
    res.status(400).json({ success: false, error: 'プロンプトが必要です' });
    return;
  }
  if (!body.sectionId || body.sectionId < 1) {
    res.status(400).json({ success: false, error: 'セクションIDが必要です' });
    return;
  }
  if (!body.geminiApiKey?.trim()) {
    res.status(400).json({ success: false, error: 'Gemini APIキーが必要です' });
    return;
  }

  const lpType: LPType = body.lpType || 'education';
  const sectionDefs = getSectionDefs(lpType);
  const sectionMeta = sectionDefs.find(s => s.id === body.sectionId);
  if (!sectionMeta) {
    res.status(400).json({ success: false, error: '無効なセクションIDです' });
    return;
  }

  try {
    const imageService = new ImageService(body.geminiApiKey.trim(), body.geminiModel);
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
