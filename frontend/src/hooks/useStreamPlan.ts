/* ── Convenience hook wrapping the session store's stream ── */

import { useCallback } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import type { Mood } from '@/types';

export function useStreamPlan() {
  const generatePlan = useSessionStore((s) => s.generatePlan);
  const isStreaming = useSessionStore((s) => s.isStreaming);
  const streamPhase = useSessionStore((s) => s.streamPhase);
  const plan = useSessionStore((s) => s.plan);
  const error = useSessionStore((s) => s.error);
  const reset = useSessionStore((s) => s.reset);

  const start = useCallback(
    (mood: Mood, timeBudget?: number, voiceTranscript?: string) => {
      generatePlan(mood, timeBudget, voiceTranscript);
    },
    [generatePlan],
  );

  return { start, isStreaming, streamPhase, plan, error, reset };
}
