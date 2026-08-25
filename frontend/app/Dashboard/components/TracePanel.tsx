"use client";

import { useEffect, useState } from "react";
import { Activity, Coins, Database, Gauge } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBanner } from "@/components/ui/ErrorBanner";

type TraceStage = {
  stage: string;
  latency_ms: number;
  error?: string;
  degraded?: boolean;
  [key: string]: unknown;
};

type TraceCitation = {
  n: number;
  chunk_id: number | null;
  source?: string;
  sources?: string[];
  rerank_score?: number | null;
};

type Trace = {
  request_id: string;
  total_latency_ms: number | null;
  total_tokens_in: number | null;
  total_tokens_out: number | null;
  total_cost_usd: number | null;
  cache_hit: boolean;
  stages: TraceStage[];
  context: TraceCitation[];
  error: string | null;
};

const LEG_STYLE: Record<string, string> = {
  vector: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
  bm25: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  graph: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  graph_community: "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300",
};

/**
 * Per-turn trace inspector — the backend has always recorded full stage
 * latencies, token/cost accounting and per-chunk retrieval provenance
 * (GET /trace/{request_id}), but nothing in the UI ever read it. This is
 * that missing surface, fetched lazily so it costs nothing until opened.
 */
export function TracePanel({ requestId }: { requestId: string }) {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/rag/trace/${encodeURIComponent(requestId)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`Trace unavailable (HTTP ${r.status}).`);
        return r.json();
      })
      .then((data: Trace) => {
        if (!cancelled) setTrace(data);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message || "Could not load the trace.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [requestId, nonce]);

  if (loading) {
    return (
      <div className="space-y-2 rounded-xl border border-white/10 bg-zinc-950/60 p-3">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    );
  }

  if (error || !trace) {
    return (
      <ErrorBanner
        message={error ?? "Trace not found."}
        onRetry={() => setNonce((n) => n + 1)}
      />
    );
  }

  const maxLatency = Math.max(1, ...trace.stages.map((s) => s.latency_ms || 0));

  return (
    <div className="space-y-4 rounded-xl border border-white/10 bg-zinc-950/60 p-4 font-mono text-xs">
      {/* Summary strip */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-zinc-400">
        <span className="inline-flex items-center gap-1.5">
          <Gauge className="h-3.5 w-3.5 text-indigo-400" />
          {trace.total_latency_ms != null ? `${Math.round(trace.total_latency_ms)}ms total` : "latency n/a"}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-indigo-400" />
          {trace.total_tokens_in ?? 0} in / {trace.total_tokens_out ?? 0} out tokens
        </span>
        {trace.total_cost_usd != null && (
          <span className="inline-flex items-center gap-1.5">
            <Coins className="h-3.5 w-3.5 text-indigo-400" />
            ${trace.total_cost_usd.toFixed(4)}
          </span>
        )}
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 uppercase tracking-wider text-[10px] ${
            trace.cache_hit
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-white/10 bg-white/5 text-zinc-400"
          }`}
        >
          <Database className="h-3 w-3" />
          {trace.cache_hit ? "cache hit" : "cache miss"}
        </span>
      </div>

      {trace.error && (
        <ErrorBanner message={`This request recorded an error: ${trace.error}`} />
      )}

      {/* Stage timeline */}
      {trace.stages.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">Pipeline stages</div>
          {trace.stages.map((s, i) => (
            <div key={`${s.stage}_${i}`} className="flex items-center gap-2">
              <span className="w-32 shrink-0 truncate text-zinc-400">{s.stage}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
                <div
                  className={`h-full rounded-full ${s.error ? "bg-red-500/60" : "bg-indigo-500/60"}`}
                  style={{ width: `${Math.max(4, (s.latency_ms / maxLatency) * 100)}%` }}
                />
              </div>
              <span className="w-16 shrink-0 text-right text-zinc-500">
                {Math.round(s.latency_ms)}ms
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Retrieval provenance */}
      {trace.context.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">
            Retrieval provenance
          </div>
          <div className="flex flex-wrap gap-1.5">
            {trace.context.map((c) => (
              <span
                key={c.n}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-zinc-400"
              >
                <span className="font-bold text-zinc-300">{String(c.n).padStart(2, "0")}</span>
                {(c.sources ?? (c.source ? [c.source] : [])).map((leg) => (
                  <span
                    key={leg}
                    className={`rounded border px-1.5 py-0.5 text-[10px] ${LEG_STYLE[leg] ?? "border-white/10 bg-white/5 text-zinc-400"}`}
                  >
                    {leg}
                  </span>
                ))}
                {c.rerank_score != null && (
                  <span className="text-[10px] text-zinc-500">{c.rerank_score.toFixed(3)}</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
