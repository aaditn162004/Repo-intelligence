"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { GitBranch, Send, Square, Sparkles } from "lucide-react";
import { useStreamingQuery } from "@/hooks/useStreamingQuery";
import { useRepository } from "@/hooks/useRepositories";
import { StreamingResponse } from "@/components/query/StreamingResponse";
import { SourceReferences } from "@/components/query/SourceReferences";
import { motion, AnimatePresence } from "framer-motion";

const EXAMPLE_QUERIES = [
  "Explain the overall architecture of this project",
  "Where is authentication implemented?",
  "Trace the request lifecycle for the main API endpoint",
  "What services are affected if I modify the database layer?",
  "Find potential bug locations related to error handling",
  "Generate documentation for the main module",
];

interface Props {
  params: Promise<{ id: string }>;
}

export default function QueryPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { repository } = useRepository(id);
  const { answer, sources, queryType, graphContext, isStreaming, error, ask, cancel } =
    useStreamingQuery(id);

  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    ask(input.trim());
  }

  return (
    <main className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center gap-2 text-sm shrink-0">
        <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300">
          <GitBranch className="w-5 h-5" />
        </button>
        <span className="text-zinc-600">/</span>
        <button
          onClick={() => router.push("/repositories")}
          className="text-zinc-500 hover:text-zinc-300"
        >
          Repositories
        </button>
        <span className="text-zinc-600">/</span>
        <button
          onClick={() => router.push(`/repositories/${id}`)}
          className="text-zinc-500 hover:text-zinc-300"
        >
          {repository?.name ?? id}
        </button>
        <span className="text-zinc-600">/</span>
        <span className="text-zinc-200 font-medium">Query</span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Main query area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Answer area */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {!answer && !isStreaming ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <Sparkles className="w-10 h-10 text-brand-500/50 mb-4" />
                <h2 className="text-zinc-300 font-medium mb-2">
                  Ask anything about{" "}
                  <span className="text-brand-400">{repository?.name}</span>
                </h2>
                <p className="text-zinc-500 text-sm mb-8 max-w-md">
                  Ask about architecture, trace flows, locate bugs, generate docs, or analyse
                  dependencies.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-2xl">
                  {EXAMPLE_QUERIES.map((q) => (
                    <button
                      key={q}
                      onClick={() => {
                        setInput(q);
                        ask(q);
                      }}
                      className="text-left text-xs px-3 py-2 rounded-lg border border-zinc-800 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto">
                {queryType && (
                  <div className="mb-4">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-brand-900/40 text-brand-400 border border-brand-800">
                      {queryType.replace(/_/g, " ")}
                    </span>
                  </div>
                )}
                <StreamingResponse content={answer} isStreaming={isStreaming} />
                {error && (
                  <p className="mt-4 text-red-400 text-sm">{error}</p>
                )}
              </div>
            )}
          </div>

          {/* Input bar */}
          <div className="border-t border-zinc-800 px-6 py-4 shrink-0">
            <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-end gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder="Ask about architecture, flows, bugs, dependencies…"
                rows={2}
                className="flex-1 resize-none bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-brand-600 transition-colors"
              />
              {isStreaming ? (
                <button
                  type="button"
                  onClick={cancel}
                  className="p-3 rounded-xl bg-red-900/40 border border-red-700 text-red-400 hover:bg-red-900/60 transition-colors"
                >
                  <Square className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="p-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </form>
          </div>
        </div>

        {/* Sources panel */}
        <AnimatePresence>
          {sources.length > 0 && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="border-l border-zinc-800 overflow-y-auto"
            >
              <SourceReferences sources={sources} graphContext={graphContext} />
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
