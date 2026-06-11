"use client";

import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import type { IndexingProgress as IProgress } from "@/types";

interface Props {
  progress: IProgress;
}

const STAGE_ORDER = ["cloning", "parsing", "embedding", "graphing", "ready"];

export function IndexingProgress({ progress }: Props) {
  const currentIdx = STAGE_ORDER.indexOf(progress.status);

  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Loader2 className="w-4 h-4 text-brand-400 animate-spin" />
        <span className="text-sm font-medium">Indexing in progress…</span>
        <span className="ml-auto text-xs text-zinc-500">
          {Math.round(progress.progress)}%
        </span>
      </div>

      {/* Stage pipeline */}
      <div className="flex items-center gap-1 mb-4">
        {STAGE_ORDER.slice(0, -1).map((stage, i) => {
          const done = currentIdx > i;
          const active = currentIdx === i;
          return (
            <div key={stage} className="flex items-center flex-1 gap-1">
              <div
                className={`flex-1 h-1 rounded-full transition-all duration-500 ${
                  done
                    ? "bg-brand-500"
                    : active
                    ? "bg-brand-500/50"
                    : "bg-zinc-800"
                }`}
              />
              {i < STAGE_ORDER.length - 2 && (
                <div
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    done ? "bg-brand-500" : active ? "bg-brand-400 animate-pulse" : "bg-zinc-700"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-brand-600 to-purple-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress.progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-zinc-500">
        <span>{progress.message}</span>
        {progress.total_files > 0 && (
          <span>
            {progress.indexed_files} / {progress.total_files} files
          </span>
        )}
      </div>

      {progress.current_file && (
        <p className="mt-1 text-xs text-zinc-600 truncate font-mono">
          {progress.current_file}
        </p>
      )}
    </div>
  );
}
