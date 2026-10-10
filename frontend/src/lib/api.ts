/* API client — device id, household profile header, NDJSON streaming. */

import type { Plan, Profile, Provider, Room, Shift, StreamEvent } from './types';
import { localIso, tzOffsetMinutes } from './time';

export const API_BASE: string = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1';

function store(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

let memoryDeviceId: string | null = null;
export function getDeviceId(): string {
  const s = store();
  let id = s?.getItem('vibe_device_id') ?? memoryDeviceId;
  if (!id) {
    id = (crypto as any).randomUUID ? crypto.randomUUID() : `dev-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    s?.setItem('vibe_device_id', id);
    memoryDeviceId = id;
  }
  return id;
}

export function getActiveProfileId(): string | null {
  return store()?.getItem('vibe_profile_id') ?? null;
}
export function setActiveProfileId(id: string | null) {
  const s = store();
  if (!s) return;
  if (id) s.setItem('vibe_profile_id', id);
  else s.removeItem('vibe_profile_id');
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json', 'X-Device-ID': getDeviceId() };
  const pid = getActiveProfileId();
  if (pid) h['X-Profile-ID'] = pid;
  return h;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail ?? body.message ?? `Request failed (${res.status})`;
    throw new ApiError(typeof detail === 'string' ? detail : JSON.stringify(detail), res.status);
  }
  return res.json();
}

/* ── NDJSON stream ── */

export async function* readNdjson(res: Response): AsyncGenerator<StreamEvent> {
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `Stream failed (${res.status})`, res.status);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      try {
        yield JSON.parse(line) as StreamEvent;
      } catch {
        /* ignore malformed line */
      }
    }
  }
  if (buffer.trim()) {
    try {
      yield JSON.parse(buffer.trim()) as StreamEvent;
    } catch {
      /* ignore */
    }
  }
}

export interface PlanParams {
  mood: string;
  time_budget_minutes?: number | null;
  voice_transcript?: string | null;
  kids_mode?: boolean | null;
  room_code?: string | null;
}

export function streamPlan(params: PlanParams, signal?: AbortSignal) {
  return fetch(`${API_BASE}/session/plan`, {
    method: 'POST',
    headers: headers(),
    signal,
    body: JSON.stringify({ ...params, local_time: localIso(), tz_offset_minutes: tzOffsetMinutes() }),
  }).then(readNdjson);
}

export function streamReplan(planId: string, afterPosition: number, shift: Shift, signal?: AbortSignal) {
  return fetch(`${API_BASE}/session/plan/${planId}/replan`, {
    method: 'POST',
    headers: headers(),
    signal,
    body: JSON.stringify({ after_position: afterPosition, shift, local_time: localIso(), tz_offset_minutes: tzOffsetMinutes() }),
  }).then(readNdjson);
}

export function followPlan(planId: string, signal?: AbortSignal) {
  return fetch(`${API_BASE}/session/plan/${planId}/live`, { headers: headers(), signal }).then(readNdjson);
}

export const prefetch = (mood: string, kids_mode?: boolean | null) =>
  api('/session/prefetch', { method: 'POST', body: JSON.stringify({ mood, kids_mode }) }).catch(() => null);

export const getPlan = (id: string) => api<Plan>(`/session/plan/${id}`);
export const latestPlan = () => api<{ plan: Plan | null }>('/session/plan/latest');
export const listPlans = (limit = 20) => api<{ plans: Plan[]; count: number }>(`/session/plans?limit=${limit}`);
export const swapPick = (planId: string, pickId: string) =>
  api<{ pick: any; replaced_pick_id: string; total_runtime_minutes: number }>(`/session/plan/${planId}/pick/${pickId}/swap`, { method: 'POST' });
export const setPickStatus = (planId: string, pickId: string, status: string) =>
  api(`/session/plan/${planId}/pick/${pickId}`, { method: 'PATCH', body: JSON.stringify({ status }) });

export const sessionFeedback = (planId: string, overall: string, pacing?: string | null) =>
  api(`/session/plan/${planId}/feedback`, { method: 'POST', body: JSON.stringify({ overall_rating: overall, pacing_rating: pacing ?? null }) });
export const pickFeedback = (pickId: string, rating: string) =>
  api(`/session/pick/${pickId}/feedback`, { method: 'POST', body: JSON.stringify({ rating }) });

/* ── Profiles ── */
export const getProfile = () => api<Profile>('/profile');
export const listProfiles = () => api<{ profiles: Profile[] }>('/profile/all');
export const saveOnboarding = (data: {
  name?: string;
  is_kids?: boolean;
  region?: string;
  genre_preferences?: { genre: string; action: string }[];
  streaming_services?: Provider[];
  new_profile?: boolean;
}) => api<Profile>('/profile/onboarding', { method: 'PATCH', body: JSON.stringify(data) });
export const updateSettings = (data: Partial<{ name: string; is_kids: boolean; region: string; streaming_services: Provider[]; reset_exclusions: boolean }>) =>
  api<Profile>('/profile/settings', { method: 'PATCH', body: JSON.stringify(data) });

/* ── Content ── */
export const providersFor = (region: string) => api<{ region: string; providers: Provider[] }>(`/content/providers?region=${region}`);

/* ── Couch Mode ── */
export const createRoom = () => api<Room>('/couch/rooms', { method: 'POST' });
export const getRoom = (code: string) => api<Room>(`/couch/rooms/${code}`);
export const closeRoom = (code: string) => api(`/couch/rooms/${code}`, { method: 'DELETE' });
export const joinRoom = (code: string, name: string) =>
  api<{ member_id: string; room: Room }>(`/couch/rooms/${code}/join`, { method: 'POST', body: JSON.stringify({ name }) });
export const updateMember = (code: string, memberId: string, data: { mood?: string; notes?: string; vetoes?: string[] }) =>
  api<Room>(`/couch/rooms/${code}/members/${memberId}`, { method: 'PATCH', body: JSON.stringify(data) });
export const voteSkip = (code: string, memberId: string, pickId: string) =>
  api<{ votes: number; needed: number; passed: boolean }>(`/couch/rooms/${code}/members/${memberId}/skip`, {
    method: 'POST',
    body: JSON.stringify({ pick_id: pickId }),
  });

/* ── TV link (Alexa+) ── */
export const pairCode = () => api<{ code: string; expires_in: number; linked: boolean }>(`/tv/pair-code?tz_offset_minutes=${tzOffsetMinutes()}`, { method: 'POST' });
export const inbox = () => api<{ events: { type: string; data: any }[]; linked: boolean }>(`/tv/inbox?tz_offset_minutes=${tzOffsetMinutes()}`);
