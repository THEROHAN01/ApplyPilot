/**
 * @module components/jobs/JobCard.tsx
 * @description Card component for a single job in the jobs feed.
 *              Displays role, company, match score badge, source, location,
 *              and salary range. Links to the job detail page.
 * @dependencies next/link, @/components/ui/card, @/components/ui/badge, @/types
 */

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Job } from "@/types";

export function JobCard({ job }: { job: Job }) {
  return (
    <Link href={`/jobs/${job.id}`}>
      <Card className="shadow-hard hover:shadow-hard-lg">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-xl">{job.role}</h3>
            <p className="font-mono text-[0.8rem] text-ink-soft">{job.company}</p>
          </div>
          {job.match_score !== null && (
            <Badge className="border-blueprint text-blueprint">{Math.round(job.match_score * 100)}%</Badge>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[0.7rem] text-ink-mute uppercase">
          <span>{job.source}</span>
          {job.location && <span>· {job.location}</span>}
          {job.salary_range && <span>· {job.salary_range}</span>}
        </div>
      </Card>
    </Link>
  );
}
