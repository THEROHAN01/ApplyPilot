/**
 * @module hooks/useApplications.ts
 * @description React Query hooks for applications list, single application, and status update.
 *              useApplications: optionally filtered by status.
 *              useApplication: single application by id.
 *              useUpdateApplication: mutation to PATCH /applications/:id status.
 * @dependencies @tanstack/react-query, @/lib/api, @/types
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Application, ApplicationStatus } from "@/types";

export function useApplications(status?: ApplicationStatus) {
  return useQuery<Application[]>({
    queryKey: ["applications", status ?? "all"],
    queryFn: async () => (await api.get<Application[]>("/applications", { params: status ? { status } : {} })).data,
  });
}
export function useApplication(id: string) {
  return useQuery<Application>({ queryKey: ["application", id],
    queryFn: async () => (await api.get<Application>(`/applications/${id}`)).data });
}
export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation<Application, Error, { id: string; status: ApplicationStatus }>({
    mutationFn: async ({ id, status }) => (await api.patch<Application>(`/applications/${id}`, { status })).data,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["applications"] }); },
  });
}
