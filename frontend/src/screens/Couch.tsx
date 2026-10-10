import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import QRCode from 'qrcode';
import TopBar from '@/components/ui/TopBar';
import Icon from '@/components/ui/Icon';
import { FocusScope, focusProps, useBack } from '@/lib/focus/FocusProvider';
import { moodById } from '@/lib/moods';
import { addMinutes, clock, minutesUntilBed } from '@/lib/time';
import * as api from '@/lib/api';
import { usePlan } from '@/stores/plan';
import type { Room } from '@/lib/types';

export default function Couch() {
  const nav = useNavigate();
  const start = usePlan((s) => s.start);
  const [room, setRoom] = useState<Room | null>(null);
  const [qr, setQr] = useState<string>('');
  const [minutes, setMinutes] = useState(120);
  const [err, setErr] = useState<string | null>(null);

  useBack(() => {
    nav('/');
    return true;
  });

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setInterval>;
    api
      .createRoom()
      .then((r) => {
        if (!alive) return;
        setRoom(r);
        timer = setInterval(() => api.getRoom(r.code).then((x) => alive && setRoom(x)).catch(() => null), 1500);
      })
      .catch((e) => setErr(e.message));
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  const joinUrl = useMemo(() => (room ? `${location.origin}${location.pathname}#/join/${room.code}` : ''), [room?.code]);
  useEffect(() => {
    if (!joinUrl) return;
    QRCode.toString(joinUrl, { type: 'svg', margin: 0, color: { dark: '#0a0a0c', light: '#f4f1ea' }, errorCorrectionLevel: 'M' }).then(setQr);
  }, [joinUrl]);

  const ready = room?.members.filter((m) => m.mood) ?? [];
  const now = new Date();
  const bed = minutesUntilBed(now);
  const build = () => {
    if (!room) return;
    const counts: Record<string, number> = {};
    ready.forEach((m) => (counts[m.mood!] = (counts[m.mood!] || 0) + 1));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'social';
    start({ mood: top, time_budget_minutes: minutes, room_code: room.code });
    nav('/plan');
  };

  return (
    <FocusScope className="safe relative flex h-full flex-col overflow-hidden" focusKey={ready.length ? 'ready' : 'wait'}>
      <TopBar />
      <div className="mt-[2.6rem] grid flex-1 grid-cols-[38rem_1fr] gap-[4rem]">
        <section className="animate-fade-up">
          <p className="label">Couch Mode</p>
          <h1 className="mt-[0.6rem] font-serif text-[4.4rem] leading-[0.95]">Everyone gets a say.</h1>
          <p className="mt-[1rem] text-[1.35rem] text-paper-muted">Scan with your phone camera, add how you feel and any hard no’s. Vibe blends the room into one night.</p>
          <div className="mt-[2rem] flex items-center gap-[1.6rem]">
            <div className="h-[15rem] w-[15rem] rounded-[1rem] bg-paper p-[1rem]" dangerouslySetInnerHTML={{ __html: qr }} />
            <div>
              <p className="label">Or enter code</p>
              <p className="mt-[0.3rem] font-serif text-[5.4rem] leading-none tracking-[0.12em]">{room?.code ?? '····'}</p>
              <p className="mt-[0.6rem] max-w-[16rem] break-all text-[0.95rem] text-paper-faint">{joinUrl.replace(/^https?:\/\//, '')}</p>
            </div>
          </div>
          {err && <p className="mt-[1rem] text-[1.1rem] text-[#e89a8f]">{err}</p>}
        </section>

        <section className="flex flex-col">
          <p className="label">On the couch · {room?.members.length ?? 0}</p>
          <div className="mt-[1rem] grid grid-cols-2 gap-[1rem]">
            {room?.members.map((m) => {
              const md = m.mood ? moodById(m.mood) : null;
              return (
                <div key={m.id} className="card flex items-center gap-[1.1rem] p-[1.1rem] animate-fade-up" style={md ? { background: `linear-gradient(135deg, ${md.from}, ${md.to})` } : undefined}>
                  <span className="flex h-[3.4rem] w-[3.4rem] shrink-0 items-center justify-center rounded-full bg-ink-950/40 text-[1.4rem] font-bold">{m.name.slice(0, 1)}</span>
                  <div className="min-w-0">
                    <p className="text-[1.35rem] font-semibold">{m.name}</p>
                    <p className="truncate text-[1.05rem] text-paper/75">
                      {md ? md.label : 'Choosing…'}
                      {m.notes ? ` — “${m.notes}”` : ''}
                      {m.vetoes.length ? ` · no ${m.vetoes.join(', ')}` : ''}
                    </p>
                  </div>
                </div>
              );
            })}
            {!room?.members.length && (
              <div className="col-span-2 flex h-[9rem] items-center gap-[1rem] rounded-[1rem] border border-dashed border-white/15 px-[1.6rem] text-[1.3rem] text-paper-muted">
                <span className="h-[0.7rem] w-[0.7rem] rounded-full bg-amber animate-pulse-dot" /> Waiting for phones to join…
              </div>
            )}
          </div>

          <div className="mt-auto">
            <p className="label">Time tonight</p>
            <div className="mt-[0.8rem] flex gap-[0.7rem]" data-focus-group>
              {[60, 120, 180, bed].map((m, i) => (
                <button key={i} {...focusProps} aria-pressed={minutes === m} className="chip" onClick={() => setMinutes(m)}>
                  {i === 3 ? 'Until bedtime' : `${m / 60}h`} · done {clock(addMinutes(now, m))}
                </button>
              ))}
            </div>
            <div className="mt-[1.4rem] flex gap-[1rem]">
              <button {...focusProps} data-autofocus={ready.length ? true : undefined} className="btn btn-primary" disabled={!ready.length} onClick={build}>
                <Icon name="sparkle" /> Build our night{ready.length ? ` for ${ready.length + 1}` : ''}
              </button>
              <button
                {...focusProps}
                data-autofocus={!ready.length ? true : undefined}
                className="btn btn-ghost"
                onClick={async () => {
                  if (room) await api.closeRoom(room.code).catch(() => null);
                  nav('/');
                }}
              >
                Close room
              </button>
            </div>
          </div>
        </section>
      </div>
    </FocusScope>
  );
}
