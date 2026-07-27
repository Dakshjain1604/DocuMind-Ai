"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Network, AlertCircle, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Node = { id: string; type?: string; description?: string };
type Edge = { src: string; dst: string; type?: string };
type GraphData = {
  nodes: Node[];
  edges: Edge[];
  communities?: Record<string, number>;
  community_summaries?: Record<string, string>;
};

// Atlas palette for community groups
const COMMUNITY_COLORS = [
  "#6366f1", // indigo
  "#38bdf8", // cyan
  "#10b981", // emerald
  "#fbbf24", // amber
  "#c084fc", // purple
  "#f472b6", // pink
  "#a855f7", // violet
  "#34d399", // teal
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
          setErr(`Graph fetch failed · status ${r.status}`);
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
      <div className="flex items-center gap-2 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 font-mono text-xs text-red-400">
        <AlertCircle className="h-4 w-4 shrink-0" />
        <span>{err}</span>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="flex h-[520px] items-center justify-center rounded-2xl border border-white/10 bg-zinc-950/80 font-mono text-xs uppercase tracking-wider text-zinc-400">
        <RefreshCw className="mr-2 h-4 w-4 animate-spin text-indigo-400" />
        <span>Loading Knowledge Atlas Graph…</span>
      </div>
    );
  }
  if (data.nodes.length === 0) {
    return (
      <div className="flex h-[520px] flex-col items-center justify-center gap-2 rounded-2xl border border-white/10 bg-zinc-950/80 font-mono text-xs uppercase tracking-wider text-zinc-500">
        <Network className="h-8 w-8 text-zinc-600 mb-1" />
        <span>No knowledge entities extracted from this document</span>
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
    <div className="glass-panel rounded-2xl border border-white/10 bg-zinc-950/80 shadow-2xl backdrop-blur-xl space-y-4 p-4">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between border-b border-white/10 pb-3 font-mono text-xs uppercase tracking-wider text-zinc-400">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-indigo-400" />
          <span className="font-semibold text-white">Knowledge Cartography Atlas</span>
        </div>
        {stats && (
          <div className="flex items-center gap-2">
            <Badge variant="default">{stats.n} Nodes</Badge>
            <Badge variant="secondary">{stats.e} Edges</Badge>
            <Badge variant="outline">{stats.c} Communities</Badge>
          </div>
        )}
      </div>

      <div style={{ height: 480 }} className="rounded-xl overflow-hidden bg-zinc-950/60 border border-white/5">
        <ForceGraph2D
          graphData={fgData}
          backgroundColor="rgba(0,0,0,0)"
          nodeLabel="label"
          nodeRelSize={4}
          linkColor={() => "rgba(255, 255, 255, 0.12)"}
          linkWidth={0.8}
          nodeCanvasObject={(node: any, ctx, scale) => {
            const isHi = highlightNode === node.id;
            const r = isHi ? 8 : 5;
            const color = isHi
              ? "#ffffff"
              : COMMUNITY_COLORS[(node.group as number) % COMMUNITY_COLORS.length];

            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            // Halo on highlight
            if (isHi) {
              ctx.beginPath();
              ctx.arc(node.x ?? 0, node.y ?? 0, r + 4, 0, 2 * Math.PI);
              ctx.strokeStyle = "#818cf8";
              ctx.lineWidth = 1.5 / scale;
              ctx.stroke();
            }

            if (scale > 1.2 || isHi) {
              const fontSize = isHi ? 11 / scale : 9 / scale;
              ctx.font = `${fontSize}px "JetBrains Mono", monospace`;
              ctx.fillStyle = "#fafafa";
              ctx.textBaseline = "middle";
              ctx.fillText(String(node.label ?? ""), (node.x ?? 0) + r + 4, node.y ?? 0);
            }
          }}
          onNodeClick={(n: any) => onNodeClick?.(String(n.id))}
        />
      </div>

      {/* Legend */}
      {data.community_summaries && Object.keys(data.community_summaries).length > 0 && (
        <div className="border-t border-white/10 pt-3 space-y-2">
          <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">
            Sub-Graph Communities Legend
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {Object.entries(data.community_summaries).map(([cid, summary]) => {
              const color = COMMUNITY_COLORS[Number(cid) % COMMUNITY_COLORS.length];
              return (
                <div key={cid} className="flex items-start gap-2.5 rounded-xl border border-white/5 bg-zinc-900/40 p-2.5">
                  <span
                    className="mt-1 inline-block h-2.5 w-2.5 rounded-full shrink-0"
                    style={{ background: color }}
                  />
                  <p className="font-sans text-xs leading-relaxed text-zinc-300">
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
