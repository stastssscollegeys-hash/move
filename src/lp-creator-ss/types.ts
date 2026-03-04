// ===== LP Creator SS - Type Definitions =====

/** 3-field input from the user */
export interface LPGenerateRequest {
  productName: string;   // 商品名（max 100 chars）
  target: string;        // ターゲット（max 200 chars）
  strength: string;      // 強み・特徴（max 300 chars）
}

/** 11-section AI-generated copy structure */
export interface LPCopyJSON {
  heroHeadline: string;
  heroSubheadline: string;
  heroCta: string;
  problemSection: string[];       // 3-5 pain points
  solutionSection: string;
  benefitsSection: {
    title: string;
    description: string;
  }[];                            // 3-5 benefits
  socialProofSection: {
    name: string;
    text: string;
  }[];                            // 2-3 testimonials
  featuresSection: {
    title: string;
    description: string;
  }[];                            // 3-5 features
  faqSection: {
    question: string;
    answer: string;
  }[];                            // 3-5 FAQs
  urgencySection: string;         // scarcity / urgency copy
  finalCtaSection: {
    headline: string;
    subheadline: string;
    buttonText: string;
  };
}

/** SSE event types sent to the client */
export type SSEEventType = 'chunk' | 'complete' | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: string;         // chunk: raw text, complete: full HTML, error: message
  timestamp: number;
}
