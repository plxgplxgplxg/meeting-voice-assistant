"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  AUTH_EXPIRED_EVENT,
  clearTokens,
  fetchApi,
  storeTokens,
} from "./api";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await fetchApi<User>("/auth/me");
      setUser(userData);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  useEffect(() => {
    const handleExpired = () => setUser(null);
    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
  }, []);

  const login = async (email: string, password: string) => {
    const tokens = await fetchApi<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    storeTokens(tokens);

    const userData = await fetchApi<User>("/auth/me");
    setUser(userData);
  };

  const register = async (
    email: string,
    fullName: string,
    password: string
  ) => {
    const result = await fetchApi<{ user: User; tokens: AuthTokens }>(
      "/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, full_name: fullName, password }),
      }
    );

    storeTokens(result.tokens);
    setUser(result.user);
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
