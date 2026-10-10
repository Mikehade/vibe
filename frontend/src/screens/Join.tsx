/* Phone companion — joined by scanning the TV's QR code. Touch-first, normal phone sizing. */

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { clsx } from 'clsx';
import Wordmark from '@/components/ui/Wordmark';
import Icon from '@/components/ui/Icon';
import Poster from '@/components/ui/Poster';
import { MOODS, VETO_OPTIONS } from '@/lib/moods';
import { duration } from '@/lib/time';
import * as api from '@/lib/api';
import type { Mood, Plan, Room } from '@/lib/types';

function session(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function useSpeech(onText: (t: string) => void) {
  const recRef = useRef<any>(null);
  const [listening, setListening] = useState(false);
  const Rec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  const toggle = () => {
    if (!Rec) return;
    if (listening) {
      recRef.current?.stop();
      return;
    }
    const rec = new Rec();
    rec.lang = navigator.language || 'en-US';
    rec.interimResults = false;
    rec.onresult = (e: any) => onText(Array.from(e.results).map((r: any) => r[0].transcript).join(' '));
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    rec.start();
  };
  return { supported: !!Rec, listening, toggle };
}

export default function Join() {
  const params = useParams();
  const [code, setCode] = useState((params.code || '').toUpperCase());
  const [name, setName] = useState('');
  const [memberId, setMemberId] = useState<string | null>(() => (params.code ? session()?.getItem(`vibe_member_${params.code.toUpperCase()}`) ?? null : null));
  const [room, setRoom] = useState<Room | null>(null);
  const [mood, setMood] = useState<Mood | null>(null);
  const [notes, setNotes] = useState('');
  const [vetoes, setVetoes] = useState<string[]>([]);
  const [sent, setSent] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [myVotes, setMyVotes] = useState<string[]>([]);
  const speech = useSpeech((t) => setNotes((n) => (n ? `${n} ${t}` : t)));

  useEffect(() => {
    if (!memberId || !code) return;
    let alive = true;
    const tick = async () => {
      try {
        const r = await api.getRoom(code);
        if (!alive) return;
        setRoom(r);
        if (r.plan_id) setPlan(await api.getPlan(r.plan_id));
      } catch (e: any) {
        setErr(e.message);
      }
    };
    tick();
    const t = setInterval(tick, 2500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [memberId, code]);

  const join = async () => {
    setErr(null);
    try {
      const r = await api.joinRoom(code.trim().toUpperCase(), name.trim() || 'Guest');
      session()?.setItem(`vibe_member_${code.toUpperCase()}`, r.member_id);
      setMemberId(r.member_id);
      setRoom(r.room);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const send = async () => {
    if (!memberId || !mood) return;
    try {
      setRoom(await api.updateMember(code, memberId, { mood, notes, vetoes }));
      setSent(true);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const vote = async (pickId: string) => {
    if (!memberId) return;
    await api.voteSkip(code, memberId, pickId).catch(() => null);
    setMyVotes((v) => (v.includes(pickId) ? v.filter((x) => x !== pickId) : [...v, pickId]));
  };

  return (
    <div className="mx-auto min-h-full max-w-[30rem] px-5 pb-16 pt-6 text-[16px]">
      <header className="flex items-center justify-between">
        <Wordmark className="text-3xl" />
        {room && <span className="rounded-full bg-white/10 px-3 py-1 text-sm tracking-widest">{room.code}</span>}
      </header>

      {!memberId && (
        <section className="mt-10 animate-fade-up">
          <h1 className="font-serif text-5xl leading-none">Join the couch</h1>
          <p className="mt-3 text-paper-muted">Tell the TV how you feel. It’ll plan the night for everyone.</p>
          <label className="mt-8 block text-sm text-paper-muted">Room code</label>
          <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} maxLength={4} placeholder="ABCD" className="mt-2 w-full rounded-xl bg-white/[0.06] px-4 py-3 text-2xl tracking-[0.3em] outline-none ring-amber focus:ring-2" />
          <label className="mt-5 block text-sm text-paper-muted">Your name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={30} placeholder="e.g. Ada" className="mt-2 w-full rounded-xl bg-white/[0.06] px-4 py-3 text-xl outline-none ring-amber focus:ring-2" />
          <button onClick={join} disabled={code.length < 4} className="mt-6 w-full rounded-full bg-paper py-4 text-lg font-semibold text-ink-950 disabled:opacity-40">
            Join
          </button>
        </section>
      )}

      {memberId && !sent && !plan && (
        <section className="mt-8 animate-fade-up">
          <h1 className="font-serif text-4xl leading-none">How are you feeling?</h1>
          <div className="mt-5 grid grid-cols-2 gap-3">
            {MOODS.map((m) => (
              <button
                key={m.id}
                onClick={() => setMood(m.id)}
                className={clsx('rounded-2xl p-4 text-left transition', mood === m.id ? 'ring-2 ring-paper' : 'opacity-80')}
                style={{ background: `linear-gradient(135deg, ${m.from}, ${m.to})` }}
              >
                <span className="block font-serif text-2xl leading-none">{m.label}</span>
                <span className="mt-1 block text-xs text-paper/70">{m.line}</span>
              </button>
            ))}
          </div>
          <label className="mt-6 block text-sm text-paper-muted">Anything specific? (optional)</label>
          <div className="mt-2 flex gap-2">
            <input value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={200} placeholder="something like Paddington, nothing too long" className="flex-1 rounded-xl bg-white/[0.06] px-4 py-3 outline-none ring-amber focus:ring-2" />
            {speech.supported && (
              <button onClick={speech.toggle} aria-label="Speak" className={clsx('flex w-12 items-center justify-center rounded-xl', speech.listening ? 'bg-amber text-ink-950' : 'bg-white/10')}>
                <Icon name="mic" />
              </button>
            )}
          </div>
          <p className="mt-6 text-sm text-paper-muted">Hard no’s</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {VETO_OPTIONS.map((v) => (
              <button
                key={v}
                onClick={() => setVetoes((x) => (x.includes(v) ? x.filter((y) => y !== v) : [...x, v]))}
                className={clsx('rounded-full border px-3 py-1.5 text-sm capitalize', vetoes.includes(v) ? 'border-[#e89a8f] bg-[#e89a8f]/15 text-[#f0b3aa]' : 'border-white/15 text-paper-muted')}
              >
                {v}
              </button>
            ))}
          </div>
          <button onClick={send} disabled={!mood} className="mt-8 w-full rounded-full bg-paper py-4 text-lg font-semibold text-ink-950 disabled:opacity-40">
            I’m ready
          </button>
        </section>
      )}

      {memberId && sent && !plan && (
        <section className="mt-16 text-center animate-fade-up">
          <span className="mx-auto block h-3 w-3 rounded-full bg-amber animate-pulse-dot" />
          <h1 className="mt-6 font-serif text-4xl">You’re in.</h1>
          <p className="mt-3 text-paper-muted">Watch the TV — the plan appears once everyone’s ready.</p>
          <ul className="mt-8 space-y-2 text-left">
            {room?.members.map((m) => (
              <li key={m.id} className="flex items-center justify-between rounded-xl bg-white/[0.05] px-4 py-3">
                <span>{m.name}</span>
                <span className="text-sm text-paper-muted">{m.mood ? MOODS.find((x) => x.id === m.mood)?.label : 'choosing…'}</span>
              </li>
            ))}
          </ul>
          <button onClick={() => setSent(false)} className="mt-6 text-sm text-paper-muted underline">Change my answer</button>
        </section>
      )}

      {plan && (
        <section className="mt-8 animate-fade-up">
          <p className="text-xs uppercase tracking-[0.16em] text-paper-muted">Tonight · {duration(plan.total_runtime_minutes)}</p>
          <h1 className="mt-2 font-serif text-4xl leading-none">The lineup</h1>
          <p className="mt-2 text-sm text-paper-muted">Not feeling one? Vote to skip — a majority swaps it on the TV.</p>
          <ul className="mt-5 space-y-3">
            {plan.picks.map((p) => {
              const v = p.id ? room?.skip_votes[p.id] : undefined;
              const mine = p.id ? myVotes.includes(p.id) : false;
              return (
                <li key={p.id} className="flex gap-3 rounded-2xl bg-white/[0.05] p-3">
                  <Poster path={p.poster_path} title={p.title} size="w185" className="h-24 w-16 shrink-0" rounded="rounded-lg" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] uppercase tracking-[0.16em] text-paper-muted">{p.role_label}</p>
                    <p className="truncate font-semibold">{p.title}</p>
                    <p className="line-clamp-2 text-xs text-paper-muted">{p.reason}</p>
                  </div>
                  {p.id && p.status === 'pending' && (
                    <button onClick={() => vote(p.id!)} className={clsx('self-center rounded-full px-3 py-1.5 text-xs font-semibold', mine ? 'bg-[#e89a8f] text-ink-950' : 'bg-white/10')}>
                      {mine ? 'Voted' : 'Skip'}
                      {v ? ` ${v.votes}/${v.needed}` : ''}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {err && <p className="mt-6 text-center text-sm text-[#f0b3aa]">{err}</p>}
    </div>
  );
}
