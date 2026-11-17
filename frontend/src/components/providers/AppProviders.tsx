"use client";

import React from "react";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "./QueryProvider";

/**
 * Compose the client-side providers required by every page.
 *
 * @param props - Children to wrap.
 * @returns The children inside the query and auth providers.
 */
export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <AuthProvider>{children}</AuthProvider>
    </QueryProvider>
  );
}
