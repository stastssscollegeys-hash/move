// ============================================================
// UTAGE System SS - Full API Routes
// ============================================================

import { Router } from 'express';
import type { Request, Response } from 'express';
import * as ctrl from './controller';
import * as mediaSvc from './media-service';
import * as memberSvc from './membership-service';
import * as eventSvc from './event-service';
import * as webinarSvc from './webinar-service';
import * as affiliateSvc from './affiliate-service';
import * as analyticsSvc from './analytics-service';

const router = Router();

// Helper
function uid(req: Request): string | null {
  return (req as any).userId || req.headers['x-user-id'] as string || null;
}
function auth(req: Request, res: Response): string | null {
  const u = uid(req);
  if (!u) { res.status(401).json({ success: false, error: 'Authentication required' }); return null; }
  return u;
}

// Health
router.get('/api/health', ctrl.health);

// Dashboard
router.get('/api/dashboard', ctrl.getDashboard);

// ============================================================
// CRM: Contacts & Tags
// ============================================================
router.get('/api/contacts', ctrl.listContacts);
router.post('/api/contacts', ctrl.createContact);
router.get('/api/contacts/:id', ctrl.getContact);
router.post('/api/contacts/:id/tags', ctrl.addTag);
router.delete('/api/contacts/:id/tags/:tagId', ctrl.removeTag);
router.get('/api/tags', ctrl.listTags);
router.post('/api/tags', ctrl.createTagHandler);

// ============================================================
// Funnels
// ============================================================
router.get('/api/funnels', ctrl.listFunnels);
router.post('/api/funnels', ctrl.createFunnel);
router.post('/api/funnels/:funnelId/pages', ctrl.createPage);
router.patch('/api/funnels/pages/:pageId', ctrl.updatePage);
router.get('/p/:slug', ctrl.getPublishedPage);

// ============================================================
// Email
// ============================================================
router.get('/api/email/scenarios', ctrl.listEmailScenarios);
router.post('/api/email/scenarios', ctrl.createEmailScenario);
router.post('/api/email/scenarios/:scenarioId/steps', ctrl.addEmailStep);

// ============================================================
// LINE
// ============================================================
router.get('/api/line/scenarios', ctrl.listLineScenarios);
router.post('/api/line/scenarios', ctrl.createLineScenario);

// ============================================================
// Products
// ============================================================
router.get('/api/products', ctrl.listProducts);
router.post('/api/products', ctrl.createProduct);

// ============================================================
// Media Management
// ============================================================
router.get('/api/media', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const r = await mediaSvc.listMedia(u, req.query.type as string, req.query.folder as string, parseInt(req.query.page as string) || 1);
  res.json(r);
});
router.post('/api/media/upload-url', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const { original_name, mime_type, size_bytes, folder } = req.body;
  if (!original_name || !mime_type) return res.status(400).json({ success: false, error: 'original_name and mime_type required' });
  const r = await mediaSvc.getUploadUrl(u, original_name, mime_type, size_bytes || 0, folder);
  res.json(r);
});
router.post('/api/media/:id/confirm', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const r = await mediaSvc.confirmUpload(req.params.id, u);
  res.json(r);
});
router.delete('/api/media/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const r = await mediaSvc.deleteMedia(req.params.id, u);
  res.json(r);
});

// ============================================================
// Membership: Courses & Lessons
// ============================================================
router.get('/api/courses', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.listCourses(u));
});
router.post('/api/courses', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const { name, description, access_type, product_id, thumbnail_url } = req.body;
  if (!name) return res.status(400).json({ success: false, error: 'name required' });
  res.status(201).json(await memberSvc.createCourse(u, { name, description, access_type, product_id, thumbnail_url }));
});
router.get('/api/courses/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.getCourse(u, req.params.id));
});
router.patch('/api/courses/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.updateCourse(req.params.id, req.body));
});
router.post('/api/courses/:courseId/lessons', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await memberSvc.addLesson(req.params.courseId, req.body));
});
router.patch('/api/lessons/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.updateLesson(req.params.id, req.body));
});
router.delete('/api/lessons/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await memberSvc.deleteLesson(req.params.id));
});
router.post('/api/courses/:courseId/enroll', async (req, res) => {
  const { contact_id } = req.body;
  res.json(await memberSvc.enrollContact(contact_id, req.params.courseId));
});
router.post('/api/courses/:courseId/lessons/:lessonId/complete', async (req, res) => {
  const { contact_id } = req.body;
  res.json(await memberSvc.completeLesson(contact_id, req.params.courseId, req.params.lessonId));
});
router.get('/api/courses/:courseId/enrollments', async (req, res) => {
  res.json(await memberSvc.listEnrollments(req.params.courseId));
});
router.get('/api/lessons/:lessonId/comments', async (req, res) => {
  res.json(await memberSvc.listComments(req.params.lessonId));
});
router.post('/api/lessons/:lessonId/comments', async (req, res) => {
  const { contact_id, content } = req.body;
  res.status(201).json(await memberSvc.addComment(req.params.lessonId, contact_id, content));
});
router.post('/api/bundles', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  const { name, course_ids, product_id } = req.body;
  res.status(201).json(await memberSvc.createBundle(u, name, course_ids, product_id));
});

// ============================================================
// Events & Calendar
// ============================================================
router.get('/api/events', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await eventSvc.listEvents(u));
});
router.post('/api/events', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await eventSvc.createEvent(u, req.body));
});
router.get('/api/events/:id', async (req, res) => {
  res.json(await eventSvc.getEvent(req.params.id));
});
router.patch('/api/events/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await eventSvc.updateEvent(req.params.id, req.body));
});
router.post('/api/events/:id/reserve', async (req, res) => {
  const { contact_id, order_id } = req.body;
  res.json(await eventSvc.reserveEvent(req.params.id, contact_id, order_id));
});
router.get('/api/events/:id/reservations', async (req, res) => {
  res.json(await eventSvc.listReservations(req.params.id));
});
router.patch('/api/reservations/:id/cancel', async (req, res) => {
  res.json(await eventSvc.cancelReservation(req.params.id));
});
router.patch('/api/reservations/:id/attendance', async (req, res) => {
  res.json(await eventSvc.markAttendance(req.params.id, req.body.status));
});

// Calendar
router.get('/api/calendar/slots', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await eventSvc.listCalendarSlots(u));
});
router.post('/api/calendar/slots', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await eventSvc.createCalendarSlot(u, req.body));
});
router.get('/api/calendar/slots/:id/available', async (req, res) => {
  const date = req.query.date as string;
  if (!date) return res.status(400).json({ success: false, error: 'date required (YYYY-MM-DD)' });
  res.json(await eventSvc.getAvailableSlots(req.params.id, date));
});
router.post('/api/calendar/slots/:id/book', async (req, res) => {
  const { contact_id, start_at } = req.body;
  res.json(await eventSvc.bookSlot(req.params.id, contact_id, start_at));
});
router.get('/api/calendar/bookings', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await eventSvc.listBookings(u, req.query.from as string, req.query.to as string));
});

// ============================================================
// Webinars
// ============================================================
router.get('/api/webinars', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await webinarSvc.listWebinars(u));
});
router.post('/api/webinars', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await webinarSvc.createWebinar(u, req.body));
});
router.get('/api/webinars/:id', async (req, res) => {
  res.json(await webinarSvc.getWebinar(req.params.id));
});
router.patch('/api/webinars/:id', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await webinarSvc.updateWebinar(req.params.id, req.body));
});
router.post('/api/webinars/:id/start', async (req, res) => {
  res.json(await webinarSvc.startWebinar(req.params.id));
});
router.post('/api/webinars/:id/end', async (req, res) => {
  res.json(await webinarSvc.endWebinar(req.params.id));
});
router.post('/api/webinars/:id/register', async (req, res) => {
  res.json(await webinarSvc.registerAttendee(req.params.id, req.body.contact_id));
});
router.post('/api/webinars/:id/join', async (req, res) => {
  res.json(await webinarSvc.joinWebinar(req.params.id, req.body.contact_id));
});
router.post('/api/webinars/:id/leave', async (req, res) => {
  res.json(await webinarSvc.leaveWebinar(req.params.id, req.body.contact_id, req.body.watched_seconds));
});
router.get('/api/webinars/:id/attendees', async (req, res) => {
  res.json(await webinarSvc.listAttendees(req.params.id));
});
router.post('/api/webinars/:id/chat', async (req, res) => {
  res.json(await webinarSvc.sendChatMessage(req.params.id, req.body.contact_id, req.body.message));
});
router.get('/api/webinars/:id/chat', async (req, res) => {
  res.json(await webinarSvc.listChatMessages(req.params.id, req.query.after as string));
});
router.post('/api/webinars/:id/polls', async (req, res) => {
  res.status(201).json(await webinarSvc.createPoll(req.params.id, req.body.question, req.body.options));
});
router.post('/api/webinars/polls/:pollId/vote', async (req, res) => {
  res.json(await webinarSvc.votePoll(req.params.pollId, req.body.option));
});
router.post('/api/webinars/polls/:pollId/close', async (req, res) => {
  res.json(await webinarSvc.closePoll(req.params.pollId));
});
router.post('/api/webinars/:id/popup-offers', async (req, res) => {
  res.json(await webinarSvc.addPopupOffer(req.params.id, req.body));
});

// ============================================================
// Affiliate
// ============================================================
router.get('/api/affiliate/programs', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await affiliateSvc.listPrograms(u));
});
router.post('/api/affiliate/programs', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await affiliateSvc.createProgram(u, req.body));
});
router.get('/api/affiliate/programs/:id/partners', async (req, res) => {
  res.json(await affiliateSvc.listPartners(req.params.id));
});
router.get('/api/affiliate/programs/:id/ranking', async (req, res) => {
  res.json(await affiliateSvc.getPartnerRanking(req.params.id, parseInt(req.query.limit as string) || 10));
});
router.post('/api/affiliate/programs/:id/partners', async (req, res) => {
  res.status(201).json(await affiliateSvc.registerPartner(req.params.id, req.body.contact_id, req.body.parent_partner_id));
});
router.patch('/api/affiliate/partners/:id/approve', async (req, res) => {
  res.json(await affiliateSvc.approvePartner(req.params.id));
});
router.get('/api/affiliate/partners/:id/referrals', async (req, res) => {
  res.json(await affiliateSvc.listReferrals(req.params.id));
});
router.patch('/api/affiliate/referrals/:id/approve', async (req, res) => {
  res.json(await affiliateSvc.approveReferral(req.params.id));
});
router.patch('/api/affiliate/referrals/:id/paid', async (req, res) => {
  res.json(await affiliateSvc.markReferralPaid(req.params.id));
});

// ============================================================
// Forms
// ============================================================
router.get('/api/forms', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await analyticsSvc.listForms(u));
});
router.post('/api/forms', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await analyticsSvc.createForm(u, req.body));
});
router.post('/api/forms/:id/submit', async (req, res) => {
  const { contact_id, responses } = req.body;
  res.json(await analyticsSvc.submitForm(req.params.id, contact_id, responses));
});
router.get('/api/forms/:id/submissions', async (req, res) => {
  res.json(await analyticsSvc.listFormSubmissions(req.params.id));
});

// ============================================================
// Analytics & Tracking
// ============================================================
router.get('/api/analytics/ad-trackings', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await analyticsSvc.listAdTrackings(u));
});
router.post('/api/analytics/ad-trackings', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await analyticsSvc.createAdTracking(u, req.body));
});
router.get('/api/analytics/clicks', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await analyticsSvc.getClickStats(u, req.query.source_type as string, req.query.period as string));
});
router.get('/api/analytics/conversions', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await analyticsSvc.getConversionStats(u, (req.query.period as string) || '30d'));
});
router.post('/api/analytics/cross', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await analyticsSvc.crossAnalysis(u, req.body));
});
router.post('/api/analytics/track-click', async (req, res) => {
  const { contact_id, url, source_type, source_id } = req.body;
  res.json(await analyticsSvc.trackClick(contact_id, url, source_type, source_id));
});
router.post('/api/analytics/track-conversion', async (req, res) => {
  const { contact_id, event_type, event_data, source, utm } = req.body;
  res.json(await analyticsSvc.trackConversion(contact_id, event_type, event_data || {}, source, utm));
});

// ============================================================
// Webhooks
// ============================================================
router.get('/api/webhooks', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.json(await analyticsSvc.listWebhookEndpoints(u));
});
router.post('/api/webhooks', async (req, res) => {
  const u = auth(req, res); if (!u) return;
  res.status(201).json(await analyticsSvc.createWebhookEndpoint(u, req.body));
});
router.get('/api/webhooks/:id/logs', async (req, res) => {
  res.json(await analyticsSvc.listWebhookLogs(req.params.id));
});

// ============================================================
// Frontend (SPA)
// ============================================================
router.get('/', (_req, res) => {
  res.sendFile('utage-system.html', { root: 'public' });
});

export default router;
