// レース展開の2D（2026-11-19）。上から見たコースを、カメラが先頭の集団を追う。丸＝枠の色＋馬番。
// 解説寄りの見せ方（アニメのキャラにしない）。レース映像・写真・騎手は使わない。騎手名は出さない（ユーザー「馬番に加えて馬名も」）
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {WAKU} from './race3d/logic';   // 枠の色の正本（2026-11-20 race3d-quality で logic.ts へ移した）

type Horse = {umaban: number; waku: number; name: string; finish: number | null; style?: string | null; mark?: string | null};
type Frame = {p: number[][]; cam: number[]; rank: number[]; gap: number[]; lead: number[]; phase: string; rem: number; rs?: number};
export type Race2DProps = {
  fps: number; w: number; h: number; frames: number; view: number[]; lane?: number;
  race: {name: string; venue: string; surface: string; distance: number; date: string};
  pace: {first: number; second: number; label: string} | null;
  horses: Horse[];
  track: {R: number; L: number; w: number; full: {start: number[]}; marks: {u: number; label: string; a: number[]; b: number[]}[];
    shapes?: Record<string, number[][][] | number[][]> | null; credit?: string};
  frame: Frame[];
  note: string;
  title?: string;   // 上の帯の見出し（無ければレース名）
  mode?: 'result' | 'forecast' | 'prediction';   // prediction＝予想の着順まで走らせる展開予想（2026-11-20）
  overlayOnly?: boolean;   // 3D（Race3DHQ.tsx）の上に重ねる用：コースと馬の図は描かず、帯・順位・全体図だけ
  forecast?: {nige: number; pace: string} | null;
};

const FONT = '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif';
const NAVY = 'rgba(12, 26, 58, 0.88)';
const GOLD = '#f2c14e';
const RAIL = 1.6;

// 直線2本＋半円2つの輪郭（半径 r）。下の半円の中心 (0,0)・上の半円の中心 (0,L)
const polyPath = (pts: number[][]): string => 'M' + pts.map((q) => `${q[0]},${q[1]}`).join(' L') + ' Z';
const ovalPath = (r: number, L: number, n = 72): string => {
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) { const a = (Math.PI * i) / n; pts.push(`${(r * Math.cos(a)).toFixed(2)},${(L + r * Math.sin(a)).toFixed(2)}`); }      // 上の半円 右→左
  for (let i = 0; i <= n; i++) { const a = Math.PI + (Math.PI * i) / n; pts.push(`${(r * Math.cos(a)).toFixed(2)},${(r * Math.sin(a)).toFixed(2)}`); } // 下の半円 左→右
  return 'M' + pts.join(' L') + ' Z';
};

// 実物の形（build_frames.py の track.shapes）：外の芝 → 芝の帯 → 間の芝 → ダートの帯 → 内馬場。輪の線＝内ラチ
const TrackShapes: React.FC<{sh: Record<string, number[][][] | number[][]>; rail?: boolean}> = ({sh, rail}) => {
  const turf = sh['芝'] as number[][][] | undefined, dirt = sh['ダート'] as number[][][] | undefined, chute = sh['chute'] as number[][] | undefined;
  const turfOut = sh['芝外'] as number[][][] | undefined;   // 2026-11-20 外回り（新潟・中山・京都・阪神）。内回りより先（下）に描く
  return (
    <>
      {turfOut && <path d={polyPath(turfOut[1])} fill="#4e9447" />}
      {turfOut && <path d={polyPath(turfOut[0])} fill="#2f6a33" />}
      {turf && <path d={polyPath(turf[1])} fill="#4e9447" />}
      {turf && <path d={polyPath(turf[0])} fill="#2f6a33" />}
      {dirt && <path d={polyPath(dirt[1])} fill="#b27c4c" />}
      {chute && <path d={polyPath(chute)} fill="#b27c4c" />}
      {sh['芝直線'] && <path d={polyPath(sh['芝直線'] as number[][])} fill="#4e9447" />}
      {dirt && <path d={polyPath(dirt[0])} fill="#3d7c3a" />}
      {rail && turfOut && <path d={polyPath(turfOut[0])} fill="none" stroke="rgba(255,255,255,0.8)" strokeWidth={0.5} />}
      {rail && turf && <path d={polyPath(turf[0])} fill="none" stroke="rgba(255,255,255,0.8)" strokeWidth={0.5} />}
      {rail && dirt && <path d={polyPath(dirt[1])} fill="none" stroke="#ffffff" strokeWidth={0.5} />}
      {rail && dirt && <path d={polyPath(dirt[0])} fill="none" stroke="#ffffff" strokeWidth={0.6} />}
    </>
  );
};

export const Race2D: React.FC<Race2DProps> = (p) => {
  const f = useCurrentFrame();
  if (!p.frame || !p.frame.length) return <AbsoluteFill style={{background: '#123'}} />;
  const F = p.frame[Math.min(f, p.frame.length - 1)];
  const {w: W, h: H} = p;
  const tall = H > W;
  const topH = Math.round(H * (tall ? 0.11 : 0.13));
  const [vx0, vy0, vw, vh] = p.view;              // build_frames.py が決めた、コースを描く範囲
  const vcx = vx0 + vw / 2, vcy = vy0 + vh / 2;
  const [cx, cy, s] = F.cam;
  const sx = (x: number) => vcx + (x - cx) * s;
  const sy = (y: number) => vcy - (y - cy) * s;
  const {R, L, w: tw} = p.track;
  const rIn = R + RAIL - 1, rOut = R + RAIL + tw;
  const startY = p.track.full.start[1];
  const chute = startY > L - 1;    // 向こう正面をまっすぐ延ばした引き込み線
  const byNo: Record<number, Horse> = {};
  p.horses.forEach((h) => (byNo[h.umaban] = h));
  const idx: Record<number, number> = {};
  p.horses.forEach((h, i) => (idx[h.umaban] = i));
  const rad = Math.min(Math.max(1.25 * s, tall ? 20 : 18), 0.48 * (p.lane ?? 3) * s, 1.25 * s * 1.6) * (F.rs ?? 1);   // 横の列の幅より大きくしない
  const u = (n: number) => Math.round(n * (tall ? W / 1080 : H / 1080));
  const fc = p.mode === 'forecast';
  const pr = p.mode === 'prediction';
  // 札：終わったレース＝前の3頭／展開予想＝軸と穴の馬。スタートは馬番順に並ぶだけなので出さない
  const top3 = F.phase === 'スタート' ? [] : fc ? F.rank.filter((no) => byNo[no].mark) : F.rank.slice(0, 3);
  const finished = F.phase === 'ゴール' || F.phase === '直線へ';

  // 小さな全体図
  const mmW = u(tall ? 250 : 250), mmH = u(tall ? 330 : 300);
  // 全体図の範囲：実物の形があればその外枠、無ければ楕円
  const sh = p.track.shapes || null;
  const allPts: number[][] = sh ? Object.values(sh).flatMap((v) => (Array.isArray(v[0][0]) ? (v as number[][][]).flat() : (v as number[][]))) : [];
  const bx0 = sh ? Math.min(...allPts.map((q) => q[0])) : -rOut, bx1 = sh ? Math.max(...allPts.map((q) => q[0])) : rOut;
  const by0 = sh ? Math.min(...allPts.map((q) => q[1])) : -rOut, by1 = sh ? Math.max(...allPts.map((q) => q[1])) : L + rOut + (chute ? startY - L : 0);
  const mmScale = Math.min(mmW / (bx1 - bx0 + 20), mmH / (by1 - by0 + 20));
  const mmX = W - mmW - u(24), mmY = topH + u(20);
  const mmCx = (bx0 + bx1) / 2, mmCy = (by0 + by1) / 2;
  const mx = (x: number) => mmX + mmW / 2 + (x - mmCx) * mmScale;
  const my = (y: number) => mmY + mmH / 2 - (y - mmCy) * mmScale;

  const T = `translate(${vcx} ${vcy}) scale(${s} ${-s}) translate(${-cx} ${-cy})`;
  return (
    <AbsoluteFill style={{background: p.overlayOnly ? 'transparent' : '#25502a', fontFamily: FONT}}>
      {!p.overlayOnly && <svg width={W} height={H} style={{position: 'absolute'}}>
        <g transform={T}>
          {sh ? <TrackShapes sh={sh} rail /> : <>
          {/* 外の芝 → ダート → 内の芝（形のデータが無い競馬場＝直線2本と半円2つ） */}
          <path d={ovalPath(rOut + 40, L)} fill="#2d5e30" />
          <path d={ovalPath(rOut, L)} fill="#b27c4c" />
          {chute && <rect x={-rOut} y={L - 5} width={rOut - rIn} height={startY - L + 30} fill="#b27c4c" />}
          <path d={ovalPath(rIn, L)} fill="#3d7c3a" />
          <path d={ovalPath(rOut, L)} fill="none" stroke="#ffffff" strokeWidth={0.5} />
          <path d={ovalPath(rIn, L)} fill="none" stroke="#ffffff" strokeWidth={0.6} />
          </>}
          {/* 内側の模様（芝の刈り目）で動きが分かるように */}
          {!sh && <>
          {Array.from({length: 40}).map((_, i) => (
            <line key={i} x1={-rIn} x2={rIn} y1={-rIn + i * 25} y2={-rIn + i * 25} stroke="rgba(255,255,255,0.05)" strokeWidth={10} />
          ))}
          {/* ダートの目印の線（20mごと） */}
          {Array.from({length: 110}).map((_, i) => {
            const y = -200 + i * 20;
            return <line key={'d' + i} x1={rIn} x2={rOut} y1={y} y2={y} stroke="rgba(80,45,20,0.25)" strokeWidth={0.4} />;
          })}
          </>}
          {sh && Array.from({length: 120}).map((_, i) => (
            <line key={'s' + i} x1={-3000} x2={3000} y1={-1500 + i * 25} y2={-1500 + i * 25} stroke="rgba(255,255,255,0.045)" strokeWidth={10} />
          ))}
          {/* ゴール・残り200m など */}
          {p.track.marks.map((m) => (
            <line key={m.u} x1={m.a[0]} y1={m.a[1]} x2={m.b[0]} y2={m.b[1]} stroke={m.u === 0 ? '#ffffff' : 'rgba(255,255,255,0.75)'}
              strokeWidth={m.u === 0 ? 1.2 : 0.5} strokeDasharray={m.u === 0 ? undefined : '1.5 1.5'} />
          ))}
        </g>
        {/* 目印の札（文字は向きを戻して描く） */}
        {p.track.marks.map((m) => {
          const bw = u(m.u === 0 ? 96 : 150);
          let x = sx(m.b[0]) + u(10); const y = sy(m.b[1]);
          if (x + bw > W - u(8)) x = sx(m.a[0]) - bw - u(10);
          if (x < -200 || x > W + 200 || y < vy0 || y > vy0 + vh) return null;
          return (
            <g key={'t' + m.u}>
              <rect x={x} y={y - u(22)} width={bw} height={u(44)} rx={u(10)} fill={m.u === 0 ? GOLD : 'rgba(0,0,0,0.55)'} />
              <text x={x + u(m.u === 0 ? 48 : 75)} y={y + u(10)} fontSize={u(28)} fontWeight={800} textAnchor="middle" fill={m.u === 0 ? '#1b1b1b' : '#fff'}>{m.label}</text>
            </g>
          );
        })}
        {/* 馬（後ろの馬から描いて、前の馬を上に） */}
        {[...F.rank].reverse().map((no) => {
          const pt = F.p[idx[no]]; const x = sx(pt[0]), y = sy(pt[1]);
          const [bg, fg] = WAKU[byNo[no].waku] || ['#888', '#fff'];
          const lead = top3.indexOf(no);
          return (
            <g key={no}>
              <circle cx={x} cy={y + rad * 0.12} r={rad} fill="rgba(0,0,0,0.35)" />
              <circle cx={x} cy={y} r={rad} fill={bg} stroke={lead === 0 ? GOLD : bg === '#ffffff' ? '#333' : '#ffffff'} strokeWidth={lead === 0 ? rad * 0.22 : rad * 0.12} />
              <text x={x} y={y + rad * 0.38} fontSize={rad * 1.05} fontWeight={900} textAnchor="middle" fill={fg}>{no}</text>
            </g>
          );
        })}
        {/* 前の3頭は馬名の札。集団の左（内側）にまとめて置き、線で結ぶ（右隣の馬を隠さない） */}
        {(() => {
          if (!top3.length) return null;
          const fs = u(26), gapY = fs * 1.75;
          const shown = F.rank.map((no) => F.p[idx[no]]).filter((q) => sy(q[1]) > vy0 && sy(q[1]) < vy0 + vh);
          const minX = Math.min(...shown.map((q) => sx(q[0])));
          const maxX = Math.max(...shown.map((q) => sx(q[0])));
          const tags = top3.map((no) => ({no, nm: (fc && byNo[no].mark ? `${byNo[no].mark}　` : '') + byNo[no].name, hx: sx(F.p[idx[no]][0]), hy: sy(F.p[idx[no]][1])}));
          const widest = Math.max(...tags.map((t) => t.nm.length * fs + u(24)));
          const left = minX - rad - u(24) - widest > vx0 + u(8);
          const ys: number[] = [];
          return tags.map((t, i) => {
            let y = t.hy; for (const q of ys) if (Math.abs(y - q) < gapY) y = q + gapY; ys.push(y);
            const bw = t.nm.length * fs + u(24);
            const x = left ? minX - rad - u(24) - bw : maxX + rad + u(24);
            const ex = left ? x + bw : x;
            return (
              <g key={'n' + t.no}>
                <line x1={ex} y1={y} x2={t.hx} y2={t.hy} stroke={i === 0 ? GOLD : 'rgba(255,255,255,0.8)'} strokeWidth={u(3)} />
                <rect x={x} y={y - fs * 0.8} width={bw} height={fs * 1.6} rx={fs * 0.4} fill={i === 0 ? GOLD : 'rgba(12,26,58,0.88)'} />
                <text x={x + u(12)} y={y + fs * 0.35} fontSize={fs} fontWeight={800} fill={i === 0 ? '#1b1b1b' : '#fff'}>{t.nm}</text>
              </g>
            );
          });
        })()}
      </svg>}

      {/* 縦：順位と全体図の段は地の色で塗る（馬がその下に入って隠れないように）。横：塗らずにコースの図を画面いっぱいに（札は上に重ねる） */}
      {!p.overlayOnly && tall ? <div style={{position: 'absolute', left: 0, top: topH, width: W, height: vy0 - topH, background: '#13284f'}} /> : null}
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* 全体図 */}
        <g>
          <rect x={mmX - u(10)} y={mmY - u(10)} width={mmW + u(20)} height={mmH + u(20)} rx={u(16)} fill={NAVY} />
          <g transform={`translate(${mmX + mmW / 2} ${mmY + mmH / 2}) scale(${mmScale} ${-mmScale}) translate(${-mmCx} ${-mmCy})`}>
            {sh ? <TrackShapes sh={sh} /> : <>
            <path d={ovalPath(rOut, L)} fill="#b27c4c" />
            {chute && <rect x={-rOut} y={L - 5} width={rOut - rIn} height={startY - L + 30} fill="#b27c4c" />}
            <path d={ovalPath(rIn, L)} fill="#3d7c3a" />
            </>}
          </g>
          {F.rank.map((no) => {
            const pt = F.p[idx[no]]; const [bg] = WAKU[byNo[no].waku] || ['#888'];
            return <circle key={'m' + no} cx={mx(pt[0])} cy={my(pt[1])} r={u(5)} fill={bg} stroke="#000" strokeWidth={u(1)} />;
          })}
          <line x1={mx(p.track.marks[0].a[0])} y1={my(p.track.marks[0].a[1])} x2={mx(p.track.marks[0].b[0])} y2={my(p.track.marks[0].b[1])} stroke="#fff" strokeWidth={u(3)} />
        </g>
      </svg>
      {/* 上の帯：レース名・場所・いまの地点 */}
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: topH, background: NAVY, display: 'flex', alignItems: 'center', padding: `0 ${u(30)}px`, boxSizing: 'border-box', justifyContent: 'space-between'}}>
        <div style={{color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden'}}>
          <div style={{fontSize: u(52), fontWeight: 900, lineHeight: 1.1}}>{p.title || p.race.name}</div>
          <div style={{fontSize: u(28), fontWeight: 700, color: '#cfe0ff', marginTop: u(6)}}>
            {p.race.venue} {p.race.surface}{p.race.distance}m{(fc || pr) && p.forecast ? `　展開予想：逃げ${p.forecast.nige}頭→ペース${p.forecast.pace}` : p.pace ? `　${p.pace.label}（前半${p.pace.first}・後半${p.pace.second}）` : ''}
          </div>
        </div>
        <div style={{background: finished ? GOLD : '#ffffff', color: '#0c1a3a', borderRadius: u(14), padding: `${u(8)}px ${u(20)}px`, textAlign: 'center', minWidth: u(230), whiteSpace: 'nowrap', flexShrink: 0}}>
          <div style={{fontSize: u(F.phase.length > 4 ? 34 : 40), fontWeight: 900}}>{F.phase}</div>
          {!finished && F.phase !== 'スタート' && <div style={{fontSize: u(24), fontWeight: 800}}>残り {F.rem}m</div>}
        </div>
      </div>

      {/* 順位（前の5頭） */}
      <div style={{position: 'absolute', left: u(20), top: topH + u(20), background: NAVY, borderRadius: u(16), padding: `${u(12)}px ${u(16)}px`, color: '#fff', minWidth: u(360)}}>
        <div style={{fontSize: u(24), fontWeight: 800, color: GOLD, marginBottom: u(6)}}>{fc ? '予想の隊列（AIの脚質）' : pr ? (finished ? '予想の着順' : '予想の順位') : finished ? 'ゴールの順位' : 'いまの順位'}</div>
        {F.rank.slice(0, 5).map((no, i) => {
          const [bg, fg] = WAKU[byNo[no].waku] || ['#888', '#fff'];
          return (
            <div key={no} style={{display: 'flex', alignItems: 'center', height: u(48), fontSize: u(30), fontWeight: 800}}>
              <span style={{width: u(40), color: i === 0 ? GOLD : '#fff'}}>{i + 1}</span>
              <span style={{width: u(40), height: u(40), borderRadius: '50%', background: bg, color: fg, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: u(24), fontWeight: 900, border: bg === '#ffffff' ? `${u(2)}px solid #333` : 'none', marginRight: u(12)}}>{no}</span>
              <span style={{flex: 1}}>{byNo[no].name}</span>
              <span style={{fontSize: u(22), color: '#cfe0ff', marginLeft: u(12)}}>{fc ? (byNo[no].style || '') : i === 0 || F.phase === 'スタート' ? '' : F.gap[i] < 0.3 ? '並ぶ' : `+${F.gap[i]}馬身`}</span>
            </div>
          );
        })}
      </div>

      {p.track.credit ? <div style={{position: 'absolute', right: u(14), top: mmY + mmH + u(14), width: mmW + u(20), textAlign: 'center', fontSize: u(14), color: 'rgba(255,255,255,0.7)'}}>{p.track.credit}</div> : null}
      {/* 注意書き（小さく） */}
      <div style={{position: 'absolute', left: vx0 + u(20), top: vy0 + vh - u(40), fontSize: u(20), color: 'rgba(255,255,255,0.85)', fontWeight: 600, textShadow: '0 1px 3px #000'}}>
        {fc ? '※ AIの脚質の判定（前走の通過順位）から組んだ予想の隊列です' : pr ? ('※ ' + (p.note || 'アスメシの印・脚質・前走の上がりから組んだ着順の予想です（タイムは推定）'))  /* 2026-11-20 印を出す前の版は frames.json の note で差し替える（build_frames.py --note） */ : `※ データ（通過順位・タイム）から作った${p.overlayOnly ? '映像' : '図'}です。3コーナーまでの位置と内外は推定`}
      </div>
    </AbsoluteFill>
  );
};
