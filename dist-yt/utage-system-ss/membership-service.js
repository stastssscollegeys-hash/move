"use strict";
// ============================================================
// Membership Site Service (Courses / Lessons / Enrollments)
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.createBundle = exports.listComments = exports.addComment = exports.listEnrollments = exports.completeLesson = exports.getEnrollment = exports.enrollContact = exports.deleteLesson = exports.updateLesson = exports.addLesson = exports.updateCourse = exports.getCourse = exports.createCourse = exports.listCourses = void 0;
const db_1 = require("./db");
// --- Courses ---
async function listCourses(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('courses').select('*, lessons(*)').eq('user_id', userId).order('updated_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: (data || []).map((c) => ({ ...c, lessons: c.lessons || [] })) };
}
exports.listCourses = listCourses;
async function createCourse(userId, course) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('courses').insert({
        user_id: userId, name: course.name, description: course.description || '',
        access_type: course.access_type || 'paid', product_id: course.product_id || null,
        thumbnail_url: course.thumbnail_url || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: { ...data, lessons: [] } };
}
exports.createCourse = createCourse;
async function getCourse(userId, courseId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('courses').select('*, lessons(*, media_files(*))').eq('id', courseId).eq('user_id', userId).single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: { ...data, lessons: data.lessons || [] } };
}
exports.getCourse = getCourse;
async function updateCourse(courseId, updates) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('courses').update(updates).eq('id', courseId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateCourse = updateCourse;
// --- Lessons ---
async function addLesson(courseId, lesson) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('lessons').insert({
        course_id: courseId, title: lesson.title, description: lesson.description || '',
        content_type: lesson.content_type || 'video', media_id: lesson.media_id || null,
        content_html: lesson.content_html || null, sort_order: lesson.sort_order || 0,
        drip_days: lesson.drip_days || null, is_preview: lesson.is_preview || false,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.addLesson = addLesson;
async function updateLesson(lessonId, updates) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('lessons').update(updates).eq('id', lessonId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateLesson = updateLesson;
async function deleteLesson(lessonId) {
    const db = (0, db_1.getSupabase)();
    const { error } = await db.from('lessons').delete().eq('id', lessonId);
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.deleteLesson = deleteLesson;
// --- Enrollments ---
async function enrollContact(contactId, courseId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('enrollments').upsert({
        contact_id: contactId, course_id: courseId,
    }, { onConflict: 'contact_id,course_id' }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.enrollContact = enrollContact;
async function getEnrollment(contactId, courseId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('enrollments').select('*').eq('contact_id', contactId).eq('course_id', courseId).single();
    if (error)
        return { success: false, error: 'Not enrolled' };
    return { success: true, data };
}
exports.getEnrollment = getEnrollment;
async function completeLesson(contactId, courseId, lessonId) {
    const db = (0, db_1.getSupabase)();
    const { data: enrollment, error: getErr } = await db.from('enrollments').select('*').eq('contact_id', contactId).eq('course_id', courseId).single();
    if (getErr)
        return { success: false, error: 'Not enrolled' };
    const completed = [...new Set([...(enrollment.completed_lessons || []), lessonId])];
    const { data: lessons } = await db.from('lessons').select('id').eq('course_id', courseId);
    const totalLessons = (lessons || []).length;
    const progressPercent = totalLessons > 0 ? Math.round((completed.length / totalLessons) * 100) : 0;
    const { data, error } = await db.from('enrollments').update({
        completed_lessons: completed, progress_percent: progressPercent, last_accessed_at: new Date().toISOString(),
    }).eq('id', enrollment.id).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.completeLesson = completeLesson;
async function listEnrollments(courseId, page = 1, perPage = 20) {
    const db = (0, db_1.getSupabase)();
    const { data, error, count } = await db.from('enrollments').select('*, contacts(name, email)', { count: 'exact' })
        .eq('course_id', courseId).order('enrolled_at', { ascending: false })
        .range((page - 1) * perPage, page * perPage - 1);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}
exports.listEnrollments = listEnrollments;
// --- Comments ---
async function addComment(lessonId, contactId, content) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('lesson_comments').insert({ lesson_id: lessonId, contact_id: contactId, content }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.addComment = addComment;
async function listComments(lessonId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('lesson_comments').select('*, contacts(name)').eq('lesson_id', lessonId).order('created_at', { ascending: true });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listComments = listComments;
// --- Bundle ---
async function createBundle(userId, name, courseIds, productId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('bundle_courses').insert({
        user_id: userId, name, course_ids: courseIds, product_id: productId || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createBundle = createBundle;
