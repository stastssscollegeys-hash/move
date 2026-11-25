// GLB の中身を見る（three を使わない・テストから直接読める）。2026-11-20 Codex の Must
// GLB（1つのファイルで完結した形）の中の外への参照（buffers・images の uri）を数える。data: の埋め込みはよい
// 2026-11-20 Codex の Must：horseFile に外の画像を指す GLB を渡すと GLTFLoader がそれを取りに行っていた
export const externalUris = (buf: ArrayBuffer): string[] => {
  const v = new DataView(buf);
  if (buf.byteLength < 20 || v.getUint32(0, true) !== 0x46546c67) throw new Error('馬のモデルは .glb（1つのファイルで完結した形）だけ使えます');
  const len = v.getUint32(12, true), type = v.getUint32(16, true);
  if (20 + len > buf.byteLength) throw new Error('馬のモデルが読めません（GLB の中身が途中で切れています）');
  if (type !== 0x4e4f534a) throw new Error('馬のモデルが読めません（GLB の中身の書き方が違います）');
  const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 20, len))) as {buffers?: {uri?: string}[]; images?: {uri?: string}[]};
  return [...(json.buffers || []), ...(json.images || [])].map((x) => x.uri).filter((u): u is string => !!u && !u.startsWith('data:'));
};

