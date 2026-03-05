// ============================================================
// Enrolly SS - Type Definitions (English-market extensions)
// Inherits core types from FunnelForge, adds Enrolly-specific
// ============================================================

export type { ApiResponse } from '../funnel-forge-ss/types';

// ============================================================
// Membership Site (core focus of Enrolly)
// ============================================================

export interface EnrollyCourse {
  id: string;
  user_id: string;
  title: string;
  slug: string;
  description: string;
  thumbnail_url: string;
  access_type: 'free' | 'paid' | 'subscription';
  price_cents: number;
  currency: string; // USD, EUR, GBP, etc.
  stripe_price_id: string | null;
  drip_enabled: boolean;       // Drip content (release lessons over time)
  drip_interval_days: number;
  is_published: boolean;
  enrollment_count: number;
  created_at: string;
  updated_at: string;
}

export interface EnrollyModule {
  id: string;
  course_id: string;
  title: string;
  sort_order: number;
  drip_day: number | null;  // Day number when this module unlocks (drip)
  created_at: string;
}

export interface EnrollyLesson {
  id: string;
  module_id: string;
  course_id: string;
  title: string;
  description: string;
  content_type: 'video' | 'text' | 'pdf' | 'quiz' | 'assignment';
  video_url: string | null;       // Uploaded video or embed URL
  video_duration_sec: number;     // Video duration in seconds
  video_thumbnail_url: string | null;
  text_content: string | null;    // Rich text / HTML content
  pdf_url: string | null;
  sort_order: number;
  is_free_preview: boolean;       // Allow non-enrolled users to preview
  created_at: string;
  updated_at: string;
}

export interface EnrollyEnrollment {
  id: string;
  course_id: string;
  contact_id: string;
  status: 'active' | 'paused' | 'expired' | 'cancelled';
  enrolled_at: string;
  drip_start_date: string;        // When drip clock starts for this user
  completed_lessons: string[];    // Lesson IDs
  progress_pct: number;
  last_accessed_at: string | null;
  stripe_subscription_id: string | null;
}

export interface LessonProgress {
  id: string;
  enrollment_id: string;
  lesson_id: string;
  status: 'not_started' | 'in_progress' | 'completed';
  video_watched_sec: number;      // How far they watched
  completed_at: string | null;
}

export interface VideoUpload {
  id: string;
  user_id: string;
  original_name: string;
  storage_key: string;
  mime_type: string;
  size_bytes: number;
  duration_sec: number;
  thumbnail_url: string;
  status: 'uploading' | 'processing' | 'ready' | 'error';
  hls_url: string | null;         // HLS streaming URL (after processing)
  created_at: string;
}

export interface QuizQuestion {
  id: string;
  lesson_id: string;
  question: string;
  question_type: 'multiple_choice' | 'true_false' | 'short_answer';
  options: string[];
  correct_answer: string;
  explanation: string;
  sort_order: number;
}

export interface QuizAttempt {
  id: string;
  enrollment_id: string;
  lesson_id: string;
  answers: Record<string, string>;
  score_pct: number;
  passed: boolean;
  attempted_at: string;
}

// ============================================================
// Community / Discussion
// ============================================================

export interface Discussion {
  id: string;
  course_id: string;
  lesson_id: string | null;       // null = course-wide discussion
  contact_id: string;
  title: string;
  body: string;
  reply_count: number;
  created_at: string;
}

export interface DiscussionReply {
  id: string;
  discussion_id: string;
  contact_id: string;
  body: string;
  is_instructor: boolean;
  created_at: string;
}

// ============================================================
// Certificates
// ============================================================

export interface Certificate {
  id: string;
  course_id: string;
  template_html: string;
  issuer_name: string;
}

export interface IssuedCertificate {
  id: string;
  certificate_id: string;
  enrollment_id: string;
  contact_name: string;
  issued_at: string;
  pdf_url: string;
  verification_code: string;
}
