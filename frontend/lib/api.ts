/**
 * @module lib/api.ts
 * @description Centralized axios instance for all backend API calls.
 *              Request interceptor injects Authorization Bearer token from authStore.
 *              Response interceptor handles 401s by attempting a single token
 *              refresh via /auth/refresh, retrying the original request on success,
 *              or clearing auth state on refresh failure.
 * @dependencies axios, @/store/authStore, @/types
 */

import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/store/authStore";
import type { TokenPair } from "@/types";

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const api = axios.create({ baseURL });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refresh(): Promise<string | null> {
  const rt = useAuthStore.getState().refreshToken;
  if (!rt) return null;
  try {
    const { data } = await axios.post<TokenPair>(`${baseURL}/auth/refresh`, { refresh_token: rt });
    useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch { useAuthStore.getState().clear(); return null; }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      refreshing = refreshing ?? refresh();
      const token = await refreshing;
      refreshing = null;
      if (token) { original.headers.Authorization = `Bearer ${token}`; return api(original); }
    }
    return Promise.reject(error);
  },
);
