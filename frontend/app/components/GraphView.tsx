"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Node = { id: string; type?: string; description?: string };
type Edge = { src: string; dst: string; type?: string };
type GraphData = {
  nodes: Node[];
  edges: Edge[];
  communities?: Record<string, number>;
  community_summaries?: Record<string, string>;
};

// Atlas palette for community groups — picked, not random
const COMMUNITY_COLORS = [
  "#d4351c", // vermillion
  "#b88a2b", // ochre
  "#7fa9a5", // teal-pale
  "#e6dbc3", // paper-warm
  "#9ea66d", // moss
  "#c98a73", // terra
  "#5d7a8c", // slate
  "#d39656", // copper
];

export function GraphView({
  docHash,
  onNodeClick,
  highlightNode,
}: {
  docHash: string;
  onNodeClick?: (entityId: string) => void;
  highlightNode?: string | null;
}) {
  const [data, setData] = useState<GraphData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`/api/rag/graph/${encodeURIComponent(docHash)}`);
        if (!r.ok) {
          setErr(`GRAPH FETCH FAILED · ${r.status}`);
          return;
        }
        const j = (await r.json()) as GraphData;
        if (!cancelled) setData(j);
      } catch (e: unknown) {
        if (!cancelled) setErr(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docHash]);

  const stats = useMemo(() => {
    if (!data) return null;
    const comms = new Set(Object.values(data.communities ?? {}));
    return { n: data.nodes.length, e: data.edges.length, c: comms.size };
  }, [data]);

  if (err) {
    return (
      <div className="border-l-2 border-[var(--vermillion)] bg-[var(--vermillion)]/10 px-4 py-3 font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--vermillion-hot)]">
        ✕ {err}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="flex h-[520px] items-center justify-center border border-[var(--rule)] bg-[var(--ink)] font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--paper-3)]/40">
        <span className="ticker-dot mr-2 text-[var(--vermillion)]">●</span> loading plate · graph
      </div>
    );
  }
  if (data.nodes.length === 0) {
    return (
      <div className="flex h-[520px] items-center justify-center border border-[var(--rule)] bg-[var(--ink)] font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--paper-3)]/40">
        ∅ no entities extracted from this document
      </div>
    );
  }

  const fgData = {
    nodes: data.nodes.map((n) => ({
      id: n.id,
      group: data.communities?.[n.id] ?? 0,
      label: n.id,
    })),
    links: data.edges.map((e) => ({ source: e.src, target: e.dst })),
  };

  return (
    <div className="regmark border border-[var(--rule)] bg-[var(--ink)]">
      <span className="rm-tr" />
      <span className="rm-bl" />

      {/* Cartouche header */}
      <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--paper-3)]/60">
        <span>PLATE · IV · KNOWLEDGE CARTOGRAPHY</span>
        {stats && (
          <span className="tabular-nums">
            <span className="text-[var(--vermillion)]">{stats.n}</span> NODES ·
            <span className="ml-1 text-[var(--vermillion)]">{stats.e}</span> EDGES ·
            <span className="ml-1 text-[var(--vermillion)]">{stats.c}</span> COMMUNITIES
          </span>
        )}
      </div>

      <div style={{ height: 520 }}>
        <ForceGraph2D
          graphData={fgData}
          backgroundColor="rgba(0,0,0,0)"
          nodeLabel="label"
          nodeRelSize={4}
          linkColor={() => "rgba(245, 239, 230, 0.16)"}
          linkWidth={0.6}
          nodeCanvasObject={(node: any, ctx, scale) => {
            const isHi = highlightNode === node.id;
            const r = isHi ? 8 : 5;
            const color = isHi
              ? "#f5efe6"
              : COMMUNITY_COLORS[(node.group as number) % COMMUNITY_COLORS.length];

            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            // Halo on highlight
            if (isHi) {
              ctx.beginPath();
              ctx.arc(node.x ?? 0, node.y ?? 0, r + 4, 0, 2 * Math.PI);
              ctx.strokeStyle = "#ff4422";
              ctx.lineWidth = 1.2 / scale;
              ctx.stroke();
            }

            if (scale > 1.2 || isHi) {
              const fontSize = isHi ? 11 / scale : 9 / scale;
              ctx.font = `${fontSize}px "JetBrains Mono", monospace`;
              ctx.fillStyle = "#e6dbc3";
              ctx.textBaseline = "middle";
              ctx.fillText(String(node.label ?? ""), (node.x ?? 0) + r + 4, node.y ?? 0);
            }
          }}
          onNodeClick={(n: any) => onNodeClick?.(String(n.id))}
        />
      </div>

      {/* Legend */}
      {data.community_summaries && Object.keys(data.community_summaries).length > 0 && (
        <div className="border-t border-[var(--rule)] px-4 py-3">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--paper-3)]/50">
            ── communities · legend
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {Object.entries(data.community_summaries).map(([cid, summary]) => {
              const color = COMMUNITY_COLORS[Number(cid) % COMMUNITY_COLORS.length];
              return (
                <div key={cid} className="flex items-start gap-2">
                  <span
                    className="mt-1 inline-block h-2 w-2 shrink-0"
                    style={{ background: color }}
                  />
                  <p className="font-sans text-[13px] leading-[1.5] text-[var(--paper-3)]/80">
                    {summary}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
