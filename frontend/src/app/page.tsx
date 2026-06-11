"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { GitBranch, Search, Zap, Network, FileCode2, ArrowRight } from "lucide-react";
import { AddRepositoryDialog } from "@/components/repository/AddRepositoryDialog";

const FEATURES = [
  {
    icon: FileCode2,
    title: "AST Parsing",
    desc: "Tree-sitter powered extraction of functions, classes, routes, and imports across 10+ languages.",
  },
  {
    icon: Search,
    title: "Semantic Search",
    desc: "BAAI/bge embeddings in Qdrant for repository-aware hybrid retrieval.",
  },
  {
    icon: Network,
    title: "Dependency Graph",
    desc: "Interactive React Flow visualisation of file dependencies, service boundaries, and call graphs.",
  },
  {
    icon: Zap,
    title: "Multi-Agent AI",
    desc: "LangGraph orchestrates Planner, Retriever, Architect, and Impact Analyser agents.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <main className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-brand-400" />
          <span className="font-semibold text-sm tracking-tight">RepoIntel</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/repositories")}
            className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors"
          >
            Repositories
          </button>
          <button
            onClick={() => setDialogOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-brand-600 hover:bg-brand-700 text-white transition-colors"
          >
            <span>Add Repo</span>
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl mx-auto"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-900/40 border border-brand-800 text-brand-400 text-xs mb-6">
            <Zap className="w-3 h-3" />
            Powered by Groq + LangGraph
          </div>

          <h1 className="text-5xl md:text-6xl font-bold leading-tight mb-4">
            <span className="text-gradient">Understand any codebase</span>
            <br />
            <span className="text-zinc-300">in seconds, not hours</span>
          </h1>

          <p className="text-zinc-400 text-lg mb-10 max-w-xl mx-auto">
            AI-powered repository intelligence with semantic search, AST parsing, dependency graphs,
            and multi-agent reasoning. Ask anything, understand everything.
          </p>

          <div className="flex flex-wrap gap-3 justify-center">
            <button
              onClick={() => setDialogOpen(true)}
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors glow-brand"
            >
              Index a Repository
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => router.push("/repositories")}
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-zinc-700 hover:border-zinc-500 text-zinc-300 font-medium transition-colors"
            >
              View Repositories
            </button>
          </div>
        </motion.div>
      </section>

      {/* Feature grid */}
      <section className="px-6 pb-24">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i }}
              className="glass rounded-xl p-5"
            >
              <f.icon className="w-6 h-6 text-brand-400 mb-3" />
              <h3 className="font-semibold text-sm mb-1">{f.title}</h3>
              <p className="text-zinc-500 text-xs leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <AddRepositoryDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSuccess={(repo) => router.push(`/repositories/${repo.id}`)}
      />
    </main>
  );
}
