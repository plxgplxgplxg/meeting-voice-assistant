import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class names without style conflicts.
 *
 * @param inputs - Array of class name expressions.
 * @returns Combined class string.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format duration in seconds to standard HH:MM:SS or MM:SS string.
 *
 * @param seconds - Duration in seconds.
 * @returns Formatted time string.
 */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}
