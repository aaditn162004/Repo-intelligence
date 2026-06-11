"use client";

import { useCallback, useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
  MarkerType,
  NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphData, GraphNode, GraphEdge } from "@/types";
import { languageColor } from "@/lib/utils";

const NODE_COLORS: Record<string, string> = {
  file: "#6366f1",
  function: "#10b981",
  method: "#06b6d4",
  class: "#f59e0b",
  module: "#8b5cf6",
  external_lib: "#ef4444",
  external_class: "#f97316",
  type: "#84cc16",
};

function RepositoryNode({ data }: { data: GraphNode & { label: string } }) {
  const color = NODE_COLORS[data.type] ?? "#6b7280";
  return (
    <div
      style={{ borderColor: color }}
      className="px-3 py-2 rounded-lg bg-zinc-900/90 border text-xs max-w-[180px] shadow-lg"
    >
      <div className="flex items-center gap-1.5 mb-0.5">
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="text-zinc-400 capitalize">{data.type}</span>
      </div>
      <p className="font-mono font-medium text-zinc-200 truncate">{data.label}</p>
      {data.file_path && (
        <p className="text-zinc-500 truncate mt-0.5" style={{ fontSize: 10 }}>
          {data.file_path}
        </p>
      )}
    </div>
  );
}

const nodeTypes: NodeTypes = { repository: RepositoryNode };

interface Props {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
}

function layoutNodes(rawNodes: GraphNode[]): Node[] {
  // Simple force-like layout: group by type, spread in rows
  const typeOrder = ["file", "class", "function", "method", "module", "external_lib"];
  const groups: Record<string, GraphNode[]> = {};
  for (const n of rawNodes) {
    const t = n.type ?? "module";
    if (!groups[t]) groups[t] = [];
    groups[t].push(n);
  }

  const nodes: Node[] = [];
  let y = 0;
  for (const type of typeOrder) {
    const grp = groups[type] ?? [];
    grp.forEach((n, i) => {
      nodes.push({
        id: n.id,
        type: "repository",
        position: { x: i * 220, y },
        data: { ...n, label: n.name ?? n.id },
      });
    });
    if (grp.length > 0) y += 130;
    delete groups[type];
  }
  // Remaining types
  for (const [, grp] of Object.entries(groups)) {
    grp.forEach((n, i) => {
      nodes.push({
        id: n.id,
        type: "repository",
        position: { x: i * 220, y },
        data: { ...n, label: n.name ?? n.id },
      });
    });
    y += 130;
  }
  return nodes;
}

function buildEdges(rawEdges: GraphEdge[]): Edge[] {
  return rawEdges.map((e, i) => ({
    id: `edge-${i}`,
    source: e.source,
    target: e.target,
    label: e.label ?? e.edge_type,
    type: "smoothstep",
    animated: e.edge_type === "calls",
    style: {
      stroke: e.edge_type === "inherits" ? "#f59e0b" : e.edge_type === "imports" ? "#6366f1" : "#374151",
    },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#4b5563" },
    labelStyle: { fill: "#6b7280", fontSize: 10 },
    labelBgStyle: { fill: "#0d0d14" },
  }));
}

export function DependencyGraph({ data, onNodeClick }: Props) {
  const initialNodes = useMemo(() => layoutNodes(data.nodes), [data.nodes]);
  const initialEdges = useMemo(() => buildEdges(data.edges), [data.edges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.data as GraphNode);
    },
    [onNodeClick]
  );

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        attributionPosition="bottom-left"
      >
        <Background color="#1f1f2e" gap={20} variant={BackgroundVariant.Dots} />
        <Controls
          style={{ background: "#111118", border: "1px solid #27272a" }}
          showInteractive={false}
        />
        <MiniMap
          style={{ background: "#111118", border: "1px solid #27272a" }}
          nodeColor={(n) => NODE_COLORS[(n.data as GraphNode).type] ?? "#6b7280"}
          maskColor="rgba(0,0,0,0.4)"
        />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-12 left-3 z-10 bg-zinc-900/90 border border-zinc-800 rounded-lg p-3">
        <p className="text-xs text-zinc-500 mb-2 font-medium">Legend</p>
        {Object.entries(NODE_COLORS).slice(0, 6).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5 mb-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-xs text-zinc-400 capitalize">{type.replace("_", " ")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
