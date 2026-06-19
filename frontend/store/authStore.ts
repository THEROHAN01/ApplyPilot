/**
 * @module store/authStore.ts
 * @description Zustand store for JWT auth state (accessToken + refreshToken).
 *              Persisted to localStorage under the key "applypilot-auth" so
 *              tokens survive page reloads. Consumed by lib/api.ts interceptors.
 * @dependencies zustand, zustand/middleware
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  setTokens: (a: string, r: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      setTokens: (a, r) => set({ accessToken: a, refreshToken: r }),
      clear: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: "applypilot-auth" },
  ),
);
