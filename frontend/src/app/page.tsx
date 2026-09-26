"use client";

import { useAuth } from "@/features/auth/AuthProvider";
import { LoginPage } from "@/features/auth/LoginPage";
import { PlatformDashboard } from "@/features/platform/PlatformDashboard";
import { TenantDashboard } from "@/features/tenant/TenantDashboard";
import { LearnerDashboard } from "@/features/learner/LearnerDashboard";

/**
 * Root page: shows login when unauthenticated, then routes to the
 * correct dashboard based on the user's role from /auth/me.
 */
export default function Home() {
  const { user, loading } = useAuth();

  // Initial session check — show a centered spinner.
  if (loading) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <div className="spinner spinner-lg" />
      </main>
    );
  }

  // Not logged in — show login form.
  if (!user) {
    return <LoginPage />;
  }

  // Platform account (superadmin / admin / superviewer) — no tenant.
  if (user.platform_role) {
    return <PlatformDashboard />;
  }

  // Tenant admin — manage users, courses, enrollments.
  if (user.tenant_role === "tenantadmin") {
    return <TenantDashboard />;
  }

  // Regular tenant user (learner).
  return <LearnerDashboard />;
}
