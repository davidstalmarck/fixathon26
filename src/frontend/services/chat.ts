/**
 * Chat API client for RAG-powered conversations.
 */

import { api } from "./api";
import type { ChatRequest, ChatResponse, ChatMessage } from "@/types/api";

/**
 * Send a chat message and receive a RAG-powered response.
 *
 * @param message - User's current message
 * @param history - Previous conversation messages (max 10)
 * @returns Chat response with message and source citations
 */
export async function sendChatMessage(
  message: string,
  history?: ChatMessage[]
): Promise<ChatResponse> {
  const request: ChatRequest = {
    message,
    history: history?.slice(-10), // Limit to last 10 messages
  };

  return api.post<ChatResponse>("/chat", request);
}
