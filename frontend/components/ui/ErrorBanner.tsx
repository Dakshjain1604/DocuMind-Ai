"use client";

import { AlertCircle, RefreshCw } from "lucide-react";

/**
 * The single failure surface for panels that fetch.
 *
 * Removing the fabricated fallbacks from the studio endpoints means a failed
 * request now genuinely has nothing to show. Without this, "plausible invented
 * content" would simply become "a panel that stays blank forever" — honest,
 * but no more usable. role="alert" so the failure is announced, not just seen.
 */
export function ErrorBanner({
  message,
  onRetry,
  className = "",
}: {
  message: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className={`flex items-start justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 font-mono text-xs text-red-400 ${className}`}
    >
      <span className="flex items-start gap-2">
        <AlertCircle className="mt-px h-4 w-4 shrink-0" />
        <span className="leading-relaxed">{message}</span>
      </span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-red-500/30 px-2.5 py-1 uppercase tracking-wider transition-colors hover:bg-red-500/15"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * A successful request that produced nothing. Deliberately distinct from
 * ErrorBanner: "no findings in this document" and "we could not run the
 * analysis" are different answers and must not look alike.
 */
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/60 p-8 text-center font-mono text-xs leading-relaxed text-zinc-500">
      {message}
    </div>
  );
}

/** Renders the sampling disclosure attached to a generated artifact. */
export function CoverageNote({
  coverage,
}: {
  coverage?: { sampled_chunks?: number; total_chunks?: number; unit?: string; is_partial?: boolean } | null;
}) {
  if (!coverage?.total_chunks) return null;
  const unit = coverage.unit === "parent_chunks" ? "sections" : "chunks";
  return (
    <p className="font-mono text-[10px] leading-relaxed text-zinc-500">
      {coverage.is_partial
        ? `Generated from an even-stride sample of ${coverage.sampled_chunks} of ${coverage.total_chunks} ${unit}.`
        : `Generated from all ${coverage.total_chunks} ${unit}.`}
    </p>
  );
}
