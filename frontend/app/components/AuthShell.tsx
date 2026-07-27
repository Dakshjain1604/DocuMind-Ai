"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ShieldCheck, Lock, CheckCircle2 } from "lucide-react";

export function AuthShell({
  kicker,
  heading,
  sub,
  children,
  footer,
}: {
  kicker: string;
  heading: string;
  sub: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-indigo-500/30">
      <header className="border-b border-white/10 bg-zinc-950/80 backdrop-blur-xl px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse" />
            <span className="font-display text-xl font-bold tracking-tight text-white">
              Docu<span className="gradient-accent-text">Mind</span>
            </span>
          </Link>
          <Badge variant="secondary">{kicker}</Badge>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl items-start gap-12 px-6 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1.05fr_1fr] flex-1 w-full">
        <aside className="hidden flex-col gap-6 lg:flex">
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-indigo-400 font-semibold">
            <ShieldCheck className="h-4 w-4" />
            <span>Enterprise Knowledge Workspace</span>
          </div>
          <h1 className="display-xl text-white font-bold">{heading}</h1>
          <p className="max-w-[44ch] font-sans text-lg leading-relaxed text-zinc-300">
            {sub}
          </p>

          {/* Each of these describes something the code actually does. The
              previous copy claimed zero-knowledge encryption and SOC2/HIPAA
              compliance, none of which is true of this system. */}
          <ul className="mt-4 grid gap-3 font-sans text-sm text-zinc-300">
            <FeatureRow
              title="Hybrid Retrieval Fusion"
              description="Vector search, BM25 and knowledge-graph traversal run in parallel and are merged with reciprocal rank fusion."
            />
            <FeatureRow
              title="Passage-Level Verifiable Citations"
              description="Every answer streams with source chips linked back to the exact chunks it was built from."
            />
            <FeatureRow
              title="Per-Request Trace Store"
              description="Each request records its stage latencies, token counts and retrieved context to a queryable trace."
            />
          </ul>
        </aside>

        <section className="glass-panel rounded-2xl border border-white/10 bg-zinc-950/80 p-8 sm:p-10 shadow-2xl backdrop-blur-xl">
          <div className="mb-6 lg:hidden">
            <Badge variant="default" className="mb-2">{kicker}</Badge>
            <h1 className="font-display text-3xl font-bold text-white">
              {heading}
            </h1>
            <p className="mt-2 font-sans text-sm text-zinc-400">
              {sub}
            </p>
          </div>

          <div className="mb-6 hidden items-center justify-between border-b border-white/10 pb-3 font-mono text-xs uppercase tracking-wider text-zinc-400 font-semibold lg:flex">
            <span>Secure Authentication</span>
            <Lock className="h-3.5 w-3.5 text-indigo-400" />
          </div>

          {children}

          {footer && (
            <div className="mt-6 border-t border-white/10 pt-4 font-mono text-xs text-zinc-400">
              {footer}
            </div>
          )}
        </section>
      </main>

      <footer className="border-t border-white/10 bg-zinc-950 py-6 px-6 font-mono text-xs text-zinc-500 mt-auto">
        <div className="mx-auto max-w-6xl text-center sm:text-left">
          DocuMind AI · Hybrid GraphRAG Enterprise Platform
        </div>
      </footer>
    </div>
  );
}

export function AuthField({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block space-y-2">
      <span className="block font-mono text-xs uppercase tracking-wider text-zinc-400 font-semibold">
        {label}
      </span>
      <Input {...props} />
    </label>
  );
}

function FeatureRow({ title, description }: { title: string; description: string }) {
  return (
    <li className="flex items-start gap-3 rounded-xl border border-white/5 bg-zinc-900/50 p-4 transition-colors hover:border-indigo-500/30">
      <CheckCircle2 className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
      <div>
        <div className="font-semibold text-white text-sm">{title}</div>
        <div className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{description}</div>
      </div>
    </li>
  );
}
