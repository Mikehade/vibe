import { clsx } from 'clsx';
import Poster from '@/components/ui/Poster';
import Icon from '@/components/ui/Icon';
import { focusProps } from '@/lib/focus/FocusProvider';
import { ROLE_COLOR, ROLE_LABEL } from '@/lib/moods';
import { duration } from '@/lib/time';
import type { ArcSlot, Pick } from '@/lib/types';

export const SLOT_W = 25; // rem
export const SLOT_GAP = 1.4; // rem

export default function SlotCard({
  slot,
  pick,
  timeRange,
  swapping,
  votes,
  onFocus,
  onSelect,
  autoFocus,
}: {
  slot: ArcSlot;
  pick?: Pick;
  timeRange?: string;
  swapping?: boolean;
  votes?: { votes: number; needed: number };
  onFocus: () => void;
  onSelect: () => void;
  autoFocus?: boolean;
}) {
  const color = ROLE_COLOR[slot.role];
  if (!pick) {
    return (
      <div className="flex shrink-0 gap-[1rem] rounded-[1rem] border border-dashed border-white/10 p-[0.8rem]" style={{ width: `${SLOT_W}rem` }}>
        <div className="skeleton h-[12.6rem] w-[8.4rem] shrink-0 rounded-[0.7rem]" />
        <div className="flex flex-col justify-center gap-[0.6rem]">
          <span className="label" style={{ color }}>{slot.label}</span>
          <span className="text-[1.15rem] text-paper-muted">Choosing…</span>
          <span className="text-[1rem] text-paper-faint">~{slot.target_minutes} min</span>
        </div>
      </div>
    );
  }
  const done = pick.status === 'completed';
  return (
    <button
      {...focusProps}
      data-autofocus={autoFocus ? true : undefined}
      data-scroll-inline="center"
      onFocus={onFocus}
      onClick={onSelect}
      className={clsx(
        'focusable focus-ring group relative flex shrink-0 gap-[1rem] rounded-[1rem] bg-ink-850/80 p-[0.8rem] text-left animate-fade-up focus:bg-ink-800',
        done && 'opacity-55',
      )}
      style={{ width: `${SLOT_W}rem` }}
    >
      <div className="relative">
        <Poster path={pick.poster_path} title={pick.title} size="w185" className={clsx('h-[12.6rem] w-[8.4rem] shrink-0', swapping && 'opacity-30')} rounded="rounded-[0.7rem]" />
        {swapping && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="h-[2rem] w-[2rem] rounded-full border-2 border-paper/30 border-t-paper" style={{ animation: 'slowspin 0.9s linear infinite' }} />
          </div>
        )}
      </div>
      <div className="flex min-w-0 flex-1 flex-col py-[0.2rem]">
        <span className="label" style={{ color }}>{pick.role_label || ROLE_LABEL[pick.role]}</span>
        <span className="mt-[0.4rem] line-clamp-2 text-[1.35rem] font-semibold leading-tight">{pick.title}</span>
        <span className="mt-auto text-[1rem] text-paper-muted">{done ? 'Watched' : timeRange}</span>
        <span className="mt-[0.2rem] flex items-center gap-[0.4rem] text-[1rem] text-paper-faint">
          {pick.media_type === 'tv' && pick.episodes ? `${pick.episodes} ep · ` : ''}
          {duration(pick.runtime_minutes)}
          {pick.streaming_provider ? ` · ${pick.streaming_provider}` : ''}
        </span>
      </div>
      {done && (
        <span className="absolute right-[0.8rem] top-[0.8rem] flex h-[1.8rem] w-[1.8rem] items-center justify-center rounded-full bg-role-opener text-ink-950">
          <Icon name="check" size="1.1rem" />
        </span>
      )}
      {votes && votes.votes > 0 && !done && (
        <span className="absolute right-[0.8rem] top-[0.8rem] rounded-full bg-[#e89a8f] px-[0.7rem] py-[0.15rem] text-[0.85rem] font-semibold text-ink-950">
          {votes.votes}/{votes.needed} skip
        </span>
      )}
    </button>
  );
}
