import createClient, { type Middleware } from "openapi-fetch";

import { getApiBaseUrl } from "@/config/env";
import type { components, paths } from "@/types/api";

/** Backend schema types, e.g. `Schemas["CourseRead"]`. Regenerate with `npm run gen:api`. */
export type Schemas = components["schemas"];

/** Error body returned by the backend's AppError handler. */
export type ApiError = { error: { code: string; message: string } };

/**
 * Creates a fully typed client for the backend API.
 * Paths, params, bodies and responses are all checked against the OpenAPI schema.
 *
 * @param token   - Bearer token from login.
 * @param tenantSlug - Sent as X-Tenant-Slug for tenant-scoped endpoints.
 *
 * @example
 *   const { data, error } = await createApiClient({ token, tenantSlug }).GET("/api/v1/courses");
 */
export function createApiClient({
  token,
  tenantSlug,
}: { token?: string; tenantSlug?: string } = {}) {
  const client = createClient<paths>({ baseUrl: getApiBaseUrl() });

  const headers: Middleware = {
    onRequest({ request }) {
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
      if (tenantSlug) {
        request.headers.set("X-Tenant-Slug", tenantSlug);
      }
      return request;
    },
  };
  client.use(headers);

  return client;
}
