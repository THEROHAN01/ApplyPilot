/**
 * @module components/applications/ApplicationTable.tsx
 * @description Tabular view of applications with role, company, status badge, and created date.
 *              Each role links to the application detail page.
 * @dependencies next/link, @/components/ui/badge, @/types
 */

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Application } from "@/types";

export function ApplicationTable({ apps }: { apps: Application[] }) {
  return (
    <div className="overflow-x-auto border border-rule-soft">
      <table className="w-full font-mono text-[0.8rem]">
        <thead className="border-b border-ink text-left uppercase tracking-[0.08em]">
          <tr><th className="p-3">Role</th><th className="p-3">Company</th><th className="p-3">Status</th><th className="p-3">Created</th></tr>
        </thead>
        <tbody>
          {apps.map((a) => (
            <tr key={a.id} className="border-b border-rule-soft hover:bg-surface-hover">
              <td className="p-3"><Link href={`/applications/${a.id}`} className="text-blueprint">{a.job.role}</Link></td>
              <td className="p-3">{a.job.company}</td>
              <td className="p-3"><Badge>{a.status}</Badge></td>
              <td className="p-3 text-ink-mute">{new Date(a.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
