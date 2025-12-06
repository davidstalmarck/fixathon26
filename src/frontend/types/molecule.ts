/**
 * Molecule types matching API schemas.
 */

import type { PaperSummaryBrief } from "./api";

export interface MoleculeBrief {
  id: string;
  name: string;
}

export interface Molecule {
  id: string;
  name: string;
  casNumber: string | null;
  smiles: string | null;
  description: string | null;
  relevanceScore: number;
}

export interface MoleculeDetail extends Molecule {
  linkedPapers: PaperSummaryBrief[];
}

export interface MoleculeList {
  molecules: Molecule[];
}

export interface HasMoleculesResponse {
  hasMolecules: boolean;
  count: number;
}
