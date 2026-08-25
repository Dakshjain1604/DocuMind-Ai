"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Send, Copy, Check, Lightbulb, AlertCircle, Terminal, Trash2, ArrowRight, Gauge } from "lucide-react";
import { CitationChip } from "./CitationChip";
import { readSseStream } from "@/lib/sse";
import { parseCitationSegments } from "@/lib/citations";
import { Button } from "@/components/ui/button";
import { Citation } from "../Dashboard/types";
import { TracePanel } from "../Dashboard/components/TracePanel";

type Turn = {
  id: string;
  question: string;
  answer: string;
  citations: Citation[];
  busy: boolean;
  error?: string | null;
  requestId?: string | null;
};

function renderWithCitations(
  text: string,
  citations: Citation[],
  onCite: (id: number) => void
) {
  return parseCitationSegments(text).map((seg, i) => {
    if (seg.type === "text") return <span key={i}>{seg.value}</span>;
    return (
      <span key={i}>
        {seg.ids.map((n) => (
          <CitationChip key={n} n={n} citations={citations} onClick={onCite} />
        ))}
      </span>
    );
  });
}

function newTurn(question: string): Turn {
  return {
    id: `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    question,
    answer: "",
    citations: [],
    busy: true,
    error: null,
  };
}

const SUGGESTED_QUERIES = [
  "What are the core technical concepts and methodologies described?",
  "Summarize the key findings, metrics, and operational details.",
  "What is the overall architecture model and structural design?",
];

export function ChatStream({
  docHash,
  onCiteClick,
}: {
  docHash: string;
  onCiteClick?: (chunk_id: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [docHash]);

  useEffect(() => {
    setTurns([]);
  }, [docHash]);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [turns]);

  const updateTurn = useCallback(
    (id: string, patch: Partial<Turn>) =>
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, ...patch } : t))),
    []
  );

  const askQuery = useCallback(async (qText: string) => {
    const q = qText.trim();
    if (!q || busy) return;
    setQuery("");
    const t = newTurn(q);
    setTurns((ts) => [...ts, t]);
    setBusy(true);

    try {
      const r = await fetch("/api/rag/query", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: docHash, query: q }),
      });
      const requestId = r.headers.get("X-Request-Id");
      if (requestId) updateTurn(t.id, { requestId });
      let acc = "";
      await readSseStream(r, {
        onError: (message) => updateTurn(t.id, { error: message, answer: acc }),
        onEvent: (evt, data: { citations?: Citation[]; text?: string; message?: string }) => {
          if (evt === "context") {
            updateTurn(t.id, { citations: data.citations ?? [] });
          } else if (evt === "token") {
            acc += data.text ?? "";
            updateTurn(t.id, { answer: acc });
          } else if (evt === "error") {
            updateTurn(t.id, { error: data.message ?? "stream error", answer: acc });
          }
        },
      });
      updateTurn(t.id, { busy: false });
    } catch {
      updateTurn(t.id, { busy: false, error: "The request could not be completed." });
    } finally {
      setBusy(false);
    }
  }, [docHash, busy, updateTurn]);

  const handleCopyAnswer = (turnId: string, answerText: string) => {
    navigator.clipboard.writeText(answerText);
    setCopiedId(turnId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clear = useCallback(() => setTurns([]), []);

  return (
    <div className="space-y-6">
      {/* Suggested Queries Chips */}
      {turns.length === 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">
            <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
            <span>Suggested Context Queries</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUERIES.map((sq, i) => (
              <button
                key={i}
                onClick={() => askQuery(sq)}
                disabled={busy}
                className="group inline-flex items-center gap-2 rounded-xl border border-white/10 bg-zinc-950/60 px-4 py-2.5 font-mono text-xs text-zinc-300 transition-all hover:border-indigo-500/50 hover:bg-zinc-900/90 hover:text-white disabled:opacity-50 text-left"
              >
                <span>{sq}</span>
                <ArrowRight className="h-3.5 w-3.5 text-zinc-500 group-hover:text-indigo-400 transition-transform group-hover:translate-x-1 shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Thread */}
      {turns.length > 0 && (
        <div
          ref={threadRef}
          className="max-h-[58vh] space-y-7 overflow-y-auto pr-1 scrollbar-thin"
          aria-live="polite"
        >
          {turns.map((t, i) => (
            <TurnBlock
              key={t.id}
              turn={t}
              index={i + 1}
              onCite={(cid) => onCiteClick?.(cid)}
              onCopy={() => handleCopyAnswer(t.id, t.answer)}
              isCopied={copiedId === t.id}
            />
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-zinc-950/80 p-2 shadow-xl backdrop-blur-xl">
        <div className="flex items-center px-3 font-mono text-xs font-bold uppercase tracking-wider text-indigo-400 shrink-0">
          <Terminal className="h-4 w-4 mr-1.5" />
          <span>QRY</span>
        </div>
        <input
          ref={inputRef}
          className="flex-1 bg-transparent py-2.5 font-mono text-sm text-white placeholder:text-zinc-500 focus:outline-none"
          placeholder={
            turns.length === 0
              ? "Ask anything about the document… (Enter to dispatch)"
              : "Follow-up question… (Enter to dispatch)"
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && askQuery(query)}
          disabled={busy}
        />
        <Button
          onClick={() => askQuery(query)}
          disabled={busy || !query.trim()}
          size="sm"
          className="gap-2 shrink-0"
        >
          {busy ? (
            <span>Dispatching…</span>
          ) : (
            <>
              <span>Dispatch</span>
              <Send className="h-3.5 w-3.5" />
            </>
          )}
        </Button>
      </div>

      {/* Console actions */}
      {turns.length > 0 && (
        <div className="flex items-center justify-between font-mono text-xs text-zinc-500">
          <span>
            {turns.length} exchange{turns.length === 1 ? "" : "s"} on file
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={clear}
            disabled={busy}
            className="gap-1.5 h-7 text-[11px]"
          >
            <Trash2 className="h-3 w-3 text-zinc-400" />
            <span>Clear Console</span>
          </Button>
        </div>
      )}
    </div>
  );
}

function TurnBlock({
  turn,
  index,
  onCite,
  onCopy,
  isCopied,
}: {
  turn: Turn;
  index: number;
  onCite: (id: number) => void;
  onCopy: () => void;
  isCopied: boolean;
}) {
  const [traceOpen, setTraceOpen] = useState(false);
  return (
    <article className="group space-y-3">
      {/* Question line */}
      <div className="flex items-baseline justify-between gap-3 border-b border-white/10 pb-2.5">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-xs font-semibold text-zinc-500">
            Q · {String(index).padStart(2, "0")}
          </span>
          <span className="font-display text-lg font-bold text-white">
            {turn.question}
          </span>
        </div>

        {turn.answer && !turn.busy && (
          <div className="flex items-center gap-1">
            {turn.requestId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setTraceOpen((o) => !o)}
                aria-expanded={traceOpen}
                className="h-7 px-2 font-mono text-[11px] text-zinc-400 hover:text-white"
              >
                <span className="inline-flex items-center gap-1">
                  <Gauge className="h-3.5 w-3.5" /> {traceOpen ? "Hide trace" : "View trace"}
                </span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onCopy}
              className="h-7 px-2 font-mono text-[11px] text-zinc-400 hover:text-white"
            >
              {isCopied ? (
                <span className="inline-flex items-center gap-1 text-emerald-400">
                  <Check className="h-3.5 w-3.5" /> Copied
                </span>
              ) : (
                <span className="inline-flex items-center gap-1">
                  <Copy className="h-3.5 w-3.5" /> Copy
                </span>
              )}
            </Button>
          </div>
        )}
      </div>

      {traceOpen && turn.requestId && <TracePanel requestId={turn.requestId} />}

      {/* Citations rail */}
      {turn.citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {turn.citations.map((c) => (
            <span
              key={c.n}
              onClick={() => onCite(c.chunk_id)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 font-mono text-[10px] text-indigo-300 cursor-pointer hover:border-indigo-500 hover:bg-indigo-500/20 transition-colors"
            >
              <span className="font-bold text-indigo-400">
                {String(c.n).padStart(2, "0")}
              </span>
              <span className="text-zinc-500">/</span>
              <span>Chunk {c.chunk_id}</span>
            </span>
          ))}
        </div>
      )}

      {/* Answer body */}
      <div className="border-l-2 border-indigo-500/50 pl-4 py-1">
        {turn.answer ? (
          <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-200">
            {renderWithCitations(turn.answer, turn.citations, onCite)}
            {turn.busy && (
              <span className="blink ml-1 text-indigo-400 font-mono">▮</span>
            )}
          </div>
        ) : (
          <div className="font-sans italic text-sm text-zinc-500">
            {turn.busy ? "Consulting GraphRAG passages…" : "No answer"}
          </div>
        )}
      </div>

      {turn.error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 font-mono text-xs text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{turn.error}</span>
        </div>
      )}
    </article>
  );
}
