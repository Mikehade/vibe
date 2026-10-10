/**
 * Remote-control input for the whole app:
 * - D-pad → spatial navigation within the top-most focus scope (modals trap focus)
 * - Select/Enter → click
 * - Back (Esc, Backspace, GoBack, Fire TV keyCode 4, Vega shell event) → top-most back handler
 * - Play/Pause → "vibe:play" event; Menu → "vibe:menu" event
 */

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { findNext, focusEl, focusInitial, FOCUSABLE, type Direction } from './spatial';

type BackHandler = () => boolean | void;

interface FocusCtx {
  pushBack: (fn: BackHandler) => () => void;
  pushScope: (el: HTMLElement) => () => void;
}

const Ctx = createContext<FocusCtx | null>(null);

const ARROWS: Record<string, Direction> = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right' };
const ARROW_CODES: Record<number, Direction> = { 38: 'up', 40: 'down', 37: 'left', 39: 'right', 19: 'up', 20: 'down', 21: 'left', 22: 'right' };
const BACK_KEYS = new Set(['Escape', 'GoBack', 'BrowserBack', 'Back']);
const BACK_CODES = new Set([4, 27, 461, 10009]);
const SELECT_CODES = new Set([13, 23, 66]);
const PLAY_KEYS = new Set(['MediaPlayPause', 'MediaPlay', 'MediaTogglePlayPause']);
const PLAY_CODES = new Set([179, 85, 126, 415]);

function isTextInput(el: Element | null): el is HTMLInputElement | HTMLTextAreaElement {
  if (!el) return false;
  const tag = el.tagName;
  return tag === 'TEXTAREA' || (tag === 'INPUT' && !['checkbox', 'radio', 'button', 'submit'].includes((el as HTMLInputElement).type));
}

export function FocusProvider({ children, onRootBack }: { children: ReactNode; onRootBack: () => void }) {
  const backStack = useRef<BackHandler[]>([]);
  const scopes = useRef<HTMLElement[]>([]);
  const rootBackRef = useRef(onRootBack);
  rootBackRef.current = onRootBack;

  const pushBack = useCallback((fn: BackHandler) => {
    backStack.current.push(fn);
    return () => {
      backStack.current = backStack.current.filter((f) => f !== fn);
    };
  }, []);

  const pushScope = useCallback((el: HTMLElement) => {
    scopes.current.push(el);
    return () => {
      scopes.current = scopes.current.filter((s) => s !== el);
    };
  }, []);

  useEffect(() => {
    const root = () => scopes.current[scopes.current.length - 1] ?? document.body;

    let lastBack = 0;
    const back = () => {
      // The Vega shell forwards hardware Back *and* the WebView may deliver a key event — de-dupe.
      const now = Date.now();
      if (now - lastBack < 300) return;
      lastBack = now;
      for (let i = backStack.current.length - 1; i >= 0; i--) {
        if (backStack.current[i]() !== false) return;
      }
      rootBackRef.current();
    };

    const onKey = (e: KeyboardEvent) => {
      const active = document.activeElement as HTMLElement | null;
      const code = e.keyCode || e.which;
      // Some TV WebViews send keyCode only (key === 'Unidentified'); never use keyCode for real keyboards,
      // or ordinary letters collide with Android keycodes (e.g. 'u' = 85 = media play/pause).
      const raw = !e.key || e.key === 'Unidentified';
      const dir = ARROWS[e.key] ?? (raw ? ARROW_CODES[code] : undefined);

      if (dir) {
        if (isTextInput(active) && (dir === 'left' || dir === 'right')) return;
        e.preventDefault();
        const scope = root();
        if (!active || active === document.body || !scope.contains(active) || !active.matches(FOCUSABLE)) {
          focusInitial(scope);
          return;
        }
        const next = findNext(active, dir, scope);
        if (next) focusEl(next);
        return;
      }

      const isBack = BACK_KEYS.has(e.key) || (raw && BACK_CODES.has(code)) || (e.key === 'Backspace' && !isTextInput(active));
      if (isBack) {
        e.preventDefault();
        if (isTextInput(active) && e.key === 'Escape') active.blur();
        back();
        return;
      }

      if (e.key === 'Enter' || e.key === 'Select' || (raw && SELECT_CODES.has(code))) {
        if (isTextInput(active)) return;
        if (active && active !== document.body && active.matches(FOCUSABLE)) {
          e.preventDefault();
          if (!e.repeat) active.click();
        }
        return;
      }

      if (PLAY_KEYS.has(e.key) || (raw && PLAY_CODES.has(code))) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('vibe:play'));
        return;
      }
      if (e.key === 'ContextMenu' || (raw && code === 82)) {
        window.dispatchEvent(new CustomEvent('vibe:menu'));
      }
    };

    // Mouse users (judges on a laptop) get the same focus visuals
    const onOver = (e: MouseEvent) => {
      const el = (e.target as HTMLElement | null)?.closest?.(FOCUSABLE) as HTMLElement | null;
      if (el && el !== document.activeElement && !isTextInput(document.activeElement)) el.focus({ preventScroll: true });
    };

    const onShellBack = () => back();
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('mouseover', onOver);
    window.addEventListener('vibe:back', onShellBack);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      window.removeEventListener('mouseover', onOver);
      window.removeEventListener('vibe:back', onShellBack);
    };
  }, []);

  return <Ctx.Provider value={{ pushBack, pushScope }}>{children}</Ctx.Provider>;
}

function useFocusCtx() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('FocusProvider missing');
  return ctx;
}

/** Register a back handler while mounted. Return false from the handler to let it bubble. */
export function useBack(handler: BackHandler, enabled = true) {
  const { pushBack } = useFocusCtx();
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    if (!enabled) return;
    return pushBack(() => ref.current());
  }, [enabled, pushBack]);
}

/**
 * A region that owns focus while mounted (screens, modals). Autofocuses [data-autofocus]
 * or the first focusable child. Pass `focusKey` to re-run autofocus when content changes.
 */
export function FocusScope({
  children,
  className,
  focusKey,
  autoFocus = true,
  style,
}: {
  children: ReactNode;
  className?: string;
  focusKey?: string | number;
  autoFocus?: boolean;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { pushScope } = useFocusCtx();
  useLayoutEffect(() => {
    if (!ref.current) return;
    return pushScope(ref.current);
  }, [pushScope]);
  useEffect(() => {
    if (!autoFocus || !ref.current) return;
    let tries = 0;
    const tick = () => {
      if (!ref.current) return;
      const active = document.activeElement;
      if (active && active !== document.body && ref.current.contains(active) && focusKey === undefined) return;
      if (!focusInitial(ref.current) && tries++ < 20) setTimeout(tick, 50);
    };
    const t = setTimeout(tick, 30);
    return () => clearTimeout(t);
  }, [autoFocus, focusKey]);
  return (
    <div ref={ref} className={className} style={style} data-focus-scope>
      {children}
    </div>
  );
}

/** Props that make any element take part in D-pad navigation. */
export const focusProps = { 'data-focusable': true, tabIndex: -1 } as const;
