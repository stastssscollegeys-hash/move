// ===== LP NanoBanana SS - Prompt Builder =====

import fs from 'fs';
import path from 'path';
import { LPType, LPSections, DesignSettings, SectionMeta, SECTION_DEFS } from './types';

// Knowledge files are in src/ (not copied to dist by tsc)
// Resolve from project root to src/lp-nanobanana-ss/knowledge/
const KNOWLEDGE_DIR = fs.existsSync(path.join(__dirname, 'knowledge'))
  ? path.join(__dirname, 'knowledge')
  : path.join(__dirname, '..', '..', 'src', 'lp-nanobanana-ss', 'knowledge');

/** Load knowledge file content */
function loadKnowledge(filename: string): string {
  const filePath = path.join(KNOWLEDGE_DIR, filename);
  return fs.readFileSync(filePath, 'utf-8');
}

/** Get knowledge files for the selected LP type */
function getKnowledgeForType(lpType: LPType): string {
  const fileMap: Record<LPType, string[]> = {
    'education':        ['01-education-lp.md'],
    'product-interest': ['02-product-interest-lp.md'],
    'expose':           ['03-expose-lp.md'],
    'cutting-edge':     ['04-cutting-edge-lp-v1.md', '05-cutting-edge-lp-v2.md'],
  };
  return fileMap[lpType].map(f => loadKnowledge(f)).join('\n\n---\n\n');
}

/** Build the full copy generation prompt (system + user + knowledge combined into single user message) */
export function buildCopyFullPrompt(
  productName: string,
  target: string,
  strength: string,
  lpType: LPType,
  price?: string,
  description?: string,
): string {
  const typeNames: Record<LPType, string> = {
    'education':        '教育型LP（見込み客を教育→セミナー誘導）',
    'product-interest': '商品興味づけLP（ストーリー性で興味→登録）',
    'expose':           '暴露系LP（業界の真実暴露→参加促進）',
    'cutting-edge':     '先端×秘匿LP（トレンド×FOMO→緊急性）',
  };

  // Load knowledge files for this LP type
  let knowledgeSection = '';
  try {
    const knowledge = getKnowledgeForType(lpType);
    knowledgeSection = `\n\n--- 参考ナレッジ（${typeNames[lpType]}） ---\n${knowledge}\n--- ナレッジここまで ---\n`;
  } catch (err) {
    console.warn('[LP-Copy] Knowledge files not found, proceeding without:', err);
  }

  return `あなたはLPコピーライターです。7セクションのLP画像用コピーをJSON形式で生成します。

重要ルール:
- 各セクションは画像に描画されるため、50〜120文字程度に収めること
- キャッチーで短いフレーズを使う
- 長い説明文は不要。インパクト重視
- 箇条書きは \\n で区切る
${knowledgeSection}
以下のJSON形式で返してください:

\`\`\`json
{
  "section1_fv": "キャッチコピー\\nサブコピー\\nCTAテキスト",
  "section2_problem": "ターゲットの悩み共感コピー",
  "section3_solution": "解決策・差別化コピー",
  "section4_benefit": "具体的ベネフィット",
  "section5_testimonial": "お客様の声（2-3名分）",
  "section6_pricing": "特典・価格・緊急性",
  "section7_cta": "最終CTA・追伸"
}
\`\`\`

---

商品名: ${productName}
ターゲット: ${target}
強み: ${strength}
${price ? `価格: ${price}` : ''}
${description ? `詳細: ${description}` : ''}
LPタイプ: ${typeNames[lpType]}

上記の商品情報で、${typeNames[lpType]}スタイルのLP画像用コピーを7セクション分のJSONで生成してください。
JSONのみ返してください。`;
}

/** Prompt prefix for all image generation */
const IMAGE_PROMPT_PREFIX = `(best quality, professional landing page design, web design, clean modern layout,
Japanese business website, no watermarks, no labels, no section titles in English)

IMPORTANT: Do NOT render any English section titles, labels, or metadata text.
Only render the Japanese text specified below. Ensure all content has generous
padding from all edges - nothing should be cropped. Leave at least 80px safe
margin on all sides. Do NOT duplicate any content elements - render each card, testimonial, or item exactly once.`;

/** Build image generation prompt for a single section */
export function buildImagePrompt(
  sectionMeta: SectionMeta,
  copyText: string,
  design: DesignSettings,
): string {
  const sectionStyleKey = `section_${sectionMeta.id}_${sectionMeta.name.replace('-', '_')}` as keyof typeof design.section_styles;
  // Map section name to style key format
  const styleKeyMap: Record<number, keyof typeof design.section_styles> = {
    1: 'section_1_fv',
    2: 'section_2_problem',
    3: 'section_3_solution',
    4: 'section_4_benefit',
    5: 'section_5_testimonial',
    6: 'section_6_pricing',
    7: 'section_7_cta',
  };
  const sectionStyle = design.section_styles[styleKeyMap[sectionMeta.id]] || sectionMeta.styleKeywords;

  // Truncate copy to keep prompt manageable
  const truncatedCopy = copyText.length > 500 ? copyText.substring(0, 500) + '...' : copyText;

  return `${IMAGE_PROMPT_PREFIX}

Visual style: ${sectionStyle}
Color scheme: primary ${design.colors.primary}, accent ${design.colors.accent}, CTA button ${design.colors.cta_button}, background ${design.colors.background}, heading ${design.colors.heading_color}, body text ${design.colors.body_text}

Japanese text to render on this image:
${truncatedCopy}

Image dimensions: ${sectionMeta.width}x${sectionMeta.height} (aspect ratio ${sectionMeta.aspectRatio})
Style keywords: ${sectionMeta.styleKeywords}, professional, modern, high-conversion landing page, Japanese text, clean typography, strategic whitespace`;
}

/** Build all 7 image prompts */
export function buildAllImagePrompts(
  sections: LPSections,
  design: DesignSettings,
): { sectionMeta: SectionMeta; prompt: string }[] {
  const copyTexts: Record<number, string> = {
    1: sections.section1_fv,
    2: sections.section2_problem,
    3: sections.section3_solution,
    4: sections.section4_benefit,
    5: sections.section5_testimonial,
    6: sections.section6_pricing,
    7: sections.section7_cta,
  };

  return SECTION_DEFS.map(meta => ({
    sectionMeta: meta,
    prompt: buildImagePrompt(meta, copyTexts[meta.id], design),
  }));
}
