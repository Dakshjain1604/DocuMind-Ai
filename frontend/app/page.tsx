import Link from "next/link";
import { ArrowRight, Cpu, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100 overflow-x-hidden selection:bg-indigo-500/30">
      {/* ── FLOATING GLASS HEADER ─────────────────────────────── */}
      <header className="fixed top-4 inset-x-0 z-50 mx-auto max-w-6xl px-4">
        <div className="glass-panel rounded-2xl flex items-center justify-between px-6 py-3.5 shadow-2xl backdrop-blur-xl border border-white/10 bg-zinc-950/70">
          <div className="flex items-center gap-3">
            <span className="h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse" />
            <span className="font-display text-xl font-bold tracking-tight text-white">
              Docu<span className="gradient-accent-text">Mind</span>
            </span>
            <Badge variant="secondary" className="hidden sm:inline-flex">
              GraphRAG v2.4
            </Badge>
          </div>

          <nav className="flex items-center gap-3">
            <Link href="/signin">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/Dashboard">
              <Button size="sm" className="gap-2">
                <span>Launch Studio</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* ── HERO SECTION ─────────────────────────────────────── */}
      <main className="mx-auto max-w-6xl px-6 pt-32 pb-24 sm:px-8 lg:pt-40 lg:pb-32 space-y-28">
        <section className="grid items-center gap-12 lg:grid-cols-[1.3fr_1fr]">
          <div className="space-y-8">
            <Badge variant="default" className="gap-2 px-4 py-1.5 text-xs">
              <Cpu className="h-3.5 w-3.5 text-indigo-400" />
              <span>Hybrid Vector × BM25 × Knowledge Graph Engine</span>
            </Badge>

            <h1 className="display-xl font-bold tracking-tight text-white">
              Read documents with <br />
              <span className="gradient-accent-text">cartographic precision.</span>
            </h1>

            <p className="max-w-[56ch] font-sans text-lg leading-relaxed text-zinc-300">
              DocuMind extracts knowledge entities, draws Louvain community relationships,
              and streams answers backed by verifiable passage-level citations.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link href="/Dashboard">
                <Button size="lg" className="gap-2 text-sm shadow-xl shadow-indigo-600/30">
                  <span>Launch Studio Workspace</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/signin">
                <Button variant="outline" size="lg" className="text-sm">
                  Sign In
                </Button>
              </Link>
              <span className="font-mono text-xs text-zinc-500 w-full sm:w-auto">
                PDF · TXT · MD · DOCX · Multi-File Intake
              </span>
            </div>
          </div>

          {/* Telemetry Specimen Card */}
          <Card className="p-7 space-y-6 relative overflow-hidden group">
            <div className="absolute -top-24 -right-24 h-48 w-48 bg-indigo-500/15 rounded-full blur-3xl group-hover:bg-indigo-500/25 transition-all" />

            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="font-mono text-xs uppercase tracking-wider text-zinc-400 font-semibold flex items-center gap-1.5">
                  <Activity className="h-3.5 w-3.5 text-emerald-400" />
                  System Architecture Telemetry
                </span>
              </div>
              <Badge variant="success">ACTIVE</Badge>
            </div>

            <div className="grid gap-3.5 font-mono text-xs">
              <SpecRow label="Retrieval Fusion" value="Vector × BM25 × Graph (RRF)" />
              <SpecRow label="GPU Embeddings" value="nvidia/nv-embedqa-e5-v5 (1.4s)" />
              <SpecRow label="Primary LLM" value="NVIDIA NIM · Llama 3.1 8B" />
              <SpecRow label="Graph Extraction" value="Louvain Community Detection" />
              <SpecRow label="Streaming" value="SSE Keep-Alive Heartbeat (2s)" />
              <SpecRow label="Citations" value="Passage-Level Numbered Chips" />
            </div>

            <div className="pt-3 border-t border-white/10 flex items-center justify-between font-mono text-[10px] text-zinc-500">
              <span>Latency: &lt;1.8s per turn</span>
              <span>Obsidian Zinc · MMXXVI</span>
            </div>
          </Card>
        </section>

        {/* ── INSTRUMENTS BENTO GRID ───────────────────────────── */}
        <section className="space-y-8">
          <div className="border-b border-white/10 pb-4 flex items-center justify-between">
            <div className="font-mono text-xs uppercase tracking-widest text-zinc-400 font-semibold">
              02 / Studio Instruments
            </div>
            <span className="text-indigo-400 font-mono text-xs">4 Integrated Plates</span>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {INSTRUMENTS.map((it, i) => (
              <Card key={it.title} className="p-7 flex flex-col justify-between space-y-6 group">
                <div>
                  <div className="flex items-center justify-between font-mono text-[10px] text-zinc-500 uppercase tracking-wider">
                    <span>Plate {ROMAN[i]}</span>
                    <Badge variant="default">{it.badge}</Badge>
                  </div>
                  <h3 className="mt-4 font-display text-2xl font-bold text-white group-hover:text-indigo-300 transition-colors">
                    {it.title}
                  </h3>
                  <p className="mt-2.5 font-sans text-sm leading-relaxed text-zinc-400">
                    {it.body}
                  </p>
                </div>
                <div className="pt-4 border-t border-white/10 font-mono text-xs text-zinc-500 group-hover:text-indigo-400 transition-colors">
                  {it.meta}
                </div>
              </Card>
            ))}
          </div>
        </section>
      </main>

      {/* ── FOOTER ───────────────────────────────────────────── */}
      <footer className="border-t border-white/10 bg-zinc-950/80 mt-auto">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-6 font-mono text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
          <span>DocuMind AI · Hybrid GraphRAG System</span>
          <span>© MMXXVI · All rights reserved</span>
        </div>
      </footer>
    </div>
  );
}

const ROMAN = ["I", "II", "III", "IV"];

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
    <div className="flex items-center justify-between gap-4">
      <span className="text-zinc-400 uppercase tracking-wider">{label}</span>
      <span className="text-zinc-200 font-medium text-right">{value}</span>
    </div>
  );
}
