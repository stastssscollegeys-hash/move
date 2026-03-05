// ============================================================
// UTAGE System SS - API Routes
// Phase 1 MVP
// ============================================================

import { Router } from 'express';
import * as ctrl from './controller';

const router = Router();

// Health
router.get('/api/health', ctrl.health);

// Dashboard
router.get('/api/dashboard', ctrl.getDashboard);

// Contacts (CRM)
router.get('/api/contacts', ctrl.listContacts);
router.post('/api/contacts', ctrl.createContact);
router.get('/api/contacts/:id', ctrl.getContact);
router.post('/api/contacts/:id/tags', ctrl.addTag);
router.delete('/api/contacts/:id/tags/:tagId', ctrl.removeTag);

// Tags
router.get('/api/tags', ctrl.listTags);
router.post('/api/tags', ctrl.createTagHandler);

// Funnels
router.get('/api/funnels', ctrl.listFunnels);
router.post('/api/funnels', ctrl.createFunnel);
router.post('/api/funnels/:funnelId/pages', ctrl.createPage);
router.patch('/api/funnels/pages/:pageId', ctrl.updatePage);

// Published funnel pages (public)
router.get('/p/:slug', ctrl.getPublishedPage);

// Email Scenarios
router.get('/api/email/scenarios', ctrl.listEmailScenarios);
router.post('/api/email/scenarios', ctrl.createEmailScenario);
router.post('/api/email/scenarios/:scenarioId/steps', ctrl.addEmailStep);

// LINE Scenarios
router.get('/api/line/scenarios', ctrl.listLineScenarios);
router.post('/api/line/scenarios', ctrl.createLineScenario);

// Products
router.get('/api/products', ctrl.listProducts);
router.post('/api/products', ctrl.createProduct);

// --- Frontend (SPA) ---
router.get('/', (_req, res) => {
  res.sendFile('utage-system.html', { root: 'public' });
});

export default router;
