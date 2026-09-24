// NEXT_PUBLIC_* values are inlined at build time, so they must be referenced literally.
const publicApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Base URL of the backend API (origin only; generated paths already include /api/v1).
 * Server-side code prefers API_URL_INTERNAL, e.g. http://backend:8000 inside Docker.
 */
export function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.API_URL_INTERNAL ?? publicApiUrl;
  }
  return publicApiUrl;
}
