export type IndexingStatus =
  | "pending"
  | "cloning"
  | "parsing"
  | "embedding"
  | "graphing"
  | "ready"
  | "failed";

export interface Repository {
  id: string;
  name: string;
  url: string;
  branch: string;
  status: IndexingStatus;
  languages: string[];
  primary_language?: string;
  framework_hints: string[];
  total_files: number;
  indexed_files: number;
  total_chunks: number;
  description?: string;
  created_at: string;
  updated_at: string;
  indexed_at?: string;
  error_message?: string;
}

export interface IndexingProgress {
  repository_id: string;
  status: IndexingStatus;
  stage: string;
  progress: number;
  current_file?: string;
  message: string;
  indexed_files: number;
  total_files: number;
}

export interface SourceReference {
  chunk_id: string;
  file_path: string;
  chunk_type: string;
  name?: string;
  start_line: number;
  end_line: number;
  relevance_score: number;
  snippet: string;
}

export interface QueryResponse {
  id: string;
  repository_id: string;
  question: string;
  answer: string;
  query_type: string;
  sources: SourceReference[];
  graph_context?: {
    affected_files: string[];
    related_files: string[];
  };
  reasoning_steps: string[];
  created_at: string;
}

export interface GraphNode {
  id: string;
  type: string;
  name: string;
  file_path?: string;
  language?: string;
  start_line?: number;
  end_line?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  edge_type: string;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats?: { node_count: number; edge_count: number };
}

export interface StreamToken {
  type: "metadata" | "token" | "done" | "error";
  content?: string;
  query_type?: string;
  sources?: SourceReference[];
  graph_context?: QueryResponse["graph_context"];
  message?: string;
}
