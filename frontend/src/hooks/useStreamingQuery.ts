import { useState, useCallback, useRef } from "react";
import type { SourceReference, StreamToken } from "@/types";
import { api } from "@/lib/api";

interface StreamState {
  isStreaming: boolean;
  answer: string;
  sources: SourceReference[];
  queryType: string;
  graphContext?: { affected_files: string[]; related_files: string[] };
  error?: string;
}

export function useStreamingQuery(repositoryId: string) {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    answer: "",
    sources: [],
    queryType: "general",
  });

  const abortRef = useRef<AbortController | null>(null);
  const answerRef = useRef<string>("");
  const tokenQueueRef = useRef<string[]>([]);
  const dripRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const ask = useCallback(
    async (question: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      answerRef.current = "";
      tokenQueueRef.current = [];
      if (dripRef.current) clearInterval(dripRef.current);
      setState({ isStreaming: true, answer: "", sources: [], queryType: "general" });

      // Drip queued tokens into state one at a time at ~30ms each (~33 t/s)
      const intervalId = setInterval(() => {
        const current = answerRef.current;
        setState((s) => {
          if (s.answer === current) return s;
          return { ...s, answer: current };
        });
      }, 16);

      dripRef.current = setInterval(() => {
        if (tokenQueueRef.current.length > 0) {
          answerRef.current += tokenQueueRef.current.shift()!;
        }
      }, 30);

      const { url, body } = api.query.streamUrl(repositoryId, question);

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`Stream failed: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            try {
              const token: StreamToken = JSON.parse(raw);

              if (token.type === "metadata") {
                setState((s) => ({
                  ...s,
                  sources: token.sources ?? [],
                  queryType: token.query_type ?? "general",
                  graphContext: token.graph_context,
                }));
              } else if (token.type === "token") {
                tokenQueueRef.current.push(token.content ?? "");
              } else if (token.type === "done") {
                // drip queue handles the final flush — don't stop streaming here
              } else if (token.type === "error") {
                setState((s) => ({
                  ...s,
                  isStreaming: false,
                  error: token.message,
                }));
              }
            } catch {
              // ignore malformed JSON
            }
          }
        }
      } catch (err: unknown) {
        if ((err as Error).name !== "AbortError") {
          setState((s) => ({
            ...s,
            isStreaming: false,
            error: (err as Error).message,
          }));
        }
      } finally {
        // Keep intervalId running while drip empties, then shut everything down
        const waitForDrip = setInterval(() => {
          if (tokenQueueRef.current.length === 0) {
            clearInterval(waitForDrip);
            clearInterval(intervalId);
            if (dripRef.current) { clearInterval(dripRef.current); dripRef.current = null; }
            setState((s) => ({ ...s, answer: answerRef.current, isStreaming: false }));
          }
        }, 30);
      }
    },
    [repositoryId]
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, ask, cancel };
}
