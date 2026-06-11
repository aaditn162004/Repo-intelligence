"use client";

import { Trash2, GitBranch, Files, Layers, Clock } from "lucide-react";
import type { Repository } from "@/types";
import { formatDate, languageColor, statusColor } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Props {
  repository: Repository;
  onClick: () => void;
  onDelete: () => void;
}

const STATUS_DOTS: Record<string, string> = {
  ready: "bg-emerald-400",
  failed: "bg-red-400",
  pending: "bg-zinc-500",
  cloning: "bg-blue-400 animate-pulse2",
  parsing: "bg-yellow-400 animate-pulse2",
  embedding: "bg-purple-400 animate-pulse2",
  graphing: "bg-cyan-400 animate-pulse2",
};

export function RepositoryCard({ repository, onClick, onDelete }: Props) {
  const isReady = repository.status === "ready";
  const isFailed = repository.status === "failed";

  return (
    <div
      onClick={onClick}
      className={cn(
        "group relative cursor-pointer rounded-xl border p-5 transition-all duration-200",
        "glass hover:border-zinc-600",
        isFailed && "border-red-900/50"
      )}
    >
      {/* Delete button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="absolute top-3 right-3 p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-950/30 opacity-0 group-hover:opacity-100 transition-all"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>

      {/* Status dot + name */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={cn(
            "w-2 h-2 rounded-full shrink-0",
            STATUS_DOTS[repository.status] ?? "bg-zinc-500"
          )}
        />
        <h3 className="font-medium text-sm truncate pr-6">{repository.name}</h3>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs text-zinc-500 mb-3">
        <span className="flex items-center gap-1">
          <Files className="w-3 h-3" />
          {repository.total_files.toLocaleString()} files
        </span>
        {isReady && (
          <span className="flex items-center gap-1">
            <Layers className="w-3 h-3" />
            {repository.total_chunks.toLocaleString()} chunks
          </span>
        )}
        <span className="flex items-center gap-1 ml-auto">
          <GitBranch className="w-3 h-3" />
          {repository.branch}
        </span>
      </div>

      {/* Languages */}
      {repository.languages.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {repository.languages.slice(0, 4).map((lang) => (
            <span
              key={lang}
              className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400"
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: languageColor(lang) }}
              />
              {lang}
            </span>
          ))}
          {repository.languages.length > 4 && (
            <span className="text-xs text-zinc-600">
              +{repository.languages.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-1">
        <span className={cn("text-xs font-medium capitalize", statusColor(repository.status))}>
          {repository.status}
        </span>
        {repository.indexed_at && (
          <span className="text-xs text-zinc-600 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDate(repository.indexed_at)}
          </span>
        )}
      </div>

      {/* Error */}
      {isFailed && repository.error_message && (
        <p className="mt-2 text-xs text-red-400 truncate">{repository.error_message}</p>
      )}
    </div>
  );
}
