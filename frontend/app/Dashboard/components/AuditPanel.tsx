"use client";

import { AuditFinding, Coverage } from "../types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CoverageNote, EmptyState, ErrorBanner } from "@/components/ui/ErrorBanner";

/**
 * Compliance findings extracted from the document.
 *
 * The three states are rendered separately on purpose: an empty result means
 * the analysis ran and found nothing, which is a different answer from the
 * analysis having failed. The backend used to conflate them by returning an
 * invented finding on error.
 */
export function AuditPanel({
  loading,
  items,
  error,
  coverage,
  onRetry,
}: {
  loading: boolean;
  items: AuditFinding[];
  error?: string;
  coverage?: Coverage;
  onRetry: () => void;
}) {
  if (loading) {
    return (
      <Card className="p-12 text-center space-y-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <div className="font-mono text-xs text-zinc-400">
          Auditing document batch for compliance &amp; security risks…
        </div>
      </Card>
    );
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={onRetry} />;
  }

  if (items.length === 0) {
    return <EmptyState message="No compliance findings were identified in the sampled sections." />;
  }

  return (
    <div className="grid gap-4">
      {items.map((item) => (
        <Card key={item.id} className="p-6 space-y-3 border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between">
            <Badge
              variant={
                item.severity === "high"
                  ? "destructive"
                  : item.severity === "medium"
                    ? "warning"
                    : "secondary"
              }
            >
              {/* Defensive: a model that omits severity used to throw here and
                  take down the entire audit view. */}
              {(item.severity ?? "unknown").toUpperCase()} SEVERITY
            </Badge>
            <span className="font-mono text-xs text-zinc-400">{item.category}</span>
          </div>
          <h4 className="font-display text-lg font-bold text-white">Finding: {item.finding}</h4>
          <div className="rounded-xl border border-white/5 bg-zinc-900/60 p-3 font-mono text-xs text-zinc-300 space-y-1">
            <span className="text-emerald-400 font-semibold">Recommended Mitigation:</span>
            <p>{item.mitigation}</p>
          </div>
        </Card>
      ))}
      <CoverageNote coverage={coverage} />
    </div>
  );
}
