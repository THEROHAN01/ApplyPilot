import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";
export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("inline-flex items-center border border-ink px-2 py-0.5 font-mono text-[0.68rem] uppercase tracking-[0.1em]", className)} {...props} />;
}
