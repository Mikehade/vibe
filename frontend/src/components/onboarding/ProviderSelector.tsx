/* ── Streaming provider selection for onboarding ── */

import { useState } from 'react';
import { clsx } from 'clsx';
import { useDpad } from '@/hooks/useDpad';
import { useProfileStore } from '@/stores/profileStore';
import FocusableButton from '@/components/common/FocusableButton';

const PROVIDERS = [
  { id: 'netflix', name: 'Netflix', color: '#E50914' },
  { id: 'prime', name: 'Prime Video', color: '#00A8E1' },
  { id: 'disney', name: 'Disney+', color: '#113CCF' },
  { id: 'hbo', name: 'Max (HBO)', color: '#5822B4' },
  { id: 'hulu', name: 'Hulu', color: '#1CE783' },
  { id: 'apple', name: 'Apple TV+', color: '#555555' },
  { id: 'peacock', name: 'Peacock', color: '#FDB927' },
  { id: 'paramount', name: 'Paramount+', color: '#0064FF' },
];

export default function ProviderSelector() {
  const { selectedProviders, toggleProvider, submitOnboarding, prevStep, loading } =
    useProfileStore();
  const [focusIdx, setFocusIdx] = useState(0);

  useDpad({
    onNavigate: (dir) => {
      if (dir === 'up' || dir === 'left') {
        setFocusIdx((i) => Math.max(0, i - 1));
      } else {
        setFocusIdx((i) => Math.min(PROVIDERS.length - 1, i + 1));
      }
    },
    onSelect: () => toggleProvider(PROVIDERS[focusIdx].id),
  });

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-tv-xl font-bold">Where do you stream?</h2>
        <p className="text-tv-base text-vibe-text-muted mt-2">
          Select your services so we show you where to watch.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 max-w-lg mx-auto">
        {PROVIDERS.map((p, idx) => {
          const selected = selectedProviders.includes(p.id);
          return (
            <button
              key={p.id}
              onClick={() => toggleProvider(p.id)}
              className={clsx(
                'flex items-center gap-3 p-4 rounded-tv transition-all text-left',
                selected ? 'bg-vibe-card ring-2' : 'bg-vibe-surface',
                idx === focusIdx && 'ring-2 ring-vibe-accent scale-105',
              )}
              style={selected ? { borderColor: p.color } : undefined}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-lg"
                style={{ background: p.color }}
              >
                {p.name[0]}
              </div>
              <span className="text-tv-sm font-medium">{p.name}</span>
              {selected && <span className="ml-auto text-vibe-success text-xl">✓</span>}
            </button>
          );
        })}
      </div>

      <div className="flex justify-center gap-4">
        <FocusableButton variant="secondary" size="lg" onClick={prevStep}>
          ← Back
        </FocusableButton>
        <FocusableButton size="lg" onClick={submitOnboarding} disabled={loading}>
          {loading ? 'Saving...' : "Let's Go →"}
        </FocusableButton>
      </div>
    </div>
  );
}
