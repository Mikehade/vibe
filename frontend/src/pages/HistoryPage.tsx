/* ── Session history — past plans ── */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import { useSessionStore } from '@/stores/sessionStore';
import { useDpad } from '@/hooks/useDpad';

export default function HistoryPage() {
  const { history, historyLoaded, loadHistory, loadPlan } = useSessionStore();
  const navigate = useNavigate();
  const [focusIdx, setFocusIdx] = useState(0);

  useEffect(() => {
    if (!historyLoaded) loadHistory();
  }, [historyLoaded, loadHistory]);

  useDpad({
    onNavigate: (dir) => {
      if (dir === 'up') setFocusIdx((i) => Math.max(0, i - 1));
      if (dir === 'down') setFocusIdx((i) => Math.min(history.length - 1, i + 1));
    },
    onSelect: () => {
      if (history[focusIdx]) {
        loadPlan(history[focusIdx].id);
        navigate('/');
      }
    },
    onBack: () => navigate('/'),
  });

  return (
    <div className="min-h-screen p-8 max-w-3xl mx-auto">
      <h1 className="text-tv-xl font-bold mb-8">Past Sessions</h1>

      {!historyLoaded && (
        <p className="text-vibe-text-muted text-tv-base">Loading...</p>
      )}

      {historyLoaded && history.length === 0 && (
        <p className="text-vibe-text-muted text-tv-base">
          No sessions yet. Go start one!
        </p>
      )}

      <div className="space-y-3">
        {history.map((plan, idx) => (
          <button
            key={plan.id}
            onClick={() => {
              loadPlan(plan.id);
              navigate('/');
            }}
            className={clsx(
              'w-full flex items-center justify-between p-5 rounded-tv transition-all text-left',
              idx === focusIdx ? 'bg-vibe-card ring-2 ring-vibe-accent scale-[1.02]' : 'bg-vibe-surface',
            )}
          >
            <div>
              <span className="text-tv-base font-semibold capitalize">{plan.mood} session</span>
              <p className="text-sm text-vibe-text-muted mt-1">
                {plan.picks.length} picks · {plan.total_runtime_minutes ?? '?'} min
              </p>
            </div>
            <div className="text-right">
              <span className="text-sm text-vibe-text-muted">
                {plan.created_at ? new Date(plan.created_at).toLocaleDateString() : ''}
              </span>
              <p className="text-xs text-vibe-accent capitalize mt-1">{plan.status}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
