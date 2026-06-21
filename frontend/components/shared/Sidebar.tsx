/**
 * @module components/shared/Sidebar.tsx
 * @description Fixed sidebar with primary navigation links for the dashboard shell.
 *              Highlights the active route using Next.js usePathname.
 * @dependencies next/link, next/navigation, lucide-react, @/lib/utils
 */

"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Briefcase, Send, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/applications", label: "Applications", icon: Send },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-[var(--sidebar-width)] shrink-0 border-r border-rule-soft bg-surface min-h-screen p-5">
      <div className="text-2xl mb-8" style={{ fontFamily: "var(--font-display)" }}>ApplyPilot</div>
      <nav className="space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={href} href={href}
              className={cn("flex items-center gap-3 px-3 py-2 font-mono text-[0.8rem] uppercase tracking-[0.08em] border border-transparent",
                active ? "bg-blueprint-tint border-blueprint text-ink" : "text-ink-soft hover:text-ink hover:border-rule-soft")}>
              <Icon size={16} /> {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
