"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Node = { id: string; type?: string; description?: string };
type Edge = { src: string; dst: string; type?: string };
type GraphData = {
  nodes: Node[];
  edges: Edge[];
  communities?: Record<string, number>;
};

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
          setErr(`Graph fetch failed: ${r.status}`);
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

  if (err) return <div className="text-red-400 text-sm">{err}</div>;
  if (!data) return <div className="text-zinc-400">Loading graph…</div>;
  if (data.nodes.length === 0) return <div className="text-zinc-500 text-sm">No graph extracted for this document.</div>;

  const fgData = {
    nodes: data.nodes.map((n) => ({
      id: n.id,
      group: data.communities?.[n.id] ?? 0,
      label: n.id,
    })),
    links: data.edges.map((e) => ({ source: e.src, target: e.dst })),
  };

  return (
    <div className="bg-zinc-900 rounded border border-zinc-800" style={{ height: 480 }}>
      <ForceGraph2D
        graphData={fgData}
        nodeLabel="label"
        nodeCanvasObject={(node, ctx, scale) => {
          const isHi = highlightNode === node.id;
          const r = isHi ? 7 : 4;
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
          const hue = ((node.group as number) * 67) % 360;
          ctx.fillStyle = isHi ? "#fff" : `hsl(${hue},70%,60%)`;
          ctx.fill();
          if (scale > 1.5) {
            ctx.fillStyle = "#ddd";
            ctx.font = `${10 / scale}px sans-serif`;
            ctx.fillText(String(node.label ?? ""), (node.x ?? 0) + r + 2, (node.y ?? 0) + 3);
          }
        }}
        linkColor={() => "rgba(255,255,255,0.12)"}
        onNodeClick={(n) => onNodeClick?.(String(n.id))}
      />
    </div>
  );
}
