"use strict";
// ============================================================
// Affiliate / Partner Service
// ============================================================
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.listReferrals = exports.markReferralPaid = exports.approveReferral = exports.recordReferral = exports.getPartnerRanking = exports.getPartnerByCode = exports.listPartners = exports.approvePartner = exports.registerPartner = exports.createProgram = exports.listPrograms = void 0;
const crypto_1 = __importDefault(require("crypto"));
const db_1 = require("./db");
// --- Programs ---
async function listPrograms(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_programs').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listPrograms = listPrograms;
async function createProgram(userId, program) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_programs').insert({
        user_id: userId, name: program.name,
        commission_type: program.commission_type || 'percentage',
        commission_value: program.commission_value || 10,
        cookie_days: program.cookie_days || 30,
        two_tier: program.two_tier || false,
        second_tier_rate: program.second_tier_rate || null,
        product_ids: program.product_ids || [],
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createProgram = createProgram;
// --- Partners ---
async function registerPartner(programId, contactId, parentPartnerId) {
    const db = (0, db_1.getSupabase)();
    const affiliateCode = crypto_1.default.randomBytes(6).toString('hex');
    const baseUrl = process.env.APP_URL || 'https://example.com';
    const referralUrl = `${baseUrl}?ref=${affiliateCode}`;
    const { data, error } = await db.from('affiliate_partners').insert({
        program_id: programId, contact_id: contactId,
        affiliate_code: affiliateCode, referral_url: referralUrl,
        parent_partner_id: parentPartnerId || null,
        status: 'pending',
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.registerPartner = registerPartner;
async function approvePartner(partnerId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_partners').update({ status: 'approved' }).eq('id', partnerId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.approvePartner = approvePartner;
async function listPartners(programId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_partners').select('*, contacts(name, email)').eq('program_id', programId).order('total_sales', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listPartners = listPartners;
async function getPartnerByCode(code) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_partners').select('*').eq('affiliate_code', code).eq('status', 'approved').single();
    if (error)
        return { success: false, error: 'Partner not found' };
    return { success: true, data };
}
exports.getPartnerByCode = getPartnerByCode;
async function getPartnerRanking(programId, limit = 10) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_partners').select('*, contacts(name)')
        .eq('program_id', programId).eq('status', 'approved')
        .order('total_sales', { ascending: false }).limit(limit);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.getPartnerRanking = getPartnerRanking;
// --- Referrals ---
async function recordReferral(partnerId, contactId, orderId, orderAmount) {
    const db = (0, db_1.getSupabase)();
    // Get program to calculate commission
    const { data: partner } = await db.from('affiliate_partners').select('*, affiliate_programs(*)').eq('id', partnerId).single();
    if (!partner)
        return { success: false, error: 'Partner not found' };
    const program = partner.affiliate_programs;
    const commission = program.commission_type === 'fixed' ? program.commission_value : Math.round(orderAmount * program.commission_value / 100);
    const { data, error } = await db.from('affiliate_referrals').insert({
        partner_id: partnerId, contact_id: contactId, order_id: orderId, commission_amount: commission,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    // Update partner stats
    await db.from('affiliate_partners').update({
        total_referrals: partner.total_referrals + 1,
        total_sales: partner.total_sales + orderAmount,
        total_commission: partner.total_commission + commission,
    }).eq('id', partnerId);
    // Handle two-tier
    if (program.two_tier && partner.parent_partner_id && program.second_tier_rate) {
        const secondCommission = Math.round(commission * program.second_tier_rate / 100);
        await db.from('affiliate_referrals').insert({
            partner_id: partner.parent_partner_id, contact_id: contactId, order_id: orderId, commission_amount: secondCommission,
        });
        await db.rpc('increment_partner_commission', { partner_id: partner.parent_partner_id, amount: secondCommission });
    }
    return { success: true, data };
}
exports.recordReferral = recordReferral;
async function approveReferral(referralId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_referrals').update({ status: 'approved', approved_at: new Date().toISOString() }).eq('id', referralId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.approveReferral = approveReferral;
async function markReferralPaid(referralId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_referrals').update({ status: 'paid', paid_at: new Date().toISOString() }).eq('id', referralId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.markReferralPaid = markReferralPaid;
async function listReferrals(partnerId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('affiliate_referrals').select('*, contacts(name), orders(amount, status)').eq('partner_id', partnerId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listReferrals = listReferrals;
