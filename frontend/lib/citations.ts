/**
 * Citation-marker parsing, split out from ChatStream.tsx's JSX rendering so
 * the parsing logic (the part actually worth locking down with a test) can
 * be exercised without a React renderer.
 */

const CITATION_RE = /([\[【]\d+(?:[,，]\d+)*[\]】])/g;
const CITATION_INNER = /^[\[【](\d+(?:[,，]\d+)*)[\]】]$/;

export type CitationSegment =
  | { type: "text"; value: string }
  | { type: "citation"; ids: number[] };

/** Split streamed answer text into plain-text runs and citation-marker runs. */
export function parseCitationSegments(text: string): CitationSegment[] {
  return text.split(CITATION_RE).map((part) => {
    const m = part.match(CITATION_INNER);
    if (!m) return { type: "text", value: part };
    return { type: "citation", ids: m[1].split(/[,，]/).map(Number) };
  });
}
