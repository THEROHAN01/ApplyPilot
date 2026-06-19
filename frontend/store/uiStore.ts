/**
 * @module store/uiStore.ts
 * @description Zustand store for global UI state (sidebar open/closed).
 *              Not persisted — resets to open on each page load.
 * @dependencies zustand
 */

import { create } from "zustand";

interface UiState { sidebarOpen: boolean; toggleSidebar: () => void; }

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));
