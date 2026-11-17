import type { ChangePasswordResult, User } from "@/types/api";
import { fetchApi } from "./client";

/**
 * Update the display name of the signed-in user.
 *
 * @param fullName - New display name.
 * @returns The updated user.
 */
export function updateProfile(fullName: string): Promise<User> {
  return fetchApi<User>("/users/me", {
    method: "PATCH",
    body: JSON.stringify({ full_name: fullName }),
  });
}

/**
 * Change the password and receive a fresh token pair.
 *
 * @param oldPassword - Current password.
 * @param newPassword - New password.
 * @returns New tokens; the previous ones stop working.
 */
export function changePassword(
  oldPassword: string,
  newPassword: string
): Promise<ChangePasswordResult> {
  return fetchApi<ChangePasswordResult>("/users/me/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}
