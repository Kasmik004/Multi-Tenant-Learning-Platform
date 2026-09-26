"use client";

import { useCallback, useEffect, useState } from "react";
import { useApiClient } from "@/hooks/useApiClient";
import { createApiClient, type Schemas } from "@/lib/api/client";
import { useAuth } from "@/features/auth/AuthProvider";

type TenantRead = Schemas["TenantRead"];
type UserRead = Schemas["UserRead"];
type CourseRead = Schemas["CourseRead"];

interface Props {
  slug: string;
  canManage: boolean;
  canDelete: boolean;
  isReadOnly: boolean;
  onBack: () => void;
}

export function TenantDetailPanel({ slug, canManage, canDelete, onBack }: Props) {
  const api = useApiClient();
  const { token } = useAuth();
  const [tenant, setTenant] = useState<TenantRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Invite state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [invitePassword, setInvitePassword] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [inviteActivated, setInviteActivated] = useState(false);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");
  
  // Trial state
  const [trialDays, setTrialDays] = useState(14);
  const [trialBusy, setTrialBusy] = useState(false);
  const [trialMsg, setTrialMsg] = useState("");

  useEffect(() => {
    async function fetchTenant() {
      const { data, error } = await api.GET("/api/v1/tenants/{slug}", {
        params: { path: { slug } },
      });
      if (error) {
        setError("Failed to load tenant details");
      } else if (data) {
        setTenant(data);
      }
      setLoading(false);
    }
    fetchTenant();
  }, [api, slug]);

  async function handleToggleStatus() {
    if (!tenant) return;
    const { data, error } = await api.PATCH("/api/v1/tenants/{slug}", {
      params: { path: { slug: tenant.slug } },
      body: { is_active: !tenant.is_active },
    });
    if (!error && data) {
      setTenant(data);
    }
  }

  async function handleDelete() {
    if (!tenant) return;
    if (!confirm(`Are you sure you want to permanently delete tenant '${tenant.name}'?`)) return;
    const { error } = await api.DELETE("/api/v1/tenants/{slug}", {
      params: { path: { slug: tenant.slug } },
    });
    if (!error) {
      onBack();
    }
  }

  async function handleExtendTrial(e: React.FormEvent) {
    e.preventDefault();
    if (!tenant) return;
    setTrialBusy(true);
    setTrialMsg("");
    const { data, error } = await api.POST("/api/v1/tenants/{slug}/trial", {
      params: { path: { slug: tenant.slug } },
      body: { days: trialDays },
    });
    setTrialBusy(false);
    if (error) {
      setTrialMsg("Failed to extend trial");
    } else if (data) {
      setTenant(data);
      setTrialMsg("Trial extended successfully");
      setTimeout(() => setTrialMsg(""), 3000);
    }
  }

  async function handleInviteAdmin(e: React.FormEvent) {
    e.preventDefault();
    if (!tenant) return;
    setInviteBusy(true);
    setInviteMsg("");
    setInviteToken("");
    setInviteActivated(false);
    
    const email = inviteEmail.trim().toLowerCase();
    const fullName = inviteName.trim() || email.split("@")[0];

    const { data, error } = await api.POST("/api/v1/users/invites", {
      body: { email, full_name: fullName, role: "tenantadmin" },
      headers: { "X-Tenant-Slug": tenant.slug },
    });
    
    if (error || !data) {
      setInviteBusy(false);
      const errBody = error as { error?: { message?: string } } | undefined;
      setInviteMsg(`Failed to invite: ${errBody?.error?.message || "Unknown error"}`);
      return;
    }

    let activated = false;
    if (invitePassword.length >= 8) {
      const { error: acceptErr } = await api.POST("/api/v1/auth/accept-invite", {
        body: {
          token: data.invite_token,
          password: invitePassword,
          confirm_password: invitePassword,
        },
      });

      if (acceptErr) {
        setInviteBusy(false);
        setInviteToken(data.invite_token);
        setInviteMsg(`Admin invited, but password setup failed. Invite token: ${data.invite_token}`);
        return;
      }
      activated = true;
    }

    setInviteBusy(false);
    setInviteToken(data.invite_token);
    setInviteActivated(activated);
    setInviteMsg(
      activated
        ? `Admin account '${email}' is activated! You can now log in using tenant '${tenant.slug}'.`
        : `Admin invited! An invite token was generated below.`
    );
    setInviteEmail("");
    setInviteName("");
    setInvitePassword("");
  }

  if (loading) return <div className="p-8 text-center"><span className="spinner spinner-lg inline-block" /></div>;
  if (error || !tenant) return <div className="alert-error">{error || "Not found"}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button className="btn btn-ghost" onClick={onBack}>&larr; Back</button>
        <h2 className="text-xl font-semibold">{tenant.name}</h2>
        <span className={`badge ${tenant.is_active ? (tenant.status === "trial_active" ? "badge-success" : "badge-danger") : "badge-neutral"}`}>
          {tenant.is_active ? (tenant.status === "trial_active" ? "Active Trial" : "Trial Expired") : "Suspended"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="card space-y-4">
          <h3 className="text-lg font-semibold">Tenant Info</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-[var(--muted)]">Slug</span><span className="font-mono">{tenant.slug}</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Created</span><span>{new Date(tenant.created_at).toLocaleString()}</span></div>
            <div className="flex justify-between"><span className="text-[var(--muted)]">Trial Ends</span><span>{new Date(tenant.trial_ends_at).toLocaleString()}</span></div>
            {tenant.expired_at && (
              <div className="flex justify-between"><span className="text-[var(--muted)]">Expired At</span><span>{new Date(tenant.expired_at).toLocaleString()}</span></div>
            )}
          </div>
          {canManage && (
            <div className="flex gap-2 pt-4">
              <button className="btn btn-ghost" onClick={handleToggleStatus}>
                {tenant.is_active ? "Suspend Tenant" : "Reactivate Tenant"}
              </button>
              {canDelete && (
                <button className="btn btn-danger" onClick={handleDelete}>Delete Tenant</button>
              )}
            </div>
          )}
        </div>

        {canManage && (
          <div className="card space-y-4">
            <h3 className="text-lg font-semibold">Extend Trial</h3>
            <form onSubmit={handleExtendTrial} className="space-y-4">
              {trialMsg && <div className={trialMsg.includes("Failed") ? "alert-error" : "alert-success"}>{trialMsg}</div>}
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <label className="label">Days to Extend</label>
                  <input type="number" min="1" max="365" className="input" value={trialDays} onChange={e => setTrialDays(Number(e.target.value))} required />
                </div>
                <button type="submit" className="btn btn-primary" disabled={trialBusy}>Extend</button>
              </div>
              <p className="text-xs text-[var(--muted)]">Adds to a running trial, or restarts an expired one from today.</p>
            </form>
          </div>
        )}

        {canManage && tenant.is_active && tenant.status === "trial_active" && (
          <div className="card space-y-4 md:col-span-2">
            <h3 className="text-lg font-semibold">Invite Tenant Admin</h3>
            <form onSubmit={handleInviteAdmin} className="space-y-4">
              {inviteMsg && (
                <div className={inviteMsg.includes("Failed") ? "alert-error" : "alert-success"}>
                  <p className="break-all">{inviteMsg}</p>
                </div>
              )}
              {/* Show generated token & copy buttons after successful invite */}
              {inviteToken && !inviteActivated && (
                <div className="flex items-center gap-2">
                  <input readOnly className="input font-mono text-xs flex-1" value={inviteToken} />
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => { navigator.clipboard.writeText(inviteToken); alert("Token copied!"); }}
                  >
                    Copy Token
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      const url = `${window.location.origin}/accept-invite?token=${encodeURIComponent(inviteToken)}`;
                      navigator.clipboard.writeText(url);
                      alert("Invite link copied!");
                    }}
                  >
                    Copy Link
                  </button>
                </div>
              )}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <label className="label">Email</label>
                  <input type="email" className="input" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} required />
                </div>
                <div>
                  <label className="label">Full Name</label>
                  <input type="text" className="input" value={inviteName} onChange={e => setInviteName(e.target.value)} required />
                </div>
                <div>
                  <label className="label">
                    Password <span className="text-[var(--muted)] font-normal">(optional, min 8)</span>
                  </label>
                  <input
                    type="password"
                    className="input"
                    minLength={8}
                    value={invitePassword}
                    onChange={e => setInvitePassword(e.target.value)}
                    placeholder="•••••••• (auto-activates)"
                  />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={inviteBusy}>
                {inviteBusy ? <span className="spinner spinner-sm" /> : "Invite Admin"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
