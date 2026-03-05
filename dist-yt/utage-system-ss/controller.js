"use strict";
// ============================================================
// UTAGE System SS - API Controllers
// Phase 1 MVP
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
exports.health = exports.getDashboard = exports.createProduct = exports.listProducts = exports.createLineScenario = exports.listLineScenarios = exports.addEmailStep = exports.createEmailScenario = exports.listEmailScenarios = exports.getPublishedPage = exports.updatePage = exports.createPage = exports.createFunnel = exports.listFunnels = exports.createTagHandler = exports.listTags = exports.removeTag = exports.addTag = exports.getContact = exports.createContact = exports.listContacts = void 0;
const service = __importStar(require("./service"));
// --- Helper ---
function getUserId(req) {
    // TODO: Replace with actual auth (Supabase Auth / JWT)
    return req.userId || req.headers['x-user-id'] || null;
}
function requireAuth(req, res) {
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
async function listContacts(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const query = {
        page: parseInt(req.query.page) || 1,
        per_page: Math.min(parseInt(req.query.per_page) || 20, 100),
        status: req.query.status,
        search: req.query.search,
        sort_by: req.query.sort_by || 'created_at',
        sort_order: req.query.sort_order || 'desc',
    };
    const result = await service.listContacts(userId, query);
    res.status(result.success ? 200 : 500).json(result);
}
exports.listContacts = listContacts;
async function createContact(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { email, line_user_id, name, phone, source } = req.body;
    if (!email && !line_user_id) {
        return res.status(400).json({ success: false, error: 'email or line_user_id is required' });
    }
    const result = await service.createContact(userId, { email, line_user_id, name, phone, source });
    res.status(result.success ? 201 : 500).json(result);
}
exports.createContact = createContact;
async function getContact(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.getContact(userId, req.params.id);
    res.status(result.success ? 200 : 404).json(result);
}
exports.getContact = getContact;
async function addTag(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { tag_id } = req.body;
    if (!tag_id)
        return res.status(400).json({ success: false, error: 'tag_id is required' });
    const result = await service.addTagToContact(req.params.id, tag_id);
    res.status(result.success ? 200 : 500).json(result);
}
exports.addTag = addTag;
async function removeTag(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.removeTagFromContact(req.params.id, req.params.tagId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.removeTag = removeTag;
// ============================================================
// Tags
// ============================================================
async function listTags(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.listTags(userId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.listTags = listTags;
async function createTagHandler(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { name, color } = req.body;
    if (!name)
        return res.status(400).json({ success: false, error: 'name is required' });
    const result = await service.createTag(userId, name, color);
    res.status(result.success ? 201 : 500).json(result);
}
exports.createTagHandler = createTagHandler;
// ============================================================
// Funnels
// ============================================================
async function listFunnels(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.listFunnels(userId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.listFunnels = listFunnels;
async function createFunnel(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { name } = req.body;
    if (!name)
        return res.status(400).json({ success: false, error: 'name is required' });
    const result = await service.createFunnel(userId, name);
    res.status(result.success ? 201 : 500).json(result);
}
exports.createFunnel = createFunnel;
async function createPage(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { title, slug, page_type, elements } = req.body;
    if (!title || !slug || !page_type) {
        return res.status(400).json({ success: false, error: 'title, slug, and page_type are required' });
    }
    const result = await service.createFunnelPage(req.params.funnelId, { title, slug, page_type, elements });
    res.status(result.success ? 201 : 500).json(result);
}
exports.createPage = createPage;
async function updatePage(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.updateFunnelPage(req.params.pageId, req.body);
    res.status(result.success ? 200 : 500).json(result);
}
exports.updatePage = updatePage;
async function getPublishedPage(req, res) {
    const result = await service.getPublishedPage(req.params.slug);
    if (!result.success || !result.data) {
        return res.status(404).json({ success: false, error: 'Page not found' });
    }
    // TODO: Track page view
    // TODO: Render as HTML from elements
    res.json(result);
}
exports.getPublishedPage = getPublishedPage;
// ============================================================
// Email Scenarios
// ============================================================
async function listEmailScenarios(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.listEmailScenarios(userId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.listEmailScenarios = listEmailScenarios;
async function createEmailScenario(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { name, trigger } = req.body;
    if (!name)
        return res.status(400).json({ success: false, error: 'name is required' });
    const result = await service.createEmailScenario(userId, { name, trigger });
    res.status(result.success ? 201 : 500).json(result);
}
exports.createEmailScenario = createEmailScenario;
async function addEmailStep(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { subject, body_html, delay_minutes, sort_order } = req.body;
    if (!subject || !body_html)
        return res.status(400).json({ success: false, error: 'subject and body_html are required' });
    const result = await service.addEmailStep(req.params.scenarioId, { subject, body_html, delay_minutes, sort_order });
    res.status(result.success ? 201 : 500).json(result);
}
exports.addEmailStep = addEmailStep;
// ============================================================
// LINE Scenarios
// ============================================================
async function listLineScenarios(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.listLineScenarios(userId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.listLineScenarios = listLineScenarios;
async function createLineScenario(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { name, trigger } = req.body;
    if (!name)
        return res.status(400).json({ success: false, error: 'name is required' });
    const result = await service.createLineScenario(userId, { name, trigger });
    res.status(result.success ? 201 : 500).json(result);
}
exports.createLineScenario = createLineScenario;
// ============================================================
// Products
// ============================================================
async function listProducts(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.listProducts(userId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.listProducts = listProducts;
async function createProduct(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const { name, description, price, payment_type } = req.body;
    if (!name || !price)
        return res.status(400).json({ success: false, error: 'name and price are required' });
    const result = await service.createProduct(userId, { name, description, price, payment_type });
    res.status(result.success ? 201 : 500).json(result);
}
exports.createProduct = createProduct;
// ============================================================
// Dashboard
// ============================================================
async function getDashboard(req, res) {
    const userId = requireAuth(req, res);
    if (!userId)
        return;
    const result = await service.getDashboardStats(userId);
    res.status(result.success ? 200 : 500).json(result);
}
exports.getDashboard = getDashboard;
// ============================================================
// Health
// ============================================================
function health(_req, res) {
    res.json({ success: true, data: { status: 'ok', version: '0.1.0', phase: 'Phase 1 MVP' } });
}
exports.health = health;
