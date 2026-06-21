import { cn } from "@/lib/utils";
import { forwardRef, type InputHTMLAttributes } from "react";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref}
      className={cn("w-full border border-ink bg-bg px-3 py-2 font-body text-ink",
        "focus:outline-none focus:border-blueprint placeholder:text-ink-mute", className)}
      {...props} />
  ),
);
Input.displayName = "Input";
