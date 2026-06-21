/**
 * @module components/dashboard/StatsGrid.tsx
 * @description 4-cell grid showing total applications, sent count, replied count, and reply rate.
 *              Uses display font for large numeric values.
 * @dependencies @/components/ui/card, @/types
 */

import { Card } from "@/components/ui/card";
import type { DashboardStats } from "@/types";

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  const cells = [
    { label: "Applications", value: stats.total_applications },
    { label: "Sent", value: stats.by_status["sent"] ?? 0 },
    { label: "Replied", value: stats.by_status["replied"] ?? 0 },
    { label: "Reply rate", value: `${Math.round(stats.reply_rate * 100)}%` },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
      {cells.map((c) => (
        <Card key={c.label} className="shadow-hard">
          <p className="label">{c.label}</p>
          <p className="text-4xl mt-2" style={{ fontFamily: "var(--font-display)" }}>{c.value}</p>
        </Card>
      ))}
    </div>
  );
}
