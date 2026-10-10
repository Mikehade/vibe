import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import Wordmark from '@/components/ui/Wordmark';
import Icon from '@/components/ui/Icon';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import { GENRES, guessRegion, REGIONS } from '@/lib/moods';
import { logo } from '@/lib/images';
import * as api from '@/lib/api';
import { useProfile } from '@/stores/profile';
import type { Provider } from '@/lib/types';

type Taste = 'love' | 'avoid' | undefined;

export function ProviderPicker({ region, selected, onToggle }: { region: string; selected: Provider[]; onToggle: (p: Provider) => void }) {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  useEffect(() => {
    setProviders(null);
    api.providersFor(region).then((r) => setProviders(r.providers.slice(0, 18))).catch(() => setProviders([]));
  }, [region]);
  if (!providers) return <div className="grid grid-cols-6 gap-[0.9rem]">{Array.from({ length: 12 }).map((_, i) => <div key={i} className="skeleton h-[5.4rem] rounded-[0.9rem]" />)}</div>;
  if (!providers.length) return <p className="text-[1.2rem] text-paper-muted">Couldn’t load services for this region — you can add them later in Settings.</p>;
  return (
    <div className="grid grid-cols-6 gap-[0.9rem]" data-focus-group>
      {providers.map((p) => {
        const on = selected.some((s) => s.id === p.id);
        const src = logo(p.logo_path);
        return (
          <button
            key={p.id}
            {...focusProps}
            aria-pressed={on}
            onClick={() => onToggle(p)}
            className={clsx(
              'focusable focus-ring focus-lift-sm relative flex h-[5.4rem] items-center gap-[0.8rem] rounded-[0.9rem] border px-[0.9rem] text-left',
              on ? 'border-amber/80 bg-amber/10' : 'border-white/10 bg-white/[0.03]',
            )}
          >
            {src ? <img src={src} alt="" className="h-[3rem] w-[3rem] rounded-[0.5rem]" /> : <span className="flex h-[3rem] w-[3rem] items-center justify-center rounded-[0.5rem] bg-white/10 text-[1rem] font-bold">{p.name.slice(0, 2)}</span>}
            <span className="line-clamp-2 text-[1.02rem] font-medium leading-tight">{p.name}</span>
            {on && <Icon name="check" className="absolute right-[0.5rem] top-[0.5rem] text-amber" size="1rem" />}
          </button>
        );
      })}
    </div>
  );
}

export default function Onboarding({ addingProfile = false, onDone }: { addingProfile?: boolean; onDone?: () => void }) {
  const save = useProfile((s) => s.save);
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [kids, setKids] = useState(false);
  const [region, setRegion] = useState(guessRegion());
  const [services, setServices] = useState<Provider[]>([]);
  const [tastes, setTastes] = useState<Record<string, Taste>>({});
  const [busy, setBusy] = useState(false);

  useBack(() => {
    if (step > 0) {
      setStep(step - 1);
      return true;
    }
    if (onDone) {
      onDone();
      return true;
    }
    return false;
  });

  const cycle = (g: string) => setTastes((t) => ({ ...t, [g]: t[g] === undefined ? 'love' : t[g] === 'love' ? 'avoid' : undefined }));

  const finish = async () => {
    setBusy(true);
    try {
      await save({
        name: name.trim() || (kids ? 'Kids' : 'Me'),
        is_kids: kids,
        region,
        streaming_services: services,
        genre_preferences: Object.entries(tastes)
          .filter(([, v]) => v)
          .map(([genre, v]) => ({ genre, action: v === 'love' ? 'like' : 'dislike' })),
        new_profile: addingProfile,
      });
      onDone?.();
    } finally {
      setBusy(false);
    }
  };

  const steps = ['Who’s watching', 'Your services', 'Your taste'];

  return (
    <FocusScope className="safe relative flex h-full flex-col" focusKey={step}>
      <div className="pointer-events-none absolute -left-[16rem] bottom-[-24rem] h-[56rem] w-[56rem] rounded-full opacity-[0.08]" style={{ background: 'radial-gradient(circle, #e8b04b 0%, transparent 60%)' }} />
      <header className="flex items-center justify-between">
        <Wordmark className="text-[2.6rem]" />
        <ol className="flex gap-[1.6rem] text-[1.05rem]">
          {steps.map((s, i) => (
            <li key={s} className={clsx('flex items-center gap-[0.6rem]', i === step ? 'text-paper' : 'text-paper-faint')}>
              <span className={clsx('flex h-[1.8rem] w-[1.8rem] items-center justify-center rounded-full text-[0.9rem] font-bold', i < step ? 'bg-role-opener text-ink-950' : i === step ? 'bg-paper text-ink-950' : 'bg-white/10')}>
                {i < step ? <Icon name="check" size="1rem" /> : i + 1}
              </span>
              {s}
            </li>
          ))}
        </ol>
      </header>

      {step === 0 && (
        <section className="mt-[5rem] max-w-[70rem] animate-fade-up">
          <p className="label">{addingProfile ? 'New profile' : 'Welcome'}</p>
          <h1 className="mt-[0.8rem] font-serif text-[5.4rem] leading-[0.95]">
            {addingProfile ? 'Who else watches here?' : 'Your evenings, programmed.'}
          </h1>
          <p className="mt-[1.2rem] max-w-[54rem] text-[1.6rem] text-paper-muted">
            Tell Vibe how you feel and how much time you have. It plans a whole night — an easy opener, a main event, a soft landing — from what you can actually watch.
          </p>
          <label className="mt-[2.6rem] block">
            <span className="label">Name for this profile</span>
            <input
              {...focusProps}
              data-autofocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && setStep(1)}
              placeholder="e.g. Seun"
              maxLength={40}
              className="focusable focus-ring mt-[0.7rem] block w-[34rem] rounded-[0.9rem] border border-white/10 bg-white/[0.05] px-[1.3rem] py-[1rem] text-[1.6rem] text-paper placeholder:text-paper-faint"
            />
          </label>
          <div className="mt-[1.6rem] flex gap-[0.8rem]">
            <button {...focusProps} aria-pressed={kids} className="chip" onClick={() => setKids((k) => !k)}>
              <Icon name={kids ? 'check' : 'child'} /> This is a kids profile
            </button>
          </div>
          <div className="mt-[2.4rem]">
            <button {...focusProps} className="btn btn-primary" onClick={() => setStep(1)}>
              Continue <Icon name="next" />
            </button>
          </div>
        </section>
      )}

      {step === 1 && (
        <section className="mt-[3rem] animate-fade-up">
          <p className="label">Where you watch</p>
          <h1 className="mt-[0.6rem] font-serif text-[4.2rem] leading-none">What are you subscribed to?</h1>
          <p className="mt-[0.8rem] text-[1.4rem] text-paper-muted">Vibe only plans with titles you can actually play. Pick as many as you like.</p>
          <div className="no-scrollbar mt-[1.6rem] flex gap-[0.6rem] overflow-x-auto py-[0.5rem]" data-focus-group>
            {REGIONS.map((r) => (
              <button key={r.code} {...focusProps} data-scroll-inline="center" aria-pressed={region === r.code} className="chip shrink-0" onClick={() => { setRegion(r.code); setServices([]); }}>
                {r.name}
              </button>
            ))}
          </div>
          <div className="mt-[1.4rem]">
            <ProviderPicker region={region} selected={services} onToggle={(p) => setServices((s) => (s.some((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : [...s, p]))} />
          </div>
          <div className="mt-[2rem] flex items-center gap-[1rem]">
            <button {...focusProps} data-autofocus className="btn btn-primary" onClick={() => setStep(2)}>
              {services.length ? `Continue with ${services.length}` : 'Skip — show me everything'} <Icon name="next" />
            </button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="mt-[3rem] animate-fade-up">
          <p className="label">Taste</p>
          <h1 className="mt-[0.6rem] font-serif text-[4.2rem] leading-none">What do you love — and avoid?</h1>
          <p className="mt-[0.8rem] text-[1.4rem] text-paper-muted">Select once to love, twice to avoid. Vibe keeps learning from every night.</p>
          <div className="mt-[2rem] grid grid-cols-7 gap-[0.9rem]">
            {GENRES.map((g, i) => {
              const t = tastes[g];
              return (
                <button
                  key={g}
                  {...focusProps}
                  data-autofocus={i === 0 ? true : undefined}
                  onClick={() => cycle(g)}
                  className={clsx(
                    'focusable focus-ring focus-lift-sm flex h-[6.2rem] flex-col justify-between rounded-[0.9rem] border p-[0.9rem] text-left',
                    t === 'love' ? 'border-amber/80 bg-amber/15' : t === 'avoid' ? 'border-[#e89a8f]/50 bg-[#e89a8f]/10' : 'border-white/10 bg-white/[0.03]',
                  )}
                >
                  <span className="text-[1.2rem] font-semibold capitalize">{g === 'science fiction' ? 'Sci-fi' : g}</span>
                  <span className={clsx('text-[0.95rem]', t === 'love' ? 'text-amber-soft' : t === 'avoid' ? 'text-[#f0b3aa]' : 'text-paper-faint')}>
                    {t === 'love' ? 'Love' : t === 'avoid' ? 'Avoid' : 'Neutral'}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="mt-[2.4rem]">
            <button {...focusProps} className="btn btn-primary" disabled={busy} onClick={finish}>
              {busy ? 'Saving…' : 'Start planning'} <Icon name="next" />
            </button>
          </div>
        </section>
      )}
    </FocusScope>
  );
}
