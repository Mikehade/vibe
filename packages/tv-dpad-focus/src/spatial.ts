/**
 * Geometry-based spatial navigation for D-pad remotes.
 *
 * Any element with [data-focusable] (and tabIndex=-1 or a native control) takes part.
 * Moving picks the nearest candidate in the pressed direction, weighting the
 * perpendicular offset so rows and columns feel natural.
 */

export type Direction = 'up' | 'down' | 'left' | 'right';

export const FOCUSABLE = '[data-focusable]:not([disabled]):not([aria-hidden="true"])';

function visible(el: HTMLElement): boolean {
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return false;
  const style = window.getComputedStyle(el);
  return style.visibility !== 'hidden' && style.display !== 'none';
}

export function focusables(root: ParentNode): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(visible);
}

export function findNext(current: HTMLElement, dir: Direction, root: ParentNode): HTMLElement | null {
  const from = current.getBoundingClientRect();
  const cx = from.left + from.width / 2;
  const cy = from.top + from.height / 2;
  let best: HTMLElement | null = null;
  let bestScore = Infinity;

  // Prefer staying inside the same [data-focus-group] for left/right (rails), falling back to all.
  const group = current.closest<HTMLElement>('[data-focus-group]');
  const pools: HTMLElement[][] = [];
  if (group && (dir === 'left' || dir === 'right')) pools.push(focusables(group));
  pools.push(focusables(root));

  for (const pool of pools) {
    for (const el of pool) {
      if (el === current || el.contains(current) || current.contains(el)) continue;
      const r = el.getBoundingClientRect();
      const ex = r.left + r.width / 2;
      const ey = r.top + r.height / 2;
      let primary: number;
      let secondary: number;
      switch (dir) {
        case 'right':
          if (r.left < from.right - 4 && ex <= cx + 1) continue;
          primary = Math.max(0, r.left - from.right);
          secondary = overlap(from.top, from.bottom, r.top, r.bottom) ? 0 : Math.abs(ey - cy);
          break;
        case 'left':
          if (r.right > from.left + 4 && ex >= cx - 1) continue;
          primary = Math.max(0, from.left - r.right);
          secondary = overlap(from.top, from.bottom, r.top, r.bottom) ? 0 : Math.abs(ey - cy);
          break;
        case 'down':
          if (r.top < from.bottom - 4 && ey <= cy + 1) continue;
          primary = Math.max(0, r.top - from.bottom);
          secondary = Math.abs(ex - cx);
          break;
        case 'up':
        default:
          if (r.bottom > from.top + 4 && ey >= cy - 1) continue;
          primary = Math.max(0, from.top - r.bottom);
          secondary = Math.abs(ex - cx);
          break;
      }
      const score = primary + secondary * (dir === 'left' || dir === 'right' ? 3 : 0.6);
      if (score < bestScore) {
        bestScore = score;
        best = el;
      }
    }
    if (best) return best;
  }
  return best;
}

function overlap(a1: number, a2: number, b1: number, b2: number) {
  return Math.min(a2, b2) - Math.max(a1, b1) > 4;
}

export function focusEl(el: HTMLElement | null) {
  if (!el) return;
  el.focus({ preventScroll: true });
  const inline = (el.dataset.scrollInline as ScrollLogicalPosition) || 'nearest';
  const block = (el.dataset.scrollBlock as ScrollLogicalPosition) || 'nearest';
  try {
    el.scrollIntoView({ block, inline, behavior: 'smooth' });
  } catch {
    el.scrollIntoView();
  }
}

export function focusInitial(root: ParentNode): boolean {
  const auto = root.querySelector<HTMLElement>('[data-autofocus]:not([disabled])');
  const target = auto && visible(auto) ? auto : focusables(root)[0];
  if (target) {
    focusEl(target);
    return true;
  }
  return false;
}
