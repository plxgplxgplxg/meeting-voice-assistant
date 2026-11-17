import type { RegisterResult, TokenPair, User } from "@/types/api";
import { fetchApi } from "./client";

/**
 * Exchange credentials for a token pair.
 *
 * @param email - Account email.
 * @param password - Account password.
 * @returns Access and refresh tokens.
 */
export function loginRequest(email: string, password: string): Promise<TokenPair> {
  return fetchApi<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

/**
 * Create an account and sign it in.
 *
 * @param email - Account email.
 * @param fullName - Display name.
 * @param password - Account password.
 * @returns The new user and its token pair.
 */
export function registerRequest(
  email: string,
  fullName: string,
  password: string
): Promise<RegisterResult> {
  return fetchApi<RegisterResult>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, full_name: fullName, password }),
  });
}

/**
 * Fetch the signed-in user.
 *
 * @returns Current user profile.
 */
export function getCurrentUser(): Promise<User> {
  return fetchApi<User>("/auth/me");
}
