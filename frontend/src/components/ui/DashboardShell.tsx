"use client";

import type { ReactNode } from "react";

import { useAuth } from "@/features/auth/AuthProvider";

interface NavItem {
  id: string;
  label: string;
}

interface Props {
  title: string;
  navItems: NavItem[];
  activeItem: string;
  onNavigate: (id: string) => void;
  children: ReactNode;
}

/**
 * Shared dashboard shell with a sidebar and topbar.
 * Used by Platform, TenantAdmin, and Learner dashboards.
 */
export function DashboardShell({ title, navItems, activeItem, onNavigate, children }: Props) {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen flex-col">
      {/* Top bar */}
      <div className="topbar">
        <span className="text-sm font-semibold">{title}</span>
        <div className="flex items-center gap-3 text-sm">
          <span style={{ color: "var(--muted)" }}>
            {user?.email}
            {user?.platform_role && (
              <span className="badge badge-info ml-2">{user.platform_role}</span>
            )}
            {user?.tenant_role && (
              <span className="badge badge-info ml-2">{user.tenant_role}</span>
            )}
          </span>
          <button onClick={logout} className="btn btn-ghost btn-sm cursor-pointer">
            Sign out
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="sidebar">
          <div className="sidebar-section">Navigation</div>
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`sidebar-link cursor-pointer ${activeItem === item.id ? "active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
