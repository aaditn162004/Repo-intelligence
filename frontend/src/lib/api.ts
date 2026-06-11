import type {
  Repository,
  IndexingProgress,
  QueryResponse,
  GraphData,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
  : "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ---------- Repositories ----------

export const api = {
  repositories: {
    list: () => request<Repository[]>("/repositories"),

    get: (id: string) => request<Repository>(`/repositories/${id}`),

    create: (url: string, branch = "main", name?: string) =>
      request<Repository>("/repositories", {
        method: "POST",
        body: JSON.stringify({ url, branch, name }),
      }),

    upload: async (file: File, name: string) => {
      const form = new FormData();
      form.append("file", file);
      form.append("name", name);
      const res = await fetch(`${BASE}/repositories/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`Upload failed: ${await res.text()}`);
      return res.json() as Promise<Repository>;
    },

    delete: (id: string) =>
      request<void>(`/repositories/${id}`, { method: "DELETE" }),

    reindex: (id: string) =>
      request<Repository>(`/repositories/${id}/reindex`, { method: "POST" }),

    progress: (id: string) =>
      request<IndexingProgress>(`/repositories/${id}/progress`),
  },

  query: {
    ask: (repositoryId: string, question: string, top_k = 10) =>
      request<QueryResponse>("/query", {
        method: "POST",
        body: JSON.stringify({
          repository_id: repositoryId,
          question,
          max_context_chunks: top_k,
          stream: false,
        }),
      }),

    streamUrl: (repositoryId: string, question: string) => {
      const body = JSON.stringify({
        repository_id: repositoryId,
        question,
        stream: true,
      });
      return { url: `${BASE}/query/stream`, body };
    },
  },

  graph: {
    full: (repoId: string) => request<GraphData>(`/graph/${repoId}/full`),

    subgraph: (repoId: string, filePath: string, depth = 2) =>
      request<GraphData>(
        `/graph/${repoId}/subgraph?file_path=${encodeURIComponent(filePath)}&depth=${depth}`
      ),

    affected: (repoId: string, filePath: string) =>
      request<{ file_path: string; affected_files: string[] }>(
        `/graph/${repoId}/affected?file_path=${encodeURIComponent(filePath)}`
      ),

    architecture: (repoId: string) =>
      request<Record<string, unknown>>(`/graph/${repoId}/architecture`),
  },

  documentation: {
    generate: (
      repositoryId: string,
      target: string,
      docType: string = "module"
    ) =>
      request<{ content: string }>("/documentation/generate", {
        method: "POST",
        body: JSON.stringify({ repository_id: repositoryId, target, doc_type: docType }),
      }),

    readme: (repoId: string) =>
      fetch(`${BASE}/documentation/${repoId}/readme`).then((r) => r.text()),
  },
};
