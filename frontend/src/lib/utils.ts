import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { IndexingStatus } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function statusColor(status: IndexingStatus): string {
  const map: Record<IndexingStatus, string> = {
    pending: "text-zinc-400",
    cloning: "text-blue-400",
    parsing: "text-yellow-400",
    embedding: "text-purple-400",
    graphing: "text-cyan-400",
    ready: "text-emerald-400",
    failed: "text-red-400",
  };
  return map[status] ?? "text-zinc-400";
}

export function statusBadgeVariant(
  status: IndexingStatus
): "default" | "secondary" | "destructive" | "outline" {
  if (status === "ready") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function languageColor(lang: string): string {
  const colors: Record<string, string> = {
    python: "#3572A5",
    javascript: "#f1e05a",
    typescript: "#3178c6",
    java: "#b07219",
    go: "#00ADD8",
    rust: "#dea584",
    cpp: "#f34b7d",
    ruby: "#701516",
    php: "#4F5D95",
  };
  return colors[lang.toLowerCase()] ?? "#6b7280";
}

export function chunkTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    function: "ƒ",
    method: "m",
    class: "C",
    module: "M",
    route: "⚡",
    import: "↓",
    interface: "I",
    type: "T",
  };
  return icons[type] ?? "◆";
}
