import Link from "next/link";

/* ───────────────────────────────────────────────────────────────
   Landing — editorial atlas, professional & minimal.
   Restrained sibling of the Dashboard hero. Bodoni statement,
   monospace metadata, vermillion as the only chromatic accent.
   ─────────────────────────────────────────────────────────────── */

export default function Home() {
  return (
    <div className="relative min-h-screen">
      {/* ── MASTHEAD ─────────────────────────────────────────── */}
      <header className="border-b border-[var(--rule)]">
        <div className="mx-auto flex max-w-[1380px] items-center justify-between px-6 py-5 sm:px-12">
          <div className="flex items-baseline gap-5">
            <span className="font-display text-[20px] tracking-[-0.01em] text-[var(--paper)]">
              Docu<span className="font-display-italic text-[var(--vermillion)]">·</span>Mind
            </span>
            <span className="hidden font-mono-cap text-[10px] text-[var(--paper-3)]/45 md:inline">
              hybrid graphrag · vol. i · no. 01
            </span>
          </div>

          <nav className="flex items-center gap-2">
            <Link
              href="/signin"
              className="instrument px-4 py-2 font-mono-cap text-[11px] text-[var(--paper-3)]/75 hover:text-[var(--paper)]"
            >
              sign in
            </Link>
            <Link
              href="/signup"
              className="instrument border border-[var(--paper)] bg-[var(--paper)] px-4 py-2 font-mono-cap text-[11px] text-[var(--ink)] hover:bg-[var(--vermillion)] hover:border-[var(--vermillion)] hover:text-[var(--ink)]"
            >
              get started →
            </Link>
          </nav>
        </div>
      </header>

      {/* ── HERO ─────────────────────────────────────────────── */}
      <main className="mx-auto max-w-[1380px] px-6 sm:px-12">
        <section className="grid items-end gap-12 pt-20 pb-24 lg:grid-cols-[1.5fr_1fr] lg:pt-28 lg:pb-28">
          <div>
            <div
              className="reveal mb-7 inline-flex items-center gap-3 border border-[var(--rule)] px-3 py-1.5 font-mono-cap text-[10px] text-[var(--paper-3)]/65"
              style={{ animationDelay: "60ms" }}
            >
              <span className="ticker-dot text-[var(--vermillion)]">●</span>
              vector × bm25 × knowledge graph
            </div>

            <h1
              className="reveal display-xl text-[var(--paper)]"
              style={{ animationDelay: "120ms" }}
            >
              Read documents
              <br />
              the way a cartographer
              <br />
              reads <span className="font-display-italic text-[var(--vermillion)]">a continent.</span>
            </h1>

            <p
              className="reveal mt-7 max-w-[58ch] font-display-italic text-[clamp(18px,1.6vw,22px)] leading-[1.45] text-[var(--paper-3)]/85"
              style={{ animationDelay: "260ms" }}
            >
              DocuMind extracts the entities of a document, draws their relationships,
              and answers questions with citations you can trace back to the source.
            </p>

            <div
              className="reveal mt-9 flex flex-wrap items-center gap-3"
              style={{ animationDelay: "380ms" }}
            >
              <Link
                href="/signup"
                className="instrument inline-flex items-center gap-3 bg-[var(--vermillion)] px-6 py-3.5 font-mono-cap text-[12px] text-[var(--ink)] hover:bg-[var(--vermillion-hot)]"
              >
                begin a session
                <span className="font-sans text-[16px] leading-none">→</span>
              </Link>
              <Link
                href="/signin"
                className="instrument inline-flex items-center gap-3 border border-[var(--rule-hot)] px-6 py-3.5 font-mono-cap text-[12px] text-[var(--paper)] hover:border-[var(--paper)]"
              >
                sign in
              </Link>
              <span className="ml-1 font-mono-cap text-[10px] text-[var(--paper-3)]/45">
                pdf · txt · md · docx · up to 100 mb
              </span>
            </div>
          </div>

          {/* Spec panel — small typographic facts */}
          <aside
            className="reveal regmark border border-[var(--rule)] bg-[var(--ink-1)] p-7"
            style={{ animationDelay: "500ms" }}
          >
            <span className="rm-tr" aria-hidden />
            <span className="rm-bl" aria-hidden />
            <div className="mb-5 flex items-baseline justify-between border-b border-[var(--rule)] pb-3 font-mono-cap text-[10px] text-[var(--paper-3)]/55">
              <span>specimen sheet</span>
              <span className="text-[var(--vermillion)]">·</span>
            </div>

            <dl className="grid gap-y-3 font-mono text-[11px] tabular-nums">
              <Spec label="retrieval" value="vector × bm25 × graph" />
              <Spec label="fusion" value="reciprocal rank · k=60" />
              <Spec label="embeddings" value="bge-small · local" />
              <Spec label="reasoning" value="openrouter · multi-model" />
              <Spec label="streaming" value="server-sent events" />
              <Spec label="citations" value="passage-level · numbered" />
            </dl>

            <div className="mt-6 border-t border-[var(--rule)] pt-5 font-mono-cap text-[10px] text-[var(--paper-3)]/45">
              composed in ink &amp; paper · mmxxvi
            </div>
          </aside>
        </section>

        {/* ── 02 · INSTRUMENTS ─────────────────────────────── */}
        <SectionRule index="02" title="instruments at the desk" />

        <section className="mt-8 mb-24 grid gap-4 sm:grid-cols-3">
          {INSTRUMENTS.map((it, i) => (
            <article
              key={it.title}
              className="instrument group flex h-full flex-col justify-between border border-[var(--rule)] bg-[var(--ink-1)] p-7 hover:border-[var(--vermillion)] hover:bg-[var(--ink-2)]"
            >
              <div>
                <div className="flex items-center justify-between font-mono-cap text-[10px] text-[var(--paper-3)]/55">
                  <span>plate · {ROMAN[i]}</span>
                  <span className="text-[var(--vermillion)]">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <h3 className="mt-6 font-display text-[34px] leading-[1] tracking-[-0.02em] text-[var(--paper)]">
                  {it.title}
                </h3>
                <p className="mt-4 font-sans text-[14px] leading-[1.55] text-[var(--paper-3)]/70">
                  {it.body}
                </p>
              </div>
              <div className="mt-7 border-t border-[var(--rule)] pt-3 font-mono-cap text-[10.5px] text-[var(--paper-3)]/55 transition-colors group-hover:text-[var(--vermillion)]">
                {it.meta}
              </div>
            </article>
          ))}
        </section>

        {/* ── 03 · METHOD ──────────────────────────────────── */}
        <SectionRule index="03" title="the method, in three movements" />

        <section className="mb-28 mt-8 grid gap-x-12 gap-y-10 sm:grid-cols-3">
          {METHOD.map((m, i) => (
            <div key={m.title} className="flex flex-col">
              <div className="flex items-baseline gap-3 border-b border-[var(--rule)] pb-3">
                <span className="font-display text-[44px] leading-[0.9] text-[var(--vermillion)]">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/45">
                  movement {ROMAN[i].toLowerCase()}
                </span>
              </div>
              <h4 className="mt-5 font-display text-[22px] leading-[1.15] text-[var(--paper)]">
                {m.title}
              </h4>
              <p className="mt-3 font-sans text-[14.5px] leading-[1.6] text-[var(--paper-3)]/75">
                {m.body}
              </p>
            </div>
          ))}
        </section>

        {/* ── 04 · CLOSING NOTE ────────────────────────────── */}
        <section className="mb-28 border-t border-[var(--rule)] pt-14">
          <div className="grid items-end gap-10 sm:grid-cols-[2fr_1fr]">
            <p className="font-display-italic text-[clamp(28px,4.2vw,52px)] leading-[1.05] text-[var(--paper)]">
              An instrument of attention.
              <br />
              A method for reading more.
            </p>
            <div className="flex sm:justify-end">
              <Link
                href="/signup"
                className="instrument inline-flex items-center gap-3 border border-[var(--paper)] bg-transparent px-7 py-3.5 font-mono-cap text-[12px] text-[var(--paper)] hover:bg-[var(--paper)] hover:text-[var(--ink)]"
              >
                begin a session →
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--rule)]">
        <div className="mx-auto flex max-w-[1380px] flex-col gap-2 px-6 py-7 font-mono-cap text-[10px] text-[var(--paper-3)]/45 sm:flex-row sm:items-center sm:justify-between sm:px-12">
          <span>DocuMind · hybrid graphrag · vector × bm25 × graph</span>
          <span className="text-[var(--paper-3)]/35">© mmxxvi · all marks reserved</span>
        </div>
      </footer>
    </div>
  );
}

/* ── data ─────────────────────────────────────────────────────── */

const ROMAN = ["I", "II", "III", "IV"];

const INSTRUMENTS = [
  {
    title: "Console",
    body: "Ask anything. Answers stream live, each claim chipped with a numbered citation back to the source passage.",
    meta: "chat · cited · streaming",
  },
  {
    title: "Atlas",
    body: "An interactive map of the document's entities, their relationships, and the communities they form.",
    meta: "graph · force-directed",
  },
  {
    title: "Précis",
    body: "Concise summaries and twelve-question quizzes, ranked from easy to hard, drawn from your indexed corpus.",
    meta: "summary · quiz",
  },
];

const METHOD = [
  {
    title: "Submit a document.",
    body: "PDF, plaintext, markdown or Word — up to 100 MB. The intake clerk chunks, embeds and stores it locally.",
  },
  {
    title: "Draw the cartography.",
    body: "Entities and relationships are extracted in parallel; Louvain partitions the graph into topical communities.",
  },
  {
    title: "Read with citations.",
    body: "Vector, BM25 and graph traversal fuse via reciprocal rank — every answer is annotated with its sources.",
  },
];

/* ── tiny primitives ─────────────────────────────────────────── */

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-6">
      <dt className="uppercase tracking-[0.18em] text-[var(--paper-3)]/45">{label}</dt>
      <dd className="text-right text-[var(--paper)]/85">{value}</dd>
    </div>
  );
}

function SectionRule({ index, title }: { index: string; title: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-[var(--rule)] pb-3">
      <div className="font-mono-cap text-[11px] text-[var(--paper-3)]/55">
        <span className="text-[var(--vermillion)]">{index}</span>
        <span className="mx-3 text-[var(--paper-3)]/30">/</span>
        <span>{title}</span>
      </div>
    </div>
  );
}
