/* ── D-pad navigation hook for Fire TV remote ── */

import { useEffect, useCallback, useRef } from 'react';

type Direction = 'up' | 'down' | 'left' | 'right' | 'select' | 'back';

const KEY_MAP: Record<string, Direction> = {
  ArrowUp: 'up',
  ArrowDown: 'down',
  ArrowLeft: 'left',
  ArrowRight: 'right',
  Enter: 'select',
  ' ': 'select',
  Escape: 'back',
  Backspace: 'back',
};

interface DpadOptions {
  onNavigate?: (dir: Direction) => void;
  onSelect?: () => void;
  onBack?: () => void;
  enabled?: boolean;
}

export function useDpad({ onNavigate, onSelect, onBack, enabled = true }: DpadOptions) {
  const handler = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      const dir = KEY_MAP[e.key];
      if (!dir) return;

      e.preventDefault();

      if (dir === 'select') {
        onSelect?.();
      } else if (dir === 'back') {
        onBack?.();
      } else {
        onNavigate?.(dir);
      }
    },
    [onNavigate, onSelect, onBack, enabled],
  );

  useEffect(() => {
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handler]);
}

/** Manages a focused index within a list of items for D-pad navigation. */
export function useFocusIndex(itemCount: number, options?: { wrap?: boolean }) {
  const indexRef = useRef(0);
  const wrap = options?.wrap ?? true;

  const move = useCallback(
    (dir: 'up' | 'down' | 'left' | 'right') => {
      if (itemCount === 0) return 0;

      let next = indexRef.current;
      if (dir === 'up' || dir === 'left') {
        next = wrap ? (next - 1 + itemCount) % itemCount : Math.max(0, next - 1);
      } else {
        next = wrap ? (next + 1) % itemCount : Math.min(itemCount - 1, next + 1);
      }
      indexRef.current = next;
      return next;
    },
    [itemCount, wrap],
  );

  return { indexRef, move };
}
