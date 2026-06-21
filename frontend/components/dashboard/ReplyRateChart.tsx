/**
 * @module components/dashboard/ReplyRateChart.tsx
 * @description Recharts BarChart showing application count per status.
 *              Uses CSS var(--blueprint) for bar fill — no hardcoded hex colors.
 * @dependencies recharts, @/types
 */

"use client";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Cell } from "recharts";
import type { DashboardStats } from "@/types";

export function ReplyRateChart({ stats }: { stats: DashboardStats }) {
  const data = Object.entries(stats.by_status).map(([status, count]) => ({ status, count }));
  if (data.length === 0) return <p className="font-mono text-ink-mute">No data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <XAxis dataKey="status" tick={{ fontFamily: "var(--font-mono)", fontSize: 11 }} />
        <YAxis allowDecimals={false} tick={{ fontFamily: "var(--font-mono)", fontSize: 11 }} />
        <Bar dataKey="count">{data.map((d) => <Cell key={d.status} fill="var(--blueprint)" />)}</Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
