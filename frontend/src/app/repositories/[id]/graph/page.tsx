"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { GitBranch, Info } from "lucide-react";
import { api } from "@/lib/api";
import { useRepository } from "@/hooks/useRepositories";
import { DependencyGraph } from "@/components/graph/DependencyGraph";
import type { GraphData, GraphNode } from "@/types";

interface Props {
  params: Promise<{ id: string }>;
}

export default function GraphPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { repository } = useRepository(id);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const { data: graphData, isLoading, error } = useSWR<GraphData>(
    `graph:${id}`,
    () => api.graph.full(id),
    { revalidateOnFocus: false }
  );

  return (
    <main className="min-h-screen flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center gap-2 text-sm shrink-0">
        <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300">
          <GitBranch className="w-5 h-5" />
        </button>
        <span className="text-zinc-600">/</span>
        <button
          onClick={() => router.push(`/repositories/${id}`)}
          className="text-zinc-500 hover:text-zinc-300"
        >
          {repository?.name ?? id}
        </button>
        <span className="text-zinc-600">/</span>
        <span className="text-zinc-200 font-medium">Dependency Graph</span>

        {graphData?.stats && (
          <div className="ml-auto flex items-center gap-4 text-xs text-zinc-500">
            <span>{graphData.stats.node_count} nodes</span>
            <span>{graphData.stats.edge_count} edges</span>
          </div>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Graph */}
        <div className="flex-1 relative">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-10 h-10 rounded-full border-2 border-brand-500 border-t-transparent animate-spin mx-auto mb-3" />
                <p className="text-zinc-500 text-sm">Loading dependency graph…</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
              Graph not available yet. Ensure the repository is fully indexed.
            </div>
          ) : graphData ? (
            <DependencyGraph data={graphData} onNodeClick={setSelectedNode} />
          ) : null}
        </div>

        {/* Node inspector */}
        {selectedNode && (
          <div className="w-72 border-l border-zinc-800 p-4 overflow-y-auto shrink-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold">Node Inspector</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-zinc-600 hover:text-zinc-300 text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <Field label="Name" value={selectedNode.name} mono />
              <Field label="Type" value={selectedNode.type} />
              {selectedNode.file_path && (
                <Field label="File" value={selectedNode.file_path} mono small />
              )}
              {selectedNode.language && (
                <Field label="Language" value={selectedNode.language} />
              )}
              {selectedNode.start_line && (
                <Field
                  label="Lines"
                  value={`${selectedNode.start_line} – ${selectedNode.end_line ?? "?"}`}
                />
              )}
            </div>

            <button
              onClick={() => {
                if (selectedNode.file_path) {
                  router.push(
                    `/repositories/${id}/query?q=${encodeURIComponent(
                      `Explain ${selectedNode.name} in ${selectedNode.file_path}`
                    )}`
                  );
                }
              }}
              className="mt-4 w-full py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-xs text-white transition-colors"
            >
              Ask about this node
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  mono = false,
  small = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-zinc-500 mb-0.5">{label}</p>
      <p
        className={`text-zinc-200 break-all ${mono ? "font-mono" : ""} ${
          small ? "text-xs" : "text-sm"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
