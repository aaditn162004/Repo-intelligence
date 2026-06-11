"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { GitBranch, FileText, Loader2, Download } from "lucide-react";
import { api } from "@/lib/api";
import { useRepository } from "@/hooks/useRepositories";
import { StreamingResponse } from "@/components/query/StreamingResponse";

interface Props {
  params: Promise<{ id: string }>;
}

const DOC_TYPES = [
  { value: "module", label: "Module" },
  { value: "function", label: "Function/Method" },
  { value: "api", label: "API Endpoints" },
  { value: "architecture", label: "Architecture" },
  { value: "readme", label: "README" },
];

export default function DocsPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { repository } = useRepository(id);

  const [target, setTarget] = useState("");
  const [docType, setDocType] = useState("module");
  const [content, setContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setContent("");
    setIsLoading(true);
    try {
      if (docType === "readme") {
        const text = await api.documentation.readme(id);
        setContent(text);
      } else {
        const res = await api.documentation.generate(id, target, docType);
        setContent(res.content);
      }
    } catch (err: unknown) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  function downloadMd() {
    const blob = new Blob([content], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${target || "readme"}.md`;
    a.click();
  }

  return (
    <main className="min-h-screen flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center gap-2 text-sm shrink-0">
        <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300">
          <GitBranch className="w-5 h-5" />
        </button>
        <span className="text-zinc-600">/</span>
        <button
          onClick={() => router.push(`/repositories/${id}`)}
          className="text-zinc-500 hover:text-zinc-300"
        >
          {repository?.name ?? id}
        </button>
        <span className="text-zinc-600">/</span>
        <span className="text-zinc-200 font-medium">Documentation</span>
      </header>

      <div className="max-w-4xl mx-auto w-full px-6 py-8">
        {/* Controls */}
        <form onSubmit={handleGenerate} className="glass rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold mb-4">Generate Documentation</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs text-zinc-400 mb-1.5">Target</label>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. UserService, auth module, /api/login"
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-brand-600 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-brand-600"
              >
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <p className="text-xs text-zinc-500">
              Select README to generate a full project README automatically
            </p>
            <button
              type="submit"
              disabled={isLoading || (docType !== "readme" && !target.trim())}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-sm text-white transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Generate
            </button>
          </div>
        </form>

        {error && (
          <div className="p-4 rounded-xl bg-red-950/30 border border-red-800 text-red-400 text-sm mb-6">
            {error}
          </div>
        )}

        {content && (
          <div className="glass rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold">Generated Documentation</h3>
              <button
                onClick={downloadMd}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-zinc-700 hover:border-zinc-500 text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Download .md
              </button>
            </div>
            <StreamingResponse content={content} isStreaming={false} />
          </div>
        )}
      </div>
    </main>
  );
}
