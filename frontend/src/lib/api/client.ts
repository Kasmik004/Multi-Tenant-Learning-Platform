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
 * @example
 *   const { data, error } = await createApiClient({ token }).GET("/api/v1/courses");
 */
export function createApiClient({ token }: { token?: string } = {}) {
  const client = createClient<paths>({ baseUrl: getApiBaseUrl() });

  if (token) {
    const auth: Middleware = {
      onRequest({ request }) {
        request.headers.set("Authorization", `Bearer ${token}`);
        return request;
      },
    };
    client.use(auth);
  }

  return client;
}
