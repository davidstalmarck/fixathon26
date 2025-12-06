/**
 * Research API client functions.
 */

import { api } from "./api";
import type {
  CreateResearchRunRequest,
  ResearchRun,
  ResearchRunDetail,
  ResearchRunList,
} from "@/types/research";
import type { MoleculeList } from "@/types/molecule";

/**
 * Create a new research run.
 */
export async function createResearchRun(
  request: CreateResearchRunRequest
): Promise<ResearchRun> {
  return api.post<ResearchRun>("/research", request);
}

/**
 * Get research run status and details.
 */
export async function getResearchRun(runId: string): Promise<ResearchRunDetail> {
  return api.get<ResearchRunDetail>(`/research/${runId}`);
}

/**
 * Get molecules discovered in a research run.
 */
export async function getRunMolecules(runId: string): Promise<MoleculeList> {
  return api.get<MoleculeList>(`/research/${runId}/molecules`);
}

/**
 * List research run history.
 */
export async function listResearchRuns(
  limit: number = 20,
  offset: number = 0
): Promise<ResearchRunList> {
  return api.get<ResearchRunList>(`/research?limit=${limit}&offset=${offset}`);
}

/**
 * Retry a failed research run.
 */
export async function retryResearchRun(runId: string): Promise<ResearchRun> {
  return api.post<ResearchRun>(`/research/${runId}/retry`);
}
