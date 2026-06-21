/**
 * @module app/(dashboard)/layout.tsx
 * @description Client-side auth guard and shell layout for all dashboard routes.
 *              Redirects to /login if getMe() fails (no token or expired).
 *              Renders fixed sidebar + topnav wrapping page content.
 * @dependencies @/components/shared/Sidebar, @/components/shared/TopNav, @/hooks/useMe
 */

"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/shared/Sidebar";
import { TopNav } from "@/components/shared/TopNav";
import { useMe } from "@/hooks/useMe";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, isError } = useMe();
  useEffect(() => { if (isError) router.replace("/login"); }, [isError, router]);
  if (isLoading) return <div className="p-10 font-mono text-ink-soft">Loading…</div>;
  if (!user) return null;
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 min-h-screen">
        <TopNav user={user} />
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
