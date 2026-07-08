"use client";

import Link from "next/link";

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
    <div className="relative min-h-screen">
      <header className="border-b border-[var(--rule)]">
        <div className="mx-auto flex max-w-[1380px] items-center justify-between px-6 py-5 sm:px-12">
          <Link
            href="/"
            className="font-display text-[20px] tracking-[-0.01em] text-[var(--paper)] hover:text-[var(--vermillion)]"
          >
            Docu<span className="font-display-italic text-[var(--vermillion)]">·</span>Mind
          </Link>
          <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/55">
            {kicker}
          </span>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1380px] items-start gap-12 px-6 py-16 sm:px-12 sm:py-24 lg:grid-cols-[1.05fr_1fr]">
        <aside className="hidden flex-col gap-6 lg:flex">
          <span className="font-mono-cap text-[10.5px] text-[var(--paper-3)]/45">
            ── DocuMind · session console
          </span>
          <h1 className="display-xl text-[var(--paper)]">{heading}</h1>
          <p className="max-w-[44ch] font-display-italic text-[clamp(18px,1.5vw,22px)] leading-[1.45] text-[var(--paper-3)]/75">
            {sub}
          </p>

          <ul className="mt-4 grid gap-2 font-mono text-[11px] tabular-nums">
            <ShellSpec label="auth" value="bcrypt · jwt cookie" />
            <ShellSpec label="session" value="signed · http-only" />
            <ShellSpec label="transport" value="https · sse" />
          </ul>
        </aside>

        <section className="regmark border border-[var(--rule)] bg-[var(--ink-1)] p-8 sm:p-10">
          <span className="rm-tr" aria-hidden />
          <span className="rm-bl" aria-hidden />

          <div className="mb-7 lg:hidden">
            <span className="font-mono-cap text-[10.5px] text-[var(--paper-3)]/45">
              ── session console
            </span>
            <h1 className="mt-3 font-display text-[40px] leading-[0.95] text-[var(--paper)]">
              {heading}
            </h1>
            <p className="mt-3 font-display-italic text-[16px] leading-[1.5] text-[var(--paper-3)]/70">
              {sub}
            </p>
          </div>

          <div className="mb-7 hidden items-baseline justify-between border-b border-[var(--rule)] pb-3 font-mono-cap text-[10px] text-[var(--paper-3)]/55 lg:flex">
            <span>credentials</span>
            <span className="text-[var(--vermillion)]">·</span>
          </div>

          {children}

          {footer && (
            <p className="mt-7 border-t border-[var(--rule)] pt-5 font-mono-cap text-[10.5px] text-[var(--paper-3)]/55">
              {footer}
            </p>
          )}
        </section>
      </main>

      <footer className="border-t border-[var(--rule)]">
        <div className="mx-auto px-6 py-7 font-mono-cap text-[10px] text-[var(--paper-3)]/40 sm:px-12">
          DocuMind · hybrid graphrag · vector × bm25 × graph
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
    <label className="block">
      <span className="block font-mono-cap text-[10px] text-[var(--paper-3)]/55">
        {label}
      </span>
      <input
        {...props}
        className="mt-2 w-full border border-[var(--rule)] bg-[var(--ink)] px-4 py-3 font-mono text-[13.5px] tracking-[0.01em] text-[var(--paper)] placeholder:text-[var(--paper-3)]/30 focus:border-[var(--vermillion)] focus:outline-none"
      />
    </label>
  );
}

function ShellSpec({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-baseline justify-between gap-6">
      <span className="uppercase tracking-[0.18em] text-[var(--paper-3)]/45">
        {label}
      </span>
      <span className="text-right text-[var(--paper)]/80">{value}</span>
    </li>
  );
}
