"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  GitBranch,
  MessageSquare,
  Network,
  FileText,
  RefreshCw,
  ChevronRight,
  Clock,
  Files,
  Layers,
} from "lucide-react";
import { useRepository, useIndexingProgress } from "@/hooks/useRepositories";
import { IndexingProgress } from "@/components/repository/IndexingProgress";
import { api } from "@/lib/api";
import { formatDate, languageColor, statusColor } from "@/lib/utils";

interface Props {
  params: Promise<{ id: string }>;
}

export default function RepositoryDetailPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { repository, isLoading } = useRepository(id);
  const isIndexing =
    repository?.status &&
    !["ready", "failed"].includes(repository.status);

  const progress = useIndexingProgress(id, !!isIndexing);

  async function handleReindex() {
    await api.repositories.reindex(id);
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!repository) {
    return (
      <div className="min-h-screen flex items-center justify-center text-zinc-500">
        Repository not found
      </div>
    );
  }

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm">
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
          <span className="text-zinc-200 font-medium">{repository.name}</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReindex}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-zinc-700 hover:border-zinc-500 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Re-index
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Repo info */}
        <div className="glass rounded-xl p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-semibold mb-1">{repository.name}</h1>
              {repository.url && (
                <a
                  href={repository.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-400 hover:underline"
                >
                  {repository.url}
                </a>
              )}
            </div>
            <span
              className={`text-xs font-medium px-2.5 py-1 rounded-full border ${
                repository.status === "ready"
                  ? "border-emerald-700 bg-emerald-950 text-emerald-400"
                  : repository.status === "failed"
                  ? "border-red-700 bg-red-950 text-red-400"
                  : "border-yellow-700 bg-yellow-950 text-yellow-400"
              }`}
            >
              {repository.status}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat icon={Files} label="Files" value={repository.total_files.toLocaleString()} />
            <Stat icon={Layers} label="Chunks" value={repository.total_chunks.toLocaleString()} />
            <Stat
              icon={GitBranch}
              label="Branch"
              value={repository.branch}
            />
            {repository.indexed_at && (
              <Stat icon={Clock} label="Indexed" value={formatDate(repository.indexed_at)} />
            )}
          </div>

          {/* Languages */}
          {repository.languages.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {repository.languages.slice(0, 8).map((lang) => (
                <span
                  key={lang}
                  className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-300"
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: languageColor(lang) }}
                  />
                  {lang}
                </span>
              ))}
            </div>
          )}

          {/* Framework hints */}
          {repository.framework_hints.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {repository.framework_hints.map((fw) => (
                <span
                  key={fw}
                  className="text-xs px-2 py-0.5 rounded bg-brand-900/40 text-brand-400 border border-brand-800"
                >
                  {fw}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Indexing progress */}
        {isIndexing && progress && (
          <IndexingProgress progress={progress} />
        )}

        {/* Error */}
        {repository.status === "failed" && repository.error_message && (
          <div className="p-4 rounded-xl bg-red-950/30 border border-red-800 text-red-400 text-sm">
            {repository.error_message}
          </div>
        )}

        {/* Action cards */}
        {repository.status === "ready" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ActionCard
              icon={MessageSquare}
              title="Ask Questions"
              description="Natural language queries — architecture, flows, bugs, dependencies."
              onClick={() => router.push(`/repositories/${id}/query`)}
              primary
            />
            <ActionCard
              icon={Network}
              title="Dependency Graph"
              description="Interactive visualisation of file and symbol dependencies."
              onClick={() => router.push(`/repositories/${id}/graph`)}
            />
            <ActionCard
              icon={FileText}
              title="Generate Docs"
              description="AI-generated module documentation and README."
              onClick={() => router.push(`/repositories/${id}/docs`)}
            />
          </div>
        )}
      </div>
    </main>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="w-4 h-4 text-zinc-500 shrink-0" />
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className="text-sm font-medium text-zinc-200">{value}</p>
      </div>
    </div>
  );
}

function ActionCard({
  icon: Icon,
  title,
  description,
  onClick,
  primary = false,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`text-left p-5 rounded-xl border transition-colors w-full ${
        primary
          ? "border-brand-700 bg-brand-900/30 hover:bg-brand-900/50"
          : "border-zinc-800 glass hover:border-zinc-600"
      }`}
    >
      <Icon
        className={`w-6 h-6 mb-3 ${primary ? "text-brand-400" : "text-zinc-400"}`}
      />
      <h3 className="font-semibold text-sm mb-1">{title}</h3>
      <p className="text-xs text-zinc-500 leading-relaxed">{description}</p>
      <ChevronRight className="w-4 h-4 text-zinc-600 mt-2" />
    </motion.button>
  );
}
