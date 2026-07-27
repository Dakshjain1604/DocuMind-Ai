"use client";

import { MouseEventHandler } from "react";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface HomecardProps {
  heading: string;
  mainText: string;
  ButtonText: string;
  onClick?: MouseEventHandler;
  numeral?: string;
  disabled?: boolean;
  glyph?: React.ReactNode;
}

export function Homecard({
  heading,
  mainText,
  ButtonText,
  onClick,
  numeral = "I",
  disabled = false,
  glyph,
}: HomecardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={`${ButtonText} — plate ${numeral}: ${heading}`}
      className={`group relative flex h-full w-full flex-col justify-between rounded-2xl border p-6 text-left transition-all duration-200 backdrop-blur-xl ${
        disabled
          ? "cursor-not-allowed opacity-50 border-white/5 bg-zinc-950/40"
          : "border-white/10 bg-zinc-950/70 hover:border-indigo-500/50 hover:bg-zinc-900/80 hover:shadow-xl hover:shadow-indigo-500/10 active:scale-[0.99]"
      }`}
    >
      {/* Plate header */}
      <div className="flex items-center justify-between">
        <Badge variant={disabled ? "secondary" : "default"}>
          Plate {numeral}
        </Badge>
        <span
          className={`h-2 w-2 rounded-full ${
            disabled ? "bg-zinc-600" : "bg-indigo-500 animate-pulse"
          }`}
          aria-hidden
        />
      </div>

      {/* Glyph + Title */}
      <div className="my-5 flex flex-col items-start gap-3">
        {glyph && (
          <span className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 group-hover:text-indigo-300 transition-colors">
            {glyph}
          </span>
        )}
        <h3 className="font-display text-2xl font-bold tracking-tight text-white group-hover:text-indigo-300 transition-colors">
          {heading}
        </h3>
      </div>

      {/* Description */}
      <p className="mb-6 font-sans text-sm leading-relaxed text-zinc-400">
        {mainText}
      </p>

      {/* Action */}
      <div className="flex items-center justify-between border-t border-white/10 pt-4 font-mono text-xs uppercase tracking-wider font-semibold text-zinc-300 group-hover:text-white transition-colors">
        <span>{ButtonText}</span>
        <ArrowRight className="h-4 w-4 text-indigo-400 transition-transform group-hover:translate-x-1" />
      </div>
    </button>
  );
}
