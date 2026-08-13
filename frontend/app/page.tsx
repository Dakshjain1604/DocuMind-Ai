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
    <div className="flex flex-col min-h-screen">
      {/* ── HEADER ─────────────────────────────── */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-lg tracking-tight">
              DocuMind
            </span>
            <Badge variant="secondary" className="hidden sm:inline-flex rounded-sm">
              GraphRAG v2.4
            </Badge>
          </div>

          <nav className="flex items-center gap-4">
            <Link href="/signin" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Sign In
            </Link>
            <Link href="/Dashboard">
              <Button size="sm" className="gap-2">
                Launch Studio
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* ── HERO SECTION ─────────────────────────────────────── */}
      <main className="flex-1">
        <section className="container mx-auto px-4 py-24 sm:px-6 lg:py-32 flex flex-col items-center text-center space-y-10">
          <Badge variant="outline" className="px-3 py-1 rounded-full gap-2">
            <Cpu className="h-4 w-4" />
            Hybrid Vector × BM25 × Knowledge Graph Engine
          </Badge>

          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl max-w-3xl">
            Read documents with <br className="hidden sm:inline" />
            cartographic precision.
          </h1>

          <p className="max-w-[42rem] leading-normal text-muted-foreground sm:text-xl sm:leading-8">
            DocuMind extracts knowledge entities, draws Louvain community relationships,
            and streams answers backed by verifiable passage-level citations.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Link href="/Dashboard">
              <Button size="lg" className="h-12 px-8 gap-2">
                Launch Studio Workspace
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/signin">
              <Button variant="outline" size="lg" className="h-12 px-8">
                Sign In
              </Button>
            </Link>
          </div>
          <p className="text-sm text-muted-foreground mt-4">
            PDF · TXT · MD · DOCX · Multi-File Intake
          </p>
        </section>

        {/* ── METRICS SECTION ───────────────────────────── */}
        <section className="border-y bg-muted/30">
          <div className="container mx-auto px-4 py-16 sm:px-6">
            <div className="grid md:grid-cols-2 gap-12 items-center max-w-5xl mx-auto">
              <div>
                <h2 className="text-2xl font-bold tracking-tight mb-4">Enterprise-grade Infrastructure</h2>
                <p className="text-muted-foreground mb-6">
                  Built on a highly optimized foundation combining dense vector embeddings with sparse keyword search and a knowledge graph core.
                </p>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-sm font-medium">System Architecture Telemetry</span>
                  <Badge variant="outline" className="ml-2 font-mono text-xs rounded-sm">
                    {telemetry ? "ACTIVE" : "OFFLINE"}
                  </Badge>
                </div>
              </div>

              <Card className="p-6">
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
            <h2 className="text-3xl font-bold tracking-tight mb-4">Studio Instruments</h2>
            <p className="text-muted-foreground max-w-2xl text-lg">
              Four integrated tools designed for comprehensive document analysis.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {INSTRUMENTS.map((it) => (
              <Card key={it.title} className="flex flex-col p-6 hover:shadow-md transition-shadow">
                <div className="mb-4">
                  <Badge variant="secondary" className="mb-4 rounded-sm">{it.badge}</Badge>
                  <h3 className="font-semibold text-lg mb-2">{it.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{it.body}</p>
                </div>
                <div className="mt-auto pt-6">
                  <span className="text-xs font-medium text-muted-foreground">{it.meta}</span>
                </div>
              </Card>
            ))}
          </div>
        </section>
      </main>

      {/* ── FOOTER ───────────────────────────────────────────── */}
      <footer className="border-t bg-muted/20">
        <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 py-8 px-4 sm:px-6">
          <p className="text-sm text-muted-foreground">
            DocuMind AI · Hybrid GraphRAG System
          </p>
          <p className="text-sm text-muted-foreground">
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
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground font-medium text-right">{value}</span>
    </div>
  );
}
