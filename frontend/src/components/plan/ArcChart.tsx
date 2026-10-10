import { useMemo } from 'react';
import { ROLE_COLOR } from '@/lib/moods';
import type { ArcSlot } from '@/lib/types';

/**
 * The evening's energy curve, drawn above the lineup. Each dot sits over its slot's card.
 * `slotWidth`/`gap` are in rem so the chart lines up with the rail at any resolution.
 */
export default function ArcChart({
  slots,
  focused,
  slotWidth,
  gap,
  height = 6,
  provisional,
}: {
  slots: ArcSlot[];
  focused: number | null;
  slotWidth: number;
  gap: number;
  height?: number;
  provisional?: boolean;
}) {
  const width = slots.length * slotWidth + (slots.length - 1) * gap;
  const pts = useMemo(
    () =>
      slots.map((s, i) => ({
        x: i * (slotWidth + gap) + slotWidth / 2,
        y: height - 0.8 - s.energy * (height - 1.6),
        s,
      })),
    [slots, slotWidth, gap, height],
  );
  if (!slots.length) return null;

  const all = [{ x: 0, y: pts[0].y + 0.6 }, ...pts, { x: width, y: pts[pts.length - 1].y + 0.6 }];
  let d = `M ${all[0].x} ${all[0].y}`;
  for (let i = 0; i < all.length - 1; i++) {
    const p0 = all[Math.max(0, i - 1)];
    const p1 = all[i];
    const p2 = all[i + 1];
    const p3 = all[Math.min(all.length - 1, i + 2)];
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: `${width}rem`, height: `${height}rem` }} className="overflow-visible">
      <defs>
        <linearGradient id="arcStroke" x1="0" x2="1" y1="0" y2="0">
          {pts.map((p, i) => (
            <stop key={i} offset={`${(p.x / width) * 100}%`} stopColor={ROLE_COLOR[p.s.role]} />
          ))}
        </linearGradient>
        <linearGradient id="arcFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#e8b04b" stopOpacity="0.16" />
          <stop offset="100%" stopColor="#e8b04b" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L ${width} ${height} L 0 ${height} Z`} fill="url(#arcFill)" />
      <path
        d={d}
        fill="none"
        stroke="url(#arcStroke)"
        strokeWidth={0.12}
        strokeLinecap="round"
        strokeDasharray={provisional ? '0.4 0.3' : undefined}
        style={{ transition: 'd 600ms ease' }}
      />
      {pts.map((p) => (
        <g key={p.s.position}>
          <circle cx={p.x} cy={p.y} r={focused === p.s.position ? 0.55 : 0.32} fill={ROLE_COLOR[p.s.role]} style={{ transition: 'r 200ms ease' }} />
          {focused === p.s.position && <circle cx={p.x} cy={p.y} r={0.9} fill="none" stroke={ROLE_COLOR[p.s.role]} strokeOpacity={0.4} strokeWidth={0.08} />}
        </g>
      ))}
    </svg>
  );
}
