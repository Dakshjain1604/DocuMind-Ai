"use client";

type Citation = { n: number; chunk_id: number };

export function CitationChip({
  n,
  citations,
  onClick,
}: {
  n: number;
  citations: Citation[];
  onClick?: (chunk_id: number) => void;
}) {
  const c = citations.find((x) => x.n === n);
  const label = String(n).padStart(2, "0");

  if (!c) {
    return (
      <span className="mx-0.5 inline-block font-mono text-[11px] text-[var(--paper-3)]/60">
        [{label}]
      </span>
    );
  }
  return (
    <button
      onClick={() => onClick?.(c.chunk_id)}
      className="mx-0.5 inline-flex items-center border border-[var(--vermillion)]/40 bg-[var(--ink-3)] px-1.5 py-0.5 align-baseline font-mono text-[10px] leading-none text-[var(--vermillion-hot)] transition-colors hover:border-[var(--vermillion)] hover:bg-[var(--vermillion)] hover:text-[var(--ink)]"
      title={`SOURCE · CHUNK ${c.chunk_id}`}
    >
      [{label}]
    </button>
  );
}
