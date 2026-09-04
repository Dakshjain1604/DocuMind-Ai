"use client";

import { Citation } from "../Dashboard/types";

/**
 * A [nn] source marker inside a streamed answer.
 *
 * Styled with the same zinc/sky utilities as ChatStream, its only consumer -
 * sky is the one sparing accent color this app uses, reserved for citations.
 * It previously used the legacy --vermillion / --ink-3 / --paper-3 custom
 * properties, so the chips did not match the surface they sat on — and
 * --ink-3 was never even defined.
 */
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
      <span className="mx-0.5 inline-block font-mono text-[11px] text-zinc-500">[{label}]</span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onClick?.(c.chunk_id)}
      aria-label={`Jump to source chunk ${c.chunk_id}`}
      title={`Source · chunk ${c.chunk_id}`}
      className="mx-0.5 inline-flex items-center rounded border border-sky-500/40 bg-zinc-900 px-1.5 py-0.5 align-baseline font-mono text-[10px] leading-none text-sky-300 transition-colors hover:border-sky-400 hover:bg-sky-500 hover:text-white"
    >
      [{label}]
    </button>
  );
}
