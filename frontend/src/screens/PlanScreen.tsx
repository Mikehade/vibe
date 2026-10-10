import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import Backdrop from '@/components/ui/Backdrop';
import Icon from '@/components/ui/Icon';
import Wordmark from '@/components/ui/Wordmark';
import { useToast } from '@/components/ui/Toast';
import ArcChart from '@/components/plan/ArcChart';
import SlotCard, { SLOT_GAP, SLOT_W } from '@/components/plan/SlotCard';
import LiveLog from '@/components/plan/LiveLog';
import CandidateWall from '@/components/plan/CandidateWall';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import { focusEl } from '@/lib/focus/spatial';
import { moodById, ROLE_COLOR, ROLE_LABEL } from '@/lib/moods';
import { addMinutes, clock, duration } from '@/lib/time';
import { logo } from '@/lib/images';
import * as api from '@/lib/api';
import { usePlan } from '@/stores/plan';
import type { ArcSlot, Pick, Room } from '@/lib/types';

function useSchedule(picks: Pick[]) {
  return useMemo(() => {
    const out: Record<number, { start: Date; end: Date }> = {};
    let t = new Date();
    for (const p of [...picks].sort((a, b) => a.position - b.position)) {
      if (p.status === 'completed' || p.status === 'skipped') continue;
      const end = addMinutes(t, p.runtime_minutes);
      out[p.position] = { start: t, end };
      t = end;
    }
    return { slots: out, end: t };
  }, [picks]);
}

function useRoomVotes(code: string | null) {
  const [room, setRoom] = useState<Room | null>(null);
  useEffect(() => {
    if (!code) return;
    let alive = true;
    const tick = () => api.getRoom(code).then((r) => alive && setRoom(r)).catch(() => null);
    tick();
    const t = setInterval(tick, 2500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [code]);
  return room;
}

export default function PlanScreen() {
  const nav = useNavigate();
  const toast = useToast((s) => s.show);
  const { plan, arc, log, sample, phase, error, swapping, swap, setStatus, roomCode, candidateCount, outsideServices, start } = usePlan();
  const [focusedPos, setFocusedPos] = useState<number | null>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const room = useRoomVotes(roomCode);
  const autoSwapped = useRef<Set<string>>(new Set());

  useBack(() => {
    nav('/');
    return true;
  });

  const picks = plan?.picks ?? [];
  const slots: ArcSlot[] = useMemo(() => {
    if (arc?.slots?.length) {
      const bySlot = new Map(arc.slots.map((s) => [s.position, s]));
      for (const p of picks) if (!bySlot.has(p.position)) bySlot.set(p.position, { position: p.position, role: p.role, label: ROLE_LABEL[p.role], energy: p.energy ?? 0.5, target_minutes: p.runtime_minutes });
      return [...bySlot.values()].sort((a, b) => a.position - b.position);
    }
    return picks.map((p) => ({ position: p.position, role: p.role, label: p.role_label || ROLE_LABEL[p.role], energy: p.energy ?? 0.5, target_minutes: p.runtime_minutes }));
  }, [arc, picks]);

  const byPos = useMemo(() => new Map(picks.map((p) => [p.position, p])), [picks]);
  const schedule = useSchedule(picks);
  const firstPending = picks.find((p) => p.status === 'pending' || p.status === 'watching');
  const current = (focusedPos != null && byPos.get(focusedPos)) || firstPending || picks[0];
  const streaming = phase === 'streaming';
  const mood = plan ? moodById(plan.mood) : null;
  const total = picks.filter((p) => p.status !== 'skipped').reduce((a, p) => a + p.runtime_minutes, 0);
  const lastLine = log[log.length - 1];

  // First pick arrives → move focus onto it
  const hadPick = useRef(false);
  useEffect(() => {
    if (!hadPick.current && picks.length && railRef.current) {
      hadPick.current = true;
      const el = railRef.current.querySelector<HTMLElement>('[data-focusable]');
      if (el && (document.activeElement === document.body || !document.activeElement?.closest('[data-rail-actions]'))) focusEl(el);
    }
  }, [picks.length]);

  // After a re-plan or when a pick is finished, bring focus to what's next
  useEffect(() => {
    if (!firstPending?.id || !railRef.current) return;
    const active = document.activeElement as HTMLElement | null;
    const onRail = active && railRef.current.contains(active);
    const onDone = focusedPos != null && byPos.get(focusedPos)?.status === 'completed';
    if (!active || active === document.body || (onRail && onDone)) {
      const idx = slots.findIndex((s) => s.position === firstPending.position);
      const el = railRef.current.querySelectorAll<HTMLElement>(':scope > *')[idx];
      if (el?.matches('[data-focusable]')) {
        focusEl(el);
        setFocusedPos(firstPending.position);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firstPending?.id, phase]);

  const doSwap = useCallback(
    async (p: Pick, reason?: string) => {
      if (!p.id) return;
      try {
        const n = await swap(p.id);
        if (n) toast(reason ? `${reason} — swapped for ${n.title}` : `Swapped for ${n.title}`);
      } catch (e: any) {
        toast(e.message || 'No alternatives left');
      }
    },
    [swap, toast],
  );

  // Couch Mode: a majority skip vote swaps the pick automatically
  useEffect(() => {
    if (!room) return;
    for (const p of picks) {
      const v = p.id ? room.skip_votes[p.id] : undefined;
      if (v && v.votes >= v.needed && p.id && !autoSwapped.current.has(p.id) && p.status === 'pending') {
        autoSwapped.current.add(p.id);
        doSwap(p, 'The room voted');
      }
    }
  }, [room, picks, doSwap]);

  const watch = useCallback(
    (p: Pick | undefined) => {
      if (!p?.id || !plan?.id) return;
      setStatus(p.id, 'watching');
      nav(`/watch/${plan.id}/${p.id}`);
    },
    [plan?.id, setStatus, nav],
  );

  useEffect(() => {
    const onPlay = () => watch(current);
    window.addEventListener('vibe:play', onPlay);
    return () => window.removeEventListener('vibe:play', onPlay);
  }, [watch, current]);

  if (!plan) {
    return (
      <FocusScope className="safe flex h-full flex-col items-center justify-center gap-[1.6rem]">
        <p className="text-[1.6rem] text-paper-muted">No plan yet.</p>
        <button {...focusProps} className="btn btn-primary" onClick={() => nav('/')}>Pick a mood</button>
      </FocusScope>
    );
  }

  const endBy = schedule.end;
  const building = !picks.length;

  return (
    <FocusScope className="relative h-full overflow-hidden">
      <Backdrop path={current?.backdrop_path} fallbackColor={mood ? mood.from : undefined} />
      {building && <CandidateWall sample={sample} />}

      <div className="safe relative z-10 flex h-full flex-col">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-[1.6rem]">
            <Wordmark className="text-[2.2rem]" />
            <span className="h-[1.6rem] w-px bg-white/15" />
            <span className="text-[1.15rem] text-paper-muted">
              <span className="font-semibold text-paper">{mood?.label}</span>
              {plan.audience && plan.audience.startsWith('a group') ? ' · Couch Mode' : ''}
              {total ? ` · ${duration(total)} · done by ${clock(endBy)}` : plan.time_budget_minutes ? ` · ${duration(plan.time_budget_minutes)}` : ''}
            </span>
          </div>
          <div className="flex items-center gap-[0.8rem]">
            {streaming && picks.length > 0 && lastLine && (
              <span className="flex max-w-[34rem] items-center gap-[0.7rem] rounded-full bg-ink-950/70 px-[1.2rem] py-[0.6rem] text-[1rem] text-paper-muted">
                <span className="h-[0.55rem] w-[0.55rem] shrink-0 rounded-full bg-amber animate-pulse-dot" />
                <span className="truncate">{lastLine.message}</span>
              </span>
            )}
            {room && room.members.length > 0 && (
              <span className="rounded-full bg-ink-950/70 px-[1.2rem] py-[0.6rem] text-[1rem] text-paper-muted">
                {room.members.map((m) => m.name).join(', ')} on phones
              </span>
            )}
            <button {...focusProps} className="btn btn-ghost !py-[0.7rem] text-[1rem]" onClick={() => nav('/')}>
              <Icon name="back" /> New plan
            </button>
          </div>
        </header>

        {/* Hero */}
        <section className="mt-[2.4rem] min-h-0 flex-1">
          {building ? (
            <div className="max-w-[56rem] animate-fade-up">
              <p className="label">{phase === 'error' ? 'Something went wrong' : 'Building your night'}</p>
              <h1 className="mt-[0.8rem] font-serif text-[4.6rem] leading-[0.95]">
                {phase === 'error' ? 'Let’s try that again.' : arc?.energy_trajectory || 'Reading the room…'}
              </h1>
              <div className="mt-[2rem]">
                <LiveLog lines={log} active={streaming} />
              </div>
              {phase === 'error' && (
                <div className="mt-[2rem] flex gap-[1rem]">
                  <button {...focusProps} data-autofocus className="btn btn-primary" onClick={() => start({ mood: plan.mood, time_budget_minutes: plan.time_budget_minutes, room_code: roomCode })}>
                    <Icon name="refresh" /> Try again
                  </button>
                  <button {...focusProps} className="btn btn-ghost" onClick={() => nav('/')}>Change mood</button>
                </div>
              )}
              {error && phase === 'error' && <p className="mt-[1rem] text-[1.1rem] text-paper-faint">{error}</p>}
            </div>
          ) : current ? (
            <div key={current.id || current.position} className="max-w-[64rem] animate-fade-up">
              <p className="label flex items-center gap-[0.8rem]">
                <span style={{ color: ROLE_COLOR[current.role] }}>{current.role_label || ROLE_LABEL[current.role]}</span>
                {schedule.slots[current.position] && (
                  <span>
                    {clock(schedule.slots[current.position].start)} – {clock(schedule.slots[current.position].end)}
                  </span>
                )}
              </p>
              <h1 className="mt-[0.6rem] line-clamp-2 font-serif text-[4.8rem] leading-[0.95]">{current.title}</h1>
              <div className="mt-[1rem] flex flex-wrap items-center gap-x-[1.2rem] gap-y-[0.4rem] text-[1.2rem] text-paper-muted">
                {current.year && <span>{current.year}</span>}
                <span>{current.media_type === 'tv' && current.episodes ? `${current.episodes} episode${current.episodes > 1 ? 's' : ''} · ${duration(current.runtime_minutes)}` : duration(current.runtime_minutes)}</span>
                {current.rating ? (
                  <span className="flex items-center gap-[0.3rem]">
                    <Icon name="star" filled className="text-amber" size="1em" /> {current.rating.toFixed(1)}
                  </span>
                ) : null}
                {current.certification && <span className="rounded border border-white/25 px-[0.5rem] text-[1rem]">{current.certification}</span>}
                {current.streaming_provider && (
                  <span className="flex items-center gap-[0.5rem] text-paper">
                    {logo(current.provider_logo_path) && <img src={logo(current.provider_logo_path)!} alt="" className="h-[1.6rem] w-[1.6rem] rounded-[0.35rem]" />}
                    {current.streaming_provider}
                  </span>
                )}
                {current.genres?.length ? <span>{current.genres.slice(0, 2).join(' · ')}</span> : null}
              </div>
              <p className="mt-[1.4rem] max-w-[56rem] text-[1.6rem] leading-snug text-paper/90">{current.reason}</p>
              <div className="mt-[1.8rem] flex gap-[1rem]" data-rail-actions>
                <button {...focusProps} className="btn btn-primary" disabled={current.status === 'completed'} onClick={() => watch(current)}>
                  <Icon name="play" /> {current.status === 'completed' ? 'Watched' : 'Start watching'}
                </button>
                <button {...focusProps} className="btn btn-ghost" disabled={!current.id || !!swapping || current.status === 'completed'} onClick={() => doSwap(current)}>
                  <Icon name="swap" /> {swapping === current.id ? 'Finding another…' : 'Not this one'}
                </button>
                {phase !== 'streaming' && picks.every((p) => p.status === 'completed' || p.status === 'skipped') && (
                  <button {...focusProps} className="btn btn-ghost" onClick={() => nav(`/feedback/${plan.id}`)}>
                    <Icon name="star" /> Rate tonight
                  </button>
                )}
              </div>
            </div>
          ) : null}
        </section>

        {/* Arc + lineup */}
        <section className="relative">
          {slots.length > 0 && (
            <div className="mb-[0.6rem] flex items-end justify-between">
              <ArcChart slots={slots} focused={current?.position ?? null} slotWidth={SLOT_W} gap={SLOT_GAP} provisional={arc?.provisional} />
            </div>
          )}
          <div ref={railRef} className="no-scrollbar flex gap-[1.4rem] overflow-x-auto pb-[0.6rem] pt-[0.4rem]" data-focus-group>
            {slots.map((s) => {
              const p = byPos.get(s.position);
              const sch = schedule.slots[s.position];
              return (
                <SlotCard
                  key={`${s.position}-${p?.id ?? 'empty'}`}
                  slot={s}
                  pick={p}
                  autoFocus={!!p && p === firstPending}
                  timeRange={sch ? `${clock(sch.start)} – ${clock(sch.end)}` : undefined}
                  swapping={!!p?.id && swapping === p.id}
                  votes={p?.id ? room?.skip_votes[p.id] : undefined}
                  onFocus={() => setFocusedPos(s.position)}
                  onSelect={() => {
                    setFocusedPos(s.position);
                    const btn = document.querySelector<HTMLElement>('[data-rail-actions] [data-focusable]');
                    if (btn) focusEl(btn);
                  }}
                />
              );
            })}
          </div>
          <p className={clsx('mt-[0.6rem] text-[1rem] text-paper-faint', !candidateCount && !plan.plan_summary && 'invisible')}>
            {plan.plan_summary && !streaming && <span className="italic text-paper-muted">{plan.plan_summary} </span>}
            {candidateCount ? `Chosen from ${candidateCount} titles` : ''}{candidateCount ? (outsideServices ? ' (some outside your services)' : ' on your services') : ''}
            {phase === 'done' && usePlan.getState().elapsedMs ? ` · planned in ${(usePlan.getState().elapsedMs! / 1000).toFixed(1)}s` : ''}
          </p>
        </section>
      </div>
    </FocusScope>
  );
}
