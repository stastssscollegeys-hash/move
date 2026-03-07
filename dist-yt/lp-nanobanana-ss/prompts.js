"use strict";
// ===== LP NanoBanana SS - Prompt Builder =====
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildAllImagePrompts = exports.buildImagePrompt = exports.buildCopyFullPrompt = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const types_1 = require("./types");
// Knowledge files are in src/ (not copied to dist by tsc)
// Resolve from project root to src/lp-nanobanana-ss/knowledge/
const KNOWLEDGE_DIR = fs_1.default.existsSync(path_1.default.join(__dirname, 'knowledge'))
    ? path_1.default.join(__dirname, 'knowledge')
    : path_1.default.join(__dirname, '..', '..', 'src', 'lp-nanobanana-ss', 'knowledge');
/** Load knowledge file content */
function loadKnowledge(filename) {
    const filePath = path_1.default.join(KNOWLEDGE_DIR, filename);
    return fs_1.default.readFileSync(filePath, 'utf-8');
}
/** Get knowledge files for the selected LP type */
function getKnowledgeForType(lpType) {
    const fileMap = {
        'education': ['01-education-lp.md'],
        'product-interest': ['02-product-interest-lp.md'],
        'expose': ['03-expose-lp.md'],
        'cutting-edge': ['04-cutting-edge-lp-v1.md', '05-cutting-edge-lp-v2.md'],
    };
    return fileMap[lpType].map(f => loadKnowledge(f)).join('\n\n---\n\n');
}
/** Build section key for JSON output (e.g., "section1_headline") */
function buildSectionKey(meta) {
    return `section${meta.id}_${meta.name.replace(/-/g, '_')}`;
}
/** Build the full copy generation prompt (dynamic sections based on LP type) */
function buildCopyFullPrompt(productName, target, strength, lpType, price, description, ctaText) {
    const typeNames = {
        'education': '教育型LP（見込み客を教育→セミナー誘導）',
        'product-interest': '商品興味づけLP（ストーリー性で興味→登録）',
        'expose': '暴露系LP（業界の真実暴露→参加促進）',
        'cutting-edge': '先端×秘匿LP（トレンド×FOMO→緊急性）',
    };
    // Load knowledge files for this LP type
    let knowledgeSection = '';
    try {
        const knowledge = getKnowledgeForType(lpType);
        knowledgeSection = `\n\n--- 参考ナレッジ（${typeNames[lpType]}） ---\n${knowledge}\n--- ナレッジここまで ---\n`;
    }
    catch (err) {
        console.warn('[LP-Copy] Knowledge files not found, proceeding without:', err);
    }
    // Build dynamic JSON template from section defs
    const sectionDefs = (0, types_1.getSectionDefs)(lpType);
    const jsonExample = {};
    for (const meta of sectionDefs) {
        jsonExample[buildSectionKey(meta)] = `${meta.nameJa}のコピー`;
    }
    const jsonTemplate = JSON.stringify(jsonExample, null, 2);
    const sectionCount = sectionDefs.length;
    const sectionList = sectionDefs.map(m => `- ${buildSectionKey(m)}: ${m.nameJa}`).join('\n');
    return `あなたはLPコピーライターです。${sectionCount}セクションのLP画像用コピーをJSON形式で生成します。

重要ルール:
- 各セクションは画像に描画されるため、30〜80文字程度に収めること（短いほど文字化けしにくい）
- キャッチーで短いフレーズを使う。1行あたり15文字以内が理想
- 長い説明文は不要。インパクト重視
- 箇条書きは \\n で区切る
- ナレッジの構成・心理テクニックを活かしたコピーを作成すること
- 難読漢字・特殊記号は避ける。ひらがな・カタカナ・常用漢字のみ使用

【でっちあげ禁止ルール（最重要）】
- ユーザーが提供した商品情報に含まれない事実は絶対に捏造しないこと
- 架空の認定・資格・受賞歴・認証マークを作らないこと
  NG例: 「○○協会認定」「△△アワード受賞」「ISO○○取得」（ユーザーが言及していないもの）
- 架空の数値データ・統計を作らないこと
  NG例: 「満足度98.7%」「3,000人が参加」（ユーザーが提供していない数字）
- 権威性セクションでは、ユーザーの「強み・特徴」から抽出できる情報のみ使う
- 数字を使いたい場合は「多くの方に選ばれています」等の抽象表現にすること
- コピーにロゴ・バッジ・認証マークの表示指示を含めないこと（画像生成時に架空ロゴが生成される原因になる）
  NG例: 「プライバシーマーク取得」「セキュリティ認証済み」「VISA/PayPay対応」

【CTAボタンテキストの重要ルール】
- CTAセクションでは「CTA」という英語は絶対に使わないこと
${ctaText ? `- CTAボタンのテキストは「${ctaText}」を使うこと（ユーザー指定）
- このボタンテキストをCTAセクションのメインボタンに必ず使用すること` : `- ボタンテキストは行動を促す日本語にすること。例:
  「今すぐ無料で申し込む」「限定枠を確保する」「無料セミナーに参加する」
  「詳細を見る」「特別価格で手に入れる」「今すぐ始める」`}
- ボタンの上にはマイクロコピー（安心感を与える一文）を添えること。例:
  「30日間全額返金保証」「たった3分で完了」「クレジットカード不要」
- 英語のマーケティング用語（CTA、CV、LP等）は出力に含めないこと
${knowledgeSection}
このLPタイプのセクション構成（${sectionCount}セクション）:
${sectionList}

以下のJSON形式で返してください:

\`\`\`json
${jsonTemplate}
\`\`\`

---

商品名: ${productName}
ターゲット: ${target}
強み: ${strength}
${price ? `価格: ${price}` : ''}
${description ? `詳細: ${description}` : ''}
LPタイプ: ${typeNames[lpType]}

上記の商品情報で、${typeNames[lpType]}スタイルのLP画像用コピーを${sectionCount}セクション分のJSONで生成してください。
JSONのみ返してください。`;
}
exports.buildCopyFullPrompt = buildCopyFullPrompt;
/** Prompt prefix for all image generation */
const IMAGE_PROMPT_PREFIX = `(best quality, professional landing page design, web design, clean modern layout,
Japanese business website, no watermarks, no labels, no section titles in English)

CRITICAL RULES - READ CAREFULLY:
1. Do NOT render any English text at all. No "CTA", "CLICK HERE", "SIGN UP", or any English words.
   ALL text on the image must be in Japanese only.
2. Ensure ALL content has generous padding from ALL edges - NOTHING should be cropped or cut off.
   Leave at least 100px safe margin on all sides. No text or elements near the edges.
3. Do NOT duplicate any content elements - render each card, testimonial, or item exactly once.
4. Keep the layout clean and centered. All elements must be fully visible within the image bounds.
5. Text must be clearly readable - use sufficient contrast and font size.
6. Maintain consistent visual hierarchy - headings larger, body text smaller, buttons prominent.
7. NEVER generate any logos, trust badges, certification marks, or brand icons.
   Do NOT render: プライバシーマーク, セキュリティ認証, ISO認証, 決済ロゴ (VISA, PayPay, etc.),
   協会ロゴ, 企業ロゴ, or any official-looking emblems/seals. These are legally problematic.
   If the design needs trust elements, use plain text only (e.g., "安心の全額返金保証").
8. NEVER render clickable-looking buttons with shadow/3D effects for CTA sections.
   Instead, render a flat colored banner area with the action text. The image is static and
   buttons cannot be clicked, so do not make them look interactive/clickable.
   Use a simple colored rectangle with text, not a realistic button.
9. Each section image must be a SINGLE cohesive design. Do NOT split into two side-by-side panels
   or create a horizontally divided layout. The entire image width should be one unified composition.
   Especially for the first view (FV/hero) section: use the FULL width as one single banner design.`;
/** Build image generation prompt for a single section */
function buildImagePrompt(sectionMeta, copyText, design, ctaText) {
    // Look up section style from design settings, fall back to section's styleKeywords
    const styleKey = `section_${sectionMeta.id}_${sectionMeta.name.replace(/-/g, '_')}`;
    const sectionStyle = design.section_styles[styleKey] || sectionMeta.styleKeywords;
    // Truncate copy to keep prompt manageable
    const truncatedCopy = copyText.length > 500 ? copyText.substring(0, 500) + '...' : copyText;
    // Add CTA button text instruction for CTA-related sections
    const isCTASection = ['cta', 'decision', 'urgency'].includes(sectionMeta.name) ||
        sectionMeta.name.includes('cta');
    const ctaInstruction = isCTASection && ctaText
        ? `\n\nIMPORTANT: The main action button on this image MUST display the text「${ctaText}」in Japanese. This is the user-specified CTA button text. Render it prominently on the button.`
        : '';
    return `${IMAGE_PROMPT_PREFIX}

Visual style: ${sectionStyle}
Color scheme: primary ${design.colors.primary}, accent ${design.colors.accent}, CTA button ${design.colors.cta_button}, background ${design.colors.background}, heading ${design.colors.heading_color}, body text ${design.colors.body_text}

Japanese text to render on this image:
${truncatedCopy}${ctaInstruction}

Image dimensions: ${sectionMeta.width}x${sectionMeta.height} (aspect ratio ${sectionMeta.aspectRatio})
Style keywords: ${sectionMeta.styleKeywords}, professional, modern, high-conversion landing page, Japanese text, clean typography, strategic whitespace`;
}
exports.buildImagePrompt = buildImagePrompt;
/** Build all image prompts for the given LP type's sections */
function buildAllImagePrompts(copySections, design, lpType, ctaText) {
    const sectionDefs = (0, types_1.getSectionDefs)(lpType);
    return sectionDefs.map(meta => {
        const key = buildSectionKey(meta);
        const copyText = copySections[key] || '';
        return {
            sectionMeta: meta,
            prompt: buildImagePrompt(meta, copyText, design, ctaText),
        };
    });
}
exports.buildAllImagePrompts = buildAllImagePrompts;
