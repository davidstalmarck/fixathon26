/**
 * Research run types matching API schemas.
 */

export type ResearchStatus = "queued" | "processing" | "complete" | "failed";

export interface ResearchRun {
  id: string;
  query: string;
  status: ResearchStatus;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  errorMessage: string | null;
}

export interface ResearchRunDetail extends ResearchRun {
  moleculeCount: number;
  paperCount: number;
}

export interface ResearchRunList {
  runs: ResearchRun[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface CreateResearchRunRequest {
  query: string;
}
