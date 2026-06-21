/**
 * @module components/jobs/JobFeed.tsx
 * @description Renders the jobs grid from a JobList response.
 *              Handles all 4 states: loading, error, empty, and success.
 *              On success renders a responsive grid of JobCard components.
 * @dependencies @/components/jobs/JobCard, @/types
 */

"use client";
import { JobCard } from "@/components/jobs/JobCard";
import type { JobList } from "@/types";
export function JobFeed({ data, isLoading, isError }: { data?: JobList; isLoading: boolean; isError: boolean }) {
  if (isLoading) return <p className="font-mono text-ink-soft">Loading jobs…</p>;
  if (isError) return <p className="font-mono text-warn">Failed to load jobs.</p>;
  if (!data || data.items.length === 0) return <p className="font-mono text-ink-mute">No jobs yet.</p>;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.items.map((j) => <JobCard key={j.id} job={j} />)}
    </div>
  );
}
