/**
 * @module components/jobs/JobFilters.tsx
 * @description Controlled filter bar for the jobs feed.
 *              Exposes q (search) and source filter inputs.
 *              Fully controlled — parent owns state, onChange propagates updates.
 * @dependencies @/components/ui/input
 */

"use client";
import { Input } from "@/components/ui/input";
export interface Filters { q: string; source: string; }
export function JobFilters({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6">
      <Input placeholder="Search role or company" value={value.q}
        onChange={(e) => onChange({ ...value, q: e.target.value })} />
      <Input placeholder="Source (e.g. greenhouse)" value={value.source}
        onChange={(e) => onChange({ ...value, source: e.target.value })} />
    </div>
  );
}
