"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { setShareToken } from "@/lib/api";

const ShareTokenContext = createContext<string | null>(null);

interface ShareTokenProviderProps {
  token: string | null;
  children: React.ReactNode;
}

/**
 * Scope a meeting view to a share-link token.
 *
 * The token is registered with the API client before any child mounts, so the
 * first request of every child query already carries it. Children render only
 * once the client holds the matching token.
 *
 * @param props - Token from the URL (null for signed-in access) and children.
 * @returns The children wrapped in the token context, or null while syncing.
 */
export function ShareTokenProvider({ token, children }: ShareTokenProviderProps) {
  const [syncedToken, setSyncedToken] = useState<string | null | undefined>(
    undefined
  );

  useEffect(() => {
    setShareToken(token);
    setSyncedToken(token);
    return () => setShareToken(null);
  }, [token]);

  if (syncedToken !== token) return null;

  return (
    <ShareTokenContext.Provider value={token}>
      {children}
    </ShareTokenContext.Provider>
  );
}

/**
 * Read the share token of the meeting being viewed.
 *
 * @returns The token for guest access, otherwise null.
 */
export function useShareToken(): string | null {
  return useContext(ShareTokenContext);
}

/**
 * Build the public URL guests open to view a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @param token - Share token issued by the backend.
 * @returns Absolute URL on the current origin.
 */
export function buildShareUrl(meetingId: string, token: string): string {
  return `${window.location.origin}/meetings/${meetingId}?share=${encodeURIComponent(token)}`;
}
