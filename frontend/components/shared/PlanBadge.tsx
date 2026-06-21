/**
 * @module components/shared/PlanBadge.tsx
 * @description Displays the user's subscription plan as a styled badge.
 *              Color-codes each plan tier using semantic border/text tokens.
 * @dependencies @/components/ui/badge, @/types
 */

import { Badge } from "@/components/ui/badge";
import type { Plan } from "@/types";

export function PlanBadge({ plan }: { plan: Plan }) {
  const color = plan === "unlimited" ? "border-blueprint text-blueprint"
    : plan === "pro" ? "border-ink text-ink" : "border-ink-mute text-ink-mute";
  return <Badge className={color}>{plan}</Badge>;
}
