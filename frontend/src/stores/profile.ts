import { create } from 'zustand';
import * as api from '@/lib/api';
import type { Profile, Provider } from '@/lib/types';

interface ProfileState {
  profile: Profile | null;
  profiles: Profile[];
  ready: boolean;
  error: string | null;
  load: () => Promise<void>;
  loadAll: () => Promise<void>;
  switchTo: (id: string) => Promise<void>;
  save: (data: Parameters<typeof api.saveOnboarding>[0]) => Promise<Profile>;
  update: (data: Partial<{ name: string; is_kids: boolean; region: string; streaming_services: Provider[]; reset_exclusions: boolean }>) => Promise<void>;
}

export const useProfile = create<ProfileState>((set, get) => ({
  profile: null,
  profiles: [],
  ready: false,
  error: null,

  load: async () => {
    try {
      const profile = await api.getProfile();
      if (profile.id) api.setActiveProfileId(profile.id);
      set({ profile, ready: true, error: null });
    } catch (e: any) {
      set({ ready: true, error: e.message ?? 'Could not reach Vibe' });
    }
  },

  loadAll: async () => {
    try {
      const { profiles } = await api.listProfiles();
      set({ profiles });
    } catch {
      /* ignore */
    }
  },

  switchTo: async (id) => {
    api.setActiveProfileId(id);
    await get().load();
  },

  save: async (data) => {
    const profile = await api.saveOnboarding(data);
    if (profile.id) api.setActiveProfileId(profile.id);
    set({ profile });
    get().loadAll();
    return profile;
  },

  update: async (data) => {
    const profile = await api.updateSettings(data);
    set({ profile });
    get().loadAll();
  },
}));
