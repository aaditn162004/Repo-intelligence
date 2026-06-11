"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";

interface Props {
  content: string;
  isStreaming: boolean;
}

export function StreamingResponse({ content, isStreaming }: Props) {
  if (isStreaming) {
    return (
      <div className="text-zinc-100 text-sm whitespace-pre-wrap leading-relaxed">
        {content}
        <span className="inline-block w-2 h-4 bg-brand-400 animate-pulse ml-0.5 align-text-bottom" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "prose prose-invert prose-sm max-w-none",
        "prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800",
        "prose-code:text-brand-300 prose-code:bg-zinc-900 prose-code:px-1 prose-code:rounded",
        "prose-a:text-brand-400 prose-headings:text-zinc-100",
        "prose-strong:text-zinc-200 prose-blockquote:border-brand-600"
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            return match ? (
              <SyntaxHighlighter
                style={oneDark as Record<string, React.CSSProperties>}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: "0.5rem",
                  fontSize: "0.8rem",
                  background: "#0d0d14",
                }}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
