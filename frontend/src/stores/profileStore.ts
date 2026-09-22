/* ── Zustand store for user taste profile and onboarding ── */

import { create } from 'zustand';
import type { GenrePreference, OnboardingData, TasteProfile } from '@/types';
import * as api from '@/api/client';

interface ProfileState {
  profile: TasteProfile | null;
  loading: boolean;
  error: string | null;

  /* onboarding wizard state */
  onboardingStep: number;
  genrePreferences: GenrePreference[];
  selectedProviders: string[];

  /* actions */
  loadProfile: () => Promise<void>;
  submitOnboarding: () => Promise<void>;
  setGenrePreference: (genre: string, action: 'like' | 'dislike' | 'skip') => void;
  toggleProvider: (provider: string) => void;
  nextStep: () => void;
  prevStep: () => void;
}

const ONBOARDING_GENRES = [
  'action', 'comedy', 'drama', 'horror', 'romance',
  'sci-fi', 'thriller', 'animation', 'documentary', 'fantasy',
];

export const useProfileStore = create<ProfileState>((set, get) => ({
  profile: null,
  loading: false,
  error: null,
  onboardingStep: 0,
  genrePreferences: ONBOARDING_GENRES.map((g) => ({ genre: g, action: 'skip' as const })),
  selectedProviders: [],

  loadProfile: async () => {
    set({ loading: true, error: null });
    try {
      const profile = await api.getProfile();
      set({ profile, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  submitOnboarding: async () => {
    const { genrePreferences, selectedProviders } = get();
    set({ loading: true });

    const data: OnboardingData = {
      genre_preferences: genrePreferences.filter((g) => g.action !== 'skip'),
      streaming_services: selectedProviders,
    };

    try {
      await api.saveOnboarding(data);
      await get().loadProfile();
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  setGenrePreference: (genre, action) => {
    set({
      genrePreferences: get().genrePreferences.map((g) =>
        g.genre === genre ? { ...g, action } : g,
      ),
    });
  },

  toggleProvider: (provider) => {
    const current = get().selectedProviders;
    set({
      selectedProviders: current.includes(provider)
        ? current.filter((p) => p !== provider)
        : [...current, provider],
    });
  },

  nextStep: () => set({ onboardingStep: get().onboardingStep + 1 }),
  prevStep: () => set({ onboardingStep: Math.max(0, get().onboardingStep - 1) }),
}));
