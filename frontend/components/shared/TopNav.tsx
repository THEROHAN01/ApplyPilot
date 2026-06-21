/**
 * @module components/shared/TopNav.tsx
 * @description Top navigation bar for the dashboard shell.
 *              Displays the user's email, plan badge, theme toggle, and logout button.
 * @dependencies next/navigation, lucide-react, @/components/shared/ThemeToggle,
 *               @/components/shared/PlanBadge, @/lib/auth, @/types
 */

"use client";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { PlanBadge } from "@/components/shared/PlanBadge";
import { logout } from "@/lib/auth";
import type { User } from "@/types";

export function TopNav({ user }: { user: User }) {
  const router = useRouter();
  return (
    <header className="h-[var(--header-height)] border-b border-rule-soft flex items-center justify-between px-6">
      <span className="label">{user.email}</span>
      <div className="flex items-center gap-3">
        <PlanBadge plan={user.plan} />
        <ThemeToggle />
        <button onClick={() => { logout(); router.push("/login"); }}
          aria-label="Log out" className="border border-ink p-2 hover:bg-ink hover:text-bg transition-colors">
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
