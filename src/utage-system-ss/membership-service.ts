// ============================================================
// Membership Site Service (Courses / Lessons / Enrollments)
// ============================================================

import type { Course, Lesson, Enrollment, LessonComment, BundleCourse, ApiResponse } from './types';

let supabase: any = null;
function getSupabase() {
  if (!supabase) {
    const { createClient } = require('@supabase/supabase-js');
    supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);
  }
  return supabase;
}

// --- Courses ---

export async function listCourses(userId: string): Promise<ApiResponse<Course[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('courses').select('*, lessons(*)').eq('user_id', userId).order('updated_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data: (data || []).map((c: any) => ({ ...c, lessons: c.lessons || [] })) };
}

export async function createCourse(userId: string, course: Partial<Course>): Promise<ApiResponse<Course>> {
  const db = getSupabase();
  const { data, error } = await db.from('courses').insert({
    user_id: userId, name: course.name, description: course.description || '',
    access_type: course.access_type || 'paid', product_id: course.product_id || null,
    thumbnail_url: course.thumbnail_url || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: { ...data, lessons: [] } };
}

export async function getCourse(userId: string, courseId: string): Promise<ApiResponse<Course>> {
  const db = getSupabase();
  const { data, error } = await db.from('courses').select('*, lessons(*, media_files(*))').eq('id', courseId).eq('user_id', userId).single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: { ...data, lessons: data.lessons || [] } };
}

export async function updateCourse(courseId: string, updates: Partial<Course>): Promise<ApiResponse<Course>> {
  const db = getSupabase();
  const { data, error } = await db.from('courses').update(updates).eq('id', courseId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Lessons ---

export async function addLesson(courseId: string, lesson: Partial<Lesson>): Promise<ApiResponse<Lesson>> {
  const db = getSupabase();
  const { data, error } = await db.from('lessons').insert({
    course_id: courseId, title: lesson.title, description: lesson.description || '',
    content_type: lesson.content_type || 'video', media_id: lesson.media_id || null,
    content_html: lesson.content_html || null, sort_order: lesson.sort_order || 0,
    drip_days: lesson.drip_days || null, is_preview: lesson.is_preview || false,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateLesson(lessonId: string, updates: Partial<Lesson>): Promise<ApiResponse<Lesson>> {
  const db = getSupabase();
  const { data, error } = await db.from('lessons').update(updates).eq('id', lessonId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function deleteLesson(lessonId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { error } = await db.from('lessons').delete().eq('id', lessonId);
  if (error) return { success: false, error: error.message };
  return { success: true };
}

// --- Enrollments ---

export async function enrollContact(contactId: string, courseId: string): Promise<ApiResponse<Enrollment>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrollments').upsert({
    contact_id: contactId, course_id: courseId,
  }, { onConflict: 'contact_id,course_id' }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getEnrollment(contactId: string, courseId: string): Promise<ApiResponse<Enrollment>> {
  const db = getSupabase();
  const { data, error } = await db.from('enrollments').select('*').eq('contact_id', contactId).eq('course_id', courseId).single();
  if (error) return { success: false, error: 'Not enrolled' };
  return { success: true, data };
}

export async function completeLesson(contactId: string, courseId: string, lessonId: string): Promise<ApiResponse<Enrollment>> {
  const db = getSupabase();
  const { data: enrollment, error: getErr } = await db.from('enrollments').select('*').eq('contact_id', contactId).eq('course_id', courseId).single();
  if (getErr) return { success: false, error: 'Not enrolled' };

  const completed = [...new Set([...(enrollment.completed_lessons || []), lessonId])];
  const { data: lessons } = await db.from('lessons').select('id').eq('course_id', courseId);
  const totalLessons = (lessons || []).length;
  const progressPercent = totalLessons > 0 ? Math.round((completed.length / totalLessons) * 100) : 0;

  const { data, error } = await db.from('enrollments').update({
    completed_lessons: completed, progress_percent: progressPercent, last_accessed_at: new Date().toISOString(),
  }).eq('id', enrollment.id).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listEnrollments(courseId: string, page = 1, perPage = 20): Promise<ApiResponse<Enrollment[]>> {
  const db = getSupabase();
  const { data, error, count } = await db.from('enrollments').select('*, contacts(name, email)', { count: 'exact' })
    .eq('course_id', courseId).order('enrolled_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1);
  if (error) return { success: false, error: error.message };
  return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}

// --- Comments ---

export async function addComment(lessonId: string, contactId: string, content: string): Promise<ApiResponse<LessonComment>> {
  const db = getSupabase();
  const { data, error } = await db.from('lesson_comments').insert({ lesson_id: lessonId, contact_id: contactId, content }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listComments(lessonId: string): Promise<ApiResponse<LessonComment[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('lesson_comments').select('*, contacts(name)').eq('lesson_id', lessonId).order('created_at', { ascending: true });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Bundle ---

export async function createBundle(userId: string, name: string, courseIds: string[], productId?: string): Promise<ApiResponse<BundleCourse>> {
  const db = getSupabase();
  const { data, error } = await db.from('bundle_courses').insert({
    user_id: userId, name, course_ids: courseIds, product_id: productId || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}
