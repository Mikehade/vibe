import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Poster from '@/components/ui/Poster';
import TopBar from '@/components/ui/TopBar';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import { moodById } from '@/lib/moods';
import { duration, relativeDay } from '@/lib/time';
import * as api from '@/lib/api';
import { usePlan } from '@/stores/plan';
import type { Plan } from '@/lib/types';

export default function History() {
  const nav = useNavigate();
  const load = usePlan((s) => s.load);
  const [plans, setPlans] = useState<Plan[] | null>(null);
  useEffect(() => {
    api.listPlans(20).then((r) => setPlans(r.plans)).catch(() => setPlans([]));
  }, []);
  useBack(() => {
    nav('/');
    return true;
  });

  return (
    <FocusScope className="safe flex h-full flex-col" focusKey={plans?.length ?? -1}>
      <TopBar />
      <h1 className="mt-[2.6rem] font-serif text-[4.4rem] leading-none">Past nights</h1>
      <div className="no-scrollbar mt-[2rem] grid flex-1 grid-cols-2 content-start gap-[1.2rem] overflow-y-auto pb-[2rem]">
        {plans === null && Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-[11rem] rounded-[1rem]" />)}
        {plans?.length === 0 && <p className="text-[1.4rem] text-paper-muted">No nights yet. Your plans will show up here.</p>}
        {plans?.map((p, i) => {
          const m = moodById(p.mood);
          return (
            <button
              key={p.id}
              {...focusProps}
              data-autofocus={i === 0 ? true : undefined}
              onClick={async () => {
                await load(p.id);
                nav('/plan');
              }}
              className="focusable focus-ring focus-lift-sm card flex items-center gap-[1.4rem] p-[1.1rem] text-left"
            >
              <div className="flex -space-x-[2rem]">
                {p.picks.slice(0, 4).map((pk) => (
                  <Poster key={pk.id} path={pk.poster_path} title={pk.title} size="w185" className="h-[8.4rem] w-[5.6rem] ring-2 ring-ink-850" rounded="rounded-[0.5rem]" />
                ))}
              </div>
              <div className="min-w-0">
                <p className="label" style={{ color: m.glow }}>{relativeDay(p.created_at)} · {m.label}</p>
                <p className="mt-[0.3rem] line-clamp-2 text-[1.3rem] font-semibold leading-tight">{p.picks.map((x) => x.title).join(' · ')}</p>
                <p className="mt-[0.3rem] text-[1rem] text-paper-muted">{duration(p.total_runtime_minutes)}{p.plan_summary ? ` — ${p.plan_summary}` : ''}</p>
              </div>
            </button>
          );
        })}
      </div>
    </FocusScope>
  );
}
