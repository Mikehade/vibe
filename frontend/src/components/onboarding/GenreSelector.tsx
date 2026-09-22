/* ── Genre preference swipe cards for onboarding ── */

import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useDpad } from '@/hooks/useDpad';
import { useProfileStore } from '@/stores/profileStore';
import FocusableButton from '@/components/common/FocusableButton';

const GENRE_EMOJI: Record<string, string> = {
  action: '💥', comedy: '😂', drama: '🎭', horror: '👻', romance: '💕',
  'sci-fi': '🚀', thriller: '🔪', animation: '🎨', documentary: '📽', fantasy: '🧙',
};

export default function GenreSelector() {
  const { genrePreferences, setGenrePreference, nextStep } = useProfileStore();
  const [focusIdx, setFocusIdx] = useState(0);
  const [actionFocus, setActionFocus] = useState<number>(0); // 0=like, 1=skip, 2=dislike

  useDpad({
    onNavigate: (dir) => {
      if (dir === 'up' || dir === 'down') {
        setFocusIdx((i) => {
          const next = dir === 'up' ? i - 1 : i + 1;
          return Math.max(0, Math.min(genrePreferences.length - 1, next));
        });
      }
      if (dir === 'left' || dir === 'right') {
        setActionFocus((i) => {
          const next = dir === 'left' ? i - 1 : i + 1;
          return Math.max(0, Math.min(2, next));
        });
      }
    },
    onSelect: () => {
      const genre = genrePreferences[focusIdx].genre;
      const actions = ['like', 'skip', 'dislike'] as const;
      setGenrePreference(genre, actions[actionFocus]);
    },
  });

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-tv-xl font-bold">What do you love?</h2>
        <p className="text-tv-base text-vibe-text-muted mt-2">
          Tell us your genre preferences so we can curate perfect sessions.
        </p>
      </div>

      <div className="grid gap-3 max-w-2xl mx-auto">
        {genrePreferences.map((gp, idx) => (
          <div
            key={gp.genre}
            className={clsx(
              'flex items-center justify-between p-4 rounded-tv transition-all',
              idx === focusIdx ? 'bg-vibe-card ring-2 ring-vibe-accent' : 'bg-vibe-surface',
            )}
          >
            <span className="text-tv-base font-medium flex items-center gap-3">
              <span className="text-2xl">{GENRE_EMOJI[gp.genre] ?? '🎬'}</span>
              <span className="capitalize">{gp.genre}</span>
            </span>

            <div className="flex gap-2">
              {(['like', 'skip', 'dislike'] as const).map((action, ai) => (
                <button
                  key={action}
                  onClick={() => setGenrePreference(gp.genre, action)}
                  className={clsx(
                    'px-4 py-2 rounded-lg text-sm font-semibold transition-all',
                    gp.action === action && action === 'like' && 'bg-vibe-success text-white',
                    gp.action === action && action === 'dislike' && 'bg-vibe-danger text-white',
                    gp.action === action && action === 'skip' && 'bg-vibe-text-muted/30 text-vibe-text',
                    gp.action !== action && 'bg-vibe-surface text-vibe-text-muted hover:bg-vibe-border',
                    idx === focusIdx && ai === actionFocus && 'ring-2 ring-white',
                  )}
                >
                  {action === 'like' ? '👍' : action === 'dislike' ? '👎' : '—'}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center">
        <FocusableButton size="lg" onClick={nextStep}>
          Next: Streaming Services →
        </FocusableButton>
      </div>
    </div>
  );
}
