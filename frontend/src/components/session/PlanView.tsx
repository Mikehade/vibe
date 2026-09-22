/* ── Rendered session plan — the pick lineup ── */

import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { useSessionStore } from '@/stores/sessionStore';
import { useDpad } from '@/hooks/useDpad';
import PosterCard from '@/components/common/PosterCard';
import LoadingPulse from '@/components/common/LoadingPulse';
import FocusableButton from '@/components/common/FocusableButton';
import type { Pick } from '@/types';

interface Props {
  onFeedback: () => void;
  onReset: () => void;
}

export default function PlanView({ onFeedback, onReset }: Props) {
  const plan = useSessionStore((s) => s.plan);
  const isStreaming = useSessionStore((s) => s.isStreaming);
  const streamPhase = useSessionStore((s) => s.streamPhase);
  const updatePickStatus = useSessionStore((s) => s.updatePickStatus);
  const [focusIdx, setFocusIdx] = useState(0);
  const [showDetail, setShowDetail] = useState(false);

  const picks = plan?.picks ?? [];

  useDpad({
    onNavigate: (dir) => {
      if (dir === 'left') setFocusIdx((i) => Math.max(0, i - 1));
      if (dir === 'right') setFocusIdx((i) => Math.min(picks.length - 1, i + 1));
    },
    onSelect: () => {
      if (picks[focusIdx]) setShowDetail(true);
    },
    onBack: () => setShowDetail(false),
  });

  if (!plan) return null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-tv-xl font-bold capitalize">
            {plan.mood} session
          </h2>
          {plan.energy_trajectory && (
            <p className="text-tv-sm text-vibe-text-muted mt-1">
              Energy: {plan.energy_trajectory}
            </p>
          )}
        </div>
        {plan.total_runtime_minutes && (
          <span className="text-tv-base text-vibe-accent-light font-semibold">
            {Math.floor(plan.total_runtime_minutes / 60)}h {plan.total_runtime_minutes % 60}m total
          </span>
        )}
      </div>

      {/* Streaming indicator */}
      {isStreaming && <LoadingPulse phase={streamPhase} />}

      {/* Pick rail — horizontal scroll */}
      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
        {picks.map((pick, idx) => (
          <PosterCard
            key={pick.id || idx}
            title={pick.title}
            posterPath={pick.poster_path}
            role={pick.role}
            runtime={pick.runtime_minutes}
            reason={pick.reason}
            confidence={pick.confidence}
            streamingProvider={pick.streaming_provider}
            focused={idx === focusIdx}
            status={pick.status}
            onClick={() => {
              setFocusIdx(idx);
              setShowDetail(true);
            }}
          />
        ))}
      </div>

      {/* Plan summary */}
      {plan.plan_summary && (
        <div className="bg-vibe-card rounded-tv p-6">
          <p className="text-tv-base text-vibe-text leading-relaxed">{plan.plan_summary}</p>
        </div>
      )}

      {/* Actions */}
      {!isStreaming && (
        <div className="flex gap-4 justify-center">
          <FocusableButton onClick={onFeedback}>Rate this session</FocusableButton>
          <FocusableButton variant="secondary" onClick={onReset}>
            New session
          </FocusableButton>
        </div>
      )}

      {/* Detail overlay */}
      {showDetail && picks[focusIdx] && (
        <PickDetail
          pick={picks[focusIdx]}
          onClose={() => setShowDetail(false)}
          onStatusChange={(status) => updatePickStatus(picks[focusIdx].id, status)}
        />
      )}
    </div>
  );
}

/* ── Focused pick detail card ── */

function PickDetail({
  pick,
  onClose,
  onStatusChange,
}: {
  pick: Pick;
  onClose: () => void;
  onStatusChange: (status: string) => void;
}) {
  const imgSrc = pick.poster_path
    ? `https://image.tmdb.org/t/p/w500${pick.poster_path}`
    : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <div
        className="bg-vibe-surface rounded-tv max-w-2xl w-full mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex">
          {imgSrc && (
            <img src={imgSrc} alt={pick.title} className="w-48 object-cover" />
          )}
          <div className="p-6 flex-1 space-y-4">
            <div>
              <span
                className={clsx(
                  'px-2 py-0.5 rounded-full text-xs font-bold uppercase mr-2',
                  pick.role === 'opener' && 'bg-green-600 text-white',
                  pick.role === 'main_event' && 'bg-vibe-accent text-white',
                  pick.role === 'bridge' && 'bg-yellow-600 text-white',
                  pick.role === 'nightcap' && 'bg-red-500 text-white',
                )}
              >
                {pick.role}
              </span>
              <h3 className="text-tv-lg font-bold mt-2">{pick.title}</h3>
              <p className="text-sm text-vibe-text-muted">{pick.runtime_minutes} min</p>
            </div>

            <p className="text-tv-sm leading-relaxed">{pick.reason}</p>

            {pick.streaming_provider && (
              <p className="text-sm text-vibe-accent-light">
                Available on {pick.streaming_provider}
              </p>
            )}

            <div className="flex gap-3 pt-2">
              <FocusableButton
                size="sm"
                onClick={() => onStatusChange('watching')}
                variant={pick.status === 'watching' ? 'primary' : 'secondary'}
              >
                ▶ Watch
              </FocusableButton>
              <FocusableButton
                size="sm"
                onClick={() => onStatusChange('completed')}
                variant={pick.status === 'completed' ? 'primary' : 'secondary'}
              >
                ✓ Done
              </FocusableButton>
              <FocusableButton
                size="sm"
                onClick={() => onStatusChange('skipped')}
                variant="ghost"
              >
                Skip
              </FocusableButton>
            </div>

            {pick.deep_link_url && (
              <a
                href={pick.deep_link_url}
                className="inline-block mt-2 text-sm text-vibe-accent underline"
              >
                Open in app →
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
