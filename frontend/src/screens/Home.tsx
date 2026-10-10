import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import TopBar from '@/components/ui/TopBar';
import Modal from '@/components/ui/Modal';
import Poster from '@/components/ui/Poster';
import Icon from '@/components/ui/Icon';
import { FocusScope, focusProps } from '@/lib/focus/FocusProvider';
import { MOODS } from '@/lib/moods';
import { addMinutes, clock, dayLabel, greeting, minutesUntilBed, relativeDay } from '@/lib/time';
import * as api from '@/lib/api';
import { useProfile } from '@/stores/profile';
import { usePlan } from '@/stores/plan';
import type { Mood, Plan } from '@/lib/types';

const ARC_GLYPH: Record<Mood, string> = {
  tired: 'M0 22 C 20 8, 40 6, 60 14 S 90 30, 120 28',
  stressed: 'M0 18 C 25 12, 45 12, 60 16 S 95 26, 120 26',
  social: 'M0 22 C 20 10, 40 4, 60 10 S 95 20, 120 16',
  bored: 'M0 26 C 30 22, 50 12, 70 8 S 105 4, 120 2',
  energised: 'M0 10 C 25 4, 45 4, 60 6 S 100 2, 120 4',
  adventurous: 'M0 24 C 20 18, 35 6, 55 10 S 90 2, 120 6',
};

export function TimeSheet({ mood, onClose }: { mood: Mood; onClose: () => void }) {
  const nav = useNavigate();
  const profile = useProfile((s) => s.profile);
  const start = usePlan((s) => s.start);
  const [kids, setKids] = useState<boolean>(!!profile?.is_kids);
  const now = new Date();
  const bed = minutesUntilBed(now);
  const options = [
    { minutes: 60, label: 'About an hour' },
    { minutes: 120, label: 'Two hours' },
    { minutes: 180, label: 'A proper evening' },
    { minutes: bed, label: 'Until bedtime' },
  ];

  const go = (minutes: number) => {
    start({ mood, time_budget_minutes: minutes, kids_mode: kids || null });
    onClose();
    nav('/plan');
  };

  return (
    <Modal onClose={onClose} width="58rem">
      <p className="label">{MOODS.find((m) => m.id === mood)?.label} · the shortlist is already being prepared</p>
      <h2 className="mt-[0.6rem] font-serif text-[3.2rem] leading-none">How much time do you have?</h2>
      <div className="mt-[2rem] grid gap-[0.8rem]">
        {options.map((o, i) => (
          <button
            key={o.label}
            {...focusProps}
            data-autofocus={i === 1 ? true : undefined}
            onClick={() => go(o.minutes)}
            className="focusable focus-ring group flex items-center justify-between rounded-[1rem] bg-white/[0.04] px-[1.6rem] py-[1.2rem] text-left focus:bg-paper focus:text-ink-950"
          >
            <span className="text-[1.6rem] font-semibold">{o.label}</span>
            <span className="text-[1.15rem] text-paper-muted group-focus:text-ink-800">
              {Math.floor(o.minutes / 60)}h{o.minutes % 60 ? ` ${o.minutes % 60}m` : ''} · done by {clock(addMinutes(now, o.minutes))}
            </span>
          </button>
        ))}
      </div>
      <div className="mt-[1.6rem] flex items-center justify-between">
        <button {...focusProps} aria-pressed={kids} onClick={() => setKids((k) => !k)} className="chip">
          <Icon name={kids ? 'check' : 'child'} />
          Kids-safe picks
        </button>
        <span className="text-[1rem] text-paper-faint">Back to change mood</span>
      </div>
    </Modal>
  );
}

function ResumeCard({ plan }: { plan: Plan }) {
  const nav = useNavigate();
  const load = usePlan((s) => s.load);
  const next = plan.picks.find((p) => p.status === 'pending' || p.status === 'watching');
  return (
    <button
      {...focusProps}
      onClick={async () => {
        await load(plan.id);
        nav('/plan');
      }}
      className="focusable focus-ring focus-lift-sm card flex flex-1 items-center gap-[1.4rem] p-[1.2rem] text-left"
    >
      <div className="flex -space-x-[1.6rem]">
        {plan.picks.slice(0, 3).map((p) => (
          <Poster key={p.position} path={p.poster_path} title={p.title} size="w185" className="h-[7rem] w-[4.7rem] shadow-xl ring-2 ring-ink-850" rounded="rounded-[0.6rem]" />
        ))}
      </div>
      <div className="min-w-0">
        <p className="label">{relativeDay(plan.created_at)} · {plan.mood}</p>
        <p className="mt-[0.3rem] truncate text-[1.5rem] font-semibold">{next ? `Up next: ${next.title}` : 'Tonight’s plan'}</p>
        <p className="text-[1.05rem] text-paper-muted">Continue where you left off</p>
      </div>
    </button>
  );
}

export default function Home() {
  const nav = useNavigate();
  const profile = useProfile((s) => s.profile);
  const [mood, setMood] = useState<Mood | null>(null);
  const [latest, setLatest] = useState<Plan | null>(null);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30000);
    api.latestPlan().then((r) => {
      const p = r.plan;
      if (p && p.picks.length && Date.now() - new Date(p.created_at || 0).getTime() < 14 * 3600 * 1000) setLatest(p);
    }).catch(() => null);
    return () => clearInterval(t);
  }, []);

  const name = useMemo(() => (profile?.name && profile.name !== 'Me' ? `, ${profile.name}` : ''), [profile]);

  const pickMood = (m: Mood) => {
    api.prefetch(m, profile?.is_kids ?? null);
    setMood(m);
  };

  return (
    <FocusScope className="safe relative flex h-full flex-col overflow-hidden" autoFocus={!mood}>
      <div className="pointer-events-none absolute -right-[20rem] -top-[20rem] h-[60rem] w-[60rem] rounded-full opacity-[0.10]" style={{ background: 'radial-gradient(circle, #e8b04b 0%, transparent 60%)' }} />
      <TopBar />

      <section className="mt-[3.2rem] animate-fade-up">
        <p className="label">{dayLabel(now)}</p>
        <h1 className="mt-[0.6rem] font-serif text-[5.2rem] leading-[0.95] tracking-[-0.01em]">
          {greeting(now)}
          {name}.
        </h1>
        <p className="mt-[0.8rem] text-[1.7rem] text-paper-muted">How are you feeling {now.getHours() >= 17 || now.getHours() < 4 ? 'tonight' : 'right now'}?</p>
      </section>

      <section className="mt-[2.4rem] grid grid-cols-3 gap-[1.4rem]">
        {MOODS.map((m, i) => (
          <button
            key={m.id}
            {...focusProps}
            data-autofocus={i === 0 ? true : undefined}
            onClick={() => pickMood(m.id)}
            className="focusable focus-ring focus-lift group relative h-[12.5rem] overflow-hidden rounded-[1.2rem] p-[1.6rem] text-left animate-fade-up"
            style={{ background: `linear-gradient(135deg, ${m.from} 0%, ${m.to} 100%)`, animationDelay: `${i * 50}ms` }}
          >
            <div className="absolute -right-[4rem] -top-[4rem] h-[14rem] w-[14rem] rounded-full opacity-30 transition-opacity duration-300 group-focus:opacity-60" style={{ background: `radial-gradient(circle, ${m.glow} 0%, transparent 65%)` }} />
            <span className="relative block font-serif text-[3.1rem] leading-none">{m.label}</span>
            <span className="relative mt-[0.5rem] block text-[1.2rem] text-paper/75">{m.line}</span>
            <svg viewBox="0 0 120 32" className="absolute bottom-[1.3rem] right-[1.5rem] h-[2.4rem] w-[9rem] opacity-70" fill="none">
              <path d={ARC_GLYPH[m.id]} stroke={m.glow} strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </button>
        ))}
      </section>

      <section className="mt-[1.6rem] flex gap-[1.4rem]">
        {latest && <ResumeCard plan={latest} />}
        <button
          {...focusProps}
          onClick={() => nav('/couch')}
          className={clsx('focusable focus-ring focus-lift-sm card flex items-center gap-[1.4rem] p-[1.2rem] pr-[2rem] text-left', latest ? 'flex-1' : 'w-full')}
        >
          <span className="flex h-[4.6rem] w-[4.6rem] shrink-0 items-center justify-center rounded-full bg-amber/15 text-amber">
            <Icon name="users" size="2rem" />
          </span>
          <span>
            <span className="block text-[1.5rem] font-semibold">Watching together?</span>
            <span className="block text-[1.05rem] text-paper-muted">Couch Mode — everyone adds their mood from their phone</span>
          </span>
        </button>
      </section>

      {mood && <TimeSheet mood={mood} onClose={() => setMood(null)} />}
    </FocusScope>
  );
}
