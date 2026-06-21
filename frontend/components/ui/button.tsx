import { cn } from "@/lib/utils";
import { forwardRef, type ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary"; size?: "sm" | "md";
}
export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variant = "default", size = "md", disabled, ...props }, ref) => (
    <button ref={ref} disabled={disabled}
      className={cn(
        "inline-flex items-center gap-2 font-mono uppercase tracking-[0.12em] border transition-colors",
        size === "sm" ? "px-3 py-1.5 text-[0.72rem]" : "px-5 py-2.5 text-[0.8rem]",
        variant === "primary"
          ? "bg-blueprint text-on-accent border-blueprint hover:bg-accent-hover hover:border-accent-hover"
          : "bg-transparent text-ink border-ink hover:bg-ink hover:text-bg",
        disabled && "opacity-50 cursor-not-allowed hover:bg-transparent hover:text-ink",
        className,
      )}
      {...props} />
  ),
);
Button.displayName = "Button";
