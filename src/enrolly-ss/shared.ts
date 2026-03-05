// ============================================================
// Enrolly SS - Shared Module (re-exports from FunnelForge)
// Both projects share the same DB, types, and demo store
// ============================================================

export { getSupabase, isDemoMode } from '../funnel-forge-ss/db';
export { demoSupabase } from '../funnel-forge-ss/demo-store';
export type {
  Contact, ContactListQuery, Tag, Funnel, FunnelPage, PageElement,
  EmailScenario, EmailStep, Product, Order,
  MediaFile, MediaUploadResponse,
  ABVariant, ApiResponse,
  SegmentCondition, Segment,
} from '../funnel-forge-ss/types';
