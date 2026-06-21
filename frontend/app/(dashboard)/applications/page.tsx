/**
 * @module app/(dashboard)/applications/page.tsx
 * @description Applications list page with kanban/table view toggle.
 *              Handles loading, error, empty, and populated states.
 * @dependencies @/components/applications/ApplicationKanban, ApplicationTable, @/hooks/useApplications
 */

"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ApplicationKanban } from "@/components/applications/ApplicationKanban";
import { ApplicationTable } from "@/components/applications/ApplicationTable";
import { useApplications } from "@/hooks/useApplications";

export default function ApplicationsPage() {
  const [view, setView] = useState<"kanban" | "table">("kanban");
  const { data, isLoading, isError } = useApplications();
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl">Applications</h1>
        <div className="flex gap-2">
          <Button size="sm" variant={view === "kanban" ? "primary" : "default"} onClick={() => setView("kanban")}>Kanban</Button>
          <Button size="sm" variant={view === "table" ? "primary" : "default"} onClick={() => setView("table")}>Table</Button>
        </div>
      </div>
      {isLoading && <p className="font-mono text-ink-soft">Loading…</p>}
      {isError && <p className="font-mono text-[var(--warn)]">Failed to load applications.</p>}
      {data && data.length === 0 && <p className="font-mono text-ink-mute">No applications yet — create one from a job.</p>}
      {data && data.length > 0 && (view === "kanban" ? <ApplicationKanban apps={data} /> : <ApplicationTable apps={data} />)}
    </div>
  );
}
