// ============================================================
// FunnelForge SS - API Controllers
// Phase 1 MVP
// ============================================================

import type { Request, Response } from 'express';
import * as service from './service';

// --- Helper ---

function getUserId(req: Request): string | null {
  // TODO: Replace with actual auth (Supabase Auth / JWT)
  return (req as any).userId || req.headers['x-user-id'] as string || null;
}

function requireAuth(req: Request, res: Response): string | null {
  const userId = getUserId(req);
  if (!userId) {
    res.status(401).json({ success: false, error: 'Authentication required' });
    return null;
  }
  return userId;
}

// ============================================================
// Contacts
// ============================================================

export async function listContacts(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const query = {
    page: parseInt(req.query.page as string) || 1,
    per_page: Math.min(parseInt(req.query.per_page as string) || 20, 100),
    status: req.query.status as any,
    search: req.query.search as string,
    sort_by: (req.query.sort_by as any) || 'created_at',
    sort_order: (req.query.sort_order as any) || 'desc',
  };

  const result = await service.listContacts(userId, query);
  res.status(result.success ? 200 : 500).json(result);
}

export async function createContact(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { email, line_user_id, name, phone, source } = req.body;
  if (!email && !line_user_id) {
    return res.status(400).json({ success: false, error: 'email or line_user_id is required' });
  }

  const result = await service.createContact(userId, { email, line_user_id, name, phone, source });
  res.status(result.success ? 201 : 500).json(result);
}

export async function getContact(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const result = await service.getContact(userId, req.params.id);
  res.status(result.success ? 200 : 404).json(result);
}

export async function addTag(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { tag_id } = req.body;
  if (!tag_id) return res.status(400).json({ success: false, error: 'tag_id is required' });

  const result = await service.addTagToContact(req.params.id, tag_id);
  res.status(result.success ? 200 : 500).json(result);
}

export async function removeTag(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const result = await service.removeTagFromContact(req.params.id, req.params.tagId);
  res.status(result.success ? 200 : 500).json(result);
}

// ============================================================
// Tags
// ============================================================

export async function listTags(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;
  const result = await service.listTags(userId);
  res.status(result.success ? 200 : 500).json(result);
}

export async function createTagHandler(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { name, color } = req.body;
  if (!name) return res.status(400).json({ success: false, error: 'name is required' });

  const result = await service.createTag(userId, name, color);
  res.status(result.success ? 201 : 500).json(result);
}

// ============================================================
// Funnels
// ============================================================

export async function listFunnels(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;
  const result = await service.listFunnels(userId);
  res.status(result.success ? 200 : 500).json(result);
}

export async function createFunnel(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { name } = req.body;
  if (!name) return res.status(400).json({ success: false, error: 'name is required' });

  const result = await service.createFunnel(userId, name);
  res.status(result.success ? 201 : 500).json(result);
}

export async function createPage(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { title, slug, page_type, elements } = req.body;
  if (!title || !slug || !page_type) {
    return res.status(400).json({ success: false, error: 'title, slug, and page_type are required' });
  }

  const result = await service.createFunnelPage(req.params.funnelId, { title, slug, page_type, elements });
  res.status(result.success ? 201 : 500).json(result);
}

export async function updatePage(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const result = await service.updateFunnelPage(req.params.pageId, req.body);
  res.status(result.success ? 200 : 500).json(result);
}

export async function getPublishedPage(req: Request, res: Response) {
  const result = await service.getPublishedPage(req.params.slug);
  if (!result.success || !result.data) {
    return res.status(404).json({ success: false, error: 'Page not found' });
  }
  // TODO: Track page view
  // TODO: Render as HTML from elements
  res.json(result);
}

// ============================================================
// Email Scenarios
// ============================================================

export async function listEmailScenarios(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;
  const result = await service.listEmailScenarios(userId);
  res.status(result.success ? 200 : 500).json(result);
}

export async function createEmailScenario(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { name, trigger } = req.body;
  if (!name) return res.status(400).json({ success: false, error: 'name is required' });

  const result = await service.createEmailScenario(userId, { name, trigger });
  res.status(result.success ? 201 : 500).json(result);
}

export async function addEmailStep(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { subject, body_html, delay_minutes, sort_order } = req.body;
  if (!subject || !body_html) return res.status(400).json({ success: false, error: 'subject and body_html are required' });

  const result = await service.addEmailStep(req.params.scenarioId, { subject, body_html, delay_minutes, sort_order });
  res.status(result.success ? 201 : 500).json(result);
}

// ============================================================
// LINE Scenarios
// ============================================================

export async function listLineScenarios(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;
  const result = await service.listLineScenarios(userId);
  res.status(result.success ? 200 : 500).json(result);
}

export async function createLineScenario(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { name, trigger } = req.body;
  if (!name) return res.status(400).json({ success: false, error: 'name is required' });

  const result = await service.createLineScenario(userId, { name, trigger });
  res.status(result.success ? 201 : 500).json(result);
}

// ============================================================
// Products
// ============================================================

export async function listProducts(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;
  const result = await service.listProducts(userId);
  res.status(result.success ? 200 : 500).json(result);
}

export async function createProduct(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;

  const { name, description, price, payment_type } = req.body;
  if (!name || !price) return res.status(400).json({ success: false, error: 'name and price are required' });

  const result = await service.createProduct(userId, { name, description, price, payment_type });
  res.status(result.success ? 201 : 500).json(result);
}

// ============================================================
// Dashboard
// ============================================================

export async function getDashboard(req: Request, res: Response) {
  const userId = requireAuth(req, res);
  if (!userId) return;
  const result = await service.getDashboardStats(userId);
  res.status(result.success ? 200 : 500).json(result);
}

// ============================================================
// Health
// ============================================================

export function health(_req: Request, res: Response) {
  res.json({ success: true, data: { status: 'ok', version: '0.1.0', phase: 'Phase 1 MVP' } });
}
