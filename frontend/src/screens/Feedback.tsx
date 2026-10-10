import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Poster from '@/components/ui/Poster';
import Icon from '@/components/ui/Icon';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import * as api from '@/lib/api';
import { usePlan } from '@/stores/plan';
import { useToast } from '@/components/ui/Toast';

export default function Feedback() {
  const { planId } = useParams();
  const nav = useNavigate();
  const { plan, load, reset } = usePlan();
  const toast = useToast((s) => s.show);
  const [overall, setOverall] = useState<string | null>(null);
  const [pacing, setPacing] = useState<string | null>(null);

  useEffect(() => {
    if (planId && plan?.id !== planId) load(planId);
  }, [planId, plan?.id, load]);
  useBack(() => {
    nav('/');
    return true;
  });

  const submit = async () => {
    if (!planId || !overall) return;
    await api.sessionFeedback(planId, overall, pacing).catch(() => null);
    toast('Thanks — your next night will be better for it');
    reset();
    nav('/');
  };

  const watched = (plan?.picks ?? []).filter((p) => p.status === 'completed');
  return (
    <FocusScope className="safe flex h-full items-center">
      <div className="grid w-full grid-cols-[1fr_auto] items-center gap-[4rem]">
        <div className="animate-fade-up">
          <p className="label">End of the night</p>
          <h1 className="mt-[0.8rem] font-serif text-[5rem] leading-none">How was tonight?</h1>
          <div className="mt-[2.2rem] flex gap-[0.8rem]">
            {[
              ['thumbs_up', 'thumbUp', 'Loved it'],
              ['thumbs_down', 'thumbDown', 'Not quite'],
            ].map(([id, icon, label], i) => (
              <button key={id} {...focusProps} data-autofocus={i === 0 ? true : undefined} aria-pressed={overall === id} className="chip !text-[1.3rem]" onClick={() => setOverall(id)}>
                <Icon name={icon} /> {label}
              </button>
            ))}
          </div>
          <p className="label mt-[2.2rem]">The pacing felt</p>
          <div className="mt-[0.8rem] flex gap-[0.8rem]">
            {[
              ['too_slow', 'Too slow'],
              ['just_right', 'Just right'],
              ['too_fast', 'Too much'],
            ].map(([id, label]) => (
              <button key={id} {...focusProps} aria-pressed={pacing === id} className="chip !text-[1.3rem]" onClick={() => setPacing(id)}>
                {label}
              </button>
            ))}
          </div>
          <div className="mt-[2.6rem] flex gap-[1rem]">
            <button {...focusProps} className="btn btn-primary" disabled={!overall} onClick={submit}>
              Save and finish
            </button>
            <button {...focusProps} className="btn btn-ghost" onClick={() => nav('/')}>
              Skip
            </button>
          </div>
        </div>
        <div className="flex -space-x-[3rem]">
          {watched.slice(0, 4).map((p, i) => (
            <Poster key={p.id} path={p.poster_path} title={p.title} className="h-[24rem] w-[16rem] shadow-2xl ring-4 ring-ink-950" size="w342" rounded="rounded-[1rem]" />
          ))}
        </div>
      </div>
    </FocusScope>
  );
}
