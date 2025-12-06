/**
 * Shared API types.
 */

import type { MoleculeBrief } from "./molecule";

export interface ApiError {
  error: string;
  message: string;
}

export interface PaperSummaryBrief {
  id: string;
  title: string;
  contextExcerpt: string | null;
}

export interface PaperSummary {
  id: string;
  pubmedId: string;
  title: string;
  summary: string;
  sourceUrl: string | null;
  taggedMolecules: MoleculeBrief[];
}

export interface PaperSummaryList {
  summaries: PaperSummary[];
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatMessage[];
}

export type ChatSourceType = "paper" | "molecule";

export interface ChatSource {
  type: ChatSourceType;
  id: string;
  title: string;
  excerpt: string | null;
}

export interface ChatResponse {
  message: string;
  sources: ChatSource[];
}
