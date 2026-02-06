import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Parse a UTC timestamp string from the database and return a Date object.
 * Database stores timestamps without timezone info, but they are UTC.
 * We append 'Z' to indicate UTC before parsing.
 */
export function parseUTCDate(dateStr: string | null | undefined): Date | null {
  if (!dateStr) return null;
  // If the date string doesn't end with 'Z', add it to indicate UTC
  const utcStr = dateStr.endsWith('Z') ? dateStr : dateStr.replace(' ', 'T') + 'Z';
  return new Date(utcStr);
}

/**
 * Format a UTC timestamp string from the database in the user's local timezone.
 */
export function formatLocalDateTime(dateStr: string | null | undefined): string {
  const date = parseUTCDate(dateStr);
  if (!date) return '-';
  return date.toLocaleString();
}

/**
 * Format a UTC timestamp string from the database as a local date (no time).
 */
export function formatLocalDate(dateStr: string | null | undefined): string {
  const date = parseUTCDate(dateStr);
  if (!date) return '-';
  return date.toLocaleDateString();
}
