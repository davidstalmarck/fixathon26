"use client";

import { motion } from "framer-motion";
import { MessageSquare, Search } from "lucide-react";

import { cn } from "@/utils/cn";
import type { InputMode } from "@/components/features/ResearchInput";

interface ModeToggleProps {
  mode: InputMode;
  onModeChange: (mode: InputMode) => void;
  chatDisabled?: boolean;
  chatDisabledReason?: string;
}

export function ModeToggle({
  mode,
  onModeChange,
  chatDisabled = false,
  chatDisabledReason = "No molecules available yet",
}: ModeToggleProps) {
  return (
    <div className="relative flex rounded-full bg-white/80 p-1 shadow-sm backdrop-blur">
      <button
        onClick={() => onModeChange("research")}
        className={cn(
          "relative z-10 flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap",
          mode === "research" ? "text-white" : "text-gray-600 hover:text-gray-900",
        )}
      >
        {mode === "research" && (
          <motion.div
            layoutId="mode-toggle-bg"
            className="absolute inset-0 rounded-full bg-[#121212]"
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        )}
        <Search className="relative size-4 shrink-0" />
        <span className="relative">New Research</span>
      </button>

      <button
        onClick={() => !chatDisabled && onModeChange("chat")}
        disabled={chatDisabled}
        title={chatDisabled ? chatDisabledReason : undefined}
        className={cn(
          "relative z-10 flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap",
          mode === "chat" ? "text-white" : "text-gray-600",
          chatDisabled ? "opacity-40 cursor-not-allowed" : "hover:text-gray-900",
        )}
      >
        {mode === "chat" && (
          <motion.div
            layoutId="mode-toggle-bg"
            className="absolute inset-0 rounded-full bg-[#121212]"
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        )}
        <MessageSquare className="relative size-4 shrink-0" />
        <span className="relative">Chat</span>
      </button>
    </div>
  );
}
