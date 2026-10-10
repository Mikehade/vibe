import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { clsx } from 'clsx';
import Backdrop from '@/components/ui/Backdrop';
import Icon from '@/components/ui/Icon';
import Modal from '@/components/ui/Modal';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import { ROLE_COLOR, ROLE_LABEL } from '@/lib/moods';
import { addMinutes, clock, duration } from '@/lib/time';
import { logo } from '@/lib/images';
import * as api from '@/lib/api';
import { usePlan } from '@/stores/plan';
import { launchProvider, inShell } from '@/lib/shell';
import type { Pick, Shift } from '@/lib/types';

function CheckIn({ pick, isLast, onDone }: { pick: Pick; isLast: boolean; onDone: (shift: Shift | 'end' | 'keep') => void }) {
  const [rated, setRated] = useState<string | null>(null);
  const rate = (r: string) => {
    setRated(r);
    if (pick.id) api.pickFeedback(pick.id, r).catch(() => null);
  };
  const options: { id: Shift | 'end' | 'keep'; icon: string; label: string; sub: string }[] = isLast
    ? [{ id: 'end', icon: 'moon', label: 'That’s the night', sub: 'Tell us how it went' }]
    : [
        { id: 'wind_down', icon: 'down', label: 'Wind me down', sub: 'Re-plan the rest to be calmer' },
        { id: 'keep', icon: 'flat', label: 'Keep going', sub: 'Stick with the plan' },
        { id: 'lift', icon: 'up', label: 'Pick it up', sub: 'Re-plan the rest with more energy' },
        { id: 'end', icon: 'moon', label: 'End the night', sub: 'Skip what’s left' },
      ];
  return (
    <Modal onClose={() => onDone('keep')} width="66rem">
      <p className="label">Finished {pick.title}</p>
      <div className="mt-[0.8rem] flex items-center justify-between">
        <h2 className="font-serif text-[3rem] leading-none">{isLast ? 'That was the last one.' : 'How are you feeling now?'}</h2>
        <div className="flex gap-[0.6rem]">
          <button {...focusProps} aria-pressed={rated === 'thumbs_up'} className="chip" onClick={() => rate('thumbs_up')}>
            <Icon name="thumbUp" /> Loved it
          </button>
          <button {...focusProps} aria-pressed={rated === 'thumbs_down'} className="chip" onClick={() => rate('thumbs_down')}>
            <Icon name="thumbDown" /> Not for me
          </button>
        </div>
      </div>
      <div className={clsx('mt-[1.8rem] grid gap-[0.8rem]', isLast ? 'grid-cols-1' : 'grid-cols-2')}>
        {options.map((o, i) => (
          <button
            key={o.id}
            {...focusProps}
            data-autofocus={i === 0 ? true : undefined}
            onClick={() => onDone(o.id)}
            className="focusable focus-ring flex items-center gap-[1.2rem] rounded-[1rem] bg-white/[0.04] p-[1.3rem] text-left focus:bg-paper focus:text-ink-950"
          >
            <span className="flex h-[3.2rem] w-[3.2rem] items-center justify-center rounded-full bg-white/10">
              <Icon name={o.icon} size="1.5rem" />
            </span>
            <span>
              <span className="block text-[1.4rem] font-semibold">{o.label}</span>
              <span className="block text-[1.05rem] opacity-70">{o.sub}</span>
            </span>
          </button>
        ))}
      </div>
    </Modal>
  );
}

export default function WatchScreen() {
  const { planId, pickId } = useParams();
  const nav = useNavigate();
  const { plan, load, setStatus, replan } = usePlan();
  const [checkIn, setCheckIn] = useState(false);
  const [startedAt] = useState(() => Date.now());
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (planId && plan?.id !== planId) load(planId);
  }, [planId, plan?.id, load]);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 15000);
    return () => clearInterval(t);
  }, []);

  useBack(() => {
    nav('/plan');
    return true;
  });

  const pick = plan?.picks.find((p) => p.id === pickId);
  const remaining = useMemo(() => (plan?.picks ?? []).filter((p) => p.position > (pick?.position ?? 0) && p.status === 'pending'), [plan, pick]);
  if (!plan || !pick) return <div className="safe text-[1.4rem] text-paper-muted">Loading…</div>;

  const progress = Math.min(1, (now - startedAt) / (pick.runtime_minutes * 60000));
  const ends = addMinutes(new Date(startedAt), pick.runtime_minutes);

  const finish = async (choice: Shift | 'end' | 'keep') => {
    setCheckIn(false);
    if (pick.id) await setStatus(pick.id, 'completed');
    if (choice === 'end' || !remaining.length) {
      for (const p of remaining) if (p.id) await setStatus(p.id, 'skipped');
      nav(`/feedback/${plan.id}`);
      return;
    }
    if (choice === 'keep') {
      nav('/plan');
      return;
    }
    replan(pick.position, choice);
    nav('/plan');
  };

  return (
    <FocusScope className="relative h-full overflow-hidden">
      <Backdrop path={pick.backdrop_path} />
      <div className="safe relative z-10 flex h-full flex-col justify-end pb-[5rem]">
        <p className="label flex items-center gap-[0.8rem]">
          <span className="h-[0.6rem] w-[0.6rem] rounded-full bg-[#e8574b] animate-pulse-dot" />
          <span>Now watching</span>
          <span style={{ color: ROLE_COLOR[pick.role] }}>{pick.role_label || ROLE_LABEL[pick.role]}</span>
        </p>
        <h1 className="mt-[0.8rem] max-w-[70rem] font-serif text-[6rem] leading-[0.92]">{pick.title}</h1>
        <p className="mt-[1rem] text-[1.4rem] text-paper-muted">
          {pick.media_type === 'tv' && pick.episodes ? `${pick.episodes} episode${pick.episodes > 1 ? 's' : ''} · ` : ''}
          {duration(pick.runtime_minutes)} · ends around {clock(ends)}
          {remaining.length ? ` · then ${remaining[0].title}` : ' · last one tonight'}
        </p>

        <div className="mt-[1.6rem] h-[0.35rem] w-[46rem] overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-amber transition-[width] duration-1000" style={{ width: `${Math.max(2, progress * 100)}%` }} />
        </div>

        {pick.streaming_provider && (
          <div className="mt-[2rem] flex max-w-[60rem] items-center gap-[1.2rem] rounded-[1rem] bg-ink-950/60 p-[1.2rem]">
            {logo(pick.provider_logo_path) ? (
              <img src={logo(pick.provider_logo_path)!} alt="" className="h-[3.2rem] w-[3.2rem] rounded-[0.6rem]" />
            ) : (
              <Icon name="tv" size="2.4rem" className="text-amber" />
            )}
            <p className="text-[1.25rem] leading-snug">
              Ready on <span className="font-semibold">{pick.streaming_provider}</span>.{' '}
              <span className="text-paper-muted">
                {inShell() ? 'Opening it hands you straight over.' : `Open ${pick.streaming_provider} and search for “${pick.title}”.`}
              </span>
            </p>
          </div>
        )}

        <div className="mt-[2rem] flex gap-[1rem]">
          <button {...focusProps} data-autofocus className="btn btn-primary" onClick={() => setCheckIn(true)}>
            <Icon name="check" /> I’ve finished
          </button>
          {pick.streaming_provider && (
            <button {...focusProps} className="btn btn-ghost" onClick={() => launchProvider(pick)}>
              <Icon name="play" /> Open {pick.streaming_provider}
            </button>
          )}
          <button
            {...focusProps}
            className="btn btn-ghost"
            onClick={async () => {
              if (pick.id) await setStatus(pick.id, 'skipped');
              nav('/plan');
            }}
          >
            <Icon name="next" /> Skip this one
          </button>
        </div>
      </div>
      {checkIn && <CheckIn pick={pick} isLast={!remaining.length} onDone={finish} />}
    </FocusScope>
  );
}
