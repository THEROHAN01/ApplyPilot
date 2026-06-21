/**
 * @module components/applications/TimelineView.tsx
 * @description Vertical timeline of application lifecycle events: Created, Sent, Follow-up, Replied.
 *              Filters out null timestamps so only completed events are shown.
 * @dependencies @/types
 */

import type { Application } from "@/types";

export function TimelineView({ app }: { app: Application }) {
  const events: { label: string; at: string | null }[] = [
    { label: "Created", at: app.created_at },
    { label: "Sent", at: app.sent_at },
    { label: "Follow-up scheduled", at: app.follow_up_at },
    { label: "Replied", at: app.reply_at },
  ];
  return (
    <ul className="space-y-3">
      {events.filter((e) => e.at).map((e) => (
        <li key={e.label} className="flex items-center gap-3">
          <span className="w-3 h-3 bg-blueprint shrink-0" />
          <span className="font-mono text-[0.8rem]">{e.label}</span>
          <span className="font-mono text-[0.75rem] text-ink-mute">{new Date(e.at as string).toLocaleString()}</span>
        </li>
      ))}
    </ul>
  );
}
