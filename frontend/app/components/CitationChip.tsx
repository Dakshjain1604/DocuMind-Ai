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
  if (!c) return <span>[{n}]</span>;
  return (
    <button
      onClick={() => onClick?.(c.chunk_id)}
      className="inline-block mx-0.5 px-1.5 py-0.5 text-xs rounded bg-purple-700/30 text-purple-200 hover:bg-purple-700/60"
      title={`Source chunk ${c.chunk_id}`}
    >
      [{n}]
    </button>
  );
}
