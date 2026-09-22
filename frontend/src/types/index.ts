/* ── Domain types matching backend schemas ── */

export type Mood = 'tired' | 'energised' | 'stressed' | 'social' | 'bored' | 'adventurous';

export type ArcRole = 'opener' | 'main_event' | 'bridge' | 'nightcap';

export type PickStatus = 'pending' | 'watching' | 'completed' | 'skipped';

export type PlanStatus = 'generated' | 'active' | 'completed' | 'abandoned';

export interface Pick {
  id: string;
  position: number;
  role: ArcRole;
  tmdb_id: number;
  title: string;
  poster_path: string | null;
  runtime_minutes: number;
  genre_ids: number[];
  reason: string;
  confidence: number;
  streaming_provider: string | null;
  deep_link_url: string | null;
  status: PickStatus;
}

export interface SessionPlan {
  id: string;
  mood: Mood;
  energy_trajectory: string | null;
  time_budget_minutes: number | null;
  total_runtime_minutes: number | null;
  plan_summary: string | null;
  status: PlanStatus;
  created_at: string | null;
  picks: Pick[];
}

export interface TasteProfile {
  id?: string;
  device_id?: string;
  genre_weights: Record<string, number>;
  pacing_preference: string | null;
  disliked_genres: string[];
  preferred_providers: string[];
  avg_session_length_minutes: number | null;
  onboarding_completed: boolean;
}

export interface GenrePreference {
  genre: string;
  action: 'like' | 'dislike' | 'skip';
}

export interface OnboardingData {
  genre_preferences: GenrePreference[];
  streaming_services: string[];
}

export interface MoodParseResult {
  mood: Mood;
  intensity: number;
  notes: string;
}

/* ── NDJSON stream event types ── */

export interface TrajectoryEvent {
  type: 'trajectory';
  data: {
    energy_trajectory: string;
    arc_roles: string[];
    session_size: number;
  };
}

export interface PickEvent {
  type: 'pick';
  data: Pick & { plan_id: string };
}

export interface SummaryEvent {
  type: 'summary';
  data: {
    plan_id: string;
    total_runtime_minutes: number;
    plan_summary: string;
  };
}

export interface ErrorEvent {
  type: 'error';
  data: { message: string };
}

export type StreamEvent = TrajectoryEvent | PickEvent | SummaryEvent | ErrorEvent;
