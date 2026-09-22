/* ── Main session flow — mood → time → plan → feedback ── */

import { useState, useCallback } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import MoodPicker from '@/components/session/MoodPicker';
import TimeBudget from '@/components/session/TimeBudget';
import PlanView from '@/components/session/PlanView';
import SessionFeedback from '@/components/feedback/SessionFeedback';
import type { Mood } from '@/types';

type Phase = 'mood' | 'time' | 'plan' | 'feedback';

export default function SessionPage() {
  const [phase, setPhase] = useState<Phase>('mood');
  const [selectedMood, setSelectedMood] = useState<Mood | null>(null);
  const generatePlan = useSessionStore((s) => s.generatePlan);
  const reset = useSessionStore((s) => s.reset);

  const handleMoodSelect = useCallback((mood: Mood) => {
    setSelectedMood(mood);
    setPhase('time');
  }, []);

  const handleTimeSelect = useCallback(
    (minutes?: number) => {
      if (selectedMood) {
        generatePlan(selectedMood, minutes);
        setPhase('plan');
      }
    },
    [selectedMood, generatePlan],
  );

  const handleReset = useCallback(() => {
    reset();
    setSelectedMood(null);
    setPhase('mood');
  }, [reset]);

  return (
    <div className="min-h-screen p-8">
      {phase === 'mood' && <MoodPicker onSelect={handleMoodSelect} />}
      {phase === 'time' && (
        <TimeBudget onSelect={handleTimeSelect} onBack={() => setPhase('mood')} />
      )}
      {phase === 'plan' && (
        <PlanView onFeedback={() => setPhase('feedback')} onReset={handleReset} />
      )}
      {phase === 'feedback' && <SessionFeedback onDone={handleReset} />}
    </div>
  );
}
