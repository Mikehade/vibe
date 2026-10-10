import { useEffect } from 'react';
import { HashRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { FocusProvider, FocusScope, focusProps } from '@/lib/focus/FocusProvider';
import { Toaster, useToast } from '@/components/ui/Toast';
import Wordmark from '@/components/ui/Wordmark';
import { exitApp } from '@/lib/shell';
import * as api from '@/lib/api';
import { useProfile } from '@/stores/profile';
import { usePlan } from '@/stores/plan';
import Home from '@/screens/Home';
import PlanScreen from '@/screens/PlanScreen';
import WatchScreen from '@/screens/WatchScreen';
import Feedback from '@/screens/Feedback';
import Onboarding from '@/screens/Onboarding';
import History from '@/screens/History';
import Settings from '@/screens/Settings';
import Couch from '@/screens/Couch';
import Join from '@/screens/Join';

/** Voice-started plans (Alexa+ via MCP) and remote updates arrive through the TV inbox. */
function useInbox(enabled: boolean) {
  const nav = useNavigate();
  const toast = useToast((s) => s.show);
  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const tick = async () => {
      try {
        const { events } = await api.inbox();
        for (const ev of events) {
          if (!alive) return;
          if (ev.type === 'linked') toast('Alexa is linked to this TV');
          if (ev.type === 'watch_plan') {
            toast('Planning from Alexa…');
            nav('/plan');
            usePlan.getState().follow(ev.data.plan_id);
          }
          if (ev.type === 'plan_updated' && usePlan.getState().plan?.id === ev.data.plan_id) {
            usePlan.getState().load(ev.data.plan_id);
          }
        }
      } catch {
        /* offline — try again next tick */
      }
    };
    const t = setInterval(tick, 3000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [enabled, nav, toast]);
}

function Boot({ error, retry }: { error: string | null; retry: () => void }) {
  return (
    <FocusScope className="flex h-full flex-col items-center justify-center gap-[1.4rem]">
      <Wordmark className="text-[6rem]" />
      {error ? (
        <>
          <p className="text-[1.4rem] text-paper-muted">Can’t reach Vibe right now. {error}</p>
          <button {...focusProps} data-autofocus className="btn btn-primary" onClick={retry}>
            Try again
          </button>
        </>
      ) : (
        <span className="h-[0.7rem] w-[0.7rem] rounded-full bg-amber animate-pulse-dot" />
      )}
    </FocusScope>
  );
}

function TvShell() {
  const { profile, ready, error, load } = useProfile();
  useEffect(() => {
    load();
  }, [load]);
  useInbox(!!profile?.onboarding_completed);

  if (!ready || (error && !profile)) return <Boot error={error} retry={load} />;
  if (!profile?.onboarding_completed) return <Onboarding />;

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/plan" element={<PlanScreen />} />
      <Route path="/watch/:planId/:pickId" element={<WatchScreen />} />
      <Route path="/feedback/:planId" element={<Feedback />} />
      <Route path="/history" element={<History />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/couch" element={<Couch />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function Root() {
  const loc = useLocation();
  const nav = useNavigate();
  const phone = loc.pathname.startsWith('/join');

  useEffect(() => {
    document.documentElement.classList.toggle('tv', !phone);
    document.documentElement.classList.toggle('phone', phone);
  }, [phone]);

  useEffect(() => {
    const onMenu = () => nav('/settings');
    window.addEventListener('vibe:menu', onMenu);
    return () => window.removeEventListener('vibe:menu', onMenu);
  }, [nav]);

  if (phone) {
    return (
      <Routes>
        <Route path="/join" element={<Join />} />
        <Route path="/join/:code" element={<Join />} />
      </Routes>
    );
  }

  return (
    <FocusProvider onRootBack={() => (loc.pathname === '/' ? exitApp() : nav('/'))}>
      <div className="h-full w-full">
        <TvShell />
      </div>
      <Toaster />
    </FocusProvider>
  );
}

export default function App() {
  return (
    <HashRouter>
      <Root />
    </HashRouter>
  );
}
