import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "destructive";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const baseStyles =
    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider transition-colors";

  const variants = {
    default:
      "border border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
    secondary:
      "border border-white/10 bg-zinc-900/60 text-zinc-400",
    outline:
      "border border-white/20 text-zinc-300",
    success:
      "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    warning:
      "border border-amber-500/30 bg-amber-500/10 text-amber-400",
    destructive:
      "border border-red-500/30 bg-red-500/10 text-red-400",
  };

  return (
    <div className={cn(baseStyles, variants[variant], className)} {...props} />
  );
}

export { Badge };
