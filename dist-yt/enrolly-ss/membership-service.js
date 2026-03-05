"use strict";
// ============================================================
// Enrolly SS - Membership & Course Service
// Core feature: Video-based membership site for English market
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.listEnrollments = exports.trackVideoProgress = exports.completeLesson = exports.getEnrollment = exports.enrollStudent = exports.listVideos = exports.confirmVideoUpload = exports.requestVideoUpload = exports.deleteLesson = exports.updateLesson = exports.createLesson = exports.deleteModule = exports.updateModule = exports.createModule = exports.publishCourse = exports.updateCourse = exports.createCourse = exports.getCourse = exports.listCourses = void 0;
const shared_1 = require("./shared");
// ============================================================
// Courses CRUD
// ============================================================
async function listCourses(userId) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_courses').select('*')
        .eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listCourses = listCourses;
async function getCourse(courseId) {
    const db = (0, shared_1.getSupabase)();
    const { data: course, error } = await db.from('enrolly_courses').select('*').eq('id', courseId).single();
    if (error)
        return { success: false, error: error.message };
    const { data: modules } = await db.from('enrolly_modules').select('*')
        .eq('course_id', courseId).order('sort_order');
    const { data: lessons } = await db.from('enrolly_lessons').select('*')
        .eq('course_id', courseId).order('sort_order');
    // Group lessons by module
    const enriched = (modules || []).map((mod) => ({
        ...mod,
        lessons: (lessons || []).filter((l) => l.module_id === mod.id),
    }));
    return { success: true, data: { ...course, modules: enriched } };
}
exports.getCourse = getCourse;
async function createCourse(userId, course) {
    const db = (0, shared_1.getSupabase)();
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
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createCourse = createCourse;
async function updateCourse(courseId, updates) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_courses').update(updates).eq('id', courseId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateCourse = updateCourse;
async function publishCourse(courseId, publish) {
    return updateCourse(courseId, { is_published: publish });
}
exports.publishCourse = publishCourse;
// ============================================================
// Modules
// ============================================================
async function createModule(courseId, title, sortOrder) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_modules').insert({
        course_id: courseId, title, sort_order: sortOrder, drip_day: null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createModule = createModule;
async function updateModule(moduleId, updates) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_modules').update(updates).eq('id', moduleId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateModule = updateModule;
async function deleteModule(moduleId) {
    const db = (0, shared_1.getSupabase)();
    await db.from('enrolly_lessons').delete().eq('module_id', moduleId);
    const { error } = await db.from('enrolly_modules').delete().eq('id', moduleId);
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.deleteModule = deleteModule;
// ============================================================
// Lessons
// ============================================================
async function createLesson(moduleId, courseId, lesson) {
    const db = (0, shared_1.getSupabase)();
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
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createLesson = createLesson;
async function updateLesson(lessonId, updates) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_lessons').update(updates).eq('id', lessonId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateLesson = updateLesson;
async function deleteLesson(lessonId) {
    const db = (0, shared_1.getSupabase)();
    const { error } = await db.from('enrolly_lessons').delete().eq('id', lessonId);
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.deleteLesson = deleteLesson;
// ============================================================
// Video Upload
// ============================================================
async function requestVideoUpload(userId, originalName, mimeType, sizeBytes) {
    const db = (0, shared_1.getSupabase)();
    const storageKey = `videos/${userId}/${Date.now()}-${originalName}`;
    const { data, error } = await db.from('enrolly_videos').insert({
        user_id: userId, original_name: originalName,
        storage_key: storageKey, mime_type: mimeType,
        size_bytes: sizeBytes, duration_sec: 0,
        thumbnail_url: '', status: 'uploading',
        hls_url: null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    // Get signed upload URL from storage
    const storage = (0, shared_1.getSupabase)().storage.from('enrolly-media');
    const { data: uploadData } = await storage.createSignedUploadUrl(storageKey);
    return { success: true, data: { ...data, upload_url: uploadData?.signedUrl } };
}
exports.requestVideoUpload = requestVideoUpload;
async function confirmVideoUpload(videoId) {
    const db = (0, shared_1.getSupabase)();
    // In production: trigger transcoding pipeline (FFmpeg → HLS)
    const { data, error } = await db.from('enrolly_videos').update({
        status: 'ready', // In production: 'processing' → webhook → 'ready'
    }).eq('id', videoId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.confirmVideoUpload = confirmVideoUpload;
async function listVideos(userId) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_videos').select('*')
        .eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listVideos = listVideos;
// ============================================================
// Enrollment & Progress
// ============================================================
async function enrollStudent(courseId, contactId) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_enrollments').upsert({
        course_id: courseId, contact_id: contactId,
        status: 'active', enrolled_at: new Date().toISOString(),
        drip_start_date: new Date().toISOString(),
        completed_lessons: [], progress_pct: 0,
    }, { onConflict: 'course_id,contact_id' }).select().single();
    if (error)
        return { success: false, error: error.message };
    // Increment enrollment count
    const { data: course } = await db.from('enrolly_courses').select('enrollment_count').eq('id', courseId).single();
    if (course) {
        await db.from('enrolly_courses').update({
            enrollment_count: (course.enrollment_count || 0) + 1,
        }).eq('id', courseId);
    }
    return { success: true, data };
}
exports.enrollStudent = enrollStudent;
async function getEnrollment(courseId, contactId) {
    const db = (0, shared_1.getSupabase)();
    const { data: enrollment } = await db.from('enrolly_enrollments').select('*')
        .eq('course_id', courseId).eq('contact_id', contactId).single();
    if (!enrollment)
        return { success: false, error: 'Not enrolled' };
    const { data: course } = await db.from('enrolly_courses').select('*').eq('id', courseId).single();
    const { data: modules } = await db.from('enrolly_modules').select('*').eq('course_id', courseId).order('sort_order');
    const { data: lessons } = await db.from('enrolly_lessons').select('*').eq('course_id', courseId).order('sort_order');
    // Apply drip logic
    let availableLessons = lessons || [];
    if (course?.drip_enabled) {
        const daysSinceEnroll = Math.floor((Date.now() - new Date(enrollment.drip_start_date).getTime()) / 86400000);
        availableLessons = availableLessons.filter((l) => {
            const mod = (modules || []).find((m) => m.id === l.module_id);
            return !mod?.drip_day || mod.drip_day <= daysSinceEnroll;
        });
    }
    return { success: true, data: { ...enrollment, course, available_lessons: availableLessons } };
}
exports.getEnrollment = getEnrollment;
async function completeLesson(enrollmentId, lessonId) {
    const db = (0, shared_1.getSupabase)();
    const { data: enrollment } = await db.from('enrolly_enrollments').select('*').eq('id', enrollmentId).single();
    if (!enrollment)
        return { success: false, error: 'Enrollment not found' };
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
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.completeLesson = completeLesson;
async function trackVideoProgress(enrollmentId, lessonId, watchedSec) {
    const db = (0, shared_1.getSupabase)();
    const { data, error } = await db.from('enrolly_lesson_progress').upsert({
        enrollment_id: enrollmentId, lesson_id: lessonId,
        status: 'in_progress', video_watched_sec: watchedSec,
    }, { onConflict: 'enrollment_id,lesson_id' }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.trackVideoProgress = trackVideoProgress;
async function listEnrollments(courseId, page = 1, perPage = 20) {
    const db = (0, shared_1.getSupabase)();
    const { data, error, count } = await db.from('enrolly_enrollments').select('*', { count: 'exact' })
        .eq('course_id', courseId).order('enrolled_at', { ascending: false })
        .range((page - 1) * perPage, page * perPage - 1);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}
exports.listEnrollments = listEnrollments;
