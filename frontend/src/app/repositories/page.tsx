"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, GitBranch, RefreshCw, Trash2 } from "lucide-react";
import { useRepositories } from "@/hooks/useRepositories";
import { RepositoryCard } from "@/components/repository/RepositoryCard";
import { AddRepositoryDialog } from "@/components/repository/AddRepositoryDialog";
import { api } from "@/lib/api";

export default function RepositoriesPage() {
  const router = useRouter();
  const { repositories, isLoading, refresh } = useRepositories();
  const [dialogOpen, setDialogOpen] = useState(false);

  async function handleDelete(id: string) {
    if (!confirm("Remove this repository?")) return;
    await api.repositories.delete(id);
    refresh();
  }

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300">
            <GitBranch className="w-5 h-5" />
          </button>
          <span className="text-zinc-500">/</span>
          <span className="font-semibold text-sm">Repositories</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            className="p-2 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setDialogOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-brand-600 hover:bg-brand-700 text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Repository
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-48 rounded-xl bg-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : repositories.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <GitBranch className="w-12 h-12 text-zinc-700 mb-4" />
            <h3 className="text-zinc-300 font-medium mb-2">No repositories indexed yet</h3>
            <p className="text-zinc-500 text-sm mb-6">
              Add a GitHub URL or upload a ZIP to get started.
            </p>
            <button
              onClick={() => setDialogOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Repository
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repositories.map((repo, i) => (
              <motion.div
                key={repo.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <RepositoryCard
                  repository={repo}
                  onClick={() => router.push(`/repositories/${repo.id}`)}
                  onDelete={() => handleDelete(repo.id)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <AddRepositoryDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSuccess={(repo) => {
          refresh();
          router.push(`/repositories/${repo.id}`);
        }}
      />
    </main>
  );
}
