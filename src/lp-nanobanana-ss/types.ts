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
  referenceUrl?: string;
  claudeApiKey: string;
  geminiApiKey: string;
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
  prompt: string;
  geminiApiKey: string;
}

/** 7 fixed LP sections */
export interface LPSections {
  section1_fv: string;
  section2_problem: string;
  section3_solution: string;
  section4_benefit: string;
  section5_testimonial: string;
  section6_pricing: string;
  section7_cta: string;
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

/** All 7 section definitions */
export const SECTION_DEFS: SectionMeta[] = [
  { id: 1, name: 'first-view',    nameJa: 'ファーストビュー', aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'cinematic hero, dark gradient overlay, bold white text, orange CTA, aspirational' },
  { id: 2, name: 'problem',       nameJa: '問題提起',         aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'light gray bg, flat icons, muted palette, warning symbols, empathetic' },
  { id: 3, name: 'solution',      nameJa: '解決策',           aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'clean white bg, narrative layout, blue accent quote box, professional' },
  { id: 4, name: 'benefit',       nameJa: 'ベネフィット',     aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: '3-column cards, soft shadow, light blue bg, green checkmarks, structured' },
  { id: 5, name: 'testimonial',   nameJa: 'お客様の声',       aspectRatio: '9:16', width: 1080, height: 1920, styleKeywords: 'warm lighting, testimonial cards, star ratings, avatars, authentic' },
  { id: 6, name: 'pricing',       nameJa: '特典・料金',       aspectRatio: '4:5',  width: 1080, height: 1350, styleKeywords: 'pricing cards, highlighted center, orange badge, clean table, value-focused' },
  { id: 7, name: 'cta',           nameJa: 'CTA',              aspectRatio: '3:4',  width: 1080, height: 1440, styleKeywords: 'solid blue bg, orange button, white space, urgency, trust badges' },
];

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
  section_styles: {
    section_1_fv: string;
    section_2_problem: string;
    section_3_solution: string;
    section_4_benefit: string;
    section_5_testimonial: string;
    section_6_pricing: string;
    section_7_cta: string;
  };
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
  section_styles: {
    section_1_fv: 'cinematic full-width hero, semi-transparent dark gradient overlay, aspirational imagery, bold white heading text, orange CTA button with rounded corners, maximum visual impact',
    section_2_problem: 'light gray (#F8FAFC) background, flat icons with muted palette, X marks or warning symbols, problem cards with subtle red/orange accents, empathetic tone',
    section_3_solution: 'bright clean product showcase, split layout text-left image-right, primary blue (#2563EB) accent elements, clean white background, professional feel',
    section_4_benefit: '3-column icon cards with soft drop shadow, light blue (#F0F9FF) background, checkmark icons in green (#10B981), benefit headlines in bold dark text',
    section_5_testimonial: 'warm lighting testimonial cards, star ratings in gold (#F59E0B), avatar circles, quote marks, soft background, authentic feel',
    section_6_pricing: 'pricing card comparison layout, highlighted center card with badge, orange (#F97316) recommended badge, clean table structure, value emphasis',
    section_7_cta: 'high-contrast solid primary (#2563EB) background, single prominent orange button, maximum white space, urgency text, trust badges below button',
  },
};

/** SSE event types */
export type SSEEventType =
  | 'copy_chunk'
  | 'copy_complete'
  | 'research_start'
  | 'research_complete'
  | 'image_start'
  | 'image_complete'
  | 'image_error'
  | 'all_complete'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: any;
  timestamp: number;
}
