/**
 * @module app/(dashboard)/applications/[id]/page.tsx
 * @description Application detail page. Shows role, status badge, email content,
 *              and a lifecycle timeline. Handles loading, error, and not-found states.
 * @dependencies @/components/ui/card, badge, @/components/applications/TimelineView, @/hooks/useApplications
 */

"use client";
import { useParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TimelineView } from "@/components/applications/TimelineView";
import { useApplication } from "@/hooks/useApplications";

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: app, isLoading, isError } = useApplication(id);
  if (isLoading) return <p className="font-mono text-ink-soft">Loading…</p>;
  if (isError || !app) return <p className="font-mono text-[var(--warn)]">Application not found.</p>;
  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-3xl">{app.job.role}</h1><Badge>{app.status}</Badge>
      </div>
      <p className="font-mono text-ink-soft mb-6">{app.job.company}</p>
      <Card className="shadow-hard mb-6">
        <p className="label mb-2">Email subject</p>
        <p className="font-body">{app.email_subject ?? "— not generated yet (Phase 2) —"}</p>
        <p className="label mt-4 mb-2">Email body</p>
        <p className="font-body whitespace-pre-wrap">{app.email_body ?? "—"}</p>
      </Card>
      <Card className="shadow-hard">
        <p className="label mb-4">Timeline</p>
        <TimelineView app={app} />
      </Card>
    </div>
  );
}
