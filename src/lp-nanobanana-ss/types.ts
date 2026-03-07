// ===== LP NanoBanana SS - Type Definitions =====

/** LP type selection */
export type LPType = 'education' | 'product-interest' | 'expose' | 'cutting-edge';

/** Request body for LP generation */
export interface LPGenerateRequest {
  productName: string;
  target: string;
  strength: string;
  lpType: LPType;
  price?: string;
  description?: string;
  ctaText?: string;
  referenceUrl?: string;
  claudeApiKey: string;
  claudeModel?: string;
  geminiApiKey: string;
  geminiModel?: string;
}

/** Request body for bulk input parsing */
export interface ParseInputRequest {
  rawText: string;
  claudeApiKey: string;
}

/** Parsed product info from bulk input */
export interface ParsedProductInfo {
  productName: string;
  target: string;
  strength: string;
  price?: string;
  description?: string;
}

/** Request body for single section retry */
export interface RetrySectionRequest {
  sectionId: number;
  lpType: LPType;
  prompt: string;
  geminiApiKey: string;
  geminiModel?: string;
}

/** Section metadata */
export interface SectionMeta {
  id: number;
  name: string;
  nameJa: string;
  aspectRatio: string;
  width: number;
  height: number;
  styleKeywords: string;
}

/** Per-LP-type section definitions */
export const SECTION_DEFS_BY_TYPE: Record<LPType, SectionMeta[]> = {
  // 教育型: 9セクション（STEP 3.2 の各セクション役割設計に基づく）
  'education': [
    { id: 1, name: 'headline',      nameJa: 'ヘッドライン',     aspectRatio: '16:9', width: 1920, height: 1080, styleKeywords: 'cinematic hero banner, wide landscape layout, dark gradient overlay, bold white text, orange CTA, aspirational, impactful headline, single unified full-width design' },
    { id: 2, name: 'problem',       nameJa: '問題提起',         aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'light gray bg, flat icons, muted palette, warning symbols, empathetic, problem visualization' },
    { id: 3, name: 'solution',      nameJa: '解決策提示',       aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'clean white bg, narrative layout, blue accent, professional, innovative solution showcase' },
    { id: 4, name: 'authority',     nameJa: '権威性確立',       aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'professional portrait style, credentials display, achievement badges, trust-building, before/after comparison' },
    { id: 5, name: 'details',       nameJa: '詳細説明',         aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'step-by-step process diagram, numbered flow, clean infographic, structured methodology' },
    { id: 6, name: 'social-proof',  nameJa: '社会的証明',       aspectRatio: '9:16', width: 1080, height: 1920, styleKeywords: 'warm lighting, testimonial cards, star ratings, avatars, success metrics, authentic voices' },
    { id: 7, name: 'urgency',       nameJa: '緊急性演出',       aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'countdown timer style, limited availability, bold red/orange accents, scarcity signals, FOMO triggers' },
    { id: 8, name: 'pricing',       nameJa: '価格戦略',         aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'pricing comparison cards, anchoring display, strikethrough prices, highlighted value, ROI emphasis' },
    { id: 9, name: 'cta',           nameJa: '行動促進',         aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'solid blue bg, prominent orange button, white space, guarantee badges, simple action steps' },
  ],

  // 商品興味づけ型: 6セクション（ナレッジの構成に基づく）
  'product-interest': [
    { id: 1, name: 'first-view',    nameJa: 'ファーストビュー', aspectRatio: '16:9', width: 1920, height: 1080, styleKeywords: 'cinematic hero banner, wide landscape layout, dark gradient overlay, bold white text, orange CTA, aspirational, product showcase, single unified full-width design' },
    { id: 2, name: 'testimonial',   nameJa: 'お客様の声',       aspectRatio: '9:16', width: 1080, height: 1920, styleKeywords: 'warm lighting, testimonial cards, star ratings, avatars, before/after, authentic voices' },
    { id: 3, name: 'problem',       nameJa: '問題提起と共感',   aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'light gray bg, flat icons, muted palette, question marks, empathetic, authority reference' },
    { id: 4, name: 'story',         nameJa: '開発者ストーリー', aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'personal narrative, warm tones, portrait photo area, passion/vision, transparent storytelling' },
    { id: 5, name: 'solution',      nameJa: '解決策・商品紹介', aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'product showcase, step diagram, feature cards, clean white bg, benefit-focused, 3-column layout' },
    { id: 6, name: 'cta',           nameJa: '行動喚起',         aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'urgency display, special offer badge, orange CTA button, Q&A section, guarantee, trust badges' },
  ],

  // 暴露系: 5セクション（5段階構成に基づく）
  'expose': [
    { id: 1, name: 'denial',        nameJa: '現状否定と疑念',   aspectRatio: '16:9', width: 1920, height: 1080, styleKeywords: 'dark dramatic hero banner, wide landscape layout, cracked/shattered imagery, bold red text accents, questioning tone, shocking revelation, single unified full-width design' },
    { id: 2, name: 'truth',         nameJa: '真実の存在示唆',   aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'mysterious dark tones, keyhole/door imagery, golden light accents, secret knowledge, exclusive information' },
    { id: 3, name: 'special',       nameJa: '読者の特別性認定', aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'luxury gold accents, VIP badge design, exclusive membership feel, elite selection, dark premium bg' },
    { id: 4, name: 'urgency',       nameJa: '希少性と緊急性',   aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'countdown urgency, limited slots display, red warning accents, closing door imagery, now-or-never' },
    { id: 5, name: 'decision',      nameJa: '最終決断の促進',   aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'fork-in-road imagery, dramatic lighting, bold CTA button, destiny/fate feel, decisive moment' },
  ],

  // 先端×秘匿型: 9セクション（v2の構成に基づく）
  'cutting-edge': [
    { id: 1, name: 'headline',      nameJa: 'ヘッドライン',     aspectRatio: '16:9', width: 1920, height: 1080, styleKeywords: 'futuristic hero banner, wide landscape layout, tech gradient bg, bold white text, trend keywords, FOMO trigger, cutting-edge feel, single unified full-width design' },
    { id: 2, name: 'problem',       nameJa: '問題提起・共感',   aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'light gray bg, problem icons, information overload visual, relatable frustration, empathetic tone' },
    { id: 3, name: 'crisis',        nameJa: '危機感の増幅',     aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'data visualization, alarming statistics, red/orange warning, industry disruption graph, authority sources' },
    { id: 4, name: 'gap',           nameJa: '経済的格差の提示', aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'comparison chart, income gap visualization, green vs red contrast, statistical data, stark difference' },
    { id: 5, name: 'solution',      nameJa: '解決策の提示',     aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'clean product showcase, innovation highlight, blue accent, unique approach, powerful declaration' },
    { id: 6, name: 'offer',         nameJa: '無料オファーと特典', aspectRatio: '4:5', width: 1080, height: 1350, styleKeywords: 'gift box imagery, bonus cards, value display, free badge, attractive bonus stack' },
    { id: 7, name: 'urgency',       nameJa: '緊急性と価格',     aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'price anchoring display, strikethrough prices, limited time badge, originally vs now, value emphasis' },
    { id: 8, name: 'cta',           nameJa: 'CTA',              aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'high-contrast bg, prominent green/orange button, form fields, security badges, micro-copy' },
    { id: 9, name: 'postscript',    nameJa: '追伸',             aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'handwritten feel, personal note style, warm tones, final emotional appeal, last chance reminder' },
  ],
};

/** Get section definitions for a given LP type */
export function getSectionDefs(lpType: LPType): SectionMeta[] {
  return SECTION_DEFS_BY_TYPE[lpType] || SECTION_DEFS_BY_TYPE['education'];
}

/** Design analysis result from reference LP */
export interface DesignSettings {
  colors: {
    primary: string;
    accent: string;
    cta_button: string;
    cta_text: string;
    background: string;
    section_bg_alt: string;
    heading_color: string;
    body_text: string;
    subtext: string;
  };
  layout: {
    max_width: string;
    content_width: string;
    heading_font_size: string;
    subheading_font_size: string;
    body_font_size: string;
    cta_font_size: string;
    cta_button_padding: string;
    cta_border_radius: string;
    section_padding_vertical: string;
    section_padding_horizontal: string;
    hero_height: string;
    section_gap: string;
  };
  section_styles: Record<string, string>;
}

/** Default design when no reference URL provided */
export const DEFAULT_DESIGN: DesignSettings = {
  colors: {
    primary: '#2563EB',
    accent: '#38BDF8',
    cta_button: '#F97316',
    cta_text: '#FFFFFF',
    background: '#FFFFFF',
    section_bg_alt: '#F0F9FF',
    heading_color: '#0F172A',
    body_text: '#374151',
    subtext: '#6B7280',
  },
  layout: {
    max_width: '1200px',
    content_width: '960px',
    heading_font_size: '48px',
    subheading_font_size: '28px',
    body_font_size: '17px',
    cta_font_size: '18px',
    cta_button_padding: '18px 40px',
    cta_border_radius: '12px',
    section_padding_vertical: '96px',
    section_padding_horizontal: '32px',
    hero_height: '700px',
    section_gap: '80px',
  },
  section_styles: {},
};

/** Job phase */
export type JobPhase = 'copy' | 'design' | 'image' | 'done' | 'error';

/** Per-section status in a job */
export interface SectionStatus {
  status: 'waiting' | 'generating' | 'complete' | 'error';
  base64?: string;
  error?: string;
  prompt?: string;
}

/** Job state for polling */
export interface JobState {
  jobId: string;
  lpType: LPType;
  phase: JobPhase;
  statusText: string;
  copyText: string;
  sections: Record<number, SectionStatus>;
  imagesCompleted: number;
  imagesTotal: number;
  error?: string;
  startedAt: number;
}
