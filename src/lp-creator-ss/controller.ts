// ===== LP Creator SS - Controller =====

import { Request, Response } from 'express';
import { LPCreatorService } from './service';
import { LPGenerateRequest, SSEEvent } from './types';
import { loadSettings, saveSettings, getEffectiveApiKey, LPCreatorSettings } from './settings-store';

const MAX_PRODUCT_NAME = 100;
const MAX_TARGET = 200;
const MAX_STRENGTH = 300;

/** Send an SSE event to the client */
function sendSSE(res: Response, event: SSEEvent): void {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

/** Extract user-friendly error message */
function classifyError(err: unknown): { status: number; message: string } {
  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes('401') || msg.includes('authentication') || msg.includes('invalid x-api-key'))
      return { status: 401, message: 'APIキーが無効です。管理画面で正しいキーを設定してください。' };
    if (msg.includes('429') || msg.includes('rate limit'))
      return { status: 429, message: 'APIレート制限に達しました。しばらくしてから再度お試しください。' };
    if (msg.includes('JSON'))
      return { status: 502, message: 'AIの出力解析に失敗しました。もう一度お試しください。' };
    return { status: 500, message: `エラーが発生しました: ${msg}` };
  }
  return { status: 500, message: 'サーバー内部エラーが発生しました' };
}

/** POST /api/generate — SSE streaming LP generation */
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

  // Check that API key is available (settings or env)
  if (!getEffectiveApiKey()) {
    res.status(400).json({ success: false, error: 'APIキーが設定されていません。管理画面（/lp-creator/settings）で設定してください。' });
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
    const service = new LPCreatorService();

    const copy = await service.generateLP(
      {
        productName: body.productName.trim(),
        target: body.target.trim(),
        strength: body.strength.trim(),
      },
      (chunk) => {
        if (!closed) {
          sendSSE(res, { type: 'chunk', data: chunk, timestamp: Date.now() });
        }
      },
    );

    if (!closed) {
      const html = service.renderHTML(copy);
      sendSSE(res, { type: 'complete', data: html, timestamp: Date.now() });
    }
  } catch (err) {
    console.error('[LP Creator] Generation error:', err);
    if (!closed) {
      const { message } = classifyError(err);
      sendSSE(res, { type: 'error', data: message, timestamp: Date.now() });
    }
  } finally {
    if (!closed) {
      res.end();
    }
  }
}

/** POST /api/generate-demo — API不要のテスト生成（デモデータでストリーミング風に返す） */
export async function handleGenerateDemo(req: Request, res: Response): Promise<void> {
  const body = req.body as LPGenerateRequest;

  const productName = body.productName?.trim() || 'サンプル商品';
  const target = body.target?.trim() || '30代の個人起業家';
  const strength = body.strength?.trim() || '簡単・高品質・低コスト';

  // SSE Setup
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  let closed = false;
  req.on('close', () => { closed = true; });

  // デモ用コピーJSON（入力値を反映）
  const demoCopy = {
    heroHeadline: `${productName}で、あなたの未来が変わる`,
    heroSubheadline: `${target}のために生まれた、新しいソリューション`,
    heroCta: '今すぐ無料で試す',
    problemSection: [
      '何から始めればいいかわからず、時間だけが過ぎていく',
      '色々試したけど、思うような成果が出ない',
      '専門家に頼みたいが、費用が高すぎて手が出ない',
    ],
    solutionSection: `${productName}は、${strength}という圧倒的な強みで、${target}が抱える課題を根本から解決します。もう一人で悩む必要はありません。`,
    benefitsSection: [
      { title: '驚くほど簡単', description: '複雑な知識は一切不要。3ステップで誰でもすぐに始められます。' },
      { title: '圧倒的なコスパ', description: '従来の方法と比べて、コストを大幅に削減しながら高品質な成果を実現。' },
      { title: '万全のサポート', description: '困ったときはいつでも相談OK。あなたの成功を最後までサポートします。' },
    ],
    socialProofSection: [
      { name: 'M.T.様 30代 個人起業家', text: `${productName}を使い始めてから、作業効率が3倍になりました。もっと早く出会いたかったです。` },
      { name: 'K.S.様 40代 コンサルタント', text: 'クライアントからの評価が一気に上がりました。プロに頼んだのかと聞かれるクオリティです。' },
    ],
    featuresSection: [
      { title: 'AIによる自動最適化', description: '最新のAI技術が、あなたに最適な結果を自動で導き出します。' },
      { title: 'ワンクリック出力', description: '面倒な設定は不要。ボタン一つで完成品が手に入ります。' },
      { title: 'リアルタイムプレビュー', description: '変更をその場で確認。納得いくまで何度でも調整できます。' },
    ],
    faqSection: [
      { question: '初心者でも使えますか？', answer: 'はい。パソコンの基本操作ができれば、どなたでもお使いいただけます。難しい専門知識は一切不要です。' },
      { question: 'どのくらいで成果が出ますか？', answer: '多くの方が導入初日から効果を実感されています。本格的な成果は1〜2週間で現れ始めます。' },
      { question: '返金保証はありますか？', answer: 'はい。30日間の全額返金保証をご用意しています。リスクゼロでお試しいただけます。' },
    ],
    urgencySection: '【期間限定】今なら初月無料キャンペーン実施中。この特別価格でのご提供は、予告なく終了する場合があります。',
    finalCtaSection: {
      headline: '今すぐ、最初の一歩を踏み出しましょう',
      subheadline: `${productName}があなたの可能性を最大限に引き出します`,
      buttonText: '無料で始める',
    },
  };

  try {
    // ストリーミング風にJSONを少しずつ送信
    const jsonStr = JSON.stringify(demoCopy, null, 2);
    const chunkSize = 30;
    for (let i = 0; i < jsonStr.length && !closed; i += chunkSize) {
      const chunk = jsonStr.slice(i, i + chunkSize);
      sendSSE(res, { type: 'chunk', data: chunk, timestamp: Date.now() });
      await new Promise(r => setTimeout(r, 20)); // 少し遅延をつけてストリーミング感を出す
    }

    if (!closed) {
      const service = new LPCreatorService();
      const html = service.renderHTML(demoCopy as any);
      sendSSE(res, { type: 'complete', data: html, timestamp: Date.now() });
    }
  } catch (err) {
    console.error('[LP Creator] Demo generation error:', err);
    if (!closed) {
      sendSSE(res, { type: 'error', data: 'テスト生成でエラーが発生しました', timestamp: Date.now() });
    }
  } finally {
    if (!closed) {
      res.end();
    }
  }
}

/** GET /api/health */
export function handleHealth(_req: Request, res: Response): void {
  res.json({ status: 'OK', service: 'lp-creator-ss' });
}

/** GET /api/settings — 現在の設定を取得 */
export function handleGetSettings(_req: Request, res: Response): void {
  const settings = loadSettings();
  // APIキーはマスクして返す
  res.json({
    success: true,
    data: {
      anthropicApiKey: settings.anthropicApiKey
        ? `sk-...${settings.anthropicApiKey.slice(-4)}`
        : '（未設定 — 環境変数を使用）',
      model: settings.model,
      maxTokens: settings.maxTokens,
      hasEnvKey: !!process.env.ANTHROPIC_API_KEY,
    },
  });
}

/** POST /api/settings — 設定を保存 */
export function handleSaveSettings(req: Request, res: Response): void {
  const body = req.body as Partial<LPCreatorSettings>;

  const updates: Partial<LPCreatorSettings> = {};

  if (typeof body.anthropicApiKey === 'string') {
    updates.anthropicApiKey = body.anthropicApiKey.trim();
  }
  if (typeof body.model === 'string' && body.model.trim()) {
    updates.model = body.model.trim();
  }
  if (typeof body.maxTokens === 'number' && body.maxTokens >= 1024 && body.maxTokens <= 16384) {
    updates.maxTokens = body.maxTokens;
  }

  try {
    const saved = saveSettings(updates);
    res.json({
      success: true,
      message: '設定を保存しました',
      data: {
        anthropicApiKey: saved.anthropicApiKey
          ? `sk-...${saved.anthropicApiKey.slice(-4)}`
          : '（未設定）',
        model: saved.model,
        maxTokens: saved.maxTokens,
      },
    });
  } catch (err) {
    console.error('[LP Creator] Save settings error:', err);
    res.status(500).json({ success: false, error: '設定の保存に失敗しました' });
  }
}
