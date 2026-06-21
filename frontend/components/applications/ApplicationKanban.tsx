/**
 * @module components/applications/ApplicationKanban.tsx
 * @description Kanban board with 7 status columns. Cards show role + company.
 *              Move-forward buttons trigger PATCH /applications/:id. Drag-drop
 *              deferred to Phase 2.
 * @dependencies @/components/ui/card, @/components/ui/button, @/hooks/useApplications, @/types
 */

"use client";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUpdateApplication } from "@/hooks/useApplications";
import type { Application, ApplicationStatus } from "@/types";

const COLUMNS: ApplicationStatus[] = ["pending", "generated", "sent", "opened", "replied", "rejected", "offer"];
const NEXT: Partial<Record<ApplicationStatus, ApplicationStatus>> = {
  pending: "generated", generated: "sent", sent: "opened", opened: "replied",
};

export function ApplicationKanban({ apps }: { apps: Application[] }) {
  const update = useUpdateApplication();
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map((col) => (
        <div key={col} className="min-w-[220px] flex-1">
          <p className="label mb-3">{col} ({apps.filter((a) => a.status === col).length})</p>
          <div className="space-y-3">
            {apps.filter((a) => a.status === col).map((a) => (
              <Card key={a.id} className="shadow-hard">
                <p className="font-mono text-[0.8rem]">{a.job.role}</p>
                <p className="font-mono text-[0.72rem] text-ink-soft">{a.job.company}</p>
                {NEXT[col] && (
                  <Button size="sm" className="mt-3" disabled={update.isPending}
                    onClick={() => update.mutate({ id: a.id, status: NEXT[col] as ApplicationStatus })}>
                    → {NEXT[col]}
                  </Button>
                )}
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
