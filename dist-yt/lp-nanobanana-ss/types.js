"use strict";
// ===== LP NanoBanana SS - Type Definitions =====
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_DESIGN = exports.SECTION_DEFS = void 0;
/** All 7 section definitions */
exports.SECTION_DEFS = [
    { id: 1, name: 'first-view', nameJa: 'ファーストビュー', aspectRatio: '3:4', width: 1080, height: 1440, styleKeywords: 'cinematic hero, dark gradient overlay, bold white text, orange CTA, aspirational' },
    { id: 2, name: 'problem', nameJa: '問題提起', aspectRatio: '4:5', width: 1080, height: 1350, styleKeywords: 'light gray bg, flat icons, muted palette, warning symbols, empathetic' },
    { id: 3, name: 'solution', nameJa: '解決策', aspectRatio: '3:4', width: 1080, height: 1440, styleKeywords: 'clean white bg, narrative layout, blue accent quote box, professional' },
    { id: 4, name: 'benefit', nameJa: 'ベネフィット', aspectRatio: '4:5', width: 1080, height: 1350, styleKeywords: '3-column cards, soft shadow, light blue bg, green checkmarks, structured' },
    { id: 5, name: 'testimonial', nameJa: 'お客様の声', aspectRatio: '9:16', width: 1080, height: 1920, styleKeywords: 'warm lighting, testimonial cards, star ratings, avatars, authentic' },
    { id: 6, name: 'pricing', nameJa: '特典・料金', aspectRatio: '4:5', width: 1080, height: 1350, styleKeywords: 'pricing cards, highlighted center, orange badge, clean table, value-focused' },
    { id: 7, name: 'cta', nameJa: 'CTA', aspectRatio: '3:4', width: 1080, height: 1440, styleKeywords: 'solid blue bg, orange button, white space, urgency, trust badges' },
];
/** Default design when no reference URL provided */
exports.DEFAULT_DESIGN = {
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
