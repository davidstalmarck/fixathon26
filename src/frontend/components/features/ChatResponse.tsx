"use client";

import { motion } from "framer-motion";
import { User, Bot, FileText, Beaker, Trash2 } from "lucide-react";
import Link from "next/link";

import { cn } from "@/utils/cn";
import type { ChatSource } from "@/types/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

interface ChatResponseProps {
  messages: ChatMessage[];
  onClearHistory?: () => void;
}

export function ChatResponse({ messages, onClearHistory }: ChatResponseProps) {
  if (messages.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Bot className="size-12 mx-auto mb-3 text-gray-300" />
        <p className="text-sm">Ask a question about the research data</p>
        <p className="text-xs mt-1 text-gray-400">
          The assistant will search through papers and molecules to help answer your questions
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with clear button */}
      {messages.length > 0 && onClearHistory && (
        <div className="flex justify-end">
          <button
            onClick={onClearHistory}
            className={cn(
              "flex items-center gap-1 px-2 py-1 text-xs text-gray-500",
              "hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
            )}
          >
            <Trash2 className="size-3" />
            <span>Clear chat</span>
          </button>
        </div>
      )}

      {/* Messages */}
      {messages.map((message, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
          className={cn(
            "flex gap-3",
            message.role === "user" ? "justify-end" : "justify-start"
          )}
        >
          {message.role === "assistant" && (
            <div className="shrink-0 size-8 rounded-full bg-blue-100 flex items-center justify-center">
              <Bot className="size-4 text-blue-600" />
            </div>
          )}

          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-4 py-2",
              message.role === "user"
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-900"
            )}
          >
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>

            {/* Source citations */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-2 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-2">Sources:</p>
                <div className="flex flex-wrap gap-2">
                  {message.sources.map((source) => (
                    <SourceTag key={source.id} source={source} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {message.role === "user" && (
            <div className="shrink-0 size-8 rounded-full bg-gray-200 flex items-center justify-center">
              <User className="size-4 text-gray-600" />
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

interface SourceTagProps {
  source: ChatSource;
}

function SourceTag({ source }: SourceTagProps) {
  const isPaper = source.type === "paper";
  const href = isPaper ? `/summaries/${source.id}` : `/molecules/${source.id}`;

  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs",
        "transition-colors",
        isPaper
          ? "bg-purple-100 text-purple-700 hover:bg-purple-200"
          : "bg-blue-100 text-blue-700 hover:bg-blue-200"
      )}
      title={source.excerpt || source.title}
    >
      {isPaper ? <FileText className="size-3" /> : <Beaker className="size-3" />}
      <span className="truncate max-w-[150px]">{source.title}</span>
    </Link>
  );
}

/**
 * Loading state component for when waiting for AI response.
 */
export function ChatLoadingIndicator() {
  return (
    <div className="flex gap-3 justify-start">
      <div className="shrink-0 size-8 rounded-full bg-blue-100 flex items-center justify-center">
        <Bot className="size-4 text-blue-600" />
      </div>
      <div className="bg-gray-100 rounded-2xl px-4 py-3">
        <div className="flex gap-1">
          <motion.span
            className="size-2 bg-gray-400 rounded-full"
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
          />
          <motion.span
            className="size-2 bg-gray-400 rounded-full"
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
          />
          <motion.span
            className="size-2 bg-gray-400 rounded-full"
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
          />
        </div>
      </div>
    </div>
  );
}
