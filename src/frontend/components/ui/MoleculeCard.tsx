"use client";

import { motion } from "framer-motion";
import { ExternalLink, Beaker, Hash, FileText } from "lucide-react";
import Link from "next/link";

import { cn } from "@/utils/cn";
import type { Molecule } from "@/types/molecule";

interface MoleculeCardProps {
  molecule: Molecule;
  rank?: number;
}

export function MoleculeCard({ molecule, rank }: MoleculeCardProps) {
  const relevancePercent = Math.round(molecule.relevanceScore * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank ? rank * 0.05 : 0 }}
    >
      <Link
        href={`/molecules/${molecule.id}`}
        className="block group"
      >
        <div
          className={cn(
            "rounded-xl border border-gray-200 bg-white p-4 shadow-sm",
            "transition-all duration-200 hover:shadow-md hover:border-gray-300",
            "cursor-pointer",
          )}
        >
          {/* Header with name and relevance */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2">
              {molecule.name}
            </h3>
            <div
              className={cn(
                "shrink-0 px-2 py-0.5 rounded-full text-xs font-medium",
                relevancePercent >= 80
                  ? "bg-green-100 text-green-700"
                  : relevancePercent >= 50
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-gray-100 text-gray-600",
              )}
            >
              {relevancePercent}%
            </div>
          </div>

          {/* Description */}
          {molecule.description && (
            <p className="text-sm text-gray-600 line-clamp-2 mb-3">
              {molecule.description}
            </p>
          )}

          {/* Identifiers */}
          <div className="flex flex-wrap gap-2 text-xs text-gray-500">
            {molecule.casNumber && (
              <div className="flex items-center gap-1">
                <Hash className="size-3" />
                <span>{molecule.casNumber}</span>
              </div>
            )}
            {molecule.smiles && (
              <div className="flex items-center gap-1">
                <Beaker className="size-3" />
                <span className="font-mono truncate max-w-[120px]" title={molecule.smiles}>
                  {molecule.smiles}
                </span>
              </div>
            )}
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

/**
 * Compact molecule tag for use in lists.
 */
interface MoleculeTagProps {
  id: string;
  name: string;
}

export function MoleculeTag({ id, name }: MoleculeTagProps) {
  return (
    <Link
      href={`/molecules/${id}`}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full",
        "text-xs font-medium bg-blue-100 text-blue-700",
        "hover:bg-blue-200 transition-colors",
      )}
    >
      <Beaker className="size-3" />
      <span className="truncate max-w-[120px]">{name}</span>
    </Link>
  );
}
