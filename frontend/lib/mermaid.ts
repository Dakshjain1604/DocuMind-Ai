/**
 * Repairs the most common syntax error in LLM-generated Mermaid flowcharts.
 *
 * Small models routinely emit a bare multi-word name where Mermaid requires a
 * single-token node ID, e.g.
 *
 *     Conductor -->|circuit breaker| Acquirer Bank
 *
 * "Acquirer Bank" is two tokens, so the parser fails on that line and the whole
 * diagram is lost. Prompting reduces how often this happens but does not
 * eliminate it, so the renderer repairs it instead:
 *
 *     Conductor -->|circuit breaker| AcquirerBank[Acquirer Bank]
 *
 * Anything already well-formed is left untouched.
 */

/** Turn a display label into a safe Mermaid node id. */
function toId(label: string): string {
  const id = label.replace(/[^A-Za-z0-9]/g, "");
  return /^[A-Za-z]/.test(id) ? id : `n${id}`;
}

/** A node reference is fine if it is a single token, or already has a label. */
function needsRepair(ref: string): boolean {
  const t = ref.trim();
  if (!t) return false;
  if (/[[({>]/.test(t)) return false; // already Foo[...] / Foo(...) / Foo{...}
  return /\s/.test(t); // bare multi-word name
}

function repairRef(ref: string): string {
  const label = ref.trim();
  if (!needsRepair(label)) return ref;
  return `${toId(label)}[${label}]`;
}

// An edge: <source> <arrow>[|label|] <target>
// Arrows: --> --- -.-> ==> and friends.
const EDGE = /^(\s*)(.+?)(\s*(?:-{2,3}>|-{3}|-\.->|={2,3}>|--)\s*(?:\|[^|]*\|\s*)?)(.+?)(\s*;?\s*)$/;

export function sanitizeMermaid(src: string): string {
  if (!src) return src;
  const lines = src.split("\n");
  let inFlowchart = false;

  return lines
    .map((line) => {
      const trimmed = line.trim();
      if (/^(graph|flowchart)\s/i.test(trimmed)) {
        inFlowchart = true;
        return line;
      }
      // Only flowcharts use this node syntax; leave sequence/class/etc alone.
      if (!inFlowchart) return line;
      if (!trimmed || trimmed.startsWith("%%")) return line;
      // Subgraph headers and style directives are not edges.
      if (/^(subgraph|end|style|classDef|class|click|linkStyle)\b/i.test(trimmed)) return line;

      const m = EDGE.exec(line);
      if (!m) return line;
      const [, indent, source, arrow, target, tail] = m;
      return `${indent}${repairRef(source)}${arrow}${repairRef(target)}${tail}`;
    })
    .join("\n");
}
