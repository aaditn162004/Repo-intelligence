"use client";

import { FileCode2, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import type { SourceReference } from "@/types";
import { chunkTypeIcon, languageColor } from "@/lib/utils";

interface Props {
  sources: SourceReference[];
  graphContext?: { affected_files: string[]; related_files: string[] };
}

export function SourceReferences({ sources, graphContext }: Props) {
  return (
    <div className="p-4 min-w-[280px]">
      <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
        Sources ({sources.length})
      </h3>

      <div className="space-y-2">
        {sources.map((src) => (
          <SourceItem key={src.chunk_id} source={src} />
        ))}
      </div>

      {graphContext &&
        (graphContext.affected_files.length > 0 || graphContext.related_files.length > 0) && (
          <div className="mt-5">
            <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Graph Context
            </h3>
            {graphContext.affected_files.length > 0 && (
              <FileList title="Affected Files" files={graphContext.affected_files} color="red" />
            )}
            {graphContext.related_files.length > 0 && (
              <FileList title="Related Files" files={graphContext.related_files} color="blue" />
            )}
          </div>
        )}
    </div>
  );
}

function SourceItem({ source }: { source: SourceReference }) {
  const [expanded, setExpanded] = useState(false);
  const fileName = source.file_path.split("/").pop() ?? source.file_path;

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-2 p-2.5 hover:bg-zinc-800/50 transition-colors text-left"
      >
        <span className="mt-0.5 text-xs font-mono text-brand-400 shrink-0">
          {chunkTypeIcon(source.chunk_type)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-zinc-200 truncate">
            {source.name || fileName}
          </p>
          <p className="text-xs text-zinc-500 truncate">{source.file_path}</p>
          <p className="text-xs text-zinc-600 mt-0.5">
            lines {source.start_line}–{source.end_line} ·{" "}
            <span className="text-brand-500">
              {Math.round(source.relevance_score * 100)}% match
            </span>
          </p>
        </div>
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-zinc-600 shrink-0 mt-0.5" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-zinc-600 shrink-0 mt-0.5" />
        )}
      </button>

      {expanded && (
        <pre className="px-3 pb-3 text-xs font-mono text-zinc-400 bg-zinc-900/50 overflow-x-auto whitespace-pre-wrap">
          {source.snippet}
        </pre>
      )}
    </div>
  );
}

function FileList({
  title,
  files,
  color,
}: {
  title: string;
  files: string[];
  color: "red" | "blue";
}) {
  const colorClass = color === "red" ? "text-red-400" : "text-blue-400";
  return (
    <div className="mb-3">
      <p className={`text-xs font-medium mb-1.5 ${colorClass}`}>{title}</p>
      <div className="space-y-1">
        {files.slice(0, 6).map((f) => (
          <div key={f} className="flex items-center gap-1.5">
            <FileCode2 className="w-3 h-3 text-zinc-600 shrink-0" />
            <span className="text-xs text-zinc-500 truncate">{f}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
