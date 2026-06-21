/**
 * @module app/(dashboard)/dashboard/page.tsx
 * @description Main dashboard overview page. Shows stats grid, status distribution
 *              bar chart, and recent activity feed. Handles loading and error states.
 * @dependencies @/components/dashboard/StatsGrid, ReplyRateChart, ActivityFeed, @/hooks/useDashboard
 */

"use client";
import { Card } from "@/components/ui/card";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { ReplyRateChart } from "@/components/dashboard/ReplyRateChart";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { useDashboard } from "@/hooks/useDashboard";

export default function DashboardPage() {
  const { data, isLoading, isError } = useDashboard();
  if (isLoading) return <p className="font-mono text-ink-soft">Loading…</p>;
  if (isError || !data) return <p className="font-mono text-warn">Failed to load dashboard.</p>;
  return (
    <div>
      <h1 className="text-3xl mb-6">Dashboard</h1>
      <StatsGrid stats={data} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-hard"><p className="label mb-4">Status distribution</p><ReplyRateChart stats={data} /></Card>
        <Card className="shadow-hard"><p className="label mb-4">Recent activity</p><ActivityFeed apps={data.recent} /></Card>
      </div>
    </div>
  );
}
