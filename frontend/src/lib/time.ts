/* Local time helpers. The TV's clock and timezone drive the whole plan. */

export function tzOffsetMinutes(): number {
  return -new Date().getTimezoneOffset();
}

export function localIso(d = new Date()): string {
  const off = tzOffsetMinutes();
  const sign = off >= 0 ? '+' : '-';
  const abs = Math.abs(off);
  const pad = (n: number) => String(n).padStart(2, '0');
  const local = new Date(d.getTime() + off * 60000);
  return (
    local.toISOString().slice(0, 19) + `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}

export function clock(d: Date): string {
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function addMinutes(d: Date, m: number): Date {
  return new Date(d.getTime() + m * 60000);
}

export function duration(mins: number | null | undefined): string {
  const m = Math.max(0, Math.round(mins || 0));
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (!h) return `${r} min`;
  return r ? `${h}h ${r}m` : `${h}h`;
}

export function greeting(d = new Date()): string {
  const h = d.getHours();
  if (h < 5) return 'Still up';
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  if (h < 22) return 'Good evening';
  return 'Late one tonight';
}

export function dayLabel(d = new Date()): string {
  return d.toLocaleDateString([], { weekday: 'long' }) + ', ' + clock(d);
}

/** Minutes from now until a sensible bedtime (23:30, or +90 if it's already late). */
export function minutesUntilBed(d = new Date()): number {
  const bed = new Date(d);
  bed.setHours(23, 30, 0, 0);
  let diff = Math.round((bed.getTime() - d.getTime()) / 60000);
  if (diff < 60) diff = 90;
  return Math.min(diff, 300);
}

export function relativeDay(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  const today = new Date();
  const days = Math.round((today.setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 86400000);
  if (days === 0) return 'Tonight';
  if (days === 1) return 'Yesterday';
  if (days < 7) return d.toLocaleDateString([], { weekday: 'long' });
  return d.toLocaleDateString([], { day: 'numeric', month: 'short' });
}
