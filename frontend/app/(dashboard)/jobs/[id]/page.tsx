/**
 * @module app/(dashboard)/jobs/[id]/page.tsx
 * @description Job detail page. Shows role, company, source, and JD link.
 *              Provides a "Create application" CTA that POSTs to /applications
 *              and navigates to the new application on success.
 *              Handles loading, error, and not-found states.
 * @dependencies @/components/ui/card, @/components/ui/button, @/hooks/useJobs
 */

"use client";
import { useParams, useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useJob, useCreateApplication } from "@/hooks/useJobs";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: job, isLoading, isError } = useJob(id);
  const create = useCreateApplication();
  if (isLoading) return <p className="font-mono text-ink-soft">Loading…</p>;
  if (isError || !job) return <p className="font-mono text-warn">Job not found.</p>;
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl">{job.role}</h1>
      <p className="font-mono text-ink-soft mb-6">{job.company}</p>
      <Card className="shadow-hard">
        <p className="label mb-2">Source</p>
        <p className="font-mono text-[0.85rem]">{job.source}</p>
        {job.jd_url && <a href={job.jd_url} className="block mt-4 text-blueprint font-mono text-[0.8rem]">View posting →</a>}
      </Card>
      <Button variant="primary" className="mt-6" disabled={create.isPending}
        onClick={async () => { try { const app = await create.mutateAsync(job.id); router.push(`/applications/${app.id}`); } catch { /* React Query sets create.isError */ } }}>
        {create.isPending ? "Creating…" : "Create application"}
      </Button>
      {create.isError && (
        <p className="font-mono text-sm text-warn mt-2">Failed to create application. Please try again.</p>
      )}
    </div>
  );
}
