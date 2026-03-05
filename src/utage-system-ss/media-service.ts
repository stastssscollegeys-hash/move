// ============================================================
// Media Management Service (Supabase Storage)
// ============================================================

import type { MediaFile, MediaUploadResponse, ApiResponse } from './types';

let supabase: any = null;
function getSupabase() {
  if (!supabase) {
    const { createClient } = require('@supabase/supabase-js');
    supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);
  }
  return supabase;
}

const BUCKET = 'utage-media';
const MAX_FILE_SIZES: Record<string, number> = {
  image: 10 * 1024 * 1024,    // 10MB
  video: 500 * 1024 * 1024,   // 500MB
  pdf: 50 * 1024 * 1024,      // 50MB
  audio: 100 * 1024 * 1024,   // 100MB
};

export async function getUploadUrl(userId: string, originalName: string, mimeType: string, sizeBytes: number, folder?: string): Promise<ApiResponse<MediaUploadResponse>> {
  const fileType = getFileType(mimeType);
  if (!fileType) return { success: false, error: '対応していないファイル形式です' };

  const maxSize = MAX_FILE_SIZES[fileType];
  if (sizeBytes > maxSize) return { success: false, error: `ファイルサイズは${Math.floor(maxSize / 1024 / 1024)}MB以下にしてください` };

  const db = getSupabase();
  const ext = originalName.split('.').pop() || '';
  const key = `${userId}/${folder || fileType}s/${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;

  // Create DB record
  const { data: media, error: dbErr } = await db.from('media_files').insert({
    user_id: userId, filename: key, original_name: originalName,
    mime_type: mimeType, file_type: fileType, size_bytes: sizeBytes,
    url: '', folder: folder || null,
  }).select().single();
  if (dbErr) return { success: false, error: dbErr.message };

  // Get signed upload URL
  const { data: uploadData, error: uploadErr } = await db.storage.from(BUCKET).createSignedUploadUrl(key);
  if (uploadErr) return { success: false, error: uploadErr.message };

  return {
    success: true,
    data: { upload_url: uploadData.signedUrl, media_id: media.id, key },
  };
}

export async function confirmUpload(mediaId: string, userId: string): Promise<ApiResponse<MediaFile>> {
  const db = getSupabase();
  const { data: media, error: getErr } = await db.from('media_files').select('*').eq('id', mediaId).eq('user_id', userId).single();
  if (getErr) return { success: false, error: 'File not found' };

  const { data: urlData } = db.storage.from(BUCKET).getPublicUrl(media.filename);
  const url = urlData?.publicUrl || '';

  let thumbnailUrl = null;
  if (media.file_type === 'image') {
    const { data: thumbData } = db.storage.from(BUCKET).getPublicUrl(media.filename, { transform: { width: 300, height: 200 } });
    thumbnailUrl = thumbData?.publicUrl || null;
  }

  const { data: updated, error: updateErr } = await db.from('media_files')
    .update({ url, thumbnail_url: thumbnailUrl })
    .eq('id', mediaId).select().single();
  if (updateErr) return { success: false, error: updateErr.message };

  return { success: true, data: updated };
}

export async function listMedia(userId: string, fileType?: string, folder?: string, page = 1, perPage = 20): Promise<ApiResponse<MediaFile[]>> {
  const db = getSupabase();
  let q = db.from('media_files').select('*', { count: 'exact' }).eq('user_id', userId).order('created_at', { ascending: false });
  if (fileType) q = q.eq('file_type', fileType);
  if (folder) q = q.eq('folder', folder);
  q = q.range((page - 1) * perPage, page * perPage - 1);

  const { data, error, count } = await q;
  if (error) return { success: false, error: error.message };
  return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}

export async function deleteMedia(mediaId: string, userId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { data: media, error: getErr } = await db.from('media_files').select('filename').eq('id', mediaId).eq('user_id', userId).single();
  if (getErr) return { success: false, error: 'File not found' };

  await db.storage.from(BUCKET).remove([media.filename]);
  await db.from('media_files').delete().eq('id', mediaId);
  return { success: true };
}

function getFileType(mimeType: string): string | null {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('video/')) return 'video';
  if (mimeType.startsWith('audio/')) return 'audio';
  if (mimeType === 'application/pdf') return 'pdf';
  return null;
}
