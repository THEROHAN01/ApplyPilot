/**
 * @module hooks/useJobs.ts
 * @description React Query hooks for jobs feed and job detail.
 *              useJobs: paginated + filtered job list keyed by params.
 *              useJob: single job by id.
 *              useCreateApplication: mutation to POST /applications for a job,
 *              invalidates the applications query on success.
 * @dependencies @tanstack/react-query, @/lib/api, @/types
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Application, Job, JobList } from "@/types";

export interface JobQuery { company?: string; source?: string; q?: string; page?: number; page_size?: number; }

export function useJobs(params: JobQuery) {
  return useQuery<JobList>({
    queryKey: ["jobs", params],
    queryFn: async () => (await api.get<JobList>("/jobs", { params })).data,
  });
}
export function useJob(id: string) {
  return useQuery<Job>({ queryKey: ["job", id], queryFn: async () => (await api.get<Job>(`/jobs/${id}`)).data });
}
export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation<Application, Error, string>({
    mutationFn: async (jobId) => (await api.post<Application>("/applications", { job_id: jobId })).data,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["applications"] }); },
  });
}
