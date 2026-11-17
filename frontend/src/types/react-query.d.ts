import type { ApiError } from "@/lib/api";

declare module "@tanstack/react-query" {
  interface Register {
    defaultError: ApiError;
  }
}
