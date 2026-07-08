"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { CitationChip } from "./CitationChip";

type Citation = { n: number; chunk_id: number };
type Turn = {
  id: string;
  question: string;
  answer: string;
  citations: Citation[];
  busy: boolean;
  error?: string | null;
};

const CITATION_RE = /([\[【]\d+(?:[,，]\d+)*[\]】])/g;
const CITATION_INNER = /^[\[【](\d+(?:[,，]\d+)*)[\]】]$/;

function renderWithCitations(
  text: string,
  citations: Citation[],
  onCite: (id: number) => void
) {
  const parts = text.split(CITATION_RE);
  return parts.map((p, i) => {
    const m = p.match(CITATION_INNER);
    if (!m) return <span key={i}>{p}</span>;
    return (
      <span key={i}>
        {m[1].split(/[,，]/).map((nStr) => (
          <CitationChip
            key={nStr}
            n={Number(nStr)}
            citations={citations}
            onClick={onCite}
          />
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

  const ask = useCallback(async () => {
    const q = query.trim();
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
      if (!r.ok || !r.body) {
        updateTurn(t.id, { busy: false, error: `request failed · ${r.status}` });
        return;
      }
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buffer = "";
      let acc = "";
      let cites: Citation[] = [];
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += dec.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const block of events) {
          const lines = block.split("\n");
          const eventLine = lines.find((l) => l.startsWith("event:"));
          const dataLine = lines.find((l) => l.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const evt = eventLine.replace("event:", "").trim();
          const data = JSON.parse(dataLine.replace("data:", "").trim());
          if (evt === "context") {
            cites = data.citations ?? [];
            updateTurn(t.id, { citations: cites });
          } else if (evt === "token") {
            acc += data.text;
            updateTurn(t.id, { answer: acc });
          } else if (evt === "error") {
            updateTurn(t.id, {
              error: data.message ?? "stream error",
              answer: acc,
            });
          }
        }
      }
      updateTurn(t.id, { busy: false });
    } catch (e: unknown) {
      updateTurn(t.id, { busy: false, error: String(e) });
    } finally {
      setBusy(false);
    }
  }, [docHash, query, busy, updateTurn]);

  const clear = useCallback(() => setTurns([]), []);

  return (
    <div className="space-y-6">
      {/* Thread */}
      {turns.length > 0 && (
        <div
          ref={threadRef}
          className="max-h-[58vh] space-y-7 overflow-y-auto pr-1"
          aria-live="polite"
        >
          {turns.map((t, i) => (
            <TurnBlock
              key={t.id}
              turn={t}
              index={i + 1}
              onCite={(cid) => onCiteClick?.(cid)}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {turns.length === 0 && (
        <div className="border border-dashed border-[var(--rule)] px-5 py-7 text-center font-display-italic text-[15px] text-[var(--paper-3)]/45">
          a quiet console awaits — ask a question to begin
        </div>
      )}

      {/* Input row */}
      <div className="flex items-stretch border border-[var(--rule)] bg-[var(--ink)]">
        <span className="flex items-center px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--vermillion)]">
          QRY <span className="ml-2 blink">▮</span>
        </span>
        <input
          ref={inputRef}
          className="flex-1 bg-transparent py-3 pr-3 font-mono text-[14px] text-[var(--paper)] placeholder:text-[var(--paper-3)]/30 focus:outline-none"
          placeholder={
            turns.length === 0
              ? "ask anything · enter to dispatch"
              : "follow up · enter to dispatch"
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && ask()}
          disabled={busy}
        />
        <button
          onClick={ask}
          disabled={busy || !query.trim()}
          className="border-l border-[var(--rule)] bg-[var(--ink-2)] px-5 font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--paper)] transition-colors hover:bg-[var(--vermillion)] hover:text-[var(--ink)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-[var(--ink-2)] disabled:hover:text-[var(--paper)]"
        >
          {busy ? "··· dispatch" : "dispatch →"}
        </button>
      </div>

      {/* Console actions */}
      {turns.length > 0 && (
        <div className="flex items-center justify-between font-mono-cap text-[10px] text-[var(--paper-3)]/45">
          <span>
            {turns.length} exchange{turns.length === 1 ? "" : "s"} on file
          </span>
          <button
            onClick={clear}
            disabled={busy}
            className="instrument border border-[var(--rule)] px-3 py-1.5 text-[var(--paper-3)]/70 hover:border-[var(--vermillion)] hover:text-[var(--vermillion)] disabled:opacity-40"
          >
            clear console
          </button>
        </div>
      )}
    </div>
  );
}

function TurnBlock({
  turn,
  index,
  onCite,
}: {
  turn: Turn;
  index: number;
  onCite: (id: number) => void;
}) {
  return (
    <article>
      {/* Question line */}
      <div className="flex items-baseline gap-3 border-b border-[var(--rule)] pb-2">
        <span className="font-mono-cap text-[10px] text-[var(--paper-3)]/45">
          Q · {String(index).padStart(2, "0")}
        </span>
        <span className="font-display-italic text-[clamp(18px,1.5vw,22px)] leading-[1.35] text-[var(--paper)]/95">
          {turn.question}
        </span>
      </div>

      {/* Citations rail */}
      {turn.citations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {turn.citations.map((c) => (
            <span
              key={c.n}
              className="inline-flex items-center gap-1 border border-[var(--rule)] bg-[var(--ink)] px-2 py-1 font-mono text-[10px] text-[var(--paper-3)]/80"
            >
              <span className="text-[var(--vermillion)]">
                {String(c.n).padStart(2, "0")}
              </span>
              <span className="text-[var(--paper-3)]/40">/</span>
              <span>chunk {c.chunk_id}</span>
            </span>
          ))}
        </div>
      )}

      {/* Answer body */}
      <div className="mt-4 border-l-2 border-[var(--vermillion)]/40 pl-5">
        {turn.answer ? (
          <div className="whitespace-pre-wrap font-sans text-[16.5px] leading-[1.6] text-[var(--paper)]">
            {renderWithCitations(turn.answer, turn.citations, onCite)}
            {turn.busy && (
              <span className="blink ml-1 text-[var(--vermillion)]">▮</span>
            )}
          </div>
        ) : (
          <div className="font-sans italic text-[15px] text-[var(--paper-3)]/35">
            {turn.busy ? "consulting passages…" : "no answer"}
          </div>
        )}
      </div>

      {turn.error && (
        <p className="mt-3 border-l-2 border-[var(--vermillion)] bg-[var(--vermillion)]/10 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--vermillion-hot)]">
          ✕ {turn.error}
        </p>
      )}
    </article>
  );
}
