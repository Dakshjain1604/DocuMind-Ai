"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ShieldCheck, Lock, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";

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
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 selection:bg-white/20">
      <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-zinc-950/80 px-6 py-4 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="h-3 w-3 rounded-full bg-white animate-pulse" />
            <span className="font-display text-lg font-bold tracking-tight text-white">
              Docu<span className="gradient-accent-text">Mind</span>
            </span>
          </Link>
          <Badge variant="secondary">{kicker}</Badge>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 items-start gap-12 px-6 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1.05fr_1fr]">
        <aside className="hidden flex-col gap-6 lg:flex">
          <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-zinc-400">
            <ShieldCheck className="h-4 w-4" />
            <span>Enterprise Knowledge Workspace</span>
          </div>
          <h1 className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">{heading}</h1>
          <p className="max-w-[44ch] text-lg leading-relaxed text-zinc-400">
            {sub}
          </p>

          <ul className="mt-4 grid gap-3 text-sm text-zinc-400">
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

        <Card className="border-white/10 bg-zinc-950/80 p-8 shadow-xl sm:p-10">
          <div className="mb-6 lg:hidden">
            <Badge variant="outline" className="mb-2">{kicker}</Badge>
            <h1 className="font-display text-3xl font-bold tracking-tight text-white">
              {heading}
            </h1>
            <p className="mt-2 text-sm text-zinc-400">
              {sub}
            </p>
          </div>

          <div className="mb-6 hidden items-center justify-between border-b border-white/10 pb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400 lg:flex">
            <span>Secure Authentication</span>
            <Lock className="h-3.5 w-3.5" />
          </div>

          {children}

          {footer && (
             <div className="mt-6 border-t border-white/10 pt-4 text-xs text-zinc-500">
              {footer}
            </div>
          )}
        </Card>
      </main>

      <footer className="mt-auto border-t border-white/10 bg-zinc-900/20 px-6 py-6 text-xs text-zinc-500">
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
      <span className="block text-sm font-medium text-zinc-300">
        {label}
      </span>
      <Input {...props} />
    </label>
  );
}

function FeatureRow({ title, description }: { title: string; description: string }) {
  return (
    <li className="flex items-start gap-3 rounded-xl border border-white/10 bg-zinc-900/40 p-4 transition-colors hover:bg-zinc-900/70">
      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-zinc-400" />
      <div>
        <div className="text-sm font-semibold text-white">{title}</div>
        <div className="mt-0.5 text-xs leading-relaxed text-zinc-500">{description}</div>
      </div>
    </li>
  );
}
