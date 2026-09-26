"use client";

import { useCallback, useEffect, useState } from "react";
import { useApiClient } from "@/hooks/useApiClient";
import type { Schemas } from "@/lib/api/client";

type TenantRead = Schemas["TenantRead"];

interface Props {
  canCreate: boolean;
  onSelectTenant: (slug: string) => void;
}

export function TenantsPanel({ canCreate, onSelectTenant }: Props) {
  const api = useApiClient();
  const [tenants, setTenants] = useState<TenantRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState("");
  const [successNotice, setSuccessNotice] = useState<{
    slug: string;
    email?: string;
    token?: string;
    activated: boolean;
  } | null>(null);

  const fetchTenants = useCallback(async () => {
    const { data, error } = await api.GET("/api/v1/tenants");
    if (error) {
      setError("Failed to load tenants");
    } else if (data) {
      setTenants(data.items);
      setError("");
    }
    setLoading(false);
  }, [api]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTenants();
  }, [fetchTenants]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateBusy(true);
    setCreateError("");
    setSuccessNotice(null);

    const slug = newSlug.trim().toLowerCase();
    const name = newName.trim();
    const email = adminEmail.trim().toLowerCase();
    const adminFullName = adminName.trim() || email.split("@")[0];

    // 1. Create the tenant
    const { data: tenantData, error: tenantErr } = await api.POST("/api/v1/tenants", {
      body: { name, slug },
    });

    if (tenantErr || !tenantData) {
      setCreateBusy(false);
      const errObj = tenantErr as { error?: { message?: string } } | undefined;
      setCreateError(
        errObj?.error?.message || "Failed to create tenant. Ensure slug is unique, lowercase alphanumeric."
      );
      return;
    }

    let token: string | undefined;
    let activated = false;

    // 2. If admin email was entered, invite the admin
    if (email) {
      const { data: inviteData, error: inviteErr } = await api.POST("/api/v1/users/invites", {
        headers: { "X-Tenant-Slug": slug },
        body: {
          email,
          full_name: adminFullName,
          role: "tenantadmin",
        },
      });

      if (inviteErr || !inviteData) {
        setCreateBusy(false);
        const errObj = inviteErr as { error?: { message?: string } } | undefined;
        setCreateError(
          `Tenant '${slug}' created, but failed to invite admin: ${errObj?.error?.message || "Check email format"}`
        );
        fetchTenants();
        return;
      }

      token = inviteData.invite_token;

      // 3. If password was provided (min 8 chars), accept the invite right away
      if (adminPassword.length >= 8) {
        const { error: acceptErr } = await api.POST("/api/v1/auth/accept-invite", {
          body: {
            token,
            password: adminPassword,
            confirm_password: adminPassword,
          },
        });

        if (acceptErr) {
          setCreateBusy(false);
          setCreateError(
            `Tenant & admin created, but password activation failed. Invite token: ${token}`
          );
          fetchTenants();
          return;
        }

        activated = true;
      }
    }

    setCreateBusy(false);
    setShowCreate(false);
    setNewName("");
    setNewSlug("");
    setAdminEmail("");
    setAdminName("");
    setAdminPassword("");
    setSuccessNotice({
      slug,
      email: email || undefined,
      token,
      activated,
    });
    fetchTenants();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Tenants</h2>
        {canCreate && !showCreate && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + New Tenant
          </button>
        )}
      </div>

      {successNotice && (
        <div className="alert-success card space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base">
              Tenant &apos;{successNotice.slug}&apos; Created!
            </h3>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setSuccessNotice(null)}
            >
              ✕
            </button>
          </div>
          {successNotice.activated ? (
            <p className="text-sm">
              Admin account <strong>{successNotice.email}</strong> is activated with your password.
              You can now sign in with tenant slug <code>{successNotice.slug}</code> and email <code>{successNotice.email}</code>.
            </p>
          ) : successNotice.token ? (
            <div className="space-y-2 text-sm">
              <p>
                Admin invited (<strong>{successNotice.email}</strong>). Since no password was set, use the invite token:
              </p>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  className="input font-mono text-xs flex-1"
                  value={successNotice.token}
                />
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    navigator.clipboard.writeText(successNotice.token || "");
                    alert("Token copied to clipboard!");
                  }}
                >
                  Copy Token
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    const url = `${window.location.origin}/accept-invite?token=${encodeURIComponent(successNotice.token || "")}`;
                    navigator.clipboard.writeText(url);
                    alert("Invite link copied to clipboard!");
                  }}
                >
                  Copy Link
                </button>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreate} className="card space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Create Tenant</h3>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </button>
          </div>
          {createError && <div className="alert-error">{createError}</div>}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="label">Tenant Name</label>
              <input
                required
                className="input"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Acme Corp"
              />
            </div>
            <div>
              <label className="label">Slug (URL-safe identifier)</label>
              <input
                required
                className="input"
                pattern="^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
                title="Lowercase alphanumeric and hyphens only, no leading/trailing hyphens"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="acme"
              />
            </div>
            <div>
              <label className="label">Initial Admin Email</label>
              <input
                required
                type="email"
                className="input"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                placeholder="admin@acme.com"
              />
            </div>
            <div>
              <label className="label">Initial Admin Name</label>
              <input
                type="text"
                className="input"
                value={adminName}
                onChange={(e) => setAdminName(e.target.value)}
                placeholder="Alice Admin (optional)"
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">
                Initial Admin Password <span className="text-[var(--muted)] font-normal">(optional, min 8 chars)</span>
              </label>
              <input
                type="password"
                className="input"
                minLength={8}
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="•••••••• (if provided, account is activated immediately)"
              />
              <p className="text-xs mt-1 text-[var(--muted)]">
                Provide a password to immediately activate the tenant admin account, or leave blank to send an invite token.
              </p>
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={createBusy}>
            {createBusy ? <span className="spinner spinner-sm" /> : "Create Tenant & Admin"}
          </button>
        </form>
      )}

      {error && <div className="alert-error">{error}</div>}

      {loading ? (
        <div className="flex justify-center p-8">
          <span className="spinner spinner-lg" />
        </div>
      ) : tenants.length === 0 ? (
        <div className="empty-state card">No tenants found.</div>
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
                <th>Status</th>
                <th>Trial Ends</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id}>
                  <td className="font-medium">{t.name}</td>
                  <td className="font-mono text-xs">{t.slug}</td>
                  <td>
                    {t.is_active ? (
                      <span
                        className={`badge ${
                          t.status === "trial_active" ? "badge-success" : "badge-danger"
                        }`}
                      >
                        {t.status === "trial_active" ? "Active" : "Trial Expired"}
                      </span>
                    ) : (
                      <span className="badge badge-neutral">Suspended</span>
                    )}
                  </td>
                  <td className="text-xs">
                    {new Date(t.trial_ends_at).toLocaleDateString()}
                  </td>
                  <td className="text-xs">
                    {new Date(t.created_at).toLocaleDateString()}
                  </td>
                  <td className="text-right">
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => onSelectTenant(t.slug)}
                    >
                      Manage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
