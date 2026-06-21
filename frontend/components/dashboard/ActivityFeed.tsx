/**
 * @module components/dashboard/ActivityFeed.tsx
 * @description Scrollable list of recent application activity.
 *              Each item links to the application detail page.
 * @dependencies next/link, @/types
 */

import Link from "next/link";
import type { Application } from "@/types";

export function ActivityFeed({ apps }: { apps: Application[] }) {
  if (apps.length === 0) return <p className="font-mono text-ink-mute">No recent activity.</p>;
  return (
    <ul className="space-y-3">
      {apps.map((a) => (
        <li key={a.id} className="flex items-center gap-3 border-b border-rule-soft pb-2">
          <span className="w-2 h-2 bg-blueprint shrink-0" />
          <Link href={`/applications/${a.id}`} className="font-mono text-[0.8rem] text-blueprint">{a.job.role}</Link>
          <span className="font-mono text-[0.72rem] text-ink-mute">{a.job.company} · {a.status}</span>
        </li>
      ))}
    </ul>
  );
}
