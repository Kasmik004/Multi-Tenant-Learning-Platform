"use client";

import { useMemo } from "react";

import { useAuth } from "@/features/auth/AuthProvider";
import { createApiClient } from "@/lib/api/client";

/**
 * Returns a typed API client that automatically injects the Bearer token
 * and X-Tenant-Slug header from the current auth session.
 *
 * Must be called inside <AuthProvider>.
 */
export function useApiClient() {
  const { token, user } = useAuth();

  return useMemo(
    () =>
      createApiClient({
        token: token ?? undefined,
        tenantSlug: user?.tenant_slug ?? undefined,
      }),
    [token, user?.tenant_slug],
  );
}
