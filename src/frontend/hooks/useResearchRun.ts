/**
 * Hook for managing research run state with TanStack Query.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createResearchRun,
  getResearchRun,
  getRunMolecules,
  getRunSummaries,
  retryResearchRun,
} from "@/services/research";
import type { CreateResearchRunRequest, ResearchRunDetail } from "@/types/research";
import type { MoleculeList } from "@/types/molecule";
import type { PaperSummaryList } from "@/types/api";

const POLLING_INTERVAL = 5000; // 5 seconds

/**
 * Query key factory for research runs.
 */
export const researchKeys = {
  all: ["research"] as const,
  run: (id: string) => [...researchKeys.all, "run", id] as const,
  molecules: (id: string) => [...researchKeys.all, "molecules", id] as const,
  summaries: (id: string) => [...researchKeys.all, "summaries", id] as const,
};

/**
 * Hook for fetching research run status with polling.
 * Polls every 5 seconds while the run is queued or processing.
 */
export function useResearchRun(runId: string | null) {
  return useQuery<ResearchRunDetail | null>({
    queryKey: researchKeys.run(runId ?? ""),
    queryFn: async () => {
      if (!runId) return null;
      return getResearchRun(runId);
    },
    enabled: !!runId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "queued" || data.status === "processing")) {
        return POLLING_INTERVAL;
      }
      return false;
    },
  });
}

/**
 * Hook for fetching molecules from a research run.
 */
export function useRunMolecules(runId: string | null, enabled: boolean = true) {
  return useQuery<MoleculeList | null>({
    queryKey: researchKeys.molecules(runId ?? ""),
    queryFn: async () => {
      if (!runId) return null;
      return getRunMolecules(runId);
    },
    enabled: !!runId && enabled,
  });
}

/**
 * Hook for creating a new research run.
 */
export function useCreateResearchRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateResearchRunRequest) => createResearchRun(request),
    onSuccess: (data) => {
      // Invalidate the runs list
      queryClient.invalidateQueries({ queryKey: researchKeys.all });
      // Prime the cache with the new run
      queryClient.setQueryData(researchKeys.run(data.id), {
        ...data,
        moleculeCount: 0,
        paperCount: 0,
      } as ResearchRunDetail);
    },
  });
}

/**
 * Hook for retrying a failed research run.
 */
export function useRetryResearchRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => retryResearchRun(runId),
    onSuccess: (data) => {
      // Invalidate the specific run query to refetch
      queryClient.invalidateQueries({ queryKey: researchKeys.run(data.id) });
    },
  });
}

/**
 * Hook for fetching paper summaries from a research run.
 */
export function useRunSummaries(runId: string | null, enabled: boolean = true) {
  return useQuery<PaperSummaryList | null>({
    queryKey: researchKeys.summaries(runId ?? ""),
    queryFn: async () => {
      if (!runId) return null;
      return getRunSummaries(runId);
    },
    enabled: !!runId && enabled,
  });
}
