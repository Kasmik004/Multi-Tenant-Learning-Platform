"use client";

import { useCallback, useEffect, useState } from "react";
import { useApiClient } from "@/hooks/useApiClient";
import type { Schemas } from "@/lib/api/client";

type UserRead = Schemas["UserRead"];

export function TenantUsersPanel() {
  const api = useApiClient();
  const [users, setUsers] = useState<UserRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<"user" | "tenantadmin">("user");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");

  const fetchUsers = useCallback(async () => {
    const { data, error } = await api.GET("/api/v1/users");
    if (error) setError("Failed to load users");
    else if (data) {
      setUsers(data.items);
      setError("");
    }
    setLoading(false);
  }, [api]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchUsers();
  }, [fetchUsers]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setInviteBusy(true);
    setInviteMsg("");
    const { data, error } = await api.POST("/api/v1/users/invites", {
      body: { email: inviteEmail, full_name: inviteName, role: inviteRole },
    });
    setInviteBusy(false);
    
    if (error) {
      setInviteMsg(`Failed to invite user.`);
    } else if (data) {
      setInviteMsg(`Invite token generated: ${data.invite_token}`);
      setInviteEmail("");
      setInviteName("");
      fetchUsers();
    }
  }

  async function handleRemove(userId: string) {
    if (!confirm("Remove this user permanently?")) return;
    const { error } = await api.DELETE("/api/v1/users/{user_id}", {
      params: { path: { user_id: userId } },
    });
    if (!error) fetchUsers();
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Users</h2>

      <div className="card space-y-4">
        <h3 className="text-lg font-semibold">Invite User</h3>
        <form onSubmit={handleInvite} className="space-y-4">
          {inviteMsg && (
            <div className={inviteMsg.includes("Failed") ? "alert-error" : "alert-success"}>
              <p className="break-all">{inviteMsg}</p>
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
              <label className="label">Role</label>
              <select className="input" value={inviteRole} onChange={e => setInviteRole(e.target.value as "user" | "tenantadmin")}>
                <option value="user">Learner</option>
                <option value="tenantadmin">Tenant Admin</option>
              </select>
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={inviteBusy}>Invite</button>
        </form>
      </div>

      {error && <div className="alert-error">{error}</div>}

      {loading ? (
        <div className="flex justify-center p-8"><span className="spinner spinner-lg" /></div>
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Joined</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="font-medium">{u.full_name}</td>
                  <td>{u.email}</td>
                  <td><span className="badge badge-info">{u.tenant_role}</span></td>
                  <td>
                    {u.invite_pending ? <span className="badge badge-warning">Invited</span> : 
                     u.is_active ? <span className="badge badge-success">Active</span> : 
                     <span className="badge badge-neutral">Inactive</span>}
                  </td>
                  <td className="text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="text-right">
                    <button className="btn btn-ghost btn-sm text-red-500 hover:text-red-600" onClick={() => handleRemove(u.id)}>
                      Remove
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
