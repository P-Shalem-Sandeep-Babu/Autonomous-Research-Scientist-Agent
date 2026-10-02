"use client";

import React, { useId } from "react";
import { KnowledgeGraphData, KnowledgeGraphNode, KnowledgeGraphEdge } from "@/types";

interface InteractiveKnowledgeGraphProps {
  graphData: KnowledgeGraphData;
  selectedGraphNode: KnowledgeGraphNode | null;
  onSelectNode: (node: KnowledgeGraphNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  paper: "#06b6d4",
  gap: "#8b5cf6",
  hypothesis: "#10b981",
  debate: "#f97316",
  dataset: "#f59e0b",
  experiment: "#3b82f6",
  code: "#14b8a6",
  paper_draft: "#ec4899",
  peer_review: "#ef4444",
};

export default function InteractiveKnowledgeGraph({
  graphData,
  selectedGraphNode,
  onSelectNode,
}: InteractiveKnowledgeGraphProps) {
  const titleId = useId();
  const descId = useId();

  if (!graphData?.nodes || graphData.nodes.length === 0) {
    return (
      <div 
        role="region" 
        aria-label="Scientific Knowledge Graph"
        className="h-full flex items-center justify-center p-8 text-center border border-card-border/60 bg-background/40 rounded-xl"
      >
        <p className="text-slate-500 text-sm">
          Execute research pipeline to construct Knowledge Graph.
        </p>
      </div>
    );
  }

  const width = 800;
  const height = 400;
  const order = [
    "paper",
    "gap",
    "hypothesis",
    "debate",
    "dataset",
    "experiment",
    "code",
    "paper_draft",
    "peer_review",
  ];

  const columns: Record<string, KnowledgeGraphNode[]> = {};
  order.forEach((o) => {
    columns[o] = [];
  });

  graphData.nodes.forEach((node: KnowledgeGraphNode) => {
    const colType = columns[node.type] ? node.type : "paper";
    columns[colType].push(node);
  });

  const activeCols = order.filter((o) => columns[o].length > 0);
  const colSpacing = width / (activeCols.length + 1);

  const nodeCoords: Record<string, { x: number; y: number }> = {};
  activeCols.forEach((colType, colIdx) => {
    const colNodes = columns[colType];
    const x = (colIdx + 1) * colSpacing;
    const rowSpacing = height / (colNodes.length + 1);

    colNodes.forEach((node, rowIdx) => {
      const y = (rowIdx + 1) * rowSpacing;
      nodeCoords[node.id] = { x, y };
    });
  });

  const getNodeColor = (type: string) => NODE_COLORS[type] || "#06b6d4";

  return (
    <div
      role="region"
      aria-label="Interactive Scientific Knowledge Graph"
      className="relative w-full h-full border border-card-border/60 bg-background/40 rounded-xl overflow-hidden flex flex-col md:flex-row shadow-inner"
    >
      {/* Screen Reader Summary */}
      <div className="sr-only">
        <h4>Knowledge Graph Summary</h4>
        <p>
          Contains {graphData.nodes.length} nodes across {activeCols.length} research stages, with {graphData.edges.length} lineage connections.
        </p>
        <ul>
          {graphData.nodes.map((n: KnowledgeGraphNode) => (
            <li key={n.id}>
              {n.label} (Stage: {n.type.replace("_", " ")}).
            </li>
          ))}
        </ul>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 min-h-[350px] relative overflow-hidden">
        <svg
          role="graphics-document"
          aria-roledescription="scientific knowledge graph"
          aria-labelledby={`${titleId} ${descId}`}
          className="w-full h-full min-h-[350px] bg-slate-950/20 select-none"
          viewBox={`0 0 ${width} ${height}`}
          tabIndex={0}
        >
          <title id={titleId}>Scientific Lineage Knowledge Graph</title>
          <desc id={descId}>
            Interactive network diagram illustrating research lineage from literature discovery to peer review.
          </desc>

          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
            </marker>
          </defs>

          {/* Graph Edges */}
          {graphData.edges.map((edge: KnowledgeGraphEdge, idx: number) => {
            const start = nodeCoords[edge.source];
            const end = nodeCoords[edge.target];
            if (!start || !end) return null;

            return (
              <g key={`edge-${idx}`} aria-hidden="true">
                <line
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  stroke="#222d44"
                  strokeWidth="2"
                  markerEnd="url(#arrow)"
                  strokeDasharray="4 4"
                />
                <text
                  x={(start.x + end.x) / 2}
                  y={(start.y + end.y) / 2 - 5}
                  fill="#64748b"
                  fontSize="8"
                  textAnchor="middle"
                  className="font-mono select-none pointer-events-none"
                >
                  {edge.type}
                </text>
              </g>
            );
          })}

          {/* Graph Nodes */}
          {graphData.nodes.map((node: KnowledgeGraphNode) => {
            const coords = nodeCoords[node.id];
            if (!coords) return null;

            const isSelected = selectedGraphNode?.id === node.id;
            const color = getNodeColor(node.type);

            return (
              <g
                key={`node-${node.id}`}
                role="button"
                tabIndex={0}
                aria-label={`${node.label}, ${node.type.replace("_", " ")} node`}
                aria-pressed={isSelected}
                transform={`translate(${coords.x}, ${coords.y})`}
                className="cursor-pointer group focus:outline-none focus-visible:scale-125 transition-transform"
                onClick={() => onSelectNode(node)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectNode(node);
                  }
                }}
              >
                {/* Focus & Selection Ring */}
                <circle
                  r={isSelected ? "15" : "11"}
                  fill={color}
                  opacity={isSelected ? "0.3" : "0.15"}
                  stroke={color}
                  strokeWidth={isSelected ? "3" : "1.5"}
                  strokeDasharray={isSelected ? "none" : undefined}
                  className="transition-all duration-200 group-hover:scale-125 group-focus-visible:stroke-white group-focus-visible:stroke-[2.5]"
                />
                <circle r="4" fill={color} />

                <text
                  y="25"
                  fill="#94a3b8"
                  fontSize="9"
                  fontWeight="bold"
                  textAnchor="middle"
                  className="select-none pointer-events-none drop-shadow-md group-hover:fill-slate-200 group-focus-visible:fill-slate-100"
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Node Inspector Panel */}
      <aside
        aria-live="polite"
        aria-label="Node Metadata Inspector"
        className="w-full md:w-64 border-t md:border-t-0 md:border-l border-card-border/80 bg-card/40 p-4 flex flex-col justify-between overflow-y-auto"
      >
        {selectedGraphNode ? (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0 shadow-sm"
                style={{ backgroundColor: getNodeColor(selectedGraphNode.type) }}
                aria-hidden="true"
              />
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400 font-mono">
                {selectedGraphNode.type.replace("_", " ")}
              </span>
            </div>
            <h4 className="text-sm font-bold text-slate-200 mb-4 break-words">
              {selectedGraphNode.label}
            </h4>

            <div className="space-y-3 text-xs text-slate-400">
              {Object.entries(selectedGraphNode.properties || {}).map(([key, val]) => (
                <div key={key} className="border-b border-card-border/30 pb-2">
                  <span className="font-semibold block capitalize text-slate-500 font-mono text-[10px]">
                    {key.replace("_", " ")}
                  </span>
                  <span className="text-slate-300 break-words block mt-0.5 font-mono text-[11px]">
                    {typeof val === "object" ? JSON.stringify(val) : String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center text-xs text-slate-500 my-auto p-4">
            Select a node on the canvas (using mouse or keyboard tab) to inspect research lineage attributes.
          </div>
        )}
      </aside>
    </div>
  );
}
