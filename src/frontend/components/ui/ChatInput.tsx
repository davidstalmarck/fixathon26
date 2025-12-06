"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, MessageSquare, Loader2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";

import { cn } from "@/utils/cn";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

export function ChatInput({
  onSubmit,
  isLoading = false,
  placeholder = "Ask about the research...",
  disabled = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  const handleSubmit = () => {
    if (disabled || isLoading || !value.trim()) return;
    onSubmit(value.trim());
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className={cn(
        "relative flex items-end gap-2 rounded-2xl border border-gray-200 bg-white p-2 shadow-sm",
        "focus-within:border-gray-300 focus-within:shadow-md transition-all",
        disabled && "opacity-50"
      )}
    >
      <MessageSquare className="shrink-0 size-5 text-gray-400 mb-2 ml-1" />

      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        rows={1}
        className={cn(
          "flex-1 resize-none bg-transparent py-2 outline-none",
          "text-gray-900 placeholder:text-gray-400",
          "max-h-32 overflow-y-auto"
        )}
      />

      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.div
            key="loading"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-gray-100"
          >
            <Loader2 className="size-4 text-gray-500 animate-spin" />
          </motion.div>
        ) : (
          <motion.button
            key="submit"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            className={cn(
              "flex size-9 shrink-0 items-center justify-center rounded-full",
              "transition-colors",
              value.trim()
                ? "bg-gray-900 text-white hover:bg-gray-800"
                : "bg-gray-100 text-gray-400"
            )}
          >
            <ArrowUp className="size-4" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
