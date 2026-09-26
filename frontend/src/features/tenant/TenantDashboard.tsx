"use client";

import { useState } from "react";
import { DashboardShell } from "@/components/ui/DashboardShell";
import { TenantUsersPanel } from "./TenantUsersPanel";
import { TenantCoursesPanel } from "./TenantCoursesPanel";

const NAV_ITEMS = [
  { id: "users", label: "Users" },
  { id: "courses", label: "Courses" },
];

export function TenantDashboard() {
  const [activeSection, setActiveSection] = useState("users");

  return (
    <DashboardShell
      title="Tenant Admin"
      navItems={NAV_ITEMS}
      activeItem={activeSection}
      onNavigate={setActiveSection}
    >
      {activeSection === "users" && <TenantUsersPanel />}
      {activeSection === "courses" && <TenantCoursesPanel />}
    </DashboardShell>
  );
}
