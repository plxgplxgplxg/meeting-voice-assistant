"use client";

import React from "react";
import {
  isServer,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { isApiError } from "@/lib/api";

const MAX_QUERY_RETRIES = 2;

function shouldRetry(failureCount: number, error: unknown): boolean {
  const isClientError =
    isApiError(error) && error.status >= 400 && error.status < 500;
  return !isClientError && failureCount < MAX_QUERY_RETRIES;
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: shouldRetry,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (isServer) return makeQueryClient();
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

/**
 * Provide the shared React Query client to the app.
 *
 * Client errors (4xx) are not retried so permission and not-found states show
 * immediately; transport and server errors retry twice.
 *
 * @param props - Children to wrap.
 * @returns The children inside a QueryClientProvider.
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>
  );
}
