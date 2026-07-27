import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-xs font-mono uppercase tracking-wider font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]";

    const variants = {
      default:
        "bg-indigo-600 text-white shadow-lg hover:bg-indigo-500 hover:shadow-indigo-500/25",
      destructive:
        "bg-red-900/80 text-red-100 border border-red-500/30 hover:bg-red-800",
      outline:
        "border border-white/10 bg-zinc-900/60 text-zinc-300 hover:border-indigo-500/40 hover:bg-zinc-800 hover:text-white",
      secondary:
        "bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-white",
      ghost:
        "text-zinc-400 hover:bg-white/5 hover:text-white",
      link:
        "text-indigo-400 underline-offset-4 hover:underline p-0 h-auto",
    };

    const sizes = {
      default: "h-10 px-4 py-2",
      sm: "h-8 px-3 text-[11px]",
      lg: "h-12 px-6 text-sm",
      icon: "h-9 w-9 p-0",
    };

    return (
      <button
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
