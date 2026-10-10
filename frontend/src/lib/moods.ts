import type { Mood, Role } from './types';

export const MOODS: { id: Mood; label: string; line: string; from: string; to: string; glow: string }[] = [
  { id: 'tired', label: 'Tired', line: 'Low battery. Keep it easy.', from: '#1b2440', to: '#2c3b6b', glow: '#7f9fdc' },
  { id: 'stressed', label: 'Stressed', line: 'Need to switch off.', from: '#12302b', to: '#23564b', glow: '#8cc0ad' },
  { id: 'social', label: 'Social', line: 'Company on the couch.', from: '#3a1a24', to: '#6b2e3c', glow: '#e89a8f' },
  { id: 'bored', label: 'Bored', line: 'Surprise me.', from: '#261c3d', to: '#46336e', glow: '#a99be0' },
  { id: 'energised', label: 'Energised', line: 'Bring the momentum.', from: '#3a2410', to: '#7a4a17', glow: '#e8b04b' },
  { id: 'adventurous', label: 'Adventurous', line: 'Take me somewhere new.', from: '#10302f', to: '#1d5a5a', glow: '#79c7c2' },
];

export const moodById = (id: string) => MOODS.find((m) => m.id === id) ?? MOODS[0];

export const ROLE_COLOR: Record<Role, string> = {
  opener: '#8cc0ad',
  main_event: '#e8b04b',
  bridge: '#a99be0',
  nightcap: '#7f9fdc',
};

export const ROLE_LABEL: Record<Role, string> = {
  opener: 'Opener',
  main_event: 'Main event',
  bridge: 'Palate cleanser',
  nightcap: 'Nightcap',
};

// TMDB genre names (lower-case) — must match the backend's taste keys
export const GENRES = [
  'comedy', 'drama', 'action', 'adventure', 'animation', 'science fiction', 'fantasy',
  'thriller', 'mystery', 'crime', 'horror', 'romance', 'documentary', 'family',
];

export const VETO_OPTIONS = ['horror', 'thriller', 'romance', 'animation', 'documentary', 'war', 'crime'];

export const REGIONS: { code: string; name: string }[] = [
  { code: 'US', name: 'United States' }, { code: 'GB', name: 'United Kingdom' }, { code: 'NG', name: 'Nigeria' },
  { code: 'CA', name: 'Canada' }, { code: 'IN', name: 'India' }, { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' }, { code: 'AU', name: 'Australia' }, { code: 'ZA', name: 'South Africa' },
  { code: 'KE', name: 'Kenya' }, { code: 'GH', name: 'Ghana' }, { code: 'BR', name: 'Brazil' },
  { code: 'MX', name: 'Mexico' }, { code: 'ES', name: 'Spain' }, { code: 'IT', name: 'Italy' }, { code: 'NL', name: 'Netherlands' },
];

export function guessRegion(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    const map: Record<string, string> = {
      'Africa/Lagos': 'NG', 'Europe/London': 'GB', 'Africa/Johannesburg': 'ZA', 'Africa/Nairobi': 'KE',
      'Africa/Accra': 'GH', 'Asia/Kolkata': 'IN', 'Asia/Calcutta': 'IN', 'Europe/Berlin': 'DE', 'Europe/Paris': 'FR',
      'Europe/Madrid': 'ES', 'Europe/Rome': 'IT', 'Europe/Amsterdam': 'NL', 'America/Sao_Paulo': 'BR',
      'America/Mexico_City': 'MX', 'America/Toronto': 'CA', 'America/Vancouver': 'CA',
    };
    if (map[tz]) return map[tz];
    if (tz.startsWith('Australia/')) return 'AU';
    if (tz.startsWith('America/')) return 'US';
    const lang = navigator.language || '';
    const cc = lang.split('-')[1];
    if (cc && REGIONS.some((r) => r.code === cc.toUpperCase())) return cc.toUpperCase();
  } catch {
    /* ignore */
  }
  return 'US';
}
