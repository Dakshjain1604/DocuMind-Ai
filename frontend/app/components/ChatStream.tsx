"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { CitationChip } from "./CitationChip";

type Citation = { n: number; chunk_id: number };

function renderWithCitations(text: string, citations: Citation[], onCite: (id: number) => void) {
  const parts = text.split(/(\[\d+(?:,\d+)*\])/g);
  return parts.map((p, i) => {
    const m = p.match(/^\[(\d+(?:,\d+)*)\]$/);
    if (!m) return <span key={i}>{p}</span>;
    return (
      <span key={i}>
        {m[1].split(",").map((nStr) => (
          <CitationChip key={nStr} n={Number(nStr)} citations={citations} onClick={onCite} />
        ))}
      </span>
    );
  });
}

export function ChatStream({
  docHash,
  onCiteClick,
}: {
  docHash: string;
  onCiteClick?: (chunk_id: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [docHash]);

  const ask = useCallback(async () => {
    if (!query.trim()) return;
    setAnswer("");
    setCitations([]);
    setErr(null);
    setBusy(true);

    try {
      const r = await fetch("/api/rag/query", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: docHash, query }),
      });
      if (!r.ok || !r.body) {
        setErr(`REQUEST FAILED · ${r.status}`);
        return;
      }
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buffer = "";
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
          if (evt === "context") setCitations(data.citations ?? []);
          else if (evt === "token") setAnswer((a) => a + data.text);
          else if (evt === "error") setErr(data.message ?? "STREAM ERROR");
        }
      }
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }, [docHash, query]);

  return (
    <div className="space-y-6">
      {/* Input row */}
      <div className="flex items-stretch border border-[var(--rule)] bg-[var(--ink)]">
        <span className="flex items-center px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--vermillion)]">
          QRY <span className="ml-2 blink">▮</span>
        </span>
        <input
          ref={inputRef}
          className="flex-1 bg-transparent py-3 pr-3 font-mono text-[14px] text-[var(--paper)] placeholder:text-[var(--paper-3)]/30 focus:outline-none"
          placeholder="ask anything · enter to dispatch"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && ask()}
        />
        <button
          onClick={ask}
          disabled={busy || !query}
          className="border-l border-[var(--rule)] bg-[var(--ink-2)] px-5 font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--paper)] transition-colors hover:bg-[var(--vermillion)] hover:text-[var(--ink)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-[var(--ink-2)] disabled:hover:text-[var(--paper)]"
        >
          {busy ? "··· dispatch" : "dispatch →"}
        </button>
      </div>

      {/* Citations index */}
      {citations.length > 0 && (
        <div className="space-y-2">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--paper-3)]/50">
            ── source index · {citations.length} passage{citations.length === 1 ? "" : "s"}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {citations.map((c) => (
              <span
                key={c.n}
                className="inline-flex items-center gap-1 border border-[var(--rule)] bg-[var(--ink)] px-2 py-1 font-mono text-[10px] text-[var(--paper-3)]/80"
              >
                <span className="text-[var(--vermillion)]">{String(c.n).padStart(2, "0")}</span>
                <span className="text-[var(--paper-3)]/40">/</span>
                <span>chunk {c.chunk_id}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Answer body */}
      <div className="min-h-[160px] border-l-2 border-[var(--vermillion)]/40 pl-5">
        {answer ? (
          <div className="font-sans text-[18px] leading-[1.6] text-[var(--paper)] whitespace-pre-wrap">
            {renderWithCitations(answer, citations, (cid) => onCiteClick?.(cid))}
            {busy && <span className="blink ml-1 text-[var(--vermillion)]">▮</span>}
          </div>
        ) : (
          <div className="font-sans text-[16px] italic text-[var(--paper-3)]/30">
            {busy ? "consulting passages…" : "awaiting query"}
          </div>
        )}
      </div>

      {err && (
        <div className="border-l-2 border-[var(--vermillion)] bg-[var(--vermillion)]/10 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--vermillion-hot)]">
          ✕ {err}
        </div>
      )}
    </div>
  );
}
