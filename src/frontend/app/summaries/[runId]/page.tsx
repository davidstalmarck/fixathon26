"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import { motion } from "framer-motion";
import { ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { use } from "react";

import { SummaryCard } from "@/components/features/SummaryCard";
import { useResearchRun, useRunSummaries } from "@/hooks/useResearchRun";

interface SummariesPageProps {
  params: Promise<{ runId: string }>;
}

export default function SummariesPage({ params }: SummariesPageProps) {
  const { runId } = use(params);
  const { data: run, isLoading: runLoading, error: runError } = useResearchRun(runId);
  const { data: summariesData, isLoading: summariesLoading } = useRunSummaries(
    runId,
    run?.status === "complete"
  );

  const summaries = summariesData?.summaries ?? [];

  return (
    <div className="relative min-h-screen">
      {/* Background */}
      <MeshGradient
        speed={0.5}
        colors={["#C1DAFE", "#96BEFF", "#CFB7FC", "#EBE1F9"]}
        distortion={0.3}
        swirl={0.5}
        grainMixer={0}
        grainOverlay={0}
        style={{
          height: "100%",
          width: "100%",
          position: "fixed",
          top: 0,
          left: 0,
          zIndex: -1,
        }}
      />

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-4xl px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Link
            href={`/results/${runId}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-4"
          >
            <ArrowLeft className="size-4" />
            <span>Back to Results</span>
          </Link>

          {run && (
            <div className="bg-white/90 backdrop-blur rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="size-5 text-gray-600" />
                <h1 className="text-xl font-semibold text-gray-900">
                  Paper Summaries
                </h1>
              </div>
              <p className="text-gray-600">{run.query}</p>
            </div>
          )}
        </motion.div>

        {/* Loading state */}
        {(runLoading || summariesLoading) && (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-500">Loading summaries...</div>
          </div>
        )}

        {/* Error state */}
        {runError && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-6 text-center">
            <p className="text-red-600">
              {runError instanceof Error ? runError.message : "Failed to load research run"}
            </p>
          </div>
        )}

        {/* Summaries list */}
        {run?.status === "complete" && !summariesLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Stats bar */}
            <div className="bg-white/90 backdrop-blur rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>
                  <strong className="text-gray-900">{summaries.length}</strong> papers analyzed
                </span>
                <span>
                  <strong className="text-gray-900">{run.moleculeCount}</strong> molecules found
                </span>
              </div>
            </div>

            {/* Summary cards */}
            {summaries.length > 0 ? (
              <div className="space-y-4">
                {summaries.map((summary, index) => (
                  <SummaryCard
                    key={summary.id}
                    summary={summary}
                    index={index}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-white/90 backdrop-blur rounded-xl p-8 shadow-sm text-center">
                <FileText className="size-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">
                  No paper summaries were generated for this research query.
                </p>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
