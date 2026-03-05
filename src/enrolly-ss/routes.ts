// ============================================================
// Enrolly SS - API Routes (English-market membership platform)
// ============================================================

import { Router } from 'express';
import type { Request, Response } from 'express';
import { isDemoMode } from './shared';
import * as memberSvc from './membership-service';

const router = Router();

// Health / Status
router.get('/api/status', (_req: Request, res: Response) => {
  res.json({
    success: true,
    data: {
      name: 'Enrolly',
      version: '1.0.0',
      demo: isDemoMode(),
      features: [
        'courses', 'modules', 'lessons', 'video_upload', 'video_streaming',
        'enrollment', 'drip_content', 'progress_tracking', 'quiz',
        'discussion', 'certificates', 'stripe_payments',
      ],
    },
  });
});

// Helper
function auth(req: Request, res: Response): string | null {
  const u = req.headers['x-user-id'] as string || null;
  if (!u) { res.status(401).json({ success: false, error: 'Authentication required' }); return null; }
  return u;
}

// Auto-assign demo user
router.use((req: Request, _res: Response, next: Function) => {
  if (isDemoMode() && !req.headers['x-user-id']) {
    (req.headers as any)['x-user-id'] = 'demo-user-001';
  }
  next();
});

// ============================================================
// Courses
// ============================================================
router.get('/api/courses', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.listCourses(u));
});

router.get('/api/courses/:id', async (req, res) => {
  res.json(await memberSvc.getCourse(req.params.id));
});

router.post('/api/courses', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  if (!req.body.title) return res.status(400).json({ success: false, error: 'title required' });
  res.status(201).json(await memberSvc.createCourse(u, req.body));
});

router.patch('/api/courses/:id', async (req, res) => {
  res.json(await memberSvc.updateCourse(req.params.id, req.body));
});

router.post('/api/courses/:id/publish', async (req, res) => {
  const { publish } = req.body;
  res.json(await memberSvc.publishCourse(req.params.id, publish !== false));
});

// ============================================================
// Modules
// ============================================================
router.post('/api/courses/:courseId/modules', async (req, res) => {
  const { title, sort_order } = req.body;
  res.status(201).json(await memberSvc.createModule(req.params.courseId, title || 'New Module', sort_order || 0));
});

router.patch('/api/modules/:id', async (req, res) => {
  res.json(await memberSvc.updateModule(req.params.id, req.body));
});

router.delete('/api/modules/:id', async (req, res) => {
  res.json(await memberSvc.deleteModule(req.params.id));
});

// ============================================================
// Lessons
// ============================================================
router.post('/api/modules/:moduleId/lessons', async (req, res) => {
  const { course_id } = req.body;
  if (!course_id) return res.status(400).json({ success: false, error: 'course_id required' });
  res.status(201).json(await memberSvc.createLesson(req.params.moduleId, course_id, req.body));
});

router.patch('/api/lessons/:id', async (req, res) => {
  res.json(await memberSvc.updateLesson(req.params.id, req.body));
});

router.delete('/api/lessons/:id', async (req, res) => {
  res.json(await memberSvc.deleteLesson(req.params.id));
});

// ============================================================
// Video Upload
// ============================================================
router.post('/api/videos/upload', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const { original_name, mime_type, size_bytes } = req.body;
  if (!original_name || !mime_type) return res.status(400).json({ success: false, error: 'original_name and mime_type required' });
  res.json(await memberSvc.requestVideoUpload(u, original_name, mime_type, size_bytes || 0));
});

router.post('/api/videos/:id/confirm', async (req, res) => {
  res.json(await memberSvc.confirmVideoUpload(req.params.id));
});

router.get('/api/videos', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.listVideos(u));
});

// ============================================================
// Enrollment & Student Progress
// ============================================================
router.post('/api/courses/:courseId/enroll', async (req, res) => {
  const { contact_id } = req.body;
  if (!contact_id) return res.status(400).json({ success: false, error: 'contact_id required' });
  res.json(await memberSvc.enrollStudent(req.params.courseId, contact_id));
});

router.get('/api/courses/:courseId/enrollment', async (req, res) => {
  const contactId = req.query.contact_id as string;
  if (!contactId) return res.status(400).json({ success: false, error: 'contact_id query param required' });
  res.json(await memberSvc.getEnrollment(req.params.courseId, contactId));
});

router.get('/api/courses/:courseId/enrollments', async (req, res) => {
  res.json(await memberSvc.listEnrollments(req.params.courseId, parseInt(req.query.page as string) || 1));
});

router.post('/api/enrollments/:id/complete-lesson', async (req, res) => {
  const { lesson_id } = req.body;
  if (!lesson_id) return res.status(400).json({ success: false, error: 'lesson_id required' });
  res.json(await memberSvc.completeLesson(req.params.id, lesson_id));
});

router.post('/api/enrollments/:id/video-progress', async (req, res) => {
  const { lesson_id, watched_sec } = req.body;
  res.json(await memberSvc.trackVideoProgress(req.params.id, lesson_id, watched_sec || 0));
});

// ============================================================
// Frontend
// ============================================================
router.get('/', (_req, res) => {
  res.sendFile('enrolly.html', { root: 'public' });
});

export default router;
