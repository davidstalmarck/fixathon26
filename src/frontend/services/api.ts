/**
 * API client base configuration with fetch wrapper and error handling.
 */

import type { ApiError } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly error: string,
    message: string
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

interface FetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: "unknown_error",
        message: `HTTP ${response.status}: ${response.statusText}`,
      };
    }
    throw new ApiClientError(response.status, errorData.error, errorData.message);
  }

  return response.json();
}

export async function apiClient<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const config: RequestInit = {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };

  if (body !== undefined) {
    config.body = JSON.stringify(body);
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, config);

  return handleResponse<T>(response);
}

export const api = {
  get: <T>(endpoint: string, options?: Omit<FetchOptions, "method">) =>
    apiClient<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: Omit<FetchOptions, "method" | "body">) =>
    apiClient<T>(endpoint, { ...options, method: "POST", body }),

  put: <T>(endpoint: string, body?: unknown, options?: Omit<FetchOptions, "method" | "body">) =>
    apiClient<T>(endpoint, { ...options, method: "PUT", body }),

  delete: <T>(endpoint: string, options?: Omit<FetchOptions, "method">) =>
    apiClient<T>(endpoint, { ...options, method: "DELETE" }),
};
