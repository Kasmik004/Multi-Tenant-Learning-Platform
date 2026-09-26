"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/ui/DashboardShell";
import { useAuth } from "@/features/auth/AuthProvider";
import { useApiClient } from "@/hooks/useApiClient";
import { TenantsPanel } from "./TenantsPanel";
import { TenantDetailPanel } from "./TenantDetailPanel";

const NAV_ITEMS = [
  { id: "tenants", label: "Tenants" },
  { id: "health", label: "API Health" },
];

/**
 * Dashboard for platform-level accounts (superadmin, admin, superviewer).
 * Shows tenant management. Superviewers get read-only access.
 */
export function PlatformDashboard() {
  const { user } = useAuth();
  const api = useApiClient();
  const [activeSection, setActiveSection] = useState("tenants");
  // When a tenant is selected, show its detail panel.
  const [selectedTenantSlug, setSelectedTenantSlug] = useState<string | null>(null);

  // Health check state
  const [healthStatus, setHealthStatus] = useState<{ liveness: string; readiness: string; database: string } | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const isReadOnly = user?.platform_role === "superviewer";
  const canCreate = user?.platform_role === "superadmin";
  const canManage = user?.platform_role === "superadmin" || user?.platform_role === "admin";

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    let liveness = "unreachable";
    let readiness = "unreachable";
    let database = "unreachable";
    try {
      const { data } = await api.GET("/api/v1/health");
      if (data?.status === "ok") liveness = "ok";
    } catch { /* unreachable */ }
    try {
      const { data } = await api.GET("/api/v1/health/ready");
      if (data?.status === "ok") readiness = "ok";
      if (data?.database === "ok") database = "ok";
    } catch { /* unreachable */ }
    setHealthStatus({ liveness, readiness, database });
    setHealthLoading(false);
  }, [api]);

  useEffect(() => {
    if (activeSection === "health") checkHealth();
  }, [activeSection, checkHealth]);

  return (
    <DashboardShell
      title="Platform Admin"
      navItems={NAV_ITEMS}
      activeItem={activeSection}
      onNavigate={(id) => {
        setActiveSection(id);
        setSelectedTenantSlug(null);
      }}
    >
      {activeSection === "tenants" && !selectedTenantSlug && (
        <TenantsPanel
          canCreate={canCreate}
          onSelectTenant={setSelectedTenantSlug}
        />
      )}
      {activeSection === "tenants" && selectedTenantSlug && (
        <TenantDetailPanel
          slug={selectedTenantSlug}
          canManage={canManage}
          canDelete={canCreate}
          isReadOnly={isReadOnly}
          onBack={() => setSelectedTenantSlug(null)}
        />
      )}

      {activeSection === "health" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">API Health</h2>
            <button className="btn btn-ghost" onClick={checkHealth} disabled={healthLoading}>
              {healthLoading ? <span className="spinner spinner-sm" /> : "Refresh"}
            </button>
          </div>
          {healthStatus ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {(["liveness", "readiness", "database"] as const).map((key) => (
                <div key={key} className="card flex flex-col items-center gap-3 py-8">
                  <div
                    className={`w-4 h-4 rounded-full ${
                      healthStatus[key] === "ok" ? "bg-[var(--success)]" : "bg-[var(--danger)]"
                    }`}
                    style={{ boxShadow: healthStatus[key] === "ok" ? "0 0 8px var(--success)" : "0 0 8px var(--danger)" }}
                  />
                  <span className="text-sm font-semibold capitalize">{key}</span>
                  <span className={`badge ${healthStatus[key] === "ok" ? "badge-success" : "badge-danger"}`}>
                    {healthStatus[key]}
                  </span>
                </div>
              ))}
            </div>
          ) : healthLoading ? (
            <div className="flex justify-center p-8"><span className="spinner spinner-lg" /></div>
          ) : null}
        </div>
      )}
    </DashboardShell>
  );
}

