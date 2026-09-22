/* ── Optional time budget picker ── */

import { useState } from 'react';
import { clsx } from 'clsx';
import { useDpad } from '@/hooks/useDpad';
import FocusableButton from '@/components/common/FocusableButton';

const PRESETS = [
  { label: '1 hour', minutes: 60 },
  { label: '1.5 hours', minutes: 90 },
  { label: '2 hours', minutes: 120 },
  { label: '3 hours', minutes: 180 },
  { label: 'No limit', minutes: 0 },
];

interface Props {
  onSelect: (minutes: number | undefined) => void;
  onBack: () => void;
}

export default function TimeBudget({ onSelect, onBack }: Props) {
  const [focusIdx, setFocusIdx] = useState(2); // default to 2 hours

  useDpad({
    onNavigate: (dir) => {
      if (dir === 'up' || dir === 'left') setFocusIdx((i) => Math.max(0, i - 1));
      else setFocusIdx((i) => Math.min(PRESETS.length - 1, i + 1));
    },
    onSelect: () => {
      const m = PRESETS[focusIdx].minutes;
      onSelect(m === 0 ? undefined : m);
    },
    onBack,
  });

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-tv-xl font-bold">How much time do you have?</h2>
        <p className="text-tv-base text-vibe-text-muted mt-2">
          We'll fit the perfect lineup into your window.
        </p>
      </div>

      <div className="flex flex-col items-center gap-3 max-w-md mx-auto">
        {PRESETS.map((preset, idx) => (
          <button
            key={preset.minutes}
            onClick={() => onSelect(preset.minutes === 0 ? undefined : preset.minutes)}
            className={clsx(
              'w-full p-5 rounded-tv text-tv-lg font-semibold transition-all',
              idx === focusIdx
                ? 'bg-vibe-accent text-white scale-105 ring-4 ring-vibe-accent/40'
                : 'bg-vibe-card text-vibe-text hover:bg-vibe-border',
            )}
          >
            {preset.label}
          </button>
        ))}
      </div>

      <div className="flex justify-center">
        <FocusableButton variant="ghost" onClick={onBack}>
          ← Change mood
        </FocusableButton>
      </div>
    </div>
  );
}
