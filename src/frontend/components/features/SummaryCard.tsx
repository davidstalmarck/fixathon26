"use client";

import { motion } from "framer-motion";
import { ExternalLink, FileText } from "lucide-react";

import { cn } from "@/utils/cn";
import { MoleculeTag } from "@/components/ui/MoleculeCard";
import type { PaperSummary } from "@/types/api";

interface SummaryCardProps {
  summary: PaperSummary;
  index?: number;
}

export function SummaryCard({ summary, index }: SummaryCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index ? index * 0.05 : 0 }}
      className={cn(
        "rounded-xl border border-gray-200 bg-white p-5 shadow-sm",
        "transition-all duration-200 hover:shadow-md hover:border-gray-300",
      )}
    >
      {/* Header with title and external link */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-2 min-w-0">
          <FileText className="size-5 text-gray-400 shrink-0 mt-0.5" />
          <h3 className="font-medium text-gray-900 line-clamp-2">
            {summary.title}
          </h3>
        </div>
        {summary.sourceUrl && (
          <a
            href={summary.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "shrink-0 p-1.5 rounded-lg",
              "text-gray-400 hover:text-blue-600 hover:bg-blue-50",
              "transition-colors",
            )}
            title="View on PubMed"
          >
            <ExternalLink className="size-4" />
          </a>
        )}
      </div>

      {/* PubMed ID */}
      <p className="text-xs text-gray-500 mb-3">
        PMID: {summary.pubmedId}
      </p>

      {/* Summary text */}
      <p className="text-sm text-gray-600 leading-relaxed mb-4">
        {summary.summary}
      </p>

      {/* Tagged molecules */}
      {summary.taggedMolecules.length > 0 && (
        <div className="pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-2">Molecules mentioned:</p>
          <div className="flex flex-wrap gap-2">
            {summary.taggedMolecules.map((molecule) => (
              <MoleculeTag
                key={molecule.id}
                id={molecule.id}
                name={molecule.name}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
