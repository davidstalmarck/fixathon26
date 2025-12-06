"use client";

import { motion } from "framer-motion";
import { Loader2, CheckCircle, XCircle, Clock, Search } from "lucide-react";

import { cn } from "@/utils/cn";
import type { ResearchStatus } from "@/types/research";

interface ProgressIndicatorProps {
  status: ResearchStatus;
  moleculeCount?: number;
  paperCount?: number;
  errorMessage?: string | null;
}

interface StatusConfig {
  icon: typeof Clock;
  text: string;
  description: string;
  color: string;
  bgColor: string;
  animate?: boolean;
}

const statusConfig: Record<ResearchStatus, StatusConfig> = {
  queued: {
    icon: Clock,
    text: "Queued",
    description: "Waiting to start processing...",
    color: "text-gray-500",
    bgColor: "bg-gray-100",
  },
  processing: {
    icon: Loader2,
    text: "Processing",
    description: "Searching PubMed and extracting molecules...",
    color: "text-blue-600",
    bgColor: "bg-blue-100",
    animate: true,
  },
  complete: {
    icon: CheckCircle,
    text: "Complete",
    description: "Research complete!",
    color: "text-green-600",
    bgColor: "bg-green-100",
  },
  failed: {
    icon: XCircle,
    text: "Failed",
    description: "Something went wrong",
    color: "text-red-600",
    bgColor: "bg-red-100",
  },
};

export function ProgressIndicator({
  status,
  moleculeCount = 0,
  paperCount = 0,
  errorMessage,
}: ProgressIndicatorProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-xl border p-6 text-center",
        config.bgColor,
        "border-transparent",
      )}
    >
      <div className="flex flex-col items-center gap-3">
        <div className={cn("p-3 rounded-full", config.bgColor)}>
          <Icon
            className={cn(
              "size-8",
              config.color,
              config.animate && "animate-spin",
            )}
          />
        </div>

        <div>
          <h3 className={cn("font-semibold text-lg", config.color)}>
            {config.text}
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {status === "failed" && errorMessage
              ? errorMessage
              : config.description}
          </p>
        </div>

        {(status === "processing" || status === "complete") && (
          <div className="flex gap-4 mt-2 text-sm text-gray-500">
            <div className="flex items-center gap-1">
              <Search className="size-4" />
              <span>{paperCount} papers</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-mono">🧪</span>
              <span>{moleculeCount} molecules</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

/**
 * Compact inline progress indicator.
 */
export function ProgressBadge({ status }: { status: ResearchStatus }) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
        config.bgColor,
        config.color,
      )}
    >
      <Icon
        className={cn("size-3.5", config.animate && "animate-spin")}
      />
      {config.text}
    </span>
  );
}
