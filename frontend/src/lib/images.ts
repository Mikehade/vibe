import { API_BASE } from './api';

const TMDB = 'https://image.tmdb.org/t/p';

export type ImgSize = 'w92' | 'w185' | 'w342' | 'w500' | 'w780' | 'w1280' | 'original';

/** TMDB image url, or the API's generated artwork in offline demo mode. */
export function img(path: string | null | undefined, size: ImgSize = 'w342'): string | null {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  if (path.startsWith('/fake-art/')) return `${API_BASE}/content/art/${path.slice('/fake-art/'.length)}`;
  return `${TMDB}/${size}${path}`;
}

export function logo(path: string | null | undefined): string | null {
  if (!path || !/^\/[A-Za-z0-9_-]{10,}\.(png|jpg|svg)$/.test(path)) return null;
  return `${TMDB}/w92${path}`;
}
