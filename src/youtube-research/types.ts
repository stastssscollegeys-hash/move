// YouTube Research Tool - Type Definitions

export interface VideoInput {
  rawText: string;
  inputType: 'url' | 'transcript' | 'summary';
}

export interface FilterParams {
  keyword?: string;
  genre?: 'education' | 'tech' | 'business' | 'lifestyle' | 'entertainment' | 'cooking' | 'beauty' | 'fitness' | 'gaming' | 'music' | 'travel' | 'pets' | 'parenting' | 'spiritual' | 'fortune' | 'healing' | 'mental' | 'other';
  lengthCategory: 'short' | 'medium' | 'long' | 'all';
  uploadPeriod: 'week' | '2weeks' | 'month' | '3months' | '6months' | 'year' | 'all';
  regionCode?: string;
}

export interface VideoMeta {
  id: string;
  title: string;
  channel: string;
  subscribers: number | null;
  views: number | null;
  likes: number | null;
  uploadDate: string | null;
  duration: string | null;
  description: string;
  tags: string[];
  transcriptOrSummary: string;
  url: string | null;
  thumbnail?: string;
}

export interface BuzzResult {
  video: VideoMeta;
  buzzRatio: number | null;
  buzzLevel: 'super-buzz' | 'buzz' | 'good' | 'average' | 'low' | 'unknown';
}

export interface TrendResult {
  originalTitle: string;
  topic: string;
  googleTrends: 'rising' | 'stable' | 'declining' | 'unknown';
  youtubeSearch: 'rising' | 'stable' | 'declining' | 'unknown';
  competition: 'low' | 'medium' | 'high' | 'unknown';
  verdict: 'go-now' | 'chance-but-competitive' | 'first-mover' | 'niche-stable' | 'too-late' | 'unknown';
  reasoning?: string;
}

export interface AudienceProfile {
  demographics: {
    ageRange: string;
    gender: string;
    occupation: string;
  };
  psychographics: {
    interests: string[];
    values: string[];
    lifestyle: string;
  };
  painPoints: string[];
  viewingMotivation: string[];
  purchaseBehavior: string[];
  relatedMedia: string[];
  contentAngle?: string;
}

export interface KeywordEntry {
  keyword: string;
  category: 'main' | 'sub' | 'longtail' | 'related' | 'buying-intent' | 'question' | 'trending';
  estimatedVolume: 'high' | 'medium' | 'low';
  competition: 'high' | 'medium' | 'low';
  relevance: 'high' | 'medium' | 'low';
  suggestedUse: string[];
}

// YouTube Search types

export interface SearchRequest {
  query: string;
  filters: FilterParams;
  maxResults?: number;
  youtubeApiKey: string;
  anthropicApiKey: string;
}

export interface SearchResponse {
  success: boolean;
  data?: {
    query: string;
    videoCount: number;
    videos: VideoMeta[];
    buzzRanking: BuzzResult[];
    audience: AudienceProfile;
    keywords: KeywordEntry[];
    recommendations: string[];
    fullReport: string;
  };
  error?: string;
}

// API Request/Response types

export interface AnalyzeRequest {
  videos: VideoInput[];
  filters: FilterParams;
  purpose?: string;
  anthropicApiKey?: string;
}

export interface BuzzRequest {
  videos: VideoInput[];
}

export interface TrendRequest {
  titles: string[];
}

export interface AnalyzeResponse {
  success: boolean;
  data?: {
    videoCount: number;
    videos: VideoMeta[];
    buzzRanking: BuzzResult[];
    trendCheck: TrendResult[];
    audience: AudienceProfile;
    keywords: KeywordEntry[];
    recommendations: string[];
    fullReport: string;
  };
  error?: string;
}

export interface BuzzResponse {
  success: boolean;
  data?: {
    ranking: BuzzResult[];
    commonPatterns: string;
  };
  error?: string;
}

export interface TrendResponse {
  success: boolean;
  data?: {
    results: TrendResult[];
    summary: string;
  };
  error?: string;
}
