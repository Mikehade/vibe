export type Mood = 'tired' | 'energised' | 'stressed' | 'social' | 'bored' | 'adventurous';
export type Role = 'opener' | 'main_event' | 'bridge' | 'nightcap';
export type PickStatus = 'pending' | 'watching' | 'completed' | 'skipped';
export type Shift = 'wind_down' | 'steady' | 'lift';

export interface Provider {
  id: number;
  name: string;
  logo_path?: string | null;
}

export interface Profile {
  id?: string;
  name?: string;
  is_kids: boolean;
  region?: string;
  genre_weights: Record<string, number>;
  disliked_genres: string[];
  preferred_providers: Provider[];
  onboarding_completed: boolean;
}

export interface Pick {
  id?: string;
  plan_id?: string;
  position: number;
  role: Role;
  role_label?: string;
  energy?: number | null;
  tmdb_id: number;
  media_type: 'movie' | 'tv';
  title: string;
  year?: number | null;
  overview?: string | null;
  poster_path: string | null;
  backdrop_path?: string | null;
  runtime_minutes: number;
  episode_runtime?: number | null;
  episodes?: number | null;
  rating?: number | null;
  certification?: string | null;
  genre_ids: number[];
  genres?: string[];
  reason: string;
  confidence?: number | null;
  streaming_provider: string | null;
  provider_logo_path?: string | null;
  deep_link_url?: string | null;
  status: PickStatus;
  source?: 'ai' | 'fallback' | 'swap';
}

export interface ArcSlot {
  position: number;
  role: Role;
  label: string;
  energy: number;
  target_minutes: number;
}

export interface Arc {
  direction: string;
  arc_shape: string;
  energy_trajectory: string;
  budget_minutes: number;
  slots: ArcSlot[];
  provisional?: boolean;
}

export interface Plan {
  id: string;
  mood: Mood;
  energy_trajectory: string | null;
  time_budget_minutes: number | null;
  total_runtime_minutes: number | null;
  plan_summary: string | null;
  status: string;
  created_at: string | null;
  local_time?: string | null;
  arc?: Arc | null;
  notes?: string | null;
  audience?: string | null;
  picks: Pick[];
}

export interface LogLine {
  id: number;
  stage: string;
  message: string;
  kind: 'status' | 'tool' | 'pick' | 'error';
  at: number;
}

export interface CandidateSample {
  tmdb_id: number;
  media_type: string;
  title: string;
  poster_path: string | null;
}

export type StreamEvent =
  | { type: 'plan'; data: { plan_id: string; mood: Mood } }
  | { type: 'replan'; data: { plan_id: string; after_position: number; shift: Shift } }
  | { type: 'status'; data: { stage: string; message: string } }
  | { type: 'trajectory'; data: Arc }
  | { type: 'candidates'; data: { count: number; outside_services: boolean; sample: CandidateSample[] } }
  | { type: 'tool'; data: { name: string; message: string } }
  | { type: 'pick'; data: Pick }
  | { type: 'summary'; data: { plan_summary: string; total_runtime_minutes: number } }
  | { type: 'done'; data: { plan_id: string; elapsed_ms: number } }
  | { type: 'error'; data: { message: string } }
  | { type: 'keepalive'; data: Record<string, never> };

export interface RoomMember {
  id: string;
  name: string;
  mood: Mood | null;
  notes: string;
  vetoes: string[];
  ready: boolean;
}

export interface Room {
  code: string;
  status: 'lobby' | 'planning' | 'ready';
  plan_id: string | null;
  version: number;
  members: RoomMember[];
  skip_votes: Record<string, { votes: number; needed: number }>;
}
