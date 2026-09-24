import { createApiClient } from "@/lib/api/client";

export type ApiStatus = "ok" | "unreachable";

export async function getApiStatus(): Promise<ApiStatus> {
  try {
    const { data } = await createApiClient().GET("/api/v1/health/ready", {
      cache: "no-store",
    });
    return data?.status === "ok" ? "ok" : "unreachable";
  } catch {
    return "unreachable";
  }
}
