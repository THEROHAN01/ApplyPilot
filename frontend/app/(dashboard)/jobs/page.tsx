/**
 * @module app/(dashboard)/jobs/page.tsx
 * @description Jobs list page. Renders JobFilters and JobFeed.
 *              Filter state is local; query params passed to useJobs.
 *              Empty strings are coerced to undefined so the API omits them.
 * @dependencies @/components/jobs/JobFilters, @/components/jobs/JobFeed, @/hooks/useJobs
 */

"use client";
import { useState } from "react";
import { JobFilters, type Filters } from "@/components/jobs/JobFilters";
import { JobFeed } from "@/components/jobs/JobFeed";
import { useJobs } from "@/hooks/useJobs";

export default function JobsPage() {
  const [filters, setFilters] = useState<Filters>({ q: "", source: "" });
  const { data, isLoading, isError } = useJobs({
    q: filters.q || undefined, source: filters.source || undefined, page: 1, page_size: 30,
  });
  return (
    <div>
      <h1 className="text-3xl mb-6">Jobs</h1>
      <JobFilters value={filters} onChange={setFilters} />
      <JobFeed data={data} isLoading={isLoading} isError={isError} />
    </div>
  );
}
