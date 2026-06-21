/**
 * @module hooks/useDashboard.ts
 * @description React Query hook for dashboard stats.
 *              Fetches total_applications, by_status breakdown, reply_rate, and recent applications.
 * @dependencies @tanstack/react-query, @/lib/api, @/types
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";

export function useDashboard() {
  return useQuery<DashboardStats>({ queryKey: ["dashboard"],
    queryFn: async () => (await api.get<DashboardStats>("/dashboard/stats")).data });
}
