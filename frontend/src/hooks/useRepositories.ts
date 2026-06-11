import useSWR, { mutate } from "swr";
import { api } from "@/lib/api";
import type { Repository, IndexingStatus } from "@/types";

const REPOS_KEY = "repositories";

export function useRepositories() {
  const { data, error, isLoading } = useSWR<Repository[]>(
    REPOS_KEY,
    () => api.repositories.list(),
    { refreshInterval: 5000 }
  );

  return {
    repositories: data ?? [],
    isLoading,
    error,
    refresh: () => mutate(REPOS_KEY),
  };
}

export function useRepository(id: string) {
  const { data, error, isLoading } = useSWR<Repository>(
    id ? `repository:${id}` : null,
    () => api.repositories.get(id),
    {
      refreshInterval: (data) =>
        data?.status !== "ready" && data?.status !== "failed" ? 2000 : 0,
    }
  );
  return { repository: data, isLoading, error };
}

export function useIndexingProgress(id: string, enabled: boolean) {
  const { data } = useSWR(
    enabled ? `progress:${id}` : null,
    () => api.repositories.progress(id),
    { refreshInterval: 1500 }
  );
  return data;
}
