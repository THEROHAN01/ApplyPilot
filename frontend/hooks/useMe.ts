/**
 * @module hooks/useMe.ts
 * @description React Query hook to fetch the authenticated user's profile.
 *              Used by the dashboard layout guard to verify auth state.
 * @dependencies @tanstack/react-query, @/lib/auth, @/types
 */

import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/lib/auth";
import type { User } from "@/types";

export function useMe() {
  return useQuery<User>({ queryKey: ["me"], queryFn: getMe, retry: false });
}
