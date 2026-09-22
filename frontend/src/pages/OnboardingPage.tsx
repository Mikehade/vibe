/* ── Onboarding wizard — genres + providers ── */

import { useProfileStore } from '@/stores/profileStore';
import GenreSelector from '@/components/onboarding/GenreSelector';
import ProviderSelector from '@/components/onboarding/ProviderSelector';

export default function OnboardingPage() {
  const step = useProfileStore((s) => s.onboardingStep);

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-3xl">
        {/* Progress dots */}
        <div className="flex justify-center gap-2 mb-8">
          {[0, 1].map((i) => (
            <div
              key={i}
              className={`w-3 h-3 rounded-full transition-all ${
                i <= step ? 'bg-vibe-accent scale-125' : 'bg-vibe-border'
              }`}
            />
          ))}
        </div>

        {step === 0 && <GenreSelector />}
        {step === 1 && <ProviderSelector />}
      </div>
    </div>
  );
}
