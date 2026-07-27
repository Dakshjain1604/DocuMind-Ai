"use client";

import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

interface MermaidDiagramProps {
  chart: string;
}

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      themeVariables: {
        darkMode: true,
        background: "#18181b",
        primaryColor: "#6366f1",
        primaryTextColor: "#ffffff",
        primaryBorderColor: "#818cf8",
        lineColor: "#38bdf8",
        secondaryColor: "#a855f7",
        tertiaryColor: "#34d399",
      },
      securityLevel: "loose",
    });

    let isMounted = true;
    const renderChart = async () => {
      if (!chart || !chart.trim()) return;
      try {
        const id = `mermaid_${Math.random().toString(36).slice(2, 9)}`;
        const { svg: svgCode } = await mermaid.render(id, chart);
        if (isMounted) {
          setSvg(svgCode);
          setError(false);
        }
      } catch (err) {
        console.warn("Mermaid render warning:", err);
        if (isMounted) setError(true);
      }
    };

    renderChart();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  if (error || !svg) {
    return (
      <div className="my-4 glass-panel rounded-xl p-4 font-mono text-[11px] text-zinc-400 overflow-x-auto">
        <pre className="text-indigo-300">{chart}</pre>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-6 glass-panel rounded-2xl p-6 overflow-x-auto flex justify-center border border-indigo-500/20 bg-zinc-950/80 shadow-2xl"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};
