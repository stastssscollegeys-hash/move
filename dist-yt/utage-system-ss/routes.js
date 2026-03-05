"use strict";
// ============================================================
// UTAGE System SS - Full API Routes
// ============================================================
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const ctrl = __importStar(require("./controller"));
const svc = __importStar(require("./service"));
const mediaSvc = __importStar(require("./media-service"));
const memberSvc = __importStar(require("./membership-service"));
const eventSvc = __importStar(require("./event-service"));
const webinarSvc = __importStar(require("./webinar-service"));
const affiliateSvc = __importStar(require("./affiliate-service"));
const analyticsSvc = __importStar(require("./analytics-service"));
const stripeSvc = __importStar(require("./stripe-service"));
const lineWebhook = __importStar(require("./line-webhook"));
const broadcastSvc = __importStar(require("./broadcast-service"));
const automationSvc = __importStar(require("./automation-service"));
const lineChatSvc = __importStar(require("./line-chat-service"));
const funnelRenderer = __importStar(require("./funnel-renderer"));
const db_1 = require("./db");
const router = (0, express_1.Router)();
// Health (includes demo mode status)
router.get('/api/status', (_req, res) => {
    res.json({ success: true, data: { version: '1.0.0', demo: (0, db_1.isDemoMode)(), features: ['crm', 'funnel', 'email', 'line', 'sms', 'payment', 'membership', 'webinar', 'event', 'affiliate', 'analytics', 'forms', 'webhooks', 'media', 'broadcast', 'automation', 'chat', 'richmenu', 'csv_export', 'ab_test', 'page_renderer', 'segments', 'domain_auth', 'countdown_timer'] } });
});
// Auto-assign demo user in demo mode
router.use((req, _res, next) => {
    if ((0, db_1.isDemoMode)() && !req.headers['x-user-id']) {
        req.headers['x-user-id'] = 'demo-user-001';
    }
    next();
});
// Helper
function uid(req) {
    return req.userId || req.headers['x-user-id'] || null;
}
function auth(req, res) {
    const u = uid(req);
    if (!u) {
        res.status(401).json({ success: false, error: 'Authentication required' });
        return null;
    }
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
    const u = auth(req, res);
    if (!u)
        return;
    const r = await mediaSvc.listMedia(u, req.query.type, req.query.folder, parseInt(req.query.page) || 1);
    res.json(r);
});
router.post('/api/media/upload-url', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const { original_name, mime_type, size_bytes, folder } = req.body;
    if (!original_name || !mime_type)
        return res.status(400).json({ success: false, error: 'original_name and mime_type required' });
    const r = await mediaSvc.getUploadUrl(u, original_name, mime_type, size_bytes || 0, folder);
    res.json(r);
});
router.post('/api/media/:id/confirm', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const r = await mediaSvc.confirmUpload(req.params.id, u);
    res.json(r);
});
router.delete('/api/media/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const r = await mediaSvc.deleteMedia(req.params.id, u);
    res.json(r);
});
// ============================================================
// Membership: Courses & Lessons
// ============================================================
router.get('/api/courses', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await memberSvc.listCourses(u));
});
router.post('/api/courses', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const { name, description, access_type, product_id, thumbnail_url } = req.body;
    if (!name)
        return res.status(400).json({ success: false, error: 'name required' });
    res.status(201).json(await memberSvc.createCourse(u, { name, description, access_type, product_id, thumbnail_url }));
});
router.get('/api/courses/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await memberSvc.getCourse(u, req.params.id));
});
router.patch('/api/courses/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await memberSvc.updateCourse(req.params.id, req.body));
});
router.post('/api/courses/:courseId/lessons', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await memberSvc.addLesson(req.params.courseId, req.body));
});
router.patch('/api/lessons/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await memberSvc.updateLesson(req.params.id, req.body));
});
router.delete('/api/lessons/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
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
    const u = auth(req, res);
    if (!u)
        return;
    const { name, course_ids, product_id } = req.body;
    res.status(201).json(await memberSvc.createBundle(u, name, course_ids, product_id));
});
// ============================================================
// Events & Calendar
// ============================================================
router.get('/api/events', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await eventSvc.listEvents(u));
});
router.post('/api/events', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await eventSvc.createEvent(u, req.body));
});
router.get('/api/events/:id', async (req, res) => {
    res.json(await eventSvc.getEvent(req.params.id));
});
router.patch('/api/events/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
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
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await eventSvc.listCalendarSlots(u));
});
router.post('/api/calendar/slots', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await eventSvc.createCalendarSlot(u, req.body));
});
router.get('/api/calendar/slots/:id/available', async (req, res) => {
    const date = req.query.date;
    if (!date)
        return res.status(400).json({ success: false, error: 'date required (YYYY-MM-DD)' });
    res.json(await eventSvc.getAvailableSlots(req.params.id, date));
});
router.post('/api/calendar/slots/:id/book', async (req, res) => {
    const { contact_id, start_at } = req.body;
    res.json(await eventSvc.bookSlot(req.params.id, contact_id, start_at));
});
router.get('/api/calendar/bookings', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await eventSvc.listBookings(u, req.query.from, req.query.to));
});
// ============================================================
// Webinars
// ============================================================
router.get('/api/webinars', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await webinarSvc.listWebinars(u));
});
router.post('/api/webinars', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await webinarSvc.createWebinar(u, req.body));
});
router.get('/api/webinars/:id', async (req, res) => {
    res.json(await webinarSvc.getWebinar(req.params.id));
});
router.patch('/api/webinars/:id', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
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
    res.json(await webinarSvc.listChatMessages(req.params.id, req.query.after));
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
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await affiliateSvc.listPrograms(u));
});
router.post('/api/affiliate/programs', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await affiliateSvc.createProgram(u, req.body));
});
router.get('/api/affiliate/programs/:id/partners', async (req, res) => {
    res.json(await affiliateSvc.listPartners(req.params.id));
});
router.get('/api/affiliate/programs/:id/ranking', async (req, res) => {
    res.json(await affiliateSvc.getPartnerRanking(req.params.id, parseInt(req.query.limit) || 10));
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
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await analyticsSvc.listForms(u));
});
router.post('/api/forms', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
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
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await analyticsSvc.listAdTrackings(u));
});
router.post('/api/analytics/ad-trackings', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await analyticsSvc.createAdTracking(u, req.body));
});
router.get('/api/analytics/clicks', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await analyticsSvc.getClickStats(u, req.query.source_type, req.query.period));
});
router.get('/api/analytics/conversions', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await analyticsSvc.getConversionStats(u, req.query.period || '30d'));
});
router.post('/api/analytics/cross', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
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
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await analyticsSvc.listWebhookEndpoints(u));
});
router.post('/api/webhooks', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await analyticsSvc.createWebhookEndpoint(u, req.body));
});
router.get('/api/webhooks/:id/logs', async (req, res) => {
    res.json(await analyticsSvc.listWebhookLogs(req.params.id));
});
// ============================================================
// Stripe Payments
// ============================================================
router.post('/api/checkout', async (req, res) => {
    const { contact_id, product_id, success_url, cancel_url } = req.body;
    if (!contact_id || !product_id)
        return res.status(400).json({ success: false, error: 'contact_id and product_id required' });
    const baseUrl = process.env.APP_URL || `${req.protocol}://${req.get('host')}`;
    res.json(await stripeSvc.createCheckoutSession(contact_id, product_id, success_url || `${baseUrl}/utage/checkout-success`, cancel_url || `${baseUrl}/utage/checkout-cancel`));
});
router.post('/api/customer-portal', async (req, res) => {
    const { contact_id, return_url } = req.body;
    if (!contact_id)
        return res.status(400).json({ success: false, error: 'contact_id required' });
    const baseUrl = process.env.APP_URL || `${req.protocol}://${req.get('host')}`;
    res.json(await stripeSvc.createPortalSession(contact_id, return_url || `${baseUrl}/utage`));
});
// Stripe webhook (needs raw body - mounted separately in app.ts)
// ============================================================
// LINE Webhook
// ============================================================
router.post('/api/line/webhook', async (req, res) => {
    const signature = req.headers['x-line-signature'];
    const body = JSON.stringify(req.body);
    if (!lineWebhook.verifySignature(body, signature || '')) {
        return res.status(401).json({ success: false, error: 'Invalid signature' });
    }
    await lineWebhook.handleWebhook(req.body.events || []);
    res.status(200).json({ success: true });
});
// ============================================================
// Email Broadcast (一斉送信)
// ============================================================
router.get('/api/email/broadcasts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await broadcastSvc.listEmailBroadcasts(u));
});
router.post('/api/email/broadcasts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await broadcastSvc.createEmailBroadcast(u, req.body));
});
router.post('/api/email/broadcasts/:id/send', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await broadcastSvc.sendEmailBroadcast(req.params.id, u));
});
router.post('/api/email/broadcasts/:id/schedule', async (req, res) => {
    const { scheduled_at } = req.body;
    if (!scheduled_at)
        return res.status(400).json({ success: false, error: 'scheduled_at required' });
    res.json(await broadcastSvc.scheduleEmailBroadcast(req.params.id, scheduled_at));
});
// ============================================================
// LINE Broadcast (一斉送信)
// ============================================================
router.get('/api/line/broadcasts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await broadcastSvc.listLineBroadcasts(u));
});
router.post('/api/line/broadcasts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await broadcastSvc.createLineBroadcast(u, req.body));
});
router.post('/api/line/broadcasts/:id/send', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await broadcastSvc.sendLineBroadcast(req.params.id, u));
});
// ============================================================
// SMS Broadcast
// ============================================================
router.get('/api/sms/broadcasts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await broadcastSvc.listSmsBroadcasts(u));
});
router.post('/api/sms/broadcasts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await broadcastSvc.createSmsBroadcast(u, req.body));
});
router.post('/api/sms/broadcasts/:id/send', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await broadcastSvc.sendSmsBroadcast(req.params.id, u));
});
// ============================================================
// LINE Individual Chat (1対1トーク)
// ============================================================
router.get('/api/line/chats', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await lineChatSvc.listChats(u, parseInt(req.query.page) || 1));
});
router.get('/api/line/chats/:contactId/messages', async (req, res) => {
    res.json(await lineChatSvc.getChatMessages(req.params.contactId, parseInt(req.query.page) || 1));
});
router.post('/api/line/chats/:contactId/send', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const { message_type, content } = req.body;
    res.json(await lineChatSvc.sendChatMessage(u, req.params.contactId, message_type || 'text', content || {}));
});
// ============================================================
// Rich Menu Management (リッチメニュー)
// ============================================================
router.get('/api/line/rich-menus', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await lineChatSvc.listRichMenus(u));
});
router.post('/api/line/rich-menus', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await lineChatSvc.createRichMenu(u, req.body));
});
router.patch('/api/line/rich-menus/:id', async (req, res) => {
    res.json(await lineChatSvc.updateRichMenu(req.params.id, req.body));
});
router.delete('/api/line/rich-menus/:id', async (req, res) => {
    res.json(await lineChatSvc.deleteRichMenu(req.params.id));
});
router.post('/api/line/rich-menus/:id/set-default', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await lineChatSvc.setDefaultRichMenu(u, req.params.id));
});
// ============================================================
// Workflow Automation
// ============================================================
router.get('/api/workflows', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await automationSvc.listWorkflows(u));
});
router.post('/api/workflows', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await automationSvc.createWorkflow(u, req.body));
});
router.patch('/api/workflows/:id', async (req, res) => {
    res.json(await automationSvc.updateWorkflow(req.params.id, req.body));
});
router.post('/api/workflows/:id/toggle', async (req, res) => {
    const { is_active } = req.body;
    res.json(await automationSvc.toggleWorkflow(req.params.id, is_active));
});
router.delete('/api/workflows/:id', async (req, res) => {
    res.json(await automationSvc.deleteWorkflow(req.params.id));
});
// ============================================================
// Segments (セグメント管理)
// ============================================================
router.get('/api/segments', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await svc.listSegments(u));
});
router.post('/api/segments', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.status(201).json(await svc.createSegment(u, req.body));
});
router.patch('/api/segments/:id', async (req, res) => {
    res.json(await svc.updateSegment(req.params.id, req.body));
});
router.delete('/api/segments/:id', async (req, res) => {
    res.json(await svc.deleteSegment(req.params.id));
});
router.post('/api/segments/preview', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const { conditions, logic } = req.body;
    res.json(await svc.previewSegment(u, conditions || [], logic || 'AND'));
});
// ============================================================
// Email Domain Authentication (SPF/DKIM認証)
// ============================================================
router.get('/api/email/domains', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    res.json(await svc.listDomainAuth(u));
});
router.post('/api/email/domains', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const { domain } = req.body;
    if (!domain)
        return res.status(400).json({ success: false, error: 'domain required' });
    res.status(201).json(await svc.addDomainAuth(u, domain));
});
router.post('/api/email/domains/:id/verify', async (req, res) => {
    res.json(await svc.verifyDomain(req.params.id));
});
// ============================================================
// CSV Export
// ============================================================
router.get('/api/export/contacts', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const result = await lineChatSvc.exportContactsCsv(u);
    if (!result.success)
        return res.status(400).json(result);
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="contacts.csv"');
    res.send('\uFEFF' + result.data); // BOM for Excel
});
router.get('/api/export/orders', async (req, res) => {
    const u = auth(req, res);
    if (!u)
        return;
    const result = await lineChatSvc.exportOrdersCsv(u);
    if (!result.success)
        return res.status(400).json(result);
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="orders.csv"');
    res.send('\uFEFF' + result.data);
});
// ============================================================
// Unsubscribe (配信停止 - 特定電子メール法準拠)
// ============================================================
router.get('/api/unsubscribe', async (req, res) => {
    const contactId = req.query.cid;
    if (!contactId)
        return res.status(400).send('Invalid request');
    await automationSvc.unsubscribeContact(contactId, 'email');
    res.send('<html><body style="text-align:center;padding:60px;font-family:sans-serif"><h1>配信停止が完了しました</h1><p>今後メールは届きません。</p></body></html>');
});
// ============================================================
// Funnel Page Renderer (公開ページ表示)
// ============================================================
router.get('/p/:slug', async (req, res) => {
    const visitorId = req.cookies?.vid || `v-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const result = await funnelRenderer.servePublishedPage(req.params.slug, visitorId);
    if (!result.success)
        return res.status(404).send('<h1>ページが見つかりません</h1>');
    // Set visitor cookie
    res.cookie('vid', visitorId, { maxAge: 365 * 24 * 60 * 60 * 1000, httpOnly: true });
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(result.data);
});
// ============================================================
// Frontend (SPA)
// ============================================================
router.get('/', (_req, res) => {
    res.sendFile('utage-system.html', { root: 'public' });
});
router.get('/checkout-success', (_req, res) => {
    res.send('<html><body><h1>お支払いが完了しました</h1><p>ありがとうございます。<a href="/utage">戻る</a></p></body></html>');
});
router.get('/checkout-cancel', (_req, res) => {
    res.send('<html><body><h1>お支払いがキャンセルされました</h1><p><a href="/utage">戻る</a></p></body></html>');
});
exports.default = router;
