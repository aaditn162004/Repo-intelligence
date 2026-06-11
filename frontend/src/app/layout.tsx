import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RepoIntel — AI Repository Intelligence",
  description:
    "AI-powered platform for deep repository understanding, semantic code search, dependency graphs, and LLM-driven code intelligence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#080810]">{children}</body>
    </html>
  );
}
