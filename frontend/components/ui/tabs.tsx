import * as React from "react";
import { cn } from "@/lib/utils";

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ value, onValueChange, children, className }: TabsProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            activeValue: value,
            onValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

export function TabsList({
  children,
  className,
  activeValue,
  onValueChange,
}: {
  children: React.ReactNode;
  className?: string;
  activeValue?: string;
  onValueChange?: (val: string) => void;
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-zinc-950/80 p-1.5 backdrop-blur-md",
        className
      )}
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            activeValue,
            onValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  className,
  activeValue,
  onValueChange,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
  activeValue?: string;
  onValueChange?: (val: string) => void;
}) {
  const isActive = activeValue === value;
  return (
    <button
      type="button"
      onClick={() => onValueChange?.(value)}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider transition-all duration-200 focus-visible:outline-none",
        isActive
          ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
          : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  children,
  activeValue,
  className,
}: {
  value: string;
  children: React.ReactNode;
  activeValue?: string;
  className?: string;
}) {
  if (activeValue !== value) return null;
  return <div className={cn("animate-in fade-in-50 duration-200", className)}>{children}</div>;
}
