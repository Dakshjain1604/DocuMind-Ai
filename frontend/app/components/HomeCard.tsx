"use client";

import { MouseEventHandler } from "react";

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
      className={`regmark instrument group/inst relative flex h-full w-full flex-col justify-between border border-[var(--rule)] bg-[var(--ink-1)] p-7 text-left text-[var(--paper)] ${
        disabled
          ? "cursor-not-allowed opacity-40"
          : "hover:border-[var(--vermillion)] hover:bg-[var(--ink-2)]"
      }`}
    >
      <span className="rm-tr" aria-hidden />
      <span className="rm-bl" aria-hidden />

      {/* Plate header */}
      <div className="flex items-start justify-between">
        <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/55">
          Plate · {numeral}
        </span>
        <span
          className={`ticker-dot text-[10px] ${
            disabled ? "text-[var(--paper-3)]/30" : "text-[var(--vermillion)]"
          }`}
          aria-hidden
        >
          ●
        </span>
      </div>

      {/* Glyph + Title */}
      <div className="my-6 flex flex-col items-start gap-4">
        {glyph && (
          <span className="text-[var(--paper)] transition-colors group-hover/inst:text-[var(--vermillion)]">
            {glyph}
          </span>
        )}
        <h3 className="font-display text-[44px] leading-[0.95] tracking-[-0.02em] text-[var(--paper)] sm:text-[52px]">
          {heading}
        </h3>
      </div>

      {/* Description */}
      <p className="mb-6 max-w-[24ch] font-sans text-[13.5px] leading-[1.55] text-[var(--paper-3)]/70">
        {mainText}
      </p>

      {/* Action */}
      <div className="flex items-center justify-between border-t border-[var(--rule)] pt-4 font-mono-cap text-[11px] text-[var(--paper)] transition-colors group-hover/inst:text-[var(--vermillion)]">
        <span>{ButtonText}</span>
        <span className="font-sans text-[18px] leading-none transition-transform group-hover/inst:translate-x-1.5">
          →
        </span>
      </div>
    </button>
  );
}
