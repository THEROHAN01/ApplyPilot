/**
 * @module hooks/useResumes.ts
 * @description React Query hooks for resumes list and file upload.
 *              useResumes: fetches all resumes for the authenticated user.
 *              useUploadResume: mutation to POST /resumes with multipart form data.
 * @dependencies @tanstack/react-query, @/lib/api, @/types
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Resume } from "@/types";

export function useResumes() {
  return useQuery<Resume[]>({ queryKey: ["resumes"], queryFn: async () => (await api.get<Resume[]>("/resumes")).data });
}
export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation<Resume, Error, File>({
    mutationFn: async (file) => {
      const fd = new FormData(); fd.append("file", file);
      return (await api.post<Resume>("/resumes", fd, { headers: { "Content-Type": "multipart/form-data" } })).data;
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["resumes"] }); },
  });
}
