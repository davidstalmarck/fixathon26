"use client";

import { motion } from "framer-motion";
import { Beaker } from "lucide-react";

import { MoleculeCard } from "@/components/ui/MoleculeCard";
import type { Molecule } from "@/types/molecule";

interface MoleculeListProps {
  molecules: Molecule[];
  emptyMessage?: string;
}

export function MoleculeList({
  molecules,
  emptyMessage = "No molecules discovered yet",
}: MoleculeListProps) {
  if (molecules.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center py-12 text-center"
      >
        <Beaker className="size-12 text-gray-300 mb-4" />
        <p className="text-gray-500">{emptyMessage}</p>
      </motion.div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {molecules.map((molecule, index) => (
        <MoleculeCard
          key={molecule.id}
          molecule={molecule}
          rank={index}
        />
      ))}
    </div>
  );
}
