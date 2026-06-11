import useSWR from "swr";
import { api } from "@/lib/api";
import type { GraphData } from "@/types";

export function useFullGraph(repoId: string) {
  const { data, error, isLoading } = useSWR<GraphData>(
    repoId ? `graph:full:${repoId}` : null,
    () => api.graph.full(repoId),
    { revalidateOnFocus: false }
  );
  return { graphData: data, isLoading, error };
}

export function useSubgraph(repoId: string, filePath: string | null, depth = 2) {
  const { data, error, isLoading } = useSWR<GraphData>(
    filePath ? `graph:sub:${repoId}:${filePath}:${depth}` : null,
    () => api.graph.subgraph(repoId, filePath!, depth),
    { revalidateOnFocus: false }
  );
  return { subgraph: data, isLoading, error };
}

export function useArchitectureSummary(repoId: string) {
  const { data } = useSWR(
    repoId ? `arch:${repoId}` : null,
    () => api.graph.architecture(repoId),
    { revalidateOnFocus: false }
  );
  return data;
}
