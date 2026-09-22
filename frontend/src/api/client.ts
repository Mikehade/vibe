/* ── API client for the Vibe backend ── */

import type { OnboardingData, StreamEvent, TasteProfile } from '@/types';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

function getDeviceId(): string {
  let id = localStorage.getItem('vibe_device_id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('vibe_device_id', id);
  }
  return id;
}

function headers(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'X-Device-ID': getDeviceId(),
  };
}

async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { ...headers(), ...opts.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

/* ── Session / Plan ── */

export async function* streamPlan(
  mood: string,
  timeBudget?: number,
  voiceTranscript?: string,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/session/plan`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      mood,
      time_budget_minutes: timeBudget ?? null,
      voice_transcript: voiceTranscript ?? null,
    }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        yield JSON.parse(trimmed) as StreamEvent;
      } catch {
        // skip malformed lines
      }
    }
  }

  // flush remaining
  if (buffer.trim()) {
    try {
      yield JSON.parse(buffer.trim()) as StreamEvent;
    } catch {
      // skip
    }
  }
}

export function getPlan(planId: string) {
  return api<any>(`/session/plan/${planId}`);
}

export function listPlans(limit = 10, offset = 0) {
  return api<{ plans: any[]; count: number }>(`/session/plans?limit=${limit}&offset=${offset}`);
}

export function updatePickStatus(planId: string, pickId: string, status: string) {
  return api(`/session/plan/${planId}/pick/${pickId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

/* ── Mood ── */

export function parseMood(transcript: string) {
  return api<{ mood: string; intensity: number; notes: string }>('/mood/parse', {
    method: 'POST',
    body: JSON.stringify({ transcript }),
  });
}

/* ── Profile ── */

export function getProfile() {
  return api<TasteProfile>('/profile');
}

export function saveOnboarding(data: OnboardingData) {
  return api('/profile/onboarding', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/* ── Feedback ── */

export function submitSessionFeedback(
  planId: string,
  overallRating: string,
  pacingRating?: string,
  comment?: string,
) {
  return api(`/session/plan/${planId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({
      overall_rating: overallRating,
      pacing_rating: pacingRating ?? null,
      comment: comment ?? null,
    }),
  });
}

export function submitPickFeedback(pickId: string, rating: string) {
  return api(`/session/pick/${pickId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ rating }),
  });
}

/* ── Content ── */

export function searchContent(query: string, page = 1) {
  return api<any>(`/content/search?q=${encodeURIComponent(query)}&page=${page}`);
}

export { getDeviceId };
