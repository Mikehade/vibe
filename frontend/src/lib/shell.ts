/**
 * Bridge to the native shell (Vega OS React Native WebView, or a Fire OS WebView wrapper).
 * In a normal browser these are no-ops.
 */
import type { Pick } from './types';

declare global {
  interface Window {
    ReactNativeWebView?: { postMessage: (msg: string) => void };
    VibeShell?: { postMessage: (msg: string) => void };
  }
}

export function inShell(): boolean {
  return !!(window.ReactNativeWebView || window.VibeShell);
}

export function postToShell(msg: Record<string, unknown>) {
  const s = JSON.stringify(msg);
  try {
    window.ReactNativeWebView?.postMessage(s);
    window.VibeShell?.postMessage(s);
  } catch {
    /* ignore */
  }
}

export function launchProvider(pick: Pick) {
  postToShell({ type: 'launch', provider: pick.streaming_provider, title: pick.title, tmdb_id: pick.tmdb_id, media_type: pick.media_type, link: pick.deep_link_url });
  if (!inShell() && pick.deep_link_url) window.open(pick.deep_link_url, '_blank', 'noopener');
}

export function exitApp() {
  postToShell({ type: 'exit' });
}
