import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import TopBar from '@/components/ui/TopBar';
import Icon from '@/components/ui/Icon';
import Modal from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import { REGIONS } from '@/lib/moods';
import * as api from '@/lib/api';
import { useProfile } from '@/stores/profile';
import Onboarding, { ProviderPicker } from './Onboarding';
import type { Provider } from '@/lib/types';

function Row({ icon, title, sub, action, onClick, autoFocus }: { icon: string; title: string; sub: string; action: string; onClick: () => void; autoFocus?: boolean }) {
  return (
    <button
      {...focusProps}
      data-autofocus={autoFocus ? true : undefined}
      onClick={onClick}
      className="focusable focus-ring group flex w-full items-center gap-[1.3rem] rounded-[1rem] bg-white/[0.035] px-[1.4rem] py-[1.1rem] text-left focus:bg-paper focus:text-ink-950"
    >
      <span className="flex h-[3rem] w-[3rem] items-center justify-center rounded-full bg-white/10">
        <Icon name={icon} size="1.4rem" />
      </span>
      <span className="flex-1">
        <span className="block text-[1.35rem] font-semibold">{title}</span>
        <span className="block text-[1.05rem] opacity-70">{sub}</span>
      </span>
      <span className="text-[1.05rem] font-semibold opacity-80">{action}</span>
    </button>
  );
}

function AlexaLink({ onClose }: { onClose: () => void }) {
  const [code, setCode] = useState<string | null>(null);
  const [linked, setLinked] = useState(false);
  useEffect(() => {
    api.pairCode().then((r) => {
      setCode(r.code);
      setLinked(r.linked);
    });
    const t = setInterval(() => api.pairCode().then((r) => setLinked(r.linked)).catch(() => null), 4000);
    return () => clearInterval(t);
  }, []);
  return (
    <Modal onClose={onClose} width="64rem">
      <p className="label">Voice · Alexa+</p>
      <h2 className="mt-[0.6rem] font-serif text-[3.2rem] leading-none">{linked ? 'Linked to Alexa' : 'Link Alexa to this TV'}</h2>
      <p className="mt-[1rem] text-[1.3rem] text-paper-muted">Say “Alexa, ask Vibe to link my TV” and read out this code. Then just ask: “plan a chill night, about two hours”.</p>
      <div className="mt-[1.6rem] flex gap-[0.8rem]">
        {(code ?? '······').split('').map((d, i) => (
          <span key={i} className="flex h-[6rem] w-[4.6rem] items-center justify-center rounded-[0.8rem] bg-white/[0.06] font-serif text-[4rem]">
            {d}
          </span>
        ))}
      </div>
      <p className="mt-[1rem] text-[1rem] text-paper-faint">Code expires in 15 minutes. MCP endpoint: {location.origin}/mcp</p>
      <div className="mt-[1.8rem]">
        <button {...focusProps} data-autofocus className="btn btn-primary" onClick={onClose}>
          {linked ? 'Done' : 'Close'}
        </button>
      </div>
    </Modal>
  );
}

function ServicesEditor({ onClose }: { onClose: () => void }) {
  const { profile, update } = useProfile();
  const [region, setRegion] = useState(profile?.region || 'US');
  const [services, setServices] = useState<Provider[]>(profile?.preferred_providers ?? []);
  return (
    <Modal onClose={onClose} width="96rem">
      <p className="label">Your services</p>
      <div className="no-scrollbar mt-[1rem] flex gap-[0.6rem] overflow-x-auto py-[0.4rem]" data-focus-group>
        {REGIONS.map((r) => (
          <button key={r.code} {...focusProps} data-scroll-inline="center" aria-pressed={region === r.code} className="chip shrink-0" onClick={() => { setRegion(r.code); setServices([]); }}>
            {r.name}
          </button>
        ))}
      </div>
      <div className="mt-[1.2rem]">
        <ProviderPicker region={region} selected={services} onToggle={(p) => setServices((s) => (s.some((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : [...s, p]))} />
      </div>
      <div className="mt-[1.6rem] flex gap-[1rem]">
        <button {...focusProps} data-autofocus className="btn btn-primary" onClick={async () => { await update({ region, streaming_services: services }); onClose(); }}>
          Save
        </button>
        <button {...focusProps} className="btn btn-ghost" onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

export default function Settings() {
  const nav = useNavigate();
  const toast = useToast((s) => s.show);
  const { profile, profiles, loadAll, switchTo, update } = useProfile();
  const [modal, setModal] = useState<'alexa' | 'services' | 'add' | null>(null);

  useEffect(() => {
    loadAll();
  }, [loadAll]);
  useBack(() => {
    nav('/');
    return true;
  });

  if (modal === 'add') return <Onboarding addingProfile onDone={() => setModal(null)} />;

  return (
    <FocusScope className="safe flex h-full flex-col" autoFocus={!modal}>
      <TopBar />
      <h1 className="mt-[2.6rem] font-serif text-[4.4rem] leading-none">Settings</h1>

      <section className="mt-[2rem]">
        <p className="label">Who’s watching</p>
        <div className="mt-[0.8rem] flex flex-wrap gap-[0.8rem]" data-focus-group>
          {profiles.map((p) => (
            <button
              key={p.id}
              {...focusProps}
              aria-pressed={p.id === profile?.id}
              className="chip !text-[1.2rem]"
              onClick={async () => {
                await switchTo(p.id!);
                toast(`Switched to ${p.name}`);
              }}
            >
              <span className={clsx('flex h-[1.8rem] w-[1.8rem] items-center justify-center rounded-full text-[0.9rem] font-bold', p.is_kids ? 'bg-role-opener/30' : 'bg-amber/25')}>
                {(p.name || 'M').slice(0, 1)}
              </span>
              {p.name}
              {p.is_kids && <span className="text-[0.9rem] opacity-70">Kids</span>}
            </button>
          ))}
          <button {...focusProps} className="chip !text-[1.2rem]" onClick={() => setModal('add')}>
            <Icon name="plus" /> Add profile
          </button>
        </div>
      </section>

      <section className="mt-[2rem] grid grid-cols-2 gap-[1rem]">
        <Row
          autoFocus
          icon="voice"
          title="Link Alexa"
          sub="Plan by voice — the lineup appears here live"
          action="Show code"
          onClick={() => setModal('alexa')}
        />
        <Row
          icon="tv"
          title="Streaming services"
          sub={profile?.preferred_providers?.length ? profile.preferred_providers.map((p) => p.name).join(', ') : 'All services'}
          action={profile?.region ?? 'US'}
          onClick={() => setModal('services')}
        />
        <Row
          icon="child"
          title="Kids-safe picks"
          sub="Family ratings only, no horror or thrillers"
          action={profile?.is_kids ? 'On' : 'Off'}
          onClick={() => update({ is_kids: !profile?.is_kids })}
        />
        <Row
          icon="refresh"
          title="Forget “not this one”"
          sub="Titles you swapped out can come back"
          action="Reset"
          onClick={async () => {
            await update({ reset_exclusions: true });
            toast('Cleared');
          }}
        />
      </section>

      <p className="mt-auto text-[1rem] text-paper-faint">
        Vibe plans with Amazon Bedrock (Claude) and TMDB data. This product uses the TMDB API but is not endorsed or certified by TMDB.
      </p>

      {modal === 'alexa' && <AlexaLink onClose={() => setModal(null)} />}
      {modal === 'services' && <ServicesEditor onClose={() => setModal(null)} />}
    </FocusScope>
  );
}
