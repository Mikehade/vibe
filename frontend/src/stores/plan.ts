/* Live plan state — applies NDJSON events as they stream in. */

import { create } from 'zustand';
import * as api from '@/lib/api';
import type { Arc, CandidateSample, LogLine, Mood, Pick, Plan, Shift, StreamEvent } from '@/lib/types';

type Phase = 'idle' | 'streaming' | 'done' | 'error';

interface PlanState {
  plan: Plan | null;
  arc: Arc | null;
  log: LogLine[];
  sample: CandidateSample[];
  candidateCount: number;
  outsideServices: boolean;
  phase: Phase;
  error: string | null;
  elapsedMs: number | null;
  swapping: string | null;
  roomCode: string | null;

  start: (params: api.PlanParams) => Promise<string | null>;
  follow: (planId: string) => Promise<void>;
  replan: (afterPosition: number, shift: Shift) => Promise<void>;
  load: (planId: string) => Promise<void>;
  swap: (pickId: string) => Promise<Pick | null>;
  setStatus: (pickId: string, status: Pick['status']) => Promise<void>;
  reset: () => void;
}

let controller: AbortController | null = null;
let lineId = 0;
const HEARTBEAT = /· \d+s$/;

function emptyPlan(mood: Mood, budget: number | null): Plan {
  return {
    id: '',
    mood,
    energy_trajectory: null,
    time_budget_minutes: budget,
    total_runtime_minutes: null,
    plan_summary: null,
    status: 'generating',
    created_at: new Date().toISOString(),
    picks: [],
  };
}

export const usePlan = create<PlanState>((set, get) => {
  const log = (message: string, kind: LogLine['kind'] = 'status', stage = '') => {
    const lines = get().log;
    const last = lines[lines.length - 1];
    if (last && HEARTBEAT.test(message) && HEARTBEAT.test(last.message)) {
      set({ log: [...lines.slice(0, -1), { ...last, message, at: Date.now() }] });
      return;
    }
    if (last && last.message === message) return;
    set({ log: [...lines, { id: ++lineId, stage, message, kind, at: Date.now() }].slice(-12) });
  };

  const apply = (ev: StreamEvent) => {
    const plan = get().plan;
    switch (ev.type) {
      case 'plan':
        if (plan) set({ plan: { ...plan, id: ev.data.plan_id } });
        break;
      case 'replan':
        if (plan) {
          set({
            plan: {
              ...plan,
              status: 'generating',
              picks: plan.picks
                .filter((p) => p.position <= ev.data.after_position)
                .map((p) => (p.status === 'pending' ? { ...p, status: 'completed' as const } : p)),
            },
          });
        }
        log(
          ev.data.shift === 'wind_down' ? 'Re-planning the rest to wind you down' : ev.data.shift === 'lift' ? 'Re-planning the rest to lift the energy' : 'Re-planning the rest at the same pace',
        );
        break;
      case 'status':
        log(ev.data.message, 'status', ev.data.stage);
        break;
      case 'trajectory': {
        const prevArc = get().arc;
        // During a re-plan the new arc only covers the remaining slots — merge with earlier ones
        const merged =
          prevArc && ev.data.slots[0]?.position > 1
            ? { ...ev.data, slots: [...prevArc.slots.filter((s) => s.position < ev.data.slots[0].position), ...ev.data.slots] }
            : ev.data;
        set({ arc: merged, plan: plan ? { ...plan, energy_trajectory: ev.data.energy_trajectory } : plan });
        break;
      }
      case 'candidates':
        set({ sample: ev.data.sample, candidateCount: ev.data.count, outsideServices: ev.data.outside_services });
        break;
      case 'tool':
        log(ev.data.message, 'tool', 'tool');
        break;
      case 'pick':
        if (plan) {
          const picks = [...plan.picks.filter((p) => p.position !== ev.data.position), { ...ev.data, status: ev.data.status ?? ('pending' as const) }].sort(
            (a, b) => a.position - b.position,
          );
          set({ plan: { ...plan, id: ev.data.plan_id || plan.id, picks } });
          log(`${ev.data.role_label || 'Pick'}: ${ev.data.title}`, 'pick', 'pick');
        }
        break;
      case 'summary':
        if (plan) set({ plan: { ...plan, plan_summary: ev.data.plan_summary, total_runtime_minutes: ev.data.total_runtime_minutes } });
        break;
      case 'done':
        set({ phase: 'done', elapsedMs: ev.data.elapsed_ms, plan: get().plan ? { ...get().plan!, status: 'generated' } : null });
        break;
      case 'error':
        set({ phase: 'error', error: ev.data.message });
        log(ev.data.message, 'error');
        break;
    }
  };

  const consume = async (stream: Promise<AsyncGenerator<StreamEvent>>) => {
    try {
      for await (const ev of await stream) apply(ev);
      if (get().phase === 'streaming') set({ phase: 'done' });
    } catch (e: any) {
      if (e?.name === 'AbortError') return;
      set({ phase: 'error', error: e?.message ?? 'Connection lost' });
    }
  };

  return {
    plan: null,
    arc: null,
    log: [],
    sample: [],
    candidateCount: 0,
    outsideServices: false,
    phase: 'idle',
    error: null,
    elapsedMs: null,
    swapping: null,
    roomCode: null,

    start: async (params) => {
      controller?.abort();
      controller = new AbortController();
      set({
        plan: emptyPlan(params.mood as Mood, params.time_budget_minutes ?? null),
        arc: null,
        log: [],
        sample: [],
        candidateCount: 0,
        phase: 'streaming',
        error: null,
        elapsedMs: null,
        roomCode: params.room_code ?? null,
      });
      await consume(api.streamPlan(params, controller.signal));
      return get().plan?.id || null;
    },

    follow: async (planId) => {
      controller?.abort();
      controller = new AbortController();
      set({ plan: { ...emptyPlan('bored', null), id: planId }, arc: null, log: [], sample: [], phase: 'streaming', error: null });
      try {
        const saved = await api.getPlan(planId);
        set({ plan: { ...saved, picks: saved.picks ?? [] }, arc: saved.arc ?? null });
      } catch {
        /* the stream will fill it in */
      }
      await consume(api.followPlan(planId, controller.signal));
      await get().load(planId);
    },

    replan: async (afterPosition, shift) => {
      const plan = get().plan;
      if (!plan?.id) return;
      controller?.abort();
      controller = new AbortController();
      set({ phase: 'streaming', error: null, log: [] });
      await consume(api.streamReplan(plan.id, afterPosition, shift, controller.signal));
      await get().load(plan.id);
    },

    load: async (planId) => {
      try {
        const saved = await api.getPlan(planId);
        set({ plan: saved, arc: saved.arc ?? get().arc, phase: get().phase === 'streaming' ? 'streaming' : 'done' });
      } catch (e: any) {
        set({ error: e.message, phase: 'error' });
      }
    },

    swap: async (pickId) => {
      const plan = get().plan;
      if (!plan?.id) return null;
      set({ swapping: pickId });
      try {
        const res = await api.swapPick(plan.id, pickId);
        const cur = get().plan!;
        set({
          plan: {
            ...cur,
            total_runtime_minutes: res.total_runtime_minutes,
            picks: cur.picks.map((p) => (p.id === pickId ? { status: 'pending', ...res.pick } : p)),
          },
        });
        return res.pick as Pick;
      } finally {
        set({ swapping: null });
      }
    },

    setStatus: async (pickId, status) => {
      const plan = get().plan;
      if (!plan) return;
      set({ plan: { ...plan, picks: plan.picks.map((p) => (p.id === pickId ? { ...p, status } : p)) } });
      await api.setPickStatus(plan.id, pickId, status).catch(() => null);
    },

    reset: () => {
      controller?.abort();
      set({ plan: null, arc: null, log: [], sample: [], phase: 'idle', error: null, roomCode: null });
    },
  };
});
