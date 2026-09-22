/* ── Mood selection — the first step of generating a session ── */

import { useState } from 'react';
import { clsx } from 'clsx';
import { useDpad } from '@/hooks/useDpad';
import type { Mood } from '@/types';

const MOODS: { id: Mood; label: string; emoji: string; color: string }[] = [
  { id: 'tired', label: 'Tired', emoji: '😴', color: 'from-blue-600/40 to-blue-900/20' },
  { id: 'energised', label: 'Energised', emoji: '🤩', color: 'from-orange-600/40 to-orange-900/20' },
  { id: 'stressed', label: 'Stressed', emoji: '😮‍💨', color: 'from-amber-600/40 to-amber-900/20' },
  { id: 'social', label: 'Social', emoji: '🎉', color: 'from-pink-600/40 to-pink-900/20' },
  { id: 'bored', label: 'Bored', emoji: '😑', color: 'from-gray-600/40 to-gray-900/20' },
  { id: 'adventurous', label: 'Adventurous', emoji: '🗺️', color: 'from-emerald-600/40 to-emerald-900/20' },
];

interface Props {
  onSelect: (mood: Mood) => void;
}

export default function MoodPicker({ onSelect }: Props) {
  const [focusIdx, setFocusIdx] = useState(0);

  useDpad({
    onNavigate: (dir) => {
      if (dir === 'left' || dir === 'up') {
        setFocusIdx((i) => (i - 1 + MOODS.length) % MOODS.length);
      } else {
        setFocusIdx((i) => (i + 1) % MOODS.length);
      }
    },
    onSelect: () => onSelect(MOODS[focusIdx].id),
  });

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-tv-2xl font-bold">How are you feeling?</h1>
        <p className="text-tv-base text-vibe-text-muted mt-3">
          Pick your vibe and we'll build the perfect session.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 max-w-3xl mx-auto">
        {MOODS.map((mood, idx) => (
          <button
            key={mood.id}
            onClick={() => onSelect(mood.id)}
            className={clsx(
              'relative flex flex-col items-center justify-center p-8 rounded-tv',
              'transition-all duration-300 bg-gradient-to-br',
              mood.color,
              idx === focusIdx && 'ring-4 ring-vibe-accent scale-110 z-10',
              idx !== focusIdx && 'hover:scale-105',
            )}
          >
            <span className="text-5xl mb-3">{mood.emoji}</span>
            <span className="text-tv-lg font-semibold">{mood.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
