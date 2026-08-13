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
    <div className="flex flex-col min-h-screen">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-semibold text-lg tracking-tight">
              DocuMind
            </span>
          </Link>
          <Badge variant="secondary">{kicker}</Badge>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl items-start gap-12 px-6 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1.05fr_1fr] flex-1 w-full">
        <aside className="hidden flex-col gap-6 lg:flex">
          <div className="flex items-center gap-2 text-sm uppercase tracking-wider text-muted-foreground font-semibold">
            <ShieldCheck className="h-4 w-4" />
            <span>Enterprise Knowledge Workspace</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">{heading}</h1>
          <p className="max-w-[44ch] text-lg leading-relaxed text-muted-foreground">
            {sub}
          </p>

          <ul className="mt-4 grid gap-3 text-sm text-muted-foreground">
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

        <Card className="p-8 sm:p-10 shadow-lg border">
          <div className="mb-6 lg:hidden">
            <Badge variant="outline" className="mb-2">{kicker}</Badge>
            <h1 className="text-3xl font-bold tracking-tight">
              {heading}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {sub}
            </p>
          </div>

          <div className="mb-6 hidden items-center justify-between border-b pb-3 text-xs uppercase tracking-wider text-muted-foreground font-semibold lg:flex">
            <span>Secure Authentication</span>
            <Lock className="h-3.5 w-3.5" />
          </div>

          {children}

          {footer && (
             <div className="mt-6 border-t pt-4 text-xs text-muted-foreground">
              {footer}
            </div>
          )}
        </Card>
      </main>

      <footer className="border-t bg-muted/20 py-6 px-6 text-xs text-muted-foreground mt-auto">
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
      <span className="block text-sm font-medium text-foreground">
        {label}
      </span>
      <Input {...props} />
    </label>
  );
}

function FeatureRow({ title, description }: { title: string; description: string }) {
  return (
    <li className="flex items-start gap-3 rounded-xl border bg-muted/30 p-4 transition-colors hover:bg-muted/50">
      <CheckCircle2 className="h-5 w-5 text-foreground shrink-0 mt-0.5" />
      <div>
        <div className="font-semibold text-foreground text-sm">{title}</div>
        <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{description}</div>
      </div>
    </li>
  );
}
