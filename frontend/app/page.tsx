import Link from "next/link";
import { ArrowRight, Cpu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const BACKEND = process.env.RAG_BACKEND_URL ?? "http://localhost:8000";

type LiveTelemetry = {
  total_requests?: number;
  avg_latency_ms?: number;
};

/**
 * Real numbers from the trace store, or null when the backend is unreachable.
 * The panel below used to hard-code its "telemetry" (a 1.4s embedding time, a
 * "<1.8s per turn" latency) — figures that were never measured.
 */
async function fetchTelemetry(): Promise<LiveTelemetry | null> {
  try {
    const res = await fetch(`${BACKEND}/telemetry/stats`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (!res.ok) return null;
    const body = await res.json();
    return body?.data ?? null;
  } catch {
    // The landing page must render with the backend down.
    return null;
  }
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const telemetry = await fetchTelemetry();
  const avgLatency =
    telemetry?.avg_latency_ms != null ? `${(telemetry.avg_latency_ms / 1000).toFixed(2)}s` : "—";
  const totalRequests = telemetry?.total_requests ?? 0;

  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 selection:bg-white/20">
      {/* ── HEADER ─────────────────────────────── */}
      <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-zinc-950/80 backdrop-blur-xl">
        <div className="container mx-auto flex h-14 items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="h-3 w-3 rounded-full bg-white animate-pulse" />
            <span className="font-display text-lg font-bold tracking-tight text-white">
              Docu<span className="gradient-accent-text">Mind</span>
            </span>
            <Badge variant="secondary" className="hidden sm:inline-flex">
              GraphRAG v2.4
            </Badge>
          </div>

          <nav className="flex items-center gap-4">
            <Link href="/signin" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Sign In
            </Link>
            <Link href="/Dashboard">
              <Button size="sm" className="gap-2 bg-white text-zinc-950 hover:bg-zinc-200">
                Launch Studio
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* ── HERO SECTION ─────────────────────────────────────── */}
      <main className="flex-1">
        <section className="container mx-auto flex flex-col items-center space-y-10 px-4 py-24 text-center sm:px-6 lg:py-32">
          <Badge variant="default" className="gap-2 px-3 py-1">
            <Cpu className="h-4 w-4" />
            Hybrid Vector × BM25 × Knowledge Graph Engine
          </Badge>

          <h1 className="max-w-3xl font-display text-4xl font-bold tracking-tight text-white sm:text-5xl md:text-6xl">
            Read documents with <br className="hidden sm:inline" />
            cartographic precision.
          </h1>

          <p className="max-w-[42rem] leading-normal text-zinc-400 sm:text-xl sm:leading-8">
            DocuMind extracts knowledge entities, draws Louvain community relationships,
            and streams answers backed by verifiable passage-level citations.
          </p>

          <div className="flex flex-col items-center gap-4 sm:flex-row">
            <Link href="/Dashboard">
              <Button size="lg" className="h-12 gap-2 bg-white px-8 text-zinc-950 hover:bg-zinc-200">
                Launch Studio Workspace
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/signin">
              <Button
                variant="outline"
                size="lg"
                className="h-12 border-white/15 bg-transparent px-8 text-zinc-200 hover:bg-white/5 hover:text-white"
              >
                Sign In
              </Button>
            </Link>
          </div>
          <p className="mt-4 font-mono text-sm text-zinc-500">
            PDF · TXT · MD · DOCX · Multi-File Intake
          </p>
        </section>

        {/* ── METRICS SECTION ───────────────────────────── */}
        <section className="border-y border-white/10 bg-zinc-900/30">
          <div className="container mx-auto px-4 py-16 sm:px-6">
            <div className="mx-auto grid max-w-5xl items-center gap-12 md:grid-cols-2">
              <div>
                <h2 className="mb-4 font-display text-2xl font-bold tracking-tight text-white">
                  Enterprise-grade Infrastructure
                </h2>
                <p className="mb-6 text-zinc-400">
                  Built on a highly optimized foundation combining dense vector embeddings with sparse keyword search and a knowledge graph core.
                </p>
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${telemetry ? "bg-emerald-400 animate-pulse" : "bg-zinc-600"}`} />
                  <span className="text-sm font-medium text-zinc-300">System Architecture Telemetry</span>
                  <Badge variant={telemetry ? "success" : "secondary"} className="ml-2">
                    {telemetry ? "ACTIVE" : "OFFLINE"}
                  </Badge>
                </div>
              </div>

              <Card className="border-white/10 bg-zinc-950/80 p-6">
                <div className="space-y-4 text-sm font-medium">
                  <SpecRow label="Retrieval Fusion" value="Vector × BM25 × Graph" />
                  <SpecRow label="Graph Extraction" value="Louvain Community Detection" />
                  <SpecRow label="Streaming" value="SSE Keep-Alive Heartbeat" />
                  <SpecRow label="Citations" value="Passage-Level Numerics" />
                  <SpecRow label="Requests Served" value={totalRequests.toLocaleString()} />
                  <SpecRow label="Mean Latency" value={avgLatency} />
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* ── INSTRUMENTS GRID ───────────────────────────── */}
        <section className="container mx-auto px-4 py-24 sm:px-6">
          <div className="mb-12">
            <h2 className="mb-4 font-display text-3xl font-bold tracking-tight text-white">Studio Instruments</h2>
            <p className="max-w-2xl text-lg text-zinc-400">
              Four integrated tools designed for comprehensive document analysis.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {INSTRUMENTS.map((it) => (
              <Card
                key={it.title}
                className="flex flex-col border-white/10 bg-zinc-950/80 p-6 transition-colors hover:border-white/30"
              >
                <div className="mb-4">
                  <Badge variant="default" className="mb-4">{it.badge}</Badge>
                  <h3 className="mb-2 text-lg font-semibold text-white">{it.title}</h3>
                  <p className="text-sm leading-relaxed text-zinc-400">{it.body}</p>
                </div>
                <div className="mt-auto pt-6">
                  <span className="font-mono text-xs font-medium text-zinc-500">{it.meta}</span>
                </div>
              </Card>
            ))}
          </div>
        </section>
      </main>

      {/* ── FOOTER ───────────────────────────────────────────── */}
      <footer className="border-t border-white/10 bg-zinc-900/20">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-6">
          <p className="text-sm text-zinc-500">
            DocuMind AI · Hybrid GraphRAG System
          </p>
          <p className="text-sm text-zinc-500">
            © {new Date().getFullYear()} · All rights reserved
          </p>
        </div>
      </footer>
    </div>
  );
}


const INSTRUMENTS = [
  {
    title: "Query Console",
    body: "Ask anything. Answers stream live with numbered citations linked to source passages.",
    meta: "Chat · Cited · Streaming",
    badge: "RAG",
  },
  {
    title: "Summary Studio",
    body: "Topical synthesis & executive breakdowns with word counts and 1-click Markdown export.",
    meta: "Executive · Markdown",
    badge: "SUMMARY",
  },
  {
    title: "Quiz Arena",
    body: "Volume-adaptive multiple choice quizzes with instant evidence callouts & difficulty filters.",
    meta: "Adaptive · Interactive",
    badge: "QUIZ",
  },
  {
    title: "Knowledge Atlas",
    body: "Interactive map of document entities, relationship edges, and Louvain community subgraphs.",
    meta: "Force-Graph · Louvain",
    badge: "GRAPH",
  },
];

function SpecRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <span className="text-zinc-500">{label}</span>
      <span className="text-right font-medium text-zinc-200">{value}</span>
    </div>
  );
}
