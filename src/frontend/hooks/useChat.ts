/**
 * Hook for managing chat state with TanStack Query and session storage.
 */

import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { sendChatMessage } from "@/services/chat";
import type { ChatMessage, ChatResponse, ChatSource } from "@/types/api";

const SESSION_STORAGE_KEY = "molecule-research-chat-history";
const MAX_HISTORY_LENGTH = 20;

interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

interface UseChatReturn {
  /** Chat message history */
  history: ChatHistoryItem[];
  /** Send a new message */
  sendMessage: (message: string) => void;
  /** Clear chat history */
  clearHistory: () => void;
  /** Whether a message is being sent */
  isLoading: boolean;
  /** Error from the last message attempt */
  error: Error | null;
}

/**
 * Hook for chat state management with session storage persistence.
 *
 * Maintains conversation history in session storage and uses TanStack Query
 * for mutations. Automatically includes history context in API calls.
 */
export function useChat(): UseChatReturn {
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load history from session storage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setHistory(parsed);
        }
      }
    } catch {
      // Ignore parse errors, start with empty history
    }
    setIsInitialized(true);
  }, []);

  // Save history to session storage whenever it changes
  useEffect(() => {
    if (isInitialized && history.length > 0) {
      try {
        sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(history));
      } catch {
        // Ignore storage errors
      }
    }
  }, [history, isInitialized]);

  const mutation = useMutation({
    mutationFn: async (message: string) => {
      // Convert history to ChatMessage format for API
      const apiHistory: ChatMessage[] = history.map((item) => ({
        role: item.role,
        content: item.content,
      }));

      return sendChatMessage(message, apiHistory);
    },
    onSuccess: (response: ChatResponse, message: string) => {
      setHistory((prev) => {
        const newHistory = [
          ...prev,
          { role: "user" as const, content: message },
          {
            role: "assistant" as const,
            content: response.message,
            sources: response.sources,
          },
        ];
        // Keep only the last MAX_HISTORY_LENGTH items
        return newHistory.slice(-MAX_HISTORY_LENGTH);
      });
    },
  });

  const sendMessage = useCallback(
    (message: string) => {
      if (message.trim() && !mutation.isPending) {
        mutation.mutate(message);
      }
    },
    [mutation]
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }, []);

  return {
    history,
    sendMessage,
    clearHistory,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Query key factory for chat queries.
 */
export const chatKeys = {
  all: ["chat"] as const,
  history: () => [...chatKeys.all, "history"] as const,
};
