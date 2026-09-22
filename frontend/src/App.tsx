/* ── Root app with routing ── */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useProfileStore } from '@/stores/profileStore';
import OnboardingPage from '@/pages/OnboardingPage';
import SessionPage from '@/pages/SessionPage';
import HistoryPage from '@/pages/HistoryPage';

function AppShell() {
  const { profile, loading, loadProfile } = useProfileStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    loadProfile().finally(() => setReady(true));
  }, [loadProfile]);

  if (!ready || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-tv-2xl font-bold bg-gradient-to-r from-vibe-accent to-vibe-accent-light bg-clip-text text-transparent">
            Vibe
          </h1>
          <p className="text-vibe-text-muted text-tv-base">Loading...</p>
        </div>
      </div>
    );
  }

  // If onboarding not completed, show onboarding
  if (!profile?.onboarding_completed) {
    return <OnboardingPage />;
  }

  return (
    <div>
      {/* Simple nav bar */}
      <nav className="fixed top-0 inset-x-0 z-40 bg-vibe-bg/80 backdrop-blur-lg border-b border-vibe-border/30">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-8 py-4">
          <h1 className="text-tv-lg font-bold bg-gradient-to-r from-vibe-accent to-vibe-accent-light bg-clip-text text-transparent">
            Vibe
          </h1>
          <div className="flex gap-6">
            <a href="/" className="text-tv-sm text-vibe-text hover:text-vibe-accent transition-colors">
              New Session
            </a>
            <a href="/history" className="text-tv-sm text-vibe-text-muted hover:text-vibe-accent transition-colors">
              History
            </a>
          </div>
        </div>
      </nav>

      <main className="pt-20">
        <Routes>
          <Route path="/" element={<SessionPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
