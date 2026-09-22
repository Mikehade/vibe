/* ── Ambient loading animation for the streaming state ── */

import { clsx } from 'clsx';

interface Props {
  phase: string;
  className?: string;
}

const PHASE_TEXT: Record<string, string> = {
  trajectory: 'Reading the mood...',
  picks: 'Finding your picks...',
  summary: 'Wrapping it up...',
  done: 'Your session is ready',
  error: 'Something went wrong',
};

export default function LoadingPulse({ phase, className }: Props) {
  const text = PHASE_TEXT[phase] ?? 'Thinking...';
  const isActive = phase !== 'done' && phase !== 'error' && phase !== 'idle';

  return (
    <div className={clsx('flex items-center gap-4', className)}>
      {isActive && (
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2.5 h-2.5 rounded-full bg-vibe-accent animate-pulse"
              style={{ animationDelay: `${i * 200}ms` }}
            />
          ))}
        </div>
      )}
      <p className="text-tv-base text-vibe-text-muted">{text}</p>
    </div>
  );
}
