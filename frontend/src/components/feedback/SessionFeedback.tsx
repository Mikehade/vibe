/* ── Post-session feedback form ── */

import { useState } from 'react';
import { clsx } from 'clsx';
import { submitSessionFeedback, submitPickFeedback } from '@/api/client';
import { useSessionStore } from '@/stores/sessionStore';
import FocusableButton from '@/components/common/FocusableButton';

interface Props {
  onDone: () => void;
}

export default function SessionFeedback({ onDone }: Props) {
  const plan = useSessionStore((s) => s.plan);
  const [overallRating, setOverallRating] = useState<'thumbs_up' | 'thumbs_down' | null>(null);
  const [pacingRating, setPacingRating] = useState<string | null>(null);
  const [pickRatings, setPickRatings] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!plan) return null;

  const handleSubmit = async () => {
    if (!overallRating) return;
    setSubmitting(true);

    try {
      // Submit session-level feedback
      await submitSessionFeedback(plan.id, overallRating, pacingRating ?? undefined);

      // Submit individual pick feedback
      for (const [pickId, rating] of Object.entries(pickRatings)) {
        await submitPickFeedback(pickId, rating);
      }

      setSubmitted(true);
      setTimeout(onDone, 1500);
    } catch {
      // silently continue
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-16">
        <span className="text-6xl">🎉</span>
        <h2 className="text-tv-xl font-bold">Thanks for the feedback!</h2>
        <p className="text-tv-base text-vibe-text-muted">Your taste profile just got smarter.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      <div className="text-center">
        <h2 className="text-tv-xl font-bold">How was this session?</h2>
        <p className="text-tv-base text-vibe-text-muted mt-2">
          Your feedback helps Vibe learn what you love.
        </p>
      </div>

      {/* Overall rating */}
      <div className="flex justify-center gap-6">
        {(['thumbs_up', 'thumbs_down'] as const).map((r) => (
          <button
            key={r}
            onClick={() => setOverallRating(r)}
            className={clsx(
              'text-6xl p-4 rounded-tv transition-all',
              overallRating === r && 'bg-vibe-card ring-4 ring-vibe-accent scale-110',
              overallRating !== r && 'opacity-50 hover:opacity-80',
            )}
          >
            {r === 'thumbs_up' ? '👍' : '👎'}
          </button>
        ))}
      </div>

      {/* Pacing */}
      {overallRating === 'thumbs_up' && (
        <div className="space-y-3">
          <p className="text-tv-sm font-medium text-center">How was the pacing?</p>
          <div className="flex justify-center gap-3">
            {['slow', 'balanced', 'fast'].map((p) => (
              <button
                key={p}
                onClick={() => setPacingRating(p)}
                className={clsx(
                  'px-6 py-3 rounded-tv text-tv-sm font-semibold capitalize transition-all',
                  pacingRating === p ? 'bg-vibe-accent text-white' : 'bg-vibe-card text-vibe-text',
                )}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Individual pick ratings */}
      <div className="space-y-3">
        <p className="text-tv-sm font-medium text-center">Rate individual picks (optional)</p>
        {plan.picks.map((pick) => (
          <div
            key={pick.id}
            className="flex items-center justify-between p-4 rounded-tv bg-vibe-card"
          >
            <span className="text-tv-sm font-medium">{pick.title}</span>
            <div className="flex gap-2">
              {(['thumbs_up', 'thumbs_down'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setPickRatings((prev) => ({ ...prev, [pick.id]: r }))}
                  className={clsx(
                    'text-2xl p-2 rounded-lg transition-all',
                    pickRatings[pick.id] === r && 'bg-vibe-accent/30',
                    pickRatings[pick.id] !== r && 'opacity-40 hover:opacity-70',
                  )}
                >
                  {r === 'thumbs_up' ? '👍' : '👎'}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center gap-4">
        <FocusableButton onClick={handleSubmit} disabled={!overallRating || submitting}>
          {submitting ? 'Submitting...' : 'Submit Feedback'}
        </FocusableButton>
        <FocusableButton variant="ghost" onClick={onDone}>
          Skip
        </FocusableButton>
      </div>
    </div>
  );
}
