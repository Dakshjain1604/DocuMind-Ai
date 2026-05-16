"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import Markdown from "react-markdown";
import { Homecard } from "../components/HomeCard";
import { QuizCard } from "../components/QuizCard";
import { ChatStream } from "../components/ChatStream";
import { GraphView } from "../components/GraphView";

type View = "quiz" | "summary" | "chat" | "graph" | "none";
type ProgressEvent = { stamp: string; label: string };

const NUMERALS = ["I", "II", "III", "IV"];

function shortHash(h: string | null): string {
  if (!h) return "—";
  return `${h.slice(0, 6)}…${h.slice(-4)}`;
}

function nowStamp() {
  const d = new Date();
  return `${d.getHours().toString().padStart(2, "0")}:${d
    .getMinutes()
    .toString()
    .padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

/* ── Small inline SVG glyphs (no emojis) ─────────────────────── */
function GlyphQuiz() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <rect x="4" y="6" width="32" height="28" stroke="currentColor" strokeWidth="1.2" />
      <path d="M10 14h12M10 20h20M10 26h16" stroke="currentColor" strokeWidth="1.2" strokeLinecap="square" />
      <circle cx="28" cy="14" r="2" fill="currentColor" />
    </svg>
  );
}
function GlyphSummary() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <path d="M8 6h18l6 6v22H8z" stroke="currentColor" strokeWidth="1.2" />
      <path d="M26 6v6h6" stroke="currentColor" strokeWidth="1.2" />
      <path d="M14 18h12M14 22h12M14 26h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="square" />
    </svg>
  );
}
function GlyphChat() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <path d="M6 8h28v18H16l-8 8V8z" stroke="currentColor" strokeWidth="1.2" />
      <path d="M12 14h16M12 19h11" stroke="currentColor" strokeWidth="1.2" strokeLinecap="square" />
    </svg>
  );
}
function GlyphGraph() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <circle cx="20" cy="8" r="3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="8" cy="26" r="3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="32" cy="26" r="3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="20" cy="34" r="3" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M19 11L10 24M21 11L30 24M10 28l9 5M30 28l-9 5"
        stroke="currentColor"
        strokeWidth="1.2"
      />
    </svg>
  );
}
function GlyphUpload() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
      <path d="M11 14V3M6 8l5-5 5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="square" />
      <path d="M3 17v2h16v-2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="square" />
    </svg>
  );
}

export default function Dashboard() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docHash, setDocHash] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [indexing, setIndexing] = useState(false);

  const [quiz, setQuiz] = useState<{ total_questions: number; cards: any[] } | null>(null);
  const [summary, setSummary] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<View>("none");
  const [highlightChunk, setHighlightChunk] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const tickerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (tickerRef.current) {
      tickerRef.current.scrollTop = tickerRef.current.scrollHeight;
    }
  }, [progress.length]);

  const scrollToSection = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  function pushProgress(label: string) {
    setProgress((p) => [...p, { stamp: nowStamp(), label }]);
  }

  async function indexFile(file: File) {
    setIndexing(true);
    setError("");
    setDocHash(null);
    setQuiz(null);
    setSummary("");
    setView("none");
    setProgress([{ stamp: nowStamp(), label: `intake · ${file.name}` }]);

    const fd = new FormData();
    fd.append("file", file);

    try {
      const r = await fetch("/api/rag/index", { method: "POST", body: fd });
      if (!r.ok || !r.body) {
        const detail = await r.text().catch(() => "");
        setError(`Upload failed · ${r.status} · ${detail.slice(0, 200)}`);
        setIndexing(false);
        return;
      }
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const evs = buf.split("\n\n");
        buf = evs.pop() ?? "";
        for (const block of evs) {
          const lines = block.split("\n");
          const evtLine = lines.find((l) => l.startsWith("event:"));
          const dataLine = lines.find((l) => l.startsWith("data:"));
          if (!evtLine || !dataLine) continue;
          const evt = evtLine.replace("event:", "").trim();
          const data = JSON.parse(dataLine.replace("data:", "").trim());

          if (evt === "done") {
            setDocHash(data.doc_hash);
            const tag = data.cached ? "cached" : "indexed";
            const s = data.stats || {};
            pushProgress(
              `${tag} · ${s.n_chunks ?? "?"} chunks · ${s.n_entities ?? "?"} entities · ${
                s.n_edges ?? "?"
              } edges`
            );
          } else if (evt === "error") {
            setError(data.message ?? "Indexing error");
            pushProgress(`× ${data.message ?? "error"}`);
          } else {
            const label = evt.replace(/_/g, " ");
            const extra = data?.n_chunks
              ? ` · ${data.n_chunks} chunks`
              : data?.total
              ? ` · ${data.total} planned`
              : data?.n
              ? ` · ${data.n}`
              : "";
            pushProgress(`${label}${extra}`);
          }
        }
      }
    } catch (e) {
      setError(String(e));
      pushProgress(`× ${String(e)}`);
    } finally {
      setIndexing(false);
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    indexFile(file);
  };

  function guardHash(): boolean {
    if (!docHash) {
      setError("Index a document first");
      scrollToSection("intake");
      return false;
    }
    return true;
  }

  async function fetchQuiz() {
    if (!guardHash()) return;
    scrollToSection("plate");
    setIsLoading(true);
    setError("");
    setQuiz(null);
    setSummary("");
    setView("none");
    try {
      const r = await axios.post("/api/rag/quiz", { doc_hash: docHash });
      const cards = r.data?.data?.cards ?? [];
      setQuiz({
        total_questions: r.data?.data?.total_questions ?? cards.length,
        cards,
      });
      setView("quiz");
    } catch (e: any) {
      setError(e?.message ?? "Quiz failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchSummary() {
    if (!guardHash()) return;
    scrollToSection("plate");
    setIsLoading(true);
    setError("");
    setSummary("");
    setView("none");
    try {
      const r = await axios.post("/api/rag/summary", { doc_hash: docHash });
      setSummary(r.data?.summary ?? "");
      setView("summary");
    } catch (e: any) {
      setError(e?.message ?? "Summary failed");
    } finally {
      setIsLoading(false);
    }
  }

  function openChat() {
    if (!guardHash()) return;
    scrollToSection("plate");
    setView("chat");
  }
  function openGraph() {
    if (!guardHash()) return;
    scrollToSection("plate");
    setView("graph");
  }

  const indexed = !!docHash && !indexing;

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      {/* ════════════════════════════════════════════════════════
          MASTHEAD
          ════════════════════════════════════════════════════════ */}
      <header className="border-b border-[var(--rule)]">
        <div className="mx-auto flex max-w-[1480px] flex-wrap items-end justify-between gap-2 px-6 pb-4 pt-5 sm:px-12">
          <div className="flex items-baseline gap-5">
            <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/55">
              Vol. I · No. 01
            </span>
            <span className="hidden font-mono-cap text-[10px] text-[var(--paper-3)]/40 md:inline">
              hybrid graphrag · vector × bm25 × graph · mmxxvi
            </span>
          </div>
          <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/55">
            <span className="ticker-dot mr-2 text-[var(--vermillion)]">●</span>
            live transmission
          </span>
        </div>

        <div className="mx-auto max-w-[1480px] px-6 pb-12 pt-3 sm:px-12 sm:pb-16">
          <h1
            className="reveal display-mega text-[var(--paper)]"
            style={{ animationDelay: "60ms" }}
          >
            Docu
            <span className="font-display-italic text-[var(--vermillion)]">·</span>Mind
          </h1>

          <div
            className="reveal mt-6 grid max-w-[1200px] gap-x-12 gap-y-6 sm:grid-cols-[2fr_1fr]"
            style={{ animationDelay: "240ms" }}
          >
            <p className="font-display-italic text-[clamp(20px,2.2vw,30px)] leading-[1.35] text-[var(--paper-3)]">
              An instrument for reading documents the way a cartographer reads a continent —
              by extracting their entities, drawing their relationships, and answering
              questions with sources you can trace.
            </p>
            <ul className="space-y-2 self-end font-mono-cap text-[10.5px] text-[var(--paper-3)]/55">
              <Spec label="retrieval" value="vector × bm25 × graph" />
              <Spec label="fusion" value="reciprocal rank · k=60" />
              <Spec label="ground" value="openrouter · multi-model" />
              <Spec label="streaming" value="sse · server-sent events" />
            </ul>
          </div>
        </div>
      </header>

      {/* ════════════════════════════════════════════════════════
          MAIN
          ════════════════════════════════════════════════════════ */}
      <main className="mx-auto max-w-[1480px] px-6 py-16 sm:px-12 sm:py-20">
        {/* ── 01 · INTAKE STATION ───────────────────────────── */}
        <SectionLabel index="01" title="intake station" />

        <section id="intake" className="mb-24 mt-6 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          {/* Submit card */}
          <div className="regmark border border-[var(--rule)] bg-[var(--ink-1)] p-8 sm:p-10">
            <span className="rm-tr" aria-hidden />
            <span className="rm-bl" aria-hidden />

            <h2 className="display-xl text-[var(--paper)]">
              Submit a
              <br />
              <span className="font-display-italic text-[var(--vermillion)]">document.</span>
            </h2>

            <p className="mt-5 max-w-md font-sans text-[15px] leading-[1.55] text-[var(--paper-3)]/65">
              PDF, plaintext, markdown or Word. The intake clerk chunks, embeds, extracts
              entities, and draws the graph — all streamed live to the right.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={indexing}
                className="group/up inline-flex items-center gap-3 bg-[var(--vermillion)] px-5 py-3 font-mono-cap text-[12px] text-[var(--ink)] transition-all hover:bg-[var(--vermillion-hot)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <GlyphUpload />
                <span>choose file</span>
              </button>
              <input
                ref={fileInputRef}
                onChange={handleFileChange}
                type="file"
                accept=".pdf,.txt,.md,.doc,.docx"
                className="hidden"
                aria-label="Upload document"
              />
              <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/45">
                .pdf · .txt · .md · .docx
              </span>
            </div>

            {selectedFile && (
              <div className="mt-6 flex items-center border border-[var(--rule)] bg-[var(--ink)] px-4 py-3">
                <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/50">
                  file
                </span>
                <span className="mx-3 text-[var(--vermillion)]">/</span>
                <span className="truncate font-mono text-[12px] text-[var(--paper)]">
                  {selectedFile.name}
                </span>
              </div>
            )}

            {/* Manifest grid */}
            <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-3 border-t border-[var(--rule)] pt-6 font-mono text-[11px] tabular-nums">
              <Manifest label="status">
                {indexing ? (
                  <span className="text-[var(--ochre)]">
                    <span className="blink mr-1">▮</span> processing
                  </span>
                ) : indexed ? (
                  <span className="text-[var(--teal-pale)]">● indexed</span>
                ) : (
                  <span className="text-[var(--paper-3)]/40">○ awaiting</span>
                )}
              </Manifest>
              <Manifest label="doc · sha-256">
                <span className="text-[var(--paper)]">{shortHash(docHash)}</span>
              </Manifest>
              <Manifest label="size">
                <span className="text-[var(--paper)]">
                  {selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} kb` : "—"}
                </span>
              </Manifest>
              <Manifest label="last event">
                <span className="truncate text-[var(--paper)]">
                  {progress.length ? progress[progress.length - 1].label : "—"}
                </span>
              </Manifest>
            </dl>
          </div>

          {/* Telex ticker */}
          <div className="regmark flex flex-col border border-[var(--rule)] bg-[var(--ink)]">
            <span className="rm-tr" aria-hidden />
            <span className="rm-bl" aria-hidden />

            <div className="flex items-center justify-between border-b border-[var(--rule)] px-5 py-3 font-mono-cap text-[10px] text-[var(--paper-3)]/55">
              <span>02 · processing telex</span>
              {indexing ? (
                <span className="text-[var(--vermillion)]">
                  <span className="ticker-dot mr-1">●</span> transmitting
                </span>
              ) : (
                <span className="text-[var(--paper-3)]/40">○ idle</span>
              )}
            </div>

            <div
              ref={tickerRef}
              className="h-[340px] flex-1 overflow-y-auto px-5 py-4 font-mono text-[12px] leading-[1.85] text-[var(--paper-3)]/80"
              role="log"
              aria-live="polite"
              aria-label="Indexing progress log"
            >
              {progress.length === 0 ? (
                <div className="text-[var(--paper-3)]/30">
                  {"// no transmissions yet. upload a document to begin."}
                </div>
              ) : (
                progress.map((p, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-[var(--paper-3)]/40">{p.stamp}</span>
                    <span className="text-[var(--vermillion)]">›</span>
                    <span className="break-all">{p.label}</span>
                  </div>
                ))
              )}
              {indexing && (
                <div className="mt-1 flex gap-3">
                  <span className="text-[var(--paper-3)]/40">{nowStamp()}</span>
                  <span className="blink text-[var(--vermillion)]">▮</span>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── 03 · INSTRUMENT PANEL ─────────────────────────── */}
        <SectionLabel
          index="03"
          title="instrument panel"
          aside={indexed ? "all four plates available" : "indexing required"}
        />

        <section className="mb-24 mt-6">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {[
              {
                heading: "Quiz",
                body: "Twelve multiple-choice questions ranked easy → hard. For studying or self-assessment.",
                btn: "generate quiz",
                action: fetchQuiz,
                glyph: <GlyphQuiz />,
              },
              {
                heading: "Summary",
                body: "A chapter-by-chapter or topical synthesis. Concise, structured, ready to read.",
                btn: "compose summary",
                action: fetchSummary,
                glyph: <GlyphSummary />,
              },
              {
                heading: "Console",
                body: "Ask anything. Answers stream live with numbered citations back to the source passages.",
                btn: "open console",
                action: openChat,
                glyph: <GlyphChat />,
              },
              {
                heading: "Atlas",
                body: "An interactive map of the document's entities, relationships, and topical communities.",
                btn: "view atlas",
                action: openGraph,
                glyph: <GlyphGraph />,
              },
            ].map((card, i) => (
              <Homecard
                key={card.heading}
                heading={card.heading}
                mainText={card.body}
                ButtonText={card.btn}
                onClick={card.action}
                numeral={NUMERALS[i]}
                disabled={!indexed}
                glyph={card.glyph}
              />
            ))}
          </div>
        </section>

        {/* ── 04 · OUTPUT PLATE ─────────────────────────────── */}
        <SectionLabel
          index="04"
          title="output plate"
          aside={
            view === "none"
              ? "no plate selected"
              : view === "quiz"
              ? "plate · quiz"
              : view === "summary"
              ? "plate · summary"
              : view === "chat"
              ? "plate · console"
              : "plate · atlas"
          }
        />

        <section id="plate" className="mt-6">
          <div className="regmark min-h-[480px] border border-[var(--rule)] bg-[var(--ink-1)] p-6 sm:p-10">
            <span className="rm-tr" aria-hidden />
            <span className="rm-bl" aria-hidden />

            {isLoading && (
              <div
                className="flex h-[420px] items-center justify-center font-mono-cap text-[11px] text-[var(--paper-3)]/45"
                aria-live="polite"
              >
                <span className="ticker-dot mr-3 text-[var(--vermillion)]">●</span>
                rendering plate…
              </div>
            )}

            {!isLoading && error && (
              <div
                role="alert"
                className="border-l-2 border-[var(--vermillion)] bg-[var(--vermillion)]/10 px-5 py-4 font-mono text-[12px] uppercase tracking-[0.12em] text-[var(--vermillion-hot)]"
              >
                ✕ {error}
              </div>
            )}

            {!isLoading && !error && view === "none" && (
              <div className="flex h-[420px] flex-col items-center justify-center text-center">
                <div className="font-display-italic text-[clamp(40px,5.5vw,72px)] leading-[1] text-[var(--paper-3)]/25">
                  awaiting selection
                </div>
                <div className="mt-4 font-mono-cap text-[10px] text-[var(--paper-3)]/35">
                  pick an instrument above
                </div>
              </div>
            )}

            {!isLoading && view === "quiz" && quiz && quiz.cards.length > 0 && (
              <div className="space-y-6">
                <PlateHeader title="Quiz" trailing={`${quiz.total_questions} questions`} />
                <div className="grid gap-5">
                  {quiz.cards.map((card) => (
                    <QuizCard key={card.id} card={card} />
                  ))}
                </div>
              </div>
            )}

            {!isLoading && view === "summary" && summary && (
              <div className="space-y-5">
                <PlateHeader title="Summary" trailing={`doc · ${shortHash(docHash)}`} />
                <article className="prose prose-invert max-w-none font-display-italic text-[clamp(17px,1.4vw,21px)] leading-[1.65] text-[var(--paper)]">
                  <Markdown>{summary}</Markdown>
                </article>
              </div>
            )}

            {!isLoading && view === "chat" && docHash && (
              <div className="space-y-5">
                <PlateHeader
                  title="Console"
                  trailing={highlightChunk ? `chunk · ${highlightChunk}` : "ready"}
                />
                <ChatStream
                  docHash={docHash}
                  onCiteClick={(cid) => setHighlightChunk(String(cid))}
                />
              </div>
            )}

            {!isLoading && view === "graph" && docHash && <GraphView docHash={docHash} />}
          </div>
        </section>
      </main>

      {/* ════════════════════════════════════════════════════════
          FOOTER
          ════════════════════════════════════════════════════════ */}
      <footer className="border-t border-[var(--rule)]">
        <div className="mx-auto flex max-w-[1480px] flex-col gap-2 px-6 py-7 font-mono-cap text-[10px] text-[var(--paper-3)]/45 sm:flex-row sm:items-center sm:justify-between sm:px-12">
          <span>DocuMind · hybrid graphrag · vector × bm25 × graph · fused via rrf</span>
          <span className="text-[var(--paper-3)]/35">
            composed in ink &amp; paper · mmxxvi
          </span>
        </div>
      </footer>
    </div>
  );
}

/* ── Tiny presentational helpers ─────────────────────────────── */

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-baseline justify-between gap-4">
      <span className="text-[var(--paper-3)]/40">{label}</span>
      <span className="text-right text-[var(--paper)]/85">{value}</span>
    </li>
  );
}

function SectionLabel({
  index,
  title,
  aside,
}: {
  index: string;
  title: string;
  aside?: string;
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-[var(--rule)] pb-3">
      <div className="font-mono-cap text-[11px] text-[var(--paper-3)]/55">
        <span className="text-[var(--vermillion)]">{index}</span>
        <span className="mx-3 text-[var(--paper-3)]/30">/</span>
        <span>{title}</span>
      </div>
      {aside && (
        <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/40">{aside}</span>
      )}
    </div>
  );
}

function PlateHeader({ title, trailing }: { title: string; trailing?: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-[var(--rule)] pb-3">
      <h3 className="display-lg text-[var(--paper)]">{title}</h3>
      {trailing && (
        <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/55">
          {trailing}
        </span>
      )}
    </div>
  );
}

function Manifest({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-3">
      <dt className="w-28 shrink-0 uppercase tracking-[0.18em] text-[var(--paper-3)]/45">
        {label}
      </dt>
      <dd className="min-w-0 flex-1 truncate">{children}</dd>
    </div>
  );
}
