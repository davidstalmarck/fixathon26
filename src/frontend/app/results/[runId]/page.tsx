"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import { motion } from "framer-motion";
import { ArrowLeft, FileText, MessageSquare } from "lucide-react";
import Link from "next/link";
import { use } from "react";

import { MoleculeList } from "@/components/features/MoleculeList";
import { ChatResponse, ChatLoadingIndicator } from "@/components/features/ChatResponse";
import { ChatInput } from "@/components/ui/ChatInput";
import { ProgressIndicator } from "@/components/ui/ProgressIndicator";
import { useResearchRun, useRunMolecules } from "@/hooks/useResearchRun";
import { useChat } from "@/hooks/useChat";

interface ResultsPageProps {
  params: Promise<{ runId: string }>;
}

export default function ResultsPage({ params }: ResultsPageProps) {
  const { runId } = use(params);
  const { data: run, isLoading: runLoading, error: runError } = useResearchRun(runId);
  const { data: moleculesData, isLoading: moleculesLoading } = useRunMolecules(
    runId,
    run?.status === "complete"
  );
  const { history, sendMessage, clearHistory, isLoading: chatLoading, error: chatError } = useChat();

  const molecules = moleculesData?.molecules ?? [];

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
            href="/"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-4"
          >
            <ArrowLeft className="size-4" />
            <span>Back to Home</span>
          </Link>

          {run && (
            <div className="bg-white/90 backdrop-blur rounded-xl p-6 shadow-sm">
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                Research Results
              </h1>
              <p className="text-gray-600">{run.query}</p>
            </div>
          )}
        </motion.div>

        {/* Loading state */}
        {runLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-500">Loading...</div>
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

        {/* Progress indicator */}
        {run && (run.status === "queued" || run.status === "processing") && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <ProgressIndicator
              status={run.status}
              moleculeCount={run.moleculeCount}
              paperCount={run.paperCount}
            />
          </motion.div>
        )}

        {/* Error state for failed runs */}
        {run?.status === "failed" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <ProgressIndicator
              status={run.status}
              errorMessage={run.errorMessage}
            />
          </motion.div>
        )}

        {/* Results */}
        {run?.status === "complete" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Stats bar */}
            <div className="flex items-center justify-between bg-white/90 backdrop-blur rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>
                  <strong className="text-gray-900">{run.moleculeCount}</strong> molecules found
                </span>
                <span>
                  <strong className="text-gray-900">{run.paperCount}</strong> papers analyzed
                </span>
              </div>
              <Link
                href={`/summaries/${runId}`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium transition-colors"
              >
                <FileText className="size-4" />
                View Summaries
              </Link>
            </div>

            {/* Molecule grid */}
            <div className="bg-white/90 backdrop-blur rounded-xl p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Discovered Molecules
              </h2>
              {moleculesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-gray-500">Loading molecules...</div>
                </div>
              ) : (
                <MoleculeList
                  molecules={molecules}
                  emptyMessage="No molecules were discovered for this research query."
                />
              )}
            </div>

            {/* Chat section */}
            <div className="bg-white/90 backdrop-blur rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare className="size-5 text-gray-600" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Ask About This Research
                </h2>
              </div>

              {/* Chat messages */}
              <div className="mb-4 max-h-96 overflow-y-auto">
                <ChatResponse messages={history} onClearHistory={clearHistory} />
                {chatLoading && <ChatLoadingIndicator />}
                {chatError && (
                  <div className="mt-2 p-3 rounded-lg bg-red-50 text-red-600 text-sm">
                    {chatError.message || "Failed to get response. Please try again."}
                  </div>
                )}
              </div>

              {/* Chat input */}
              <ChatInput
                onSubmit={sendMessage}
                isLoading={chatLoading}
                placeholder="Ask about the molecules or papers..."
              />
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
