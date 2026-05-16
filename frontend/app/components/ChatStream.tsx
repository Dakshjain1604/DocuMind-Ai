"use client";

import { useState, useCallback } from "react";
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

  const ask = useCallback(async () => {
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
        setErr(`Request failed: ${r.status}`);
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
          else if (evt === "error") setErr(data.message ?? "stream error");
        }
      }
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }, [docHash, query]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white"
          placeholder="Ask about this document…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && ask()}
        />
        <button
          onClick={ask}
          disabled={busy || !query}
          className="px-4 py-2 rounded bg-purple-600 text-white disabled:opacity-50"
        >
          {busy ? "…" : "Ask"}
        </button>
      </div>
      <div className="prose prose-invert max-w-none whitespace-pre-wrap text-white">
        {renderWithCitations(answer, citations, (cid) => onCiteClick?.(cid))}
      </div>
      {err && <div className="text-red-400 text-sm">Error: {err}</div>}
    </div>
  );
}
