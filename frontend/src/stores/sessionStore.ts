/* ── Zustand store for the active session plan ── */

import { create } from 'zustand';
import type { Mood, Pick, SessionPlan, StreamEvent } from '@/types';
import * as api from '@/api/client';

interface SessionState {
  /* current plan being generated / viewed */
  plan: SessionPlan | null;
  isStreaming: boolean;
  streamPhase: 'idle' | 'trajectory' | 'picks' | 'summary' | 'done' | 'error';
  error: string | null;

  /* past plans */
  history: SessionPlan[];
  historyLoaded: boolean;

  /* actions */
  generatePlan: (mood: Mood, timeBudget?: number, voiceTranscript?: string) => Promise<void>;
  loadPlan: (planId: string) => Promise<void>;
  loadHistory: () => Promise<void>;
  updatePickStatus: (pickId: string, status: string) => Promise<void>;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  plan: null,
  isStreaming: false,
  streamPhase: 'idle',
  error: null,
  history: [],
  historyLoaded: false,

  generatePlan: async (mood, timeBudget, voiceTranscript) => {
    set({
      isStreaming: true,
      streamPhase: 'trajectory',
      error: null,
      plan: {
        id: '',
        mood,
        energy_trajectory: null,
        time_budget_minutes: timeBudget ?? null,
        total_runtime_minutes: null,
        plan_summary: null,
        status: 'generating',
        created_at: null,
        picks: [],
      },
    });

    try {
      for await (const event of api.streamPlan(mood, timeBudget, voiceTranscript)) {
        const current = get().plan;
        if (!current) break;

        switch (event.type) {
          case 'trajectory':
            set({
              streamPhase: 'picks',
              plan: { ...current, energy_trajectory: event.data.energy_trajectory },
            });
            break;

          case 'pick':
            set({
              plan: {
                ...current,
                id: event.data.plan_id || current.id,
                picks: [...current.picks, event.data as unknown as Pick],
              },
            });
            break;

          case 'summary':
            set({
              streamPhase: 'summary',
              plan: {
                ...current,
                id: event.data.plan_id || current.id,
                total_runtime_minutes: event.data.total_runtime_minutes,
                plan_summary: event.data.plan_summary,
                status: 'generated',
              },
            });
            break;

          case 'error':
            set({ error: event.data.message, streamPhase: 'error' });
            break;
        }
      }

      set({ isStreaming: false, streamPhase: 'done' });
    } catch (err: any) {
      set({ isStreaming: false, streamPhase: 'error', error: err.message ?? 'Stream failed' });
    }
  },

  loadPlan: async (planId) => {
    try {
      const data = await api.getPlan(planId);
      set({ plan: data, streamPhase: 'done' });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  loadHistory: async () => {
    try {
      const { plans } = await api.listPlans(20);
      set({ history: plans, historyLoaded: true });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  updatePickStatus: async (pickId, status) => {
    const plan = get().plan;
    if (!plan) return;

    try {
      await api.updatePickStatus(plan.id, pickId, status);
      set({
        plan: {
          ...plan,
          picks: plan.picks.map((p) => (p.id === pickId ? { ...p, status: status as any } : p)),
        },
      });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  reset: () =>
    set({ plan: null, isStreaming: false, streamPhase: 'idle', error: null }),
}));
