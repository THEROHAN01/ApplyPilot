/**
 * @module lib/auth.ts
 * @description Typed helper functions for authentication API calls.
 *              All functions use the centralized api instance and store tokens
 *              in authStore on success.
 * @dependencies @/lib/api, @/store/authStore, @/types
 */

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { TokenPair, User } from "@/types";

export async function signup(email: string, password: string, name?: string): Promise<void> {
  const { data } = await api.post<TokenPair>("/auth/signup", { email, password, name });
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
}

export async function login(email: string, password: string): Promise<void> {
  const { data } = await api.post<TokenPair>("/auth/login", { email, password });
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
}

export async function getMe(): Promise<User> {
  return (await api.get<User>("/auth/me")).data;
}

export function logout(): void { useAuthStore.getState().clear(); }
