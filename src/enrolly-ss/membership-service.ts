// ============================================================
// Enrolly SS - Membership & Course Service
// Core feature: Video-based membership site for English market
// ============================================================

import type {
  EnrollyCourse, EnrollyModule, EnrollyLesson, EnrollyEnrollment,
  LessonProgress, VideoUpload, QuizAttempt, ApiResponse,
} from './types';
import { getSupabase } from './shared';

// ============================================================
// Courses CRUD
// ============================================================

export async function listCourses(userId: string): Promise<ApiResponse<EnrollyCourse[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_courses').select('*')
    .eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getCourse(courseId: string): Promise<ApiResponse<EnrollyCourse & { modules: any[] }>> {
  const db = getSupabase();
  const { data: course, error } = await db.from('enrolly_courses').select('*').eq('id', courseId).single();
  if (error) return { success: false, error: error.message };

  const { data: modules } = await db.from('enrolly_modules').select('*')
    .eq('course_id', courseId).order('sort_order');
  const { data: lessons } = await db.from('enrolly_lessons').select('*')
    .eq('course_id', courseId).order('sort_order');

  // Group lessons by module
  const enriched = (modules || []).map((mod: any) => ({
    ...mod,
    lessons: (lessons || []).filter((l: any) => l.module_id === mod.id),
  }));

  return { success: true, data: { ...course, modules: enriched } };
}

export async function createCourse(userId: string, course: Partial<EnrollyCourse>): Promise<ApiResponse<EnrollyCourse>> {
  const db = getSupabase();
  const slug = (course.title || 'course').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60);
  const { data, error } = await db.from('enrolly_courses').insert({
    user_id: userId, title: course.title, slug,
    description: course.description || '',
    thumbnail_url: course.thumbnail_url || '',
    access_type: course.access_type || 'paid',
    price_cents: course.price_cents || 0,
    currency: course.currency || 'USD',
    stripe_price_id: course.stripe_price_id || null,
    drip_enabled: course.drip_enabled || false,
    drip_interval_days: course.drip_interval_days || 7,
    is_published: false,
    enrollment_count: 0,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateCourse(courseId: string, updates: Partial<EnrollyCourse>): Promise<ApiResponse<EnrollyCourse>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_courses').update(updates).eq('id', courseId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function publishCourse(courseId: string, publish: boolean): Promise<ApiResponse<EnrollyCourse>> {
  return updateCourse(courseId, { is_published: publish } as any);
}

// ============================================================
// Modules
// ============================================================

export async function createModule(courseId: string, title: string, sortOrder: number): Promise<ApiResponse<EnrollyModule>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_modules').insert({
    course_id: courseId, title, sort_order: sortOrder, drip_day: null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateModule(moduleId: string, updates: Partial<EnrollyModule>): Promise<ApiResponse<EnrollyModule>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_modules').update(updates).eq('id', moduleId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function deleteModule(moduleId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  await db.from('enrolly_lessons').delete().eq('module_id', moduleId);
  const { error } = await db.from('enrolly_modules').delete().eq('id', moduleId);
  if (error) return { success: false, error: error.message };
  return { success: true };
}

// ============================================================
// Lessons
// ============================================================

export async function createLesson(moduleId: string, courseId: string, lesson: Partial<EnrollyLesson>): Promise<ApiResponse<EnrollyLesson>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_lessons').insert({
    module_id: moduleId, course_id: courseId,
    title: lesson.title || 'Untitled Lesson',
    description: lesson.description || '',
    content_type: lesson.content_type || 'video',
    video_url: lesson.video_url || null,
    video_duration_sec: lesson.video_duration_sec || 0,
    video_thumbnail_url: lesson.video_thumbnail_url || null,
    text_content: lesson.text_content || null,
    pdf_url: lesson.pdf_url || null,
    sort_order: lesson.sort_order || 0,
    is_free_preview: lesson.is_free_preview || false,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateLesson(lessonId: string, updates: Partial<EnrollyLesson>): Promise<ApiResponse<EnrollyLesson>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_lessons').update(updates).eq('id', lessonId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function deleteLesson(lessonId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { error } = await db.from('enrolly_lessons').delete().eq('id', lessonId);
  if (error) return { success: false, error: error.message };
  return { success: true };
}

// ============================================================
// Video Upload
// ============================================================

export async function requestVideoUpload(userId: string, originalName: string, mimeType: string, sizeBytes: number): Promise<ApiResponse<VideoUpload>> {
  const db = getSupabase();
  const storageKey = `videos/${userId}/${Date.now()}-${originalName}`;

  const { data, error } = await db.from('enrolly_videos').insert({
    user_id: userId, original_name: originalName,
    storage_key: storageKey, mime_type: mimeType,
    size_bytes: sizeBytes, duration_sec: 0,
    thumbnail_url: '', status: 'uploading',
    hls_url: null,
  }).select().single();
  if (error) return { success: false, error: error.message };

  // Get signed upload URL from storage
  const storage = getSupabase().storage.from('enrolly-media');
  const { data: uploadData } = await storage.createSignedUploadUrl(storageKey);

  return { success: true, data: { ...data, upload_url: uploadData?.signedUrl } };
}

export async function confirmVideoUpload(videoId: string): Promise<ApiResponse<VideoUpload>> {
  const db = getSupabase();
  // In production: trigger transcoding pipeline (FFmpeg → HLS)
  const { data, error } = await db.from('enrolly_videos').update({
    status: 'ready', // In production: 'processing' → webhook → 'ready'
  }).eq('id', videoId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listVideos(userId: string): Promise<ApiResponse<VideoUpload[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_videos').select('*')
    .eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// ============================================================
// Enrollment & Progress
// ============================================================

export async function enrollStudent(courseId: string, contactId: string): Promise<ApiResponse<EnrollyEnrollment>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_enrollments').upsert({
    course_id: courseId, contact_id: contactId,
    status: 'active', enrolled_at: new Date().toISOString(),
    drip_start_date: new Date().toISOString(),
    completed_lessons: [], progress_pct: 0,
  }, { onConflict: 'course_id,contact_id' }).select().single();
  if (error) return { success: false, error: error.message };

  // Increment enrollment count
  const { data: course } = await db.from('enrolly_courses').select('enrollment_count').eq('id', courseId).single();
  if (course) {
    await db.from('enrolly_courses').update({
      enrollment_count: (course.enrollment_count || 0) + 1,
    }).eq('id', courseId);
  }

  return { success: true, data };
}

export async function getEnrollment(courseId: string, contactId: string): Promise<ApiResponse<EnrollyEnrollment & { course: any; available_lessons: any[] }>> {
  const db = getSupabase();
  const { data: enrollment } = await db.from('enrolly_enrollments').select('*')
    .eq('course_id', courseId).eq('contact_id', contactId).single();
  if (!enrollment) return { success: false, error: 'Not enrolled' };

  const { data: course } = await db.from('enrolly_courses').select('*').eq('id', courseId).single();
  const { data: modules } = await db.from('enrolly_modules').select('*').eq('course_id', courseId).order('sort_order');
  const { data: lessons } = await db.from('enrolly_lessons').select('*').eq('course_id', courseId).order('sort_order');

  // Apply drip logic
  let availableLessons = lessons || [];
  if (course?.drip_enabled) {
    const daysSinceEnroll = Math.floor((Date.now() - new Date(enrollment.drip_start_date).getTime()) / 86400000);
    availableLessons = availableLessons.filter((l: any) => {
      const mod = (modules || []).find((m: any) => m.id === l.module_id);
      return !mod?.drip_day || mod.drip_day <= daysSinceEnroll;
    });
  }

  return { success: true, data: { ...enrollment, course, available_lessons: availableLessons } };
}

export async function completeLesson(enrollmentId: string, lessonId: string): Promise<ApiResponse<EnrollyEnrollment>> {
  const db = getSupabase();
  const { data: enrollment } = await db.from('enrolly_enrollments').select('*').eq('id', enrollmentId).single();
  if (!enrollment) return { success: false, error: 'Enrollment not found' };

  const completed = [...new Set([...(enrollment.completed_lessons || []), lessonId])];

  // Calculate progress
  const { data: totalLessons } = await db.from('enrolly_lessons').select('id', { count: 'exact', head: true })
    .eq('course_id', enrollment.course_id);
  const total = totalLessons?.count || 1;
  const progressPct = Math.round((completed.length / total) * 100);

  const { data, error } = await db.from('enrolly_enrollments').update({
    completed_lessons: completed,
    progress_pct: progressPct,
    last_accessed_at: new Date().toISOString(),
  }).eq('id', enrollmentId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function trackVideoProgress(enrollmentId: string, lessonId: string, watchedSec: number): Promise<ApiResponse<LessonProgress>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrolly_lesson_progress').upsert({
    enrollment_id: enrollmentId, lesson_id: lessonId,
    status: 'in_progress', video_watched_sec: watchedSec,
  }, { onConflict: 'enrollment_id,lesson_id' }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listEnrollments(courseId: string, page = 1, perPage = 20): Promise<ApiResponse<EnrollyEnrollment[]>> {
  const db = getSupabase();
  const { data, error, count } = await db.from('enrolly_enrollments').select('*', { count: 'exact' })
    .eq('course_id', courseId).order('enrolled_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1);
  if (error) return { success: false, error: error.message };
  return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}
