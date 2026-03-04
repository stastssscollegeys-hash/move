"use strict";
// ===== LP Creator SS - Service =====
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.LPCreatorService = void 0;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const prompts_1 = require("./prompts");
const settings_store_1 = require("./settings-store");
class LPCreatorService {
    constructor() {
        const apiKey = (0, settings_store_1.getEffectiveApiKey)();
        if (apiKey) {
            this.client = new sdk_1.default({ apiKey });
        }
        else {
            this.client = new sdk_1.default(); // fallback to ANTHROPIC_API_KEY env
        }
        this.model = (0, settings_store_1.getEffectiveModel)();
        this.maxTokens = (0, settings_store_1.getEffectiveMaxTokens)();
    }
    /**
     * Generate LP copy via Claude streaming API.
     * Calls onChunk for each text delta, returns the full accumulated text.
     */
    async generateLP(input, onChunk, maxRetries = 2) {
        const userPrompt = (0, prompts_1.buildGeneratePrompt)(input);
        let lastError = null;
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const accumulated = await this.streamClaude(userPrompt, onChunk);
                const jsonStr = this.extractJson(accumulated);
                const parsed = JSON.parse(jsonStr);
                return this.validateAndFillDefaults(parsed, input);
            }
            catch (err) {
                lastError = err instanceof Error ? err : new Error(String(err));
                // Only retry on JSON parse failures, not API errors
                if (lastError.message.includes('401') ||
                    lastError.message.includes('429') ||
                    lastError.message.includes('authentication')) {
                    throw lastError;
                }
                if (attempt < maxRetries) {
                    console.warn(`[LP Creator] Attempt ${attempt + 1} failed, retrying: ${lastError.message}`);
                }
            }
        }
        throw lastError || new Error('LP生成に失敗しました');
    }
    /** Stream Claude API and accumulate the full response */
    async streamClaude(userPrompt, onChunk) {
        let accumulated = '';
        const stream = this.client.messages.stream({
            model: this.model,
            max_tokens: this.maxTokens,
            system: prompts_1.SYSTEM_PROMPT,
            messages: [{ role: 'user', content: userPrompt }],
        });
        for await (const event of stream) {
            if (event.type === 'content_block_delta' &&
                event.delta.type === 'text_delta') {
                const text = event.delta.text;
                accumulated += text;
                onChunk(text);
            }
        }
        return accumulated;
    }
    /** Remove markdown code fences and extract JSON string */
    extractJson(raw) {
        // Remove ```json ... ``` wrapper
        const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
        if (fenceMatch) {
            return fenceMatch[1].trim();
        }
        // Try to find raw JSON object
        const jsonMatch = raw.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            return jsonMatch[0];
        }
        throw new Error('JSONの抽出に失敗しました。AIの出力にJSON構造が見つかりません。');
    }
    /** Fill missing sections with sensible defaults (REQ-004/EH-006) */
    validateAndFillDefaults(data, input) {
        return {
            heroHeadline: data.heroHeadline || `${input.productName}で理想の未来を手に入れる`,
            heroSubheadline: data.heroSubheadline || `${input.target}のための新しい選択肢`,
            heroCta: data.heroCta || '今すぐ詳細を見る',
            problemSection: data.problemSection?.length
                ? data.problemSection
                : ['日々の悩みが解決できない', '何から始めればいいかわからない', '時間もお金も無駄にしたくない'],
            solutionSection: data.solutionSection || `${input.productName}は、${input.strength}という強みを活かし、${input.target}の課題を根本から解決します。`,
            benefitsSection: data.benefitsSection?.length
                ? data.benefitsSection
                : [
                    { title: '簡単に始められる', description: '複雑な設定は不要。すぐに効果を実感できます。' },
                    { title: '確かな実績', description: '多くの方が成果を実感しています。' },
                    { title: '安心のサポート', description: '困ったときもしっかりサポートします。' },
                ],
            socialProofSection: data.socialProofSection?.length
                ? data.socialProofSection
                : [
                    { name: 'A.K.様 30代', text: `${input.productName}のおかげで悩みが解消されました。もっと早く出会いたかったです。` },
                    { name: 'T.S.様 40代', text: '半信半疑でしたが、使ってみて納得。今では手放せません。' },
                ],
            featuresSection: data.featuresSection?.length
                ? data.featuresSection
                : [
                    { title: input.strength.slice(0, 20), description: input.strength },
                ],
            faqSection: data.faqSection?.length
                ? data.faqSection
                : [
                    { question: '初心者でも大丈夫ですか？', answer: 'はい、初めての方でも安心してお使いいただけます。' },
                    { question: '返金保証はありますか？', answer: 'ご満足いただけない場合は対応いたします。詳細はお問い合わせください。' },
                ],
            urgencySection: data.urgencySection || '今だけの特別価格でご提供中。このチャンスをお見逃しなく。',
            finalCtaSection: data.finalCtaSection || {
                headline: '今すぐ始めましょう',
                subheadline: `${input.productName}があなたの未来を変えます`,
                buttonText: '申し込みはこちら',
            },
        };
    }
    /** Generate responsive LP HTML from copy JSON */
    renderHTML(copy) {
        const e = this.escapeHtml.bind(this);
        const problemItems = copy.problemSection
            .map(p => `<li>${e(p)}</li>`)
            .join('\n            ');
        const benefitCards = copy.benefitsSection
            .map(b => `
          <div class="benefit-card">
            <h3>${e(b.title)}</h3>
            <p>${e(b.description)}</p>
          </div>`)
            .join('');
        const testimonials = copy.socialProofSection
            .map(s => `
          <div class="testimonial">
            <p class="testimonial-text">${e(s.text)}</p>
            <p class="testimonial-name">— ${e(s.name)}</p>
          </div>`)
            .join('');
        const featureCards = copy.featuresSection
            .map(f => `
          <div class="feature-card">
            <h3>${e(f.title)}</h3>
            <p>${e(f.description)}</p>
          </div>`)
            .join('');
        const faqItems = copy.faqSection
            .map(f => `
          <details class="faq-item">
            <summary>${e(f.question)}</summary>
            <p>${e(f.answer)}</p>
          </details>`)
            .join('');
        return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${e(copy.heroHeadline)}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', 'Yu Gothic', sans-serif;
      color: #333; line-height: 1.8; background: #fff;
    }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }

    /* Hero */
    .hero {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff; text-align: center; padding: 80px 20px;
      position: relative; overflow: hidden;
    }
    .hero::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
                  radial-gradient(circle at 80% 20%, rgba(255,255,255,0.08) 0%, transparent 50%);
    }
    .hero h1 { font-size: clamp(1.8rem, 5vw, 3rem); margin-bottom: 16px; position: relative; }
    .hero p { font-size: clamp(1rem, 2.5vw, 1.3rem); margin-bottom: 32px; opacity: 0.95; position: relative; }
    .cta-button {
      display: inline-block; background: #ff6b35; color: #fff;
      padding: 16px 48px; border-radius: 50px; font-size: 1.1rem;
      font-weight: bold; text-decoration: none; min-height: 44px; min-width: 44px;
      transition: transform 0.2s, box-shadow 0.2s; position: relative;
      box-shadow: 0 4px 15px rgba(255,107,53,0.4);
    }
    .cta-button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255,107,53,0.5); }

    /* Sections */
    .section { padding: 60px 20px; }
    .section-alt { background: #f8f9fa; }
    .section h2 {
      text-align: center; font-size: clamp(1.4rem, 3vw, 2rem);
      margin-bottom: 40px; color: #2d3748;
    }
    .section h2::after {
      content: ''; display: block; width: 60px; height: 3px;
      background: linear-gradient(90deg, #667eea, #764ba2);
      margin: 12px auto 0;
    }

    /* Problem */
    .problem-list {
      list-style: none; max-width: 700px; margin: 0 auto;
    }
    .problem-list li {
      padding: 12px 0 12px 32px; position: relative;
      font-size: 1.05rem; border-bottom: 1px solid #e2e8f0;
    }
    .problem-list li::before {
      content: '\\2717'; position: absolute; left: 0; color: #e53e3e;
      font-weight: bold; font-size: 1.2rem;
    }

    /* Solution */
    .solution-text {
      max-width: 800px; margin: 0 auto; font-size: 1.1rem;
      text-align: center; line-height: 2;
    }

    /* Cards grid */
    .cards-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px; max-width: 1000px; margin: 0 auto;
    }
    .benefit-card, .feature-card {
      background: #fff; border-radius: 12px; padding: 32px 24px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      transition: transform 0.2s;
    }
    .benefit-card:hover, .feature-card:hover { transform: translateY(-4px); }
    .benefit-card h3, .feature-card h3 {
      color: #667eea; margin-bottom: 12px; font-size: 1.15rem;
    }

    /* Testimonials */
    .testimonials { max-width: 800px; margin: 0 auto; }
    .testimonial {
      background: #fff; border-radius: 12px; padding: 24px 32px;
      margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
      border-left: 4px solid #667eea;
    }
    .testimonial-text { font-style: italic; margin-bottom: 8px; line-height: 1.9; }
    .testimonial-name { text-align: right; color: #718096; font-size: 0.9rem; }

    /* FAQ */
    .faq-list { max-width: 800px; margin: 0 auto; }
    .faq-item {
      background: #fff; border-radius: 8px; margin-bottom: 12px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .faq-item summary {
      padding: 16px 20px; cursor: pointer; font-weight: bold;
      list-style: none; position: relative;
    }
    .faq-item summary::after {
      content: '+'; position: absolute; right: 20px; top: 50%;
      transform: translateY(-50%); font-size: 1.4rem; color: #667eea;
    }
    .faq-item[open] summary::after { content: '\\2212'; }
    .faq-item p { padding: 0 20px 16px; color: #4a5568; }

    /* Urgency */
    .urgency {
      background: linear-gradient(135deg, #fff5f5, #fed7d7);
      text-align: center; padding: 40px 20px;
    }
    .urgency p {
      font-size: 1.15rem; color: #c53030; font-weight: bold;
      max-width: 600px; margin: 0 auto;
    }

    /* Final CTA */
    .final-cta {
      background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
      color: #fff; text-align: center; padding: 80px 20px;
    }
    .final-cta h2 { color: #fff; }
    .final-cta h2::after { background: linear-gradient(90deg, #ff6b35, #ff8f65); }
    .final-cta p { margin-bottom: 32px; opacity: 0.9; font-size: 1.1rem; }

    /* Mobile adjustments */
    @media (max-width: 640px) {
      .hero { padding: 50px 16px; }
      .section { padding: 40px 16px; }
      .cta-button { padding: 14px 32px; width: 100%; max-width: 320px; }
      .cards-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>

  <!-- Hero -->
  <section class="hero">
    <div class="container">
      <h1>${e(copy.heroHeadline)}</h1>
      <p>${e(copy.heroSubheadline)}</p>
      <a href="#cta" class="cta-button">${e(copy.heroCta)}</a>
    </div>
  </section>

  <!-- Problem -->
  <section class="section section-alt">
    <div class="container">
      <h2>こんなお悩みありませんか？</h2>
      <ul class="problem-list">
        ${problemItems}
      </ul>
    </div>
  </section>

  <!-- Solution -->
  <section class="section">
    <div class="container">
      <h2>その悩み、解決できます</h2>
      <p class="solution-text">${e(copy.solutionSection)}</p>
    </div>
  </section>

  <!-- Benefits -->
  <section class="section section-alt">
    <div class="container">
      <h2>選ばれる理由</h2>
      <div class="cards-grid">${benefitCards}
      </div>
    </div>
  </section>

  <!-- Social Proof -->
  <section class="section">
    <div class="container">
      <h2>お客様の声</h2>
      <div class="testimonials">${testimonials}
      </div>
    </div>
  </section>

  <!-- Features -->
  <section class="section section-alt">
    <div class="container">
      <h2>サービスの特徴</h2>
      <div class="cards-grid">${featureCards}
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section class="section">
    <div class="container">
      <h2>よくあるご質問</h2>
      <div class="faq-list">${faqItems}
      </div>
    </div>
  </section>

  <!-- Urgency -->
  <section class="urgency">
    <p>${e(copy.urgencySection)}</p>
  </section>

  <!-- Final CTA -->
  <section class="final-cta" id="cta">
    <div class="container">
      <h2>${e(copy.finalCtaSection.headline)}</h2>
      <p>${e(copy.finalCtaSection.subheadline)}</p>
      <a href="#" class="cta-button">${e(copy.finalCtaSection.buttonText)}</a>
    </div>
  </section>

</body>
</html>`;
    }
    /** Escape HTML special characters to prevent XSS */
    escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}
exports.LPCreatorService = LPCreatorService;
